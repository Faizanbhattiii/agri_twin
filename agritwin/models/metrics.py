"""
Evaluation metrics for wheat yield regression models.
Calculates R^2, RMSE, MAE, MBE, and rRMSE.
Handles conversions between kg/ha and maund/acre (1 maund/acre = 98.8418 kg/ha).
"""

from typing import Dict, Union
import numpy as np


MAUND_ACRE_TO_KG_HA = 98.8418
KG_HA_TO_MAUND_ACRE = 1.0 / MAUND_ACRE_TO_KG_HA


def calculate_metrics(
    y_true: Union[np.ndarray, list],
    y_pred: Union[np.ndarray, list],
) -> Dict[str, float]:
    """
    Calculate standard agronomic regression metrics.

    Parameters:
        y_true: Ground truth target values
        y_pred: Predicted target values

    Returns:
        Dict containing:
            - r2: Coefficient of determination
            - rmse: Root Mean Square Error
            - mae: Mean Absolute Error
            - mbe: Mean Bias Error (positive = overestimation, negative = underestimation)
            - rrmse_pct: Relative RMSE (%) = (RMSE / y_mean) * 100
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)

    if len(y_t) == 0:
        return {"r2": 0.0, "rmse": 0.0, "mae": 0.0, "mbe": 0.0, "rrmse_pct": 0.0}

    ss_res = np.sum((y_t - y_p) ** 2)
    ss_tot = np.sum((y_t - np.mean(y_t)) ** 2)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0

    rmse = float(np.sqrt(np.mean((y_t - y_p) ** 2)))
    mae = float(np.mean(np.abs(y_t - y_p)))
    mbe = float(np.mean(y_p - y_t))

    mean_true = float(np.mean(y_t))
    rrmse_pct = float((rmse / mean_true) * 100.0) if abs(mean_true) > 1e-9 else 0.0

    return {
        "r2": float(r2),
        "rmse": rmse,
        "mae": mae,
        "mbe": mbe,
        "rrmse_pct": rrmse_pct,
    }


def to_maund_per_acre(yield_kgha: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert yield from kg/ha to maund/acre."""
    return yield_kgha * KG_HA_TO_MAUND_ACRE


def to_kg_per_ha(yield_maund_acre: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert yield from maund/acre to kg/ha."""
    return yield_maund_acre * MAUND_ACRE_TO_KG_HA
