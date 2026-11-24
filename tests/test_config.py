"""
Unit tests for configuration loading, conversion formulas, and directory integrity.
Verifies Phase 0 Definition of Done.
"""

import pytest
from pathlib import Path
from agritwin.core.config import (
    BASE_DIR,
    CONFIG_DIR,
    DATA_DIR,
    settings,
    get_crop_config,
    get_system_settings,
    maund_per_acre_to_kg_per_ha,
    kg_per_ha_to_maund_per_acre,
    MAUND_PER_ACRE_TO_KG_PER_HA
)


def test_directory_structure_exists():
    """Verify standard project directories are present."""
    assert BASE_DIR.exists()
    assert CONFIG_DIR.exists()
    assert DATA_DIR.exists()
    assert (BASE_DIR / "agritwin").exists()
    assert (BASE_DIR / "tests").exists()
    assert (BASE_DIR / "docs").exists()


def test_app_settings_defaults():
    """Verify default application settings match specifications."""
    assert settings.environment in ("development", "test", "production")
    assert settings.timezone == "Asia/Karachi"
    assert settings.telemetry_interval_minutes == 15
    assert settings.pilot_latitude == 31.4289
    assert settings.pilot_longitude == 73.0782


def test_wheat_crop_config():
    """Verify wheat crop config contains all necessary agronomic parameters."""
    crop = get_crop_config("wheat")
    assert crop["crop"]["name"] == "Wheat"
    assert crop["crop"]["season"] == "Rabi"
    assert crop["calendar"]["base_temperature_c"] == 5.0
    assert crop["calendar"]["total_weeks"] == 27

    stages = crop["growth_stages"]
    assert len(stages) == 6
    stage_ids = [s["id"] for s in stages]
    assert "germination" in stage_ids
    assert "tillering_cri" in stage_ids
    assert "heading_flowering" in stage_ids
    assert "grain_filling" in stage_ids
    assert "maturity" in stage_ids

    # Critical irrigation points defined
    critical_stages = [s for s in stages if s.get("critical_irrigation") is True]
    assert len(critical_stages) >= 3

    # Soil water parameters
    soil_params = crop["soil_water_parameters"]
    assert soil_params["depletion_factor_p"] == 0.55
    assert soil_params["critical_moisture_threshold_pct"] == 18.0

    # Risk thresholds
    risk = crop["risk_thresholds"]
    assert risk["heat_stress_temp_c"] == 32.0


def test_system_settings():
    """Verify system settings and open data attributions."""
    system = get_system_settings()
    assert system["app"]["name"] == "AgriTwin Pakistan"
    assert "Open-Meteo" in system["attribution"]["weather"]
    assert "Sentinel-2" in system["attribution"]["satellite"]
    assert "SoilGrids" in system["attribution"]["soil"]
    assert "Crop Reporting Service" in system["attribution"]["yield_records"]


def test_unit_conversions():
    """Verify maund/acre to kg/ha conversion and inverse (Decision D11)."""
    # 1 maund = 40 kg, 1 acre = 0.404686 ha -> ~98.8418 kg/ha
    assert pytest.approx(MAUND_PER_ACRE_TO_KG_PER_HA, rel=1e-4) == 98.8418

    # 35 maunds/acre in kg/ha
    kg_ha = maund_per_acre_to_kg_per_ha(35.0)
    assert pytest.approx(kg_ha, rel=1e-4) == 35.0 * 98.8418

    # Round trip
    maund_reconstructed = kg_per_ha_to_maund_per_acre(kg_ha)
    assert pytest.approx(maund_reconstructed, rel=1e-6) == 35.0
