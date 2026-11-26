"""
Machine learning & Deep learning models for crop yield forecasting.
Includes:
- DeepAgroNet: 1D-CNN + BiLSTM + Attention + Soil MLP
- BaselineRidge: Regularized linear model
- BaselineRandomForest: Random Forest Regressor
- BaselineXGBoost: Gradient Boosted Trees Regressor
- Regression metrics and unit conversion utilities
"""

from agritwin.models.deepagronet import DeepAgroNet, gaussian_nll_loss
from agritwin.models.baselines import (
    BaselineRidge,
    BaselineRandomForest,
    BaselineXGBoost,
)
from agritwin.models.metrics import (
    calculate_metrics,
    to_maund_per_acre,
    to_kg_per_ha,
    MAUND_ACRE_TO_KG_HA,
    KG_HA_TO_MAUND_ACRE,
)

__all__ = [
    "DeepAgroNet",
    "gaussian_nll_loss",
    "BaselineRidge",
    "BaselineRandomForest",
    "BaselineXGBoost",
    "calculate_metrics",
    "to_maund_per_acre",
    "to_kg_per_ha",
    "MAUND_ACRE_TO_KG_HA",
    "KG_HA_TO_MAUND_ACRE",
]
