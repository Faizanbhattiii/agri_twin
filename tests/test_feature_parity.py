"""
Unit and Parity Tests for Unified Feature Engineering Pipeline (agritwin/features/pipeline.py).
Enforces Rule 7 (run tests, report truthfully) and Rule 9 (Train/serve parity).
"""

import numpy as np
import pandas as pd
import pytest

from agritwin.features.pipeline import (
    HEAT_STRESS_THRESHOLD,
    SEASON_WEEKS,
    STATIC_FEATURE_NAMES,
    TEMPORAL_FEATURE_NAMES,
    WHEAT_BASE_TEMP,
    WheatFeaturePipeline,
    calculate_daily_gdd,
    calculate_daily_vpd,
)


def create_mock_environmental_data():
    """Create reproducible mock weather, soil, and satellite data for testing."""
    dates = pd.date_range("2022-11-01", periods=SEASON_WEEKS * 7, freq="D")
    df_weather = pd.DataFrame({
        "date": dates,
        "temperature_2m_max": 25.0 + 10.0 * np.sin(np.linspace(0, np.pi, len(dates))),
        "temperature_2m_min": 10.0 + 8.0 * np.sin(np.linspace(0, np.pi, len(dates))),
        "temperature_2m_mean": 17.5 + 9.0 * np.sin(np.linspace(0, np.pi, len(dates))),
        "precipitation_sum": np.random.RandomState(42).choice([0.0, 0.0, 5.0, 12.0], size=len(dates)),
        "shortwave_radiation_sum": 15.0 + np.random.RandomState(42).rand(len(dates)) * 5.0,
        "relative_humidity_2m_mean": 60.0 + np.random.RandomState(42).randn(len(dates)) * 10.0,
        "source": "mock",
    })

    soil_profile = {
        "clay_percent": 24.5,
        "sand_percent": 38.0,
        "silt_percent": 37.5,
        "soc_percent": 0.72,
        "ph": 7.9,
        "bulk_density_g_cm3": 1.41,
        "taw_mm_m": 138.0,
        "source": "mock",
    }

    weeks = np.arange(1, SEASON_WEEKS + 1)
    df_sat = pd.DataFrame({
        "week": weeks,
        "ndvi_mean": 0.15 + 0.65 * np.exp(-((weeks - 14) ** 2) / 32.0),
        "evi": 0.10 + 0.45 * np.exp(-((weeks - 14) ** 2) / 32.0),
        "source": "mock",
    })

    return df_weather, soil_profile, df_sat


def test_gdd_calculation():
    """Verify GDD calculation against agronomic reference values."""
    # Under base temperature
    assert calculate_daily_gdd(t_max=4.0, t_min=2.0, t_base=5.0) == 0.0
    # Exactly at base temperature
    assert calculate_daily_gdd(t_max=6.0, t_min=4.0, t_base=5.0) == 0.0
    # Normal temperature: mean = (24 + 10) / 2 = 17 -> GDD = 17 - 5 = 12
    assert calculate_daily_gdd(t_max=24.0, t_min=10.0, t_base=5.0) == 12.0


def test_vpd_calculation():
    """Verify VPD calculation follows Tetens formula and bounds."""
    # 100% relative humidity -> VPD must be 0
    vpd_sat = calculate_daily_vpd(temp_c=25.0, rh_pct=100.0)
    assert pytest.approx(vpd_sat, abs=1e-4) == 0.0

    # Hot and dry -> high VPD
    vpd_dry = calculate_daily_vpd(temp_c=35.0, rh_pct=20.0)
    assert vpd_dry > 3.0  # Around 4.5 kPa

    # Non-negative constraint
    assert calculate_daily_vpd(temp_c=10.0, rh_pct=110.0) == 0.0


def test_temporal_feature_extraction_shape():
    """Verify temporal tensor shape is exactly (27, 10)."""
    df_w, soil, df_sat = create_mock_environmental_data()
    pipeline = WheatFeaturePipeline()
    matrix = pipeline.extract_temporal_matrix(df_w, df_sat, season_start_date="2022-11-01")

    assert matrix.shape == (27, 10)
    assert matrix.dtype == np.float32
    assert not np.isnan(matrix).any()


def test_static_feature_vector_shape():
    """Verify static feature vector shape is exactly (9,)."""
    _, soil, _ = create_mock_environmental_data()
    pipeline = WheatFeaturePipeline()
    vec = pipeline.extract_static_vector(soil, latitude=31.4289, longitude=73.0782)

    assert vec.shape == (9,)
    assert vec.dtype == np.float32
    assert not np.isnan(vec).any()
    assert vec[0] == 24.5  # clay
    assert vec[7] == 31.4289  # lat


def test_tabular_features_parity():
    """Verify tabular feature derivation produces non-empty, expected feature count."""
    df_w, soil, df_sat = create_mock_environmental_data()
    pipeline = WheatFeaturePipeline()
    sample = pipeline.transform_sample(df_w, soil, df_sat, latitude=31.4, longitude=73.1, season_start_date="2022-11-01")

    assert "temporal" in sample
    assert "static" in sample
    assert "tabular" in sample
    assert sample["tabular"].shape == (len(pipeline.tabular_feature_names),)
    assert not np.isnan(sample["tabular"]).any()


def test_train_serve_parity_identical_outputs():
    """Verify identical outputs when processing same instance twice (strict parity)."""
    df_w, soil, df_sat = create_mock_environmental_data()
    pipeline1 = WheatFeaturePipeline()
    pipeline2 = WheatFeaturePipeline()

    sample1 = pipeline1.transform_sample(df_w, soil, df_sat, latitude=31.4187, longitude=73.0791)
    sample2 = pipeline2.transform_sample(df_w, soil, df_sat, latitude=31.4187, longitude=73.0791)

    np.testing.assert_array_almost_equal(sample1["temporal"], sample2["temporal"])
    np.testing.assert_array_almost_equal(sample1["static"], sample2["static"])
    np.testing.assert_array_almost_equal(sample1["tabular"], sample2["tabular"])
