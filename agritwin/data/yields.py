"""
District-level wheat yield data loader and validator for Punjab, Pakistan.
Data source: Punjab Crop Reporting Service (CRS) records (2013-14 to 2022-23).
"""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from agritwin.core.config import DATA_DIR, maund_per_acre_to_kg_per_ha, kg_per_ha_to_maund_per_acre

YIELDS_CSV_PATH = DATA_DIR / "raw" / "punjab_wheat_yields_2013_2023.csv"


class YieldDataLoader:
    """Manages loading, filtering, and querying Punjab wheat yield statistics."""

    def __init__(self, csv_path: Optional[Path] = None):
        self.csv_path = csv_path or YIELDS_CSV_PATH
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Yields dataset not found at {self.csv_path}")
        self._df = pd.read_csv(self.csv_path)
        self._validate_schema()

    def _validate_schema(self) -> None:
        """Validate required columns and non-null constraints."""
        required_cols = [
            "season", "season_year", "district", "division",
            "latitude", "longitude", "area_thousand_acres",
            "production_thousand_tonnes", "yield_maund_per_acre",
            "yield_kg_per_ha", "source"
        ]
        missing = [c for c in required_cols if c not in self._df.columns]
        if missing:
            raise ValueError(f"Yields dataset missing required columns: {missing}")

        if self._df.isnull().any().any():
            raise ValueError("Yields dataset contains unexpected null values.")

    def get_all(self) -> pd.DataFrame:
        """Return the entire dataset."""
        return self._df.copy()

    def get_districts(self) -> List[str]:
        """Return list of distinct districts available in dataset."""
        return sorted(self._df["district"].unique().tolist())

    def get_seasons(self) -> List[str]:
        """Return list of distinct seasons available in dataset."""
        return sorted(self._df["season"].unique().tolist())

    def get_district_series(self, district: str) -> pd.DataFrame:
        """Get chronological yield history for a specific district."""
        df_dist = self._df[self._df["district"].str.lower() == district.lower()]
        if df_dist.empty:
            raise KeyError(f"District '{district}' not found in dataset.")
        return df_dist.sort_values("season_year").reset_index(drop=True)

    def get_season_snapshot(self, season: str) -> pd.DataFrame:
        """Get cross-sectional yield statistics for all districts in a single season."""
        df_season = self._df[self._df["season"] == season]
        if df_season.empty:
            raise KeyError(f"Season '{season}' not found in dataset.")
        return df_season.reset_index(drop=True)

    def get_district_baseline(self, district: str) -> Dict[str, float]:
        """Compute long-term historical mean and standard deviation of yield for a district."""
        df_dist = self.get_district_series(district)
        return {
            "mean_yield_kgha": float(df_dist["yield_kg_per_ha"].mean()),
            "std_yield_kgha": float(df_dist["yield_kg_per_ha"].std()),
            "mean_yield_maund_acre": float(df_dist["yield_maund_per_acre"].mean()),
            "std_yield_maund_acre": float(df_dist["yield_maund_per_acre"].std()),
            "min_yield_kgha": float(df_dist["yield_kg_per_ha"].min()),
            "max_yield_kgha": float(df_dist["yield_kg_per_ha"].max()),
        }
