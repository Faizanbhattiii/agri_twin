"""
Integration tests for Phase 7: Web Dashboard API & Static Frontend Mounting.
Verifies districts metadata, field summaries, irrigation advisories,
pest-risk evaluation, 7-day weather forecasts, and 27-week NDVI trajectories.
"""

import pytest
from fastapi.testclient import TestClient

from agritwin.api.app import app


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


def test_get_dashboard_districts(client):
    """Test GET /api/v1/dashboard/districts returns all 36 Punjab districts."""
    resp = client.get("/api/v1/dashboard/districts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 36

    # Verify fields in sample district
    sample = data[0]
    assert "id" in sample
    assert "name" in sample
    assert "name_ur" in sample
    assert "division" in sample
    assert "average_yield_maund_acre" in sample
    assert "soil_texture" in sample
    assert "polygon_geojson" in sample


def test_get_dashboard_fields(client):
    """Test GET /api/v1/dashboard/fields returns Pilot Research Field."""
    resp = client.get("/api/v1/dashboard/fields")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    field = next((f for f in data if f["id"] == "pilot-faisalabad-01"), None)
    assert field is not None
    assert field["district_id"] == "faisalabad"
    assert field["area_acres"] == 5.0
    assert field["crop_type"] == "wheat"
    assert "latest_soil_moisture_pct" in field


def test_get_latest_advisory_for_field(client):
    """Test GET /api/v1/dashboard/advisories/latest/{field_id}."""
    resp = client.get("/api/v1/dashboard/advisories/latest/pilot-faisalabad-01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["field_id"] == "pilot-faisalabad-01"
    assert data["urgency"] in ["OPTIMAL", "MONITOR", "CRITICAL_IRRIGATE", "RAIN_DEFERRED"]
    assert data["tubewell_hours_per_acre"] >= 0.0
    assert data["gross_irrigation_needed_mm"] >= 0.0
    assert len(data["headline_en"]) > 0
    assert len(data["headline_ur"]) > 0
    assert len(data["disclaimer_en"]) > 0

    # Verify pest risk
    pest = data["pest_risk"]
    assert pest["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert len(pest["pest_name_en"]) > 0
    assert len(pest["pest_name_ur"]) > 0


def test_get_weather_forecast_for_field(client):
    """Test GET /api/v1/dashboard/weather/forecast/{field_id}."""
    resp = client.get("/api/v1/dashboard/weather/forecast/pilot-faisalabad-01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["field_id"] == "pilot-faisalabad-01"
    assert len(data["days"]) == 7
    assert data["field_capacity_pct"] > data["wilting_point_pct"]

    day0 = data["days"][0]
    assert "temp_mean_c" in day0
    assert "et0_mm" in day0
    assert "predicted_soil_moisture_pct" in day0


def test_get_ndvi_trajectory_for_field(client):
    """Test GET /api/v1/dashboard/satellite/ndvi/{field_id}."""
    resp = client.get("/api/v1/dashboard/satellite/ndvi/pilot-faisalabad-01")
    assert resp.status_code == 200
    data = resp.json()

    assert data["field_id"] == "pilot-faisalabad-01"
    assert len(data["trajectory"]) == 27
    assert 0.1 <= data["peak_ndvi"] <= 1.0
    assert 1 <= data["peak_week"] <= 27

    week1 = data["trajectory"][0]
    assert week1["week"] == 1
    assert "field_ndvi" in week1
    assert "district_normal_ndvi" in week1
    assert "growth_stage_en" in week1
    assert "growth_stage_ur" in week1


def test_frontend_static_serving(client):
    """Test that GET / returns the built React application index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "<!doctype html>" in resp.text.lower()
    assert "agritwin pakistan" in resp.text.lower()
