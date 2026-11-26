"""
Unified Feature Engineering Pipeline for AgriTwin Pakistan.
Ensures strict train/serve parity (Rule 9) across training, cross-validation, and live inference.

Calculates:
- 27-week temporal sequence (Nov 1 to May 10):
    1. GDD (T_base=5.0 C)
    2. Precipitation (mm/week)
    3. Mean Temperature (C)
    4. Max Temperature (C)
    5. Min Temperature (C)
    6. Solar Radiation (MJ/m^2/week)
    7. Vapor Pressure Deficit (VPD in kPa)
    8. Extreme Heat Days (count of T_max > 32 C per week)
    9. Interpolated Sentinel-2 NDVI
    10. Interpolated Sentinel-2 EVI
- Static soil & geospatial vector:
    1. Clay %
    2. Sand %
    3. Silt %
    4. Soil Organic Carbon (SOC %)
    5. Soil pH
    6. Bulk Density (g/cm^3)
    7. Total Available Water (TAW in mm/m)
    8. Latitude
    9. Longitude
- Tabular feature set for baseline models (Ridge, Random Forest, XGBoost):
    Full-season aggregates, 4 growth-stage aggregations, NDVI trajectory metrics, and soil features.
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from agritwin.core.config import DATA_DIR

logger = logging.getLogger(__name__)

# Constants
WHEAT_BASE_TEMP = 5.0  # Base temperature for wheat GDD (Celsius)
HEAT_STRESS_THRESHOLD = 32.0  # Threshold for extreme heat day (Celsius)
SEASON_WEEKS = 27  # Total weeks in Rabi wheat season (Nov 1 to May 10)
DAYS_PER_WEEK = 7

TEMPORAL_FEATURE_NAMES = [
    "gdd",
    "precipitation_mm",
    "temp_mean_c",
    "temp_max_c",
    "temp_min_c",
    "solar_radiation_mj",
    "vpd_kpa",
    "extreme_heat_days",
    "ndvi",
    "evi",
]

STATIC_FEATURE_NAMES = [
    "clay_pct",
    "sand_pct",
    "silt_pct",
    "soc_pct",
    "ph",
    "bulk_density",
    "taw_mm",
    "latitude",
    "longitude",
]


def calculate_daily_vpd(temp_c: float, rh_pct: float) -> float:
    """
    Calculate Vapor Pressure Deficit (VPD) in kPa from temperature (C) and relative humidity (%).
    Uses standard Tetens equation for saturation vapor pressure:
        e_s(T) = 0.61078 * exp((17.27 * T) / (T + 237.3))
        e_a = e_s * (RH / 100)
        VPD = max(0, e_s - e_a)
    """
    temp_c = float(temp_c)
    rh_pct = float(rh_pct)
    if rh_pct < 0.0:
        rh_pct = 0.0
    elif rh_pct > 100.0:
        rh_pct = 100.0

    e_s = 0.61078 * np.exp((17.27 * temp_c) / (temp_c + 237.3))
    e_a = e_s * (rh_pct / 100.0)
    vpd = max(0.0, float(e_s - e_a))
    return float(vpd)


def calculate_daily_gdd(t_max: float, t_min: float, t_base: float = WHEAT_BASE_TEMP) -> float:
    """
    Calculate Growing Degree Days (GDD) for a single day.
        GDD = max(0.0, ((T_max + T_min) / 2.0) - T_base)
    """
    t_mean = (float(t_max) + float(t_min)) / 2.0
    return max(0.0, float(t_mean - t_base))


class WheatFeaturePipeline:
    """
    Unified feature engineering pipeline for wheat yield prediction.
    Enforces strict train/serve parity by processing raw weather, soil, and satellite inputs
    into sequential tensors and tabular vectors identically.
    """

    def __init__(self) -> None:
        self.temporal_scaler: Optional[StandardScaler] = None
        self.static_scaler: Optional[StandardScaler] = None
        self.tabular_scaler: Optional[StandardScaler] = None
        self.tabular_feature_names: List[str] = []
        self._init_tabular_feature_names()

    def _init_tabular_feature_names(self) -> None:
        """Initialize list of tabular feature names for baseline tree and linear models."""
        names = [
            # Whole-season aggregates
            "total_gdd",
            "total_precipitation_mm",
            "mean_temp_c",
            "max_temp_c",
            "min_temp_c",
            "total_solar_radiation_mj",
            "mean_vpd_kpa",
            "total_heat_days",
            "grain_filling_heat_days",  # Weeks 16-22
            # NDVI Trajectory summary metrics
            "peak_ndvi",
            "peak_ndvi_week",
            "mean_ndvi",
            "integrated_ndvi",  # Area under NDVI curve
            "end_season_ndvi",
            "peak_evi",
            "mean_evi",
        ]
        # 4 Agronomic Growth Stages
        # Stage 1: Emergence & Tillering (Weeks 1 to 6)
        # Stage 2: Stem Elongation / Jointing (Weeks 7 to 12)
        # Stage 3: Heading & Flowering (Weeks 13 to 18)
        # Stage 4: Grain Filling & Ripening (Weeks 19 to 27)
        stages = [
            ("s1_tillering", 0, 6),
            ("s2_jointing", 6, 12),
            ("s3_flowering", 12, 18),
            ("s4_grain_filling", 18, 27),
        ]
        for prefix, _, _ in stages:
            names.extend([
                f"{prefix}_gdd",
                f"{prefix}_precipitation",
                f"{prefix}_mean_temp",
                f"{prefix}_mean_vpd",
                f"{prefix}_mean_ndvi",
                f"{prefix}_heat_days",
            ])

        # Static soil & geo features
        names.extend(STATIC_FEATURE_NAMES)
        self.tabular_feature_names = names

    def extract_temporal_matrix(
        self,
        weather_df: pd.DataFrame,
        satellite_df: pd.DataFrame,
        season_start_date: Optional[Union[str, datetime]] = None,
    ) -> np.ndarray:
        """
        Extract temporal matrix of shape (27, 10) representing the 27 weekly intervals of the Rabi season.

        Parameters:
            weather_df: Daily weather DataFrame with columns:
                ['date', 'temperature_2m_max', 'temperature_2m_min', 'temperature_2m_mean',
                 'precipitation_sum', 'shortwave_radiation_sum', 'relative_humidity_2m_mean']
            satellite_df: Weekly or periodic satellite DataFrame with columns:
                ['week' or 'date', 'ndvi_mean', 'evi']
            season_start_date: Start date of season (defaults to Nov 1 inferred from weather_df)

        Returns:
            np.ndarray of shape (27, 10) with float32 dtype.
        """
        df_w = weather_df.copy()
        df_w["date"] = pd.to_datetime(df_w["date"])
        df_w = df_w.sort_values("date").reset_index(drop=True)

        if season_start_date is None:
            # Nov 1 of the earliest year in df_w
            first_year = df_w["date"].iloc[0].year
            start_dt = pd.Timestamp(year=first_year, month=11, day=1)
        else:
            start_dt = pd.to_datetime(season_start_date)

        # Pre-compute daily VPD and GDD
        df_w["daily_gdd"] = [
            calculate_daily_gdd(tmax, tmin, WHEAT_BASE_TEMP)
            for tmax, tmin in zip(df_w["temperature_2m_max"], df_w["temperature_2m_min"])
        ]
        df_w["daily_vpd"] = [
            calculate_daily_vpd(tmean, rh)
            for tmean, rh in zip(df_w["temperature_2m_mean"], df_w["relative_humidity_2m_mean"])
        ]
        df_w["extreme_heat_day"] = (df_w["temperature_2m_max"] > HEAT_STRESS_THRESHOLD).astype(float)

        # Prepare satellite trajectory (aligned to 27 weeks)
        df_sat = satellite_df.copy()
        if "week" in df_sat.columns:
            df_sat = df_sat.sort_values("week").reset_index(drop=True)
            sat_ndvi = df_sat["ndvi_mean"].to_numpy()
            sat_evi = df_sat["evi"].to_numpy() if "evi" in df_sat.columns else sat_ndvi * 0.7
        else:
            df_sat["date"] = pd.to_datetime(df_sat["date"])
            df_sat = df_sat.sort_values("date").reset_index(drop=True)
            sat_ndvi = df_sat["ndvi_mean"].to_numpy()
            sat_evi = df_sat["evi"].to_numpy() if "evi" in df_sat.columns else sat_ndvi * 0.7

        # Ensure satellite has exactly 27 weekly steps via interpolation if needed
        if len(sat_ndvi) != SEASON_WEEKS:
            orig_indices = np.linspace(0, 1, len(sat_ndvi))
            target_indices = np.linspace(0, 1, SEASON_WEEKS)
            interp_ndvi = np.interp(target_indices, orig_indices, sat_ndvi)
            interp_evi = np.interp(target_indices, orig_indices, sat_evi)
        else:
            interp_ndvi = sat_ndvi
            interp_evi = sat_evi

        temporal_matrix = np.zeros((SEASON_WEEKS, len(TEMPORAL_FEATURE_NAMES)), dtype=np.float32)

        for w in range(SEASON_WEEKS):
            w_start = start_dt + timedelta(days=w * DAYS_PER_WEEK)
            w_end = w_start + timedelta(days=DAYS_PER_WEEK)

            mask = (df_w["date"] >= w_start) & (df_w["date"] < w_end)
            w_df = df_w.loc[mask]

            if len(w_df) == 0:
                # If window falls slightly outside weather range, impute with neighbor or mean
                w_df = df_w.iloc[min(w * DAYS_PER_WEEK, len(df_w) - 1): min((w + 1) * DAYS_PER_WEEK, len(df_w))]

            gdd_sum = float(w_df["daily_gdd"].sum()) if len(w_df) > 0 else 50.0
            precip_sum = float(w_df["precipitation_sum"].sum()) if len(w_df) > 0 else 0.0
            t_mean = float(w_df["temperature_2m_mean"].mean()) if len(w_df) > 0 else 18.0
            t_max = float(w_df["temperature_2m_max"].max()) if len(w_df) > 0 else 25.0
            t_min = float(w_df["temperature_2m_min"].min()) if len(w_df) > 0 else 10.0
            sol_rad = float(w_df["shortwave_radiation_sum"].sum()) if len(w_df) > 0 else 80.0
            vpd_mean = float(w_df["daily_vpd"].mean()) if len(w_df) > 0 else 1.2
            heat_days = float(w_df["extreme_heat_day"].sum()) if len(w_df) > 0 else 0.0

            ndvi_val = float(interp_ndvi[w])
            evi_val = float(interp_evi[w])

            temporal_matrix[w, 0] = gdd_sum
            temporal_matrix[w, 1] = precip_sum
            temporal_matrix[w, 2] = t_mean
            temporal_matrix[w, 3] = t_max
            temporal_matrix[w, 4] = t_min
            temporal_matrix[w, 5] = sol_rad
            temporal_matrix[w, 6] = vpd_mean
            temporal_matrix[w, 7] = heat_days
            temporal_matrix[w, 8] = ndvi_val
            temporal_matrix[w, 9] = evi_val

        return temporal_matrix

    def extract_static_vector(
        self,
        soil_profile: Dict[str, Any],
        latitude: float,
        longitude: float,
    ) -> np.ndarray:
        """
        Extract static feature vector of shape (9,) containing topsoil properties and coordinates.

        Parameters:
            soil_profile: Dictionary containing soil parameters:
                clay_percent, sand_percent, silt_percent, soc_percent, ph, bulk_density_g_cm3, taw_mm_m
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees

        Returns:
            np.ndarray of shape (9,) with float32 dtype.
        """
        vec = np.zeros(len(STATIC_FEATURE_NAMES), dtype=np.float32)
        vec[0] = float(soil_profile.get("clay_percent", 22.0))
        vec[1] = float(soil_profile.get("sand_percent", 35.0))
        vec[2] = float(soil_profile.get("silt_percent", 43.0))
        vec[3] = float(soil_profile.get("soc_percent", 0.65))
        vec[4] = float(soil_profile.get("ph", 7.8))
        vec[5] = float(soil_profile.get("bulk_density_g_cm3", 1.42))
        vec[6] = float(soil_profile.get("taw_mm_m", 145.0))
        vec[7] = float(latitude)
        vec[8] = float(longitude)
        return vec

    def extract_tabular_features(
        self,
        temporal_matrix: np.ndarray,
        static_vector: np.ndarray,
    ) -> np.ndarray:
        """
        Extract tabular 1D feature vector for tree and linear baseline models.
        Derives whole-season sums, phenological stage aggregations, and combines with static vector.

        Parameters:
            temporal_matrix: (27, 10) ndarray
            static_vector: (9,) ndarray

        Returns:
            np.ndarray of shape (len(tabular_feature_names),) with float32 dtype.
        """
        # Temporal indices:
        # 0: gdd, 1: precip, 2: t_mean, 3: t_max, 4: t_min, 5: sol_rad, 6: vpd, 7: heat_days, 8: ndvi, 9: evi
        gdd = temporal_matrix[:, 0]
        precip = temporal_matrix[:, 1]
        t_mean = temporal_matrix[:, 2]
        t_max = temporal_matrix[:, 3]
        t_min = temporal_matrix[:, 4]
        sol_rad = temporal_matrix[:, 5]
        vpd = temporal_matrix[:, 6]
        heat_days = temporal_matrix[:, 7]
        ndvi = temporal_matrix[:, 8]
        evi = temporal_matrix[:, 9]

        feats = [
            float(np.sum(gdd)),
            float(np.sum(precip)),
            float(np.mean(t_mean)),
            float(np.max(t_max)),
            float(np.min(t_min)),
            float(np.sum(sol_rad)),
            float(np.mean(vpd)),
            float(np.sum(heat_days)),
            float(np.sum(heat_days[15:22])),  # Grain filling weeks 16-22 (0-indexed 15..21)
            float(np.max(ndvi)),
            float(np.argmax(ndvi) + 1),  # Peak NDVI week (1 to 27)
            float(np.mean(ndvi)),
            float(np.trapezoid(ndvi) if hasattr(np, "trapezoid") else np.sum(ndvi)),  # Integrated NDVI
            float(ndvi[-1]),  # End season NDVI
            float(np.max(evi)),
            float(np.mean(evi)),
        ]

        # 4 Growth stages: (prefix, start_idx, end_idx)
        stages = [
            ("s1_tillering", 0, 6),
            ("s2_jointing", 6, 12),
            ("s3_flowering", 12, 18),
            ("s4_grain_filling", 18, 27),
        ]
        for _, s_start, s_end in stages:
            feats.extend([
                float(np.sum(gdd[s_start:s_end])),
                float(np.sum(precip[s_start:s_end])),
                float(np.mean(t_mean[s_start:s_end])),
                float(np.mean(vpd[s_start:s_end])),
                float(np.mean(ndvi[s_start:s_end])),
                float(np.sum(heat_days[s_start:s_end])),
            ])

        # Static soil & geo features
        feats.extend(static_vector.tolist())

        return np.array(feats, dtype=np.float32)

    def transform_sample(
        self,
        weather_df: pd.DataFrame,
        soil_profile: Dict[str, Any],
        satellite_df: pd.DataFrame,
        latitude: float,
        longitude: float,
        season_start_date: Optional[Union[str, datetime]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Transform a single instance (field or district season) into all feature representations.
        Returns dictionary with 'temporal', 'static', and 'tabular' feature arrays.
        """
        temp = self.extract_temporal_matrix(weather_df, satellite_df, season_start_date)
        stat = self.extract_static_vector(soil_profile, latitude, longitude)
        tab = self.extract_tabular_features(temp, stat)
        return {
            "temporal": temp,
            "static": stat,
            "tabular": tab,
        }

    def fit_scalers(
        self,
        temporal_array: np.ndarray,
        static_array: np.ndarray,
        tabular_array: np.ndarray,
    ) -> None:
        """
        Fit StandardScalers for temporal (N, 27, 10), static (N, 9), and tabular (N, M) arrays.
        Temporal scaler flattens over time steps to maintain feature scale consistency across weeks.
        """
        n_samples, n_weeks, n_temp_feats = temporal_array.shape
        flat_temporal = temporal_array.reshape(-1, n_temp_feats)

        self.temporal_scaler = StandardScaler()
        self.temporal_scaler.fit(flat_temporal)

        self.static_scaler = StandardScaler()
        self.static_scaler.fit(static_array)

        self.tabular_scaler = StandardScaler()
        self.tabular_scaler.fit(tabular_array)

    def scale_temporal(self, temporal_array: np.ndarray) -> np.ndarray:
        """Transform temporal tensor using fitted scaler."""
        if self.temporal_scaler is None:
            return temporal_array
        orig_shape = temporal_array.shape
        if len(orig_shape) == 2:  # Single sample (27, 10)
            scaled = self.temporal_scaler.transform(temporal_array)
            return scaled.astype(np.float32)
        elif len(orig_shape) == 3:  # Batch (N, 27, 10)
            n_samples, n_weeks, n_feats = orig_shape
            flat = temporal_array.reshape(-1, n_feats)
            scaled = self.temporal_scaler.transform(flat)
            return scaled.reshape(n_samples, n_weeks, n_feats).astype(np.float32)
        else:
            raise ValueError(f"Invalid temporal tensor shape: {orig_shape}")

    def scale_static(self, static_array: np.ndarray) -> np.ndarray:
        """Transform static vector or batch using fitted scaler."""
        if self.static_scaler is None:
            return static_array
        if len(static_array.shape) == 1:
            scaled = self.static_scaler.transform(static_array.reshape(1, -1))
            return scaled.squeeze(0).astype(np.float32)
        return self.static_scaler.transform(static_array).astype(np.float32)

    def scale_tabular(self, tabular_array: np.ndarray) -> np.ndarray:
        """Transform tabular vector or batch using fitted scaler."""
        if self.tabular_scaler is None:
            return tabular_array
        if len(tabular_array.shape) == 1:
            scaled = self.tabular_scaler.transform(tabular_array.reshape(1, -1))
            return scaled.squeeze(0).astype(np.float32)
        return self.tabular_scaler.transform(tabular_array).astype(np.float32)

    def save_pipeline(self, filepath: Union[str, Path]) -> None:
        """Serialize fitted pipeline and scalers to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            pickle.dump({
                "temporal_scaler": self.temporal_scaler,
                "static_scaler": self.static_scaler,
                "tabular_scaler": self.tabular_scaler,
                "tabular_feature_names": self.tabular_feature_names,
            }, f)
        logger.info(f"Saved feature pipeline to {filepath}")

    @classmethod
    def load_pipeline(cls, filepath: Union[str, Path]) -> "WheatFeaturePipeline":
        """Load serialized pipeline and scalers from disk."""
        filepath = Path(filepath)
        pipeline = cls()
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        pipeline.temporal_scaler = data["temporal_scaler"]
        pipeline.static_scaler = data["static_scaler"]
        pipeline.tabular_scaler = data["tabular_scaler"]
        pipeline.tabular_feature_names = data["tabular_feature_names"]
        logger.info(f"Loaded feature pipeline from {filepath}")
        return pipeline
