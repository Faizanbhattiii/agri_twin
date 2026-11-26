"""
Unit and Integration Tests for Phase 6: Climate-Risk "What-If" Scenario Simulator.
Verifies sensitivity, stress indices, physics-based water balance, and FastAPI endpoints.
"""

import time
import pytest
from fastapi.testclient import TestClient

from agritwin.api.app import app
from agritwin.simulator.what_if import PRESET_SCENARIOS, WhatIfSimulator


@pytest.fixture(scope="module")
def simulator():
    """Shared WhatIfSimulator instance for fast test execution."""
    return WhatIfSimulator()


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_scenario_presets_structure():
    """Test that all scenario presets have required metadata and bilingual fields."""
    assert len(PRESET_SCENARIOS) >= 5

    required_keys = {
        "id",
        "name_en",
        "name_ur",
        "description_en",
        "description_ur",
        "temp_delta_c",
        "precip_factor",
        "irrigation_delay_days",
        "target_stage",
    }
    for preset in PRESET_SCENARIOS:
        missing = required_keys - set(preset.keys())
        assert not missing, f"Preset {preset.get('id')} missing keys: {missing}"
        assert len(preset["name_en"]) > 0
        assert len(preset["name_ur"]) > 0


def test_whatif_simulator_baseline_run(simulator):
    """Test that running the baseline scenario produces 0 delta and valid uncertainty bounds."""
    res = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=0.0,
        precip_factor=1.0,
        irrigation_delay_days=0,
        target_stage="all",
        model_name="deepagronet",
    )

    assert res["district_id"] == "faisalabad"
    assert res["model_used"] == "deepagronet"
    assert pytest.approx(res["delta_pct"], abs=0.01) == 0.0
    assert pytest.approx(res["delta_kgha"], abs=1.0) == 0.0

    base_yield = res["baseline_yield_kgha"]
    assert 2000.0 <= base_yield <= 5000.0, f"Unrealistic baseline yield: {base_yield}"

    # Check uncertainty bounds
    bounds = res["uncertainty_bounds"]
    assert bounds is not None
    assert bounds["base_lower_kgha"] <= base_yield <= bounds["base_upper_kgha"]
    assert bounds["sigma_kgha"] > 0.0

    # Check 27-week trajectory
    traj = res["weekly_trajectory"]
    assert len(traj) == 27
    assert all(1 <= pt["week"] <= 27 for pt in traj)


def test_terminal_heatwave_sensitivity(simulator):
    """
    Test that a severe terminal heatwave (+3.5C during March grain filling)
    reduces yield, increases heat stress hours, and produces severe rating.
    """
    res = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=3.5,
        precip_factor=1.0,
        irrigation_delay_days=0,
        target_stage="grain_filling",
        model_name="deepagronet",
    )

    # Agronomic expectation: Terminal heat stress depresses grain yield
    assert res["delta_pct"] < 0.0, f"Expected yield drop, got delta_pct={res['delta_pct']}"
    assert res["delta_kgha"] < 0.0
    assert res["delta_maund_acre"] < 0.0

    stress = res["stress_indices"]
    assert stress["grain_filling_heat_days"] > 0
    assert stress["heat_stress_hours"] > 0.0
    assert stress["terminal_heat_shock_severity"] in ["MODERATE", "SEVERE", "EXTREME"]

    # Verify bilingual mitigation advice is populated
    assert len(res["mitigation_advice_en"]) > 20
    assert len(res["mitigation_advice_ur"]) > 20
    assert "پوٹاشیم" in res["mitigation_advice_ur"] or "گرمی" in res["mitigation_advice_ur"]


def test_drought_and_irrigation_delay_water_stress(simulator):
    """
    Test that severe drought (-70% precipitation) combined with a 14-day irrigation delay
    accumulates water deficit stress days and degrades soil moisture.
    """
    res = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=0.0,
        precip_factor=0.3,
        irrigation_delay_days=14,
        target_stage="all",
        model_name="deepagronet",
    )

    stress = res["stress_indices"]
    assert stress["water_deficit_stress_days"] > 0
    assert stress["drought_severity"] in ["MILD", "MODERATE", "SEVERE", "EXTREME"]

    # Soil moisture in trajectory should register water stress
    traj = res["weekly_trajectory"]
    stress_weeks = [pt for pt in traj if pt["water_stress_active"]]
    assert len(stress_weeks) > 0


def test_compound_scenario_amplification(simulator):
    """
    Test that compound climate shock (+3C heatwave + drought + irrigation delay)
    produces a more severe yield impact than single-factor heatwave.
    """
    heat_only = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=2.0,
        precip_factor=1.0,
        irrigation_delay_days=0,
        target_stage="grain_filling",
    )

    compound = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=2.0,
        precip_factor=0.4,
        irrigation_delay_days=14,
        target_stage="grain_filling",
    )

    assert compound["delta_pct"] <= heat_only["delta_pct"], (
        f"Compound delta {compound['delta_pct']} should be <= heat-only {heat_only['delta_pct']}"
    )


def test_baseline_models_support(simulator):
    """Test that simulator supports RandomForest and XGBoost inference."""
    res_rf = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=2.0,
        model_name="random_forest",
    )
    assert res_rf["model_used"] == "random_forest"
    assert res_rf["scenario_yield_kgha"] > 0

    res_xgb = simulator.run_scenario(
        district_id="faisalabad",
        temp_delta_c=2.0,
        model_name="xgboost",
    )
    assert res_xgb["model_used"] == "xgboost"
    assert res_xgb["scenario_yield_kgha"] > 0


def test_fastapi_scenarios_presets_endpoint(client):
    """Test GET /api/v1/scenarios/presets."""
    resp = client.get("/api/v1/scenarios/presets")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    assert any(p["id"] == "terminal_heatwave" for p in data)


def test_fastapi_scenarios_run_endpoint_latency_and_schema(client):
    """Test POST /api/v1/scenarios/run responds under 1 second with valid schema."""
    payload = {
        "district_id": "faisalabad",
        "temp_delta_c": 3.0,
        "precip_factor": 0.8,
        "irrigation_delay_days": 7,
        "target_stage": "grain_filling",
        "model_name": "deepagronet",
    }

    t0 = time.time()
    resp = client.post("/api/v1/scenarios/run", json=payload)
    elapsed = time.time() - t0

    assert resp.status_code == 200, resp.text
    assert elapsed < 1.0, f"Scenario execution took {elapsed:.3f}s, exceeding 1.0s requirement!"

    data = resp.json()
    assert data["district_id"] == "faisalabad"
    assert "delta_pct" in data
    assert "stress_indices" in data
    assert "weekly_trajectory" in data
    assert len(data["weekly_trajectory"]) == 27
    assert data["disclaimer_en"] != ""
    assert data["disclaimer_ur"] != ""
