"""
Unified feature engineering pipeline for train and serve parity.
"""

from agritwin.features.pipeline import (
    WheatFeaturePipeline,
    calculate_daily_gdd,
    calculate_daily_vpd,
    TEMPORAL_FEATURE_NAMES,
    STATIC_FEATURE_NAMES,
    WHEAT_BASE_TEMP,
    HEAT_STRESS_THRESHOLD,
    SEASON_WEEKS,
)
from agritwin.features.dataset import PunjabWheatDataset

__all__ = [
    "WheatFeaturePipeline",
    "PunjabWheatDataset",
    "calculate_daily_gdd",
    "calculate_daily_vpd",
    "TEMPORAL_FEATURE_NAMES",
    "STATIC_FEATURE_NAMES",
    "WHEAT_BASE_TEMP",
    "HEAT_STRESS_THRESHOLD",
    "SEASON_WEEKS",
]
