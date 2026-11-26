"""
Unit tests for Machine Learning & Deep Learning models:
- DeepAgroNet forward pass, uncertainty bounds, and attention weights.
- Ridge, Random Forest, and XGBoost baseline regressors.
- Metric calculations and unit conversions.
"""

import numpy as np
import pytest
import torch

from agritwin.models.baselines import (
    BaselineRandomForest,
    BaselineRidge,
    BaselineXGBoost,
)
from agritwin.models.deepagronet import DeepAgroNet, gaussian_nll_loss
from agritwin.models.metrics import (
    calculate_metrics,
    to_kg_per_ha,
    to_maund_per_acre,
)


def test_metric_calculations():
    """Verify R2, RMSE, MAE, MBE, and unit conversions."""
    y_true = np.array([3000.0, 3500.0, 4000.0, 3200.0])
    y_pred = np.array([2900.0, 3600.0, 3950.0, 3150.0])

    m = calculate_metrics(y_true, y_pred)
    assert m["r2"] > 0.90
    assert m["rmse"] > 0.0
    assert m["mae"] > 0.0
    assert abs(m["mbe"]) < 100.0  # low bias

    # Maund conversion: 3500 kg/ha -> ~35.41 maund/acre
    maund = to_maund_per_acre(3500.0)
    assert pytest.approx(maund, rel=1e-3) == 35.41
    # Inverse conversion
    assert pytest.approx(to_kg_per_ha(maund), rel=1e-4) == 3500.0


def test_deepagronet_forward_pass_and_shapes():
    """Verify DeepAgroNet forward pass output shapes and uncertainty bounds."""
    batch_size = 4
    seq_len = 27
    n_temp = 10
    n_stat = 9

    model = DeepAgroNet(
        num_temporal_features=n_temp,
        num_static_features=n_stat,
        cnn_channels=16,
        lstm_hidden=32,
        lstm_layers=1,
        static_hidden=16,
        fusion_hidden=32,
    )

    temp_x = torch.randn(batch_size, seq_len, n_temp)
    stat_x = torch.randn(batch_size, n_stat)

    mu, sigma, attn = model(temp_x, stat_x)

    assert mu.shape == (batch_size, 1)
    assert sigma.shape == (batch_size, 1)
    assert attn.shape == (batch_size, seq_len)
    # Sigma must be strictly positive
    assert (sigma > 0).all()
    # Attention weights per sequence must sum to ~1.0
    attn_sums = attn.sum(dim=1)
    for s in attn_sums:
        assert pytest.approx(float(s), abs=1e-4) == 1.0


def test_deepagronet_predict_yield_helper():
    """Verify predict_yield returns correct keys, bounds, and conversions."""
    model = DeepAgroNet(cnn_channels=16, lstm_hidden=32, lstm_layers=1)
    temp_x = torch.randn(2, 27, 10)
    stat_x = torch.randn(2, 9)

    out = model.predict_yield(temp_x, stat_x)

    assert "yield_kgha" in out
    assert "lower_kgha" in out
    assert "upper_kgha" in out
    assert "yield_maund_acre" in out
    assert "lower_maund_acre" in out
    assert "upper_maund_acre" in out
    assert (out["upper_kgha"] >= out["lower_kgha"]).all()
    assert (out["upper_maund_acre"] >= out["lower_maund_acre"]).all()


def test_baseline_models_fit_and_predict():
    """Verify Ridge, Random Forest, and XGBoost training and prediction on synthetic tabular data."""
    rng = np.random.RandomState(42)
    n_samples, n_features = 60, 49
    X = rng.randn(n_samples, n_features).astype(np.float32)
    # Target = linear combination + noise
    y = 3000.0 + 150.0 * X[:, 0] - 80.0 * X[:, 1] + rng.randn(n_samples) * 30.0

    # 1. Ridge
    ridge = BaselineRidge()
    ridge.fit(X, y)
    p_ridge = ridge.predict(X[:5])
    assert len(p_ridge) == 5
    assert p_ridge.dtype == np.float32

    # 2. Random Forest
    rf = BaselineRandomForest(n_estimators=20, max_depth=5)
    rf.fit(X, y)
    p_rf = rf.predict(X[:5])
    assert len(p_rf) == 5
    assert len(rf.feature_importances_) == n_features

    # 3. XGBoost
    xgb_m = BaselineXGBoost(n_estimators=20, max_depth=3)
    xgb_m.fit(X, y)
    p_xgb = xgb_m.predict(X[:5])
    assert len(p_xgb) == 5
    assert len(xgb_m.feature_importances_) == n_features
