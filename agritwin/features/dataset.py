"""
Dataset extraction and caching for Punjab Wheat Yields (2013-2023).
Processes 36 districts across 10 seasons using the unified WheatFeaturePipeline.
Provides train/val/test splits, Leave-One-Season-Out (LOSO), and Leave-Districts-Out (LDO) cross-validation iterators.
"""

import concurrent.futures
import logging
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

import numpy as np
import pandas as pd

from agritwin.core.config import DATA_DIR
from agritwin.data.satellite import SatelliteClient
from agritwin.data.soil import SoilGridsClient
from agritwin.data.weather import WeatherClient
from agritwin.features.pipeline import (
    STATIC_FEATURE_NAMES,
    TEMPORAL_FEATURE_NAMES,
    WheatFeaturePipeline,
)

logger = logging.getLogger(__name__)

RAW_YIELDS_CSV = DATA_DIR / "raw" / "punjab_wheat_yields_2013_2023.csv"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_CACHE_PATH = PROCESSED_DIR / "punjab_wheat_features.npz"
METADATA_CACHE_PATH = PROCESSED_DIR / "punjab_wheat_metadata.csv"


class PunjabWheatDataset:
    """
    Manages loading, feature extraction, caching, and cross-validation splitting
    for Punjab Wheat historical yield dataset (36 districts x 10 seasons = 360 samples).
    """

    def __init__(
        self,
        raw_csv_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
        recompute: bool = False,
    ) -> None:
        self.raw_csv_path = raw_csv_path or RAW_YIELDS_CSV
        self.cache_dir = cache_dir or PROCESSED_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.recompute = recompute

        self.pipeline = WheatFeaturePipeline()
        self.weather_client = WeatherClient()
        self.soil_client = SoilGridsClient()
        self.satellite_client = SatelliteClient()

        self.temporal_features: np.ndarray = np.array([])
        self.static_features: np.ndarray = np.array([])
        self.tabular_features: np.ndarray = np.array([])
        self.yield_kgha: np.ndarray = np.array([])
        self.yield_maund: np.ndarray = np.array([])
        self.metadata: pd.DataFrame = pd.DataFrame()

        self.load_or_build()

    def load_or_build(self) -> None:
        """Load extracted features from cache if available, otherwise compute from raw data."""
        npz_path = self.cache_dir / "punjab_wheat_features.npz"
        meta_path = self.cache_dir / "punjab_wheat_metadata.csv"

        if not self.recompute and npz_path.exists() and meta_path.exists():
            data = np.load(npz_path)
            self.temporal_features = data["temporal"]
            self.static_features = data["static"]
            self.tabular_features = data["tabular"]
            self.yield_kgha = data["yield_kgha"]
            self.yield_maund = data["yield_maund"]
            self.metadata = pd.read_csv(meta_path)
            return

        self._build_dataset()

    def _process_single_row(self, row_data: Tuple[int, pd.Series, Dict[str, Dict]]) -> Dict:
        """Process a single district-season row into feature representations."""
        idx, row, soil_cache = row_data
        district = row["district"]
        season_year = int(row["season_year"])
        season_str = row["season"]
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        y_kgha = float(row["yield_kg_per_ha"])
        y_maund = float(row["yield_maund_per_acre"])

        # 1. Soil from cache
        soil_profile = soil_cache[district]

        # 2. Weather season window: Nov 1 (year - 1) to May 10 (year)
        start_date = f"{season_year - 1}-11-01"
        end_date = f"{season_year}-05-10"
        df_weather = self.weather_client.get_historical_daily(
            latitude=lat,
            longitude=lon,
            start_date=start_date,
            end_date=end_date,
            use_cache=True,
        )

        # 3. Satellite NDVI trajectory
        df_sat = self.satellite_client.get_seasonal_ndvi(
            target_id=f"district-{district.lower().replace(' ', '-')}",
            season_year=season_year,
            latitude=lat,
            longitude=lon,
            use_cache=True,
        )

        # 4. Extract features via unified pipeline (Train/Serve Parity)
        sample_feats = self.pipeline.transform_sample(
            weather_df=df_weather,
            soil_profile=soil_profile,
            satellite_df=df_sat,
            latitude=lat,
            longitude=lon,
            season_start_date=start_date,
        )

        meta = {
            "sample_idx": idx,
            "season": season_str,
            "season_year": season_year,
            "district": district,
            "division": row["division"],
            "latitude": lat,
            "longitude": lon,
            "area_thousand_acres": row.get("area_thousand_acres", 0.0),
            "production_thousand_tonnes": row.get("production_thousand_tonnes", 0.0),
            "yield_kg_per_ha": y_kgha,
            "yield_maund_per_acre": y_maund,
            "weather_source": df_weather["source"].iloc[0] if "source" in df_weather.columns else "unknown",
        }

        return {
            "sample_idx": idx,
            "temporal": sample_feats["temporal"],
            "static": sample_feats["static"],
            "tabular": sample_feats["tabular"],
            "yield_kgha": y_kgha,
            "yield_maund": y_maund,
            "meta": meta,
        }

    def _build_dataset(self) -> None:
        """Process raw yield records and extract temporal, static, and tabular features in parallel."""
        if not self.raw_csv_path.exists():
            raise FileNotFoundError(f"Raw yield data not found at {self.raw_csv_path}")

        df_raw = pd.read_csv(self.raw_csv_path)

        # Pre-populate soil cache for 36 unique districts
        soil_cache: Dict[str, Dict] = {}
        unique_districts = df_raw.drop_duplicates(subset=["district"])[["district", "latitude", "longitude"]]
        for _, d_row in unique_districts.iterrows():
            d_name = d_row["district"]
            soil_cache[d_name] = self.soil_client.get_soil_profile(
                float(d_row["latitude"]), float(d_row["longitude"]), use_cache=True
            )

        tasks = [(idx, row, soil_cache) for idx, row in df_raw.iterrows()]
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_idx = {executor.submit(self._process_single_row, task): task[0] for task in tasks}
            for future in concurrent.futures.as_completed(future_to_idx):
                res = future.result()
                results.append(res)

        # Sort results back to original row order
        results.sort(key=lambda r: r["sample_idx"])

        temporal_list = [r["temporal"] for r in results]
        static_list = [r["static"] for r in results]
        tabular_list = [r["tabular"] for r in results]
        yield_kgha_list = [r["yield_kgha"] for r in results]
        yield_maund_list = [r["yield_maund"] for r in results]
        meta_records = [r["meta"] for r in results]

        self.temporal_features = np.stack(temporal_list, axis=0).astype(np.float32)
        self.static_features = np.stack(static_list, axis=0).astype(np.float32)
        self.tabular_features = np.stack(tabular_list, axis=0).astype(np.float32)
        self.yield_kgha = np.array(yield_kgha_list, dtype=np.float32)
        self.yield_maund = np.array(yield_maund_list, dtype=np.float32)
        self.metadata = pd.DataFrame(meta_records)

        # Save to disk cache
        npz_path = self.cache_dir / "punjab_wheat_features.npz"
        meta_path = self.cache_dir / "punjab_wheat_metadata.csv"
        np.savez_compressed(
            npz_path,
            temporal=self.temporal_features,
            static=self.static_features,
            tabular=self.tabular_features,
            yield_kgha=self.yield_kgha,
            yield_maund=self.yield_maund,
        )
        self.metadata.to_csv(meta_path, index=False)

    def get_loso_splits(self) -> Generator[Tuple[np.ndarray, np.ndarray, int], None, None]:
        """
        Leave-One-Season-Out (LOSO) Cross-Validation generator.
        Yields (train_indices, test_indices, test_season_year).
        Guarantees temporal out-of-sample evaluation across all 10 seasons (2014-2023).
        """
        unique_years = sorted(self.metadata["season_year"].unique())
        for year in unique_years:
            test_mask = (self.metadata["season_year"] == year).to_numpy()
            train_mask = ~test_mask
            train_idx = np.where(train_mask)[0]
            test_idx = np.where(test_mask)[0]
            yield train_idx, test_idx, int(year)

    def get_ldo_splits(self, n_splits: int = 5, seed: int = 42) -> Generator[Tuple[np.ndarray, np.ndarray, List[str]], None, None]:
        """
        Leave-Districts-Out (LDO) Cross-Validation generator.
        Evaluates geographic generalization by holding out entire districts.
        """
        unique_districts = np.array(sorted(self.metadata["district"].unique()))
        rng = np.random.RandomState(seed)
        shuffled = unique_districts.copy()
        rng.shuffle(shuffled)
        district_folds = np.array_split(shuffled, n_splits)

        for fold_districts in district_folds:
            test_mask = self.metadata["district"].isin(fold_districts).to_numpy()
            train_mask = ~test_mask
            train_idx = np.where(train_mask)[0]
            test_idx = np.where(test_mask)[0]
            yield train_idx, test_idx, fold_districts.tolist()
