"""
Unit & Integration Tests for Phase 1 Data Pipelines.
Tests Yield data loader, Open-Meteo weather client, SoilGrids client, and Sentinel-2 satellite client.
Verifies caching, schema validation, and offline fallback integrity (Rule 4 & 7).
"""

from pathlib import Path
import pytest
import pandas as pd
from agritwin.core.config import DATA_DIR
from agritwin.data.yields import YieldDataLoader
from agritwin.data.weather import WeatherClient
from agritwin.data.soil import SoilGridsClient
from agritwin.data.satellite import SatelliteClient


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """Create an isolated temporary cache directory."""
    cache = tmp_path / "test_cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


class TestYieldDataLoader:
    """Tests for Punjab Crop Reporting Service historical yield dataset."""

    def test_yield_dataset_structure(self):
        loader = YieldDataLoader()
        df = loader.get_all()
        assert len(df) == 360  # 36 districts x 10 seasons
        assert "yield_kg_per_ha" in df.columns
        assert "yield_maund_per_acre" in df.columns
        assert "district" in df.columns
        assert "season" in df.columns

    def test_districts_and_seasons_coverage(self):
        loader = YieldDataLoader()
        districts = loader.get_districts()
        seasons = loader.get_seasons()
        assert len(districts) == 36
        assert "Faisalabad" in districts
        assert "Multan" in districts
        assert "Rawalpindi" in districts
        assert len(seasons) == 10
        assert "2013-14" in seasons
        assert "2022-23" in seasons

    def test_unit_conversion_consistency(self):
        loader = YieldDataLoader()
        df = loader.get_all()
        # 1 maund/acre = 98.8418 kg/ha
        expected_kg = df["yield_maund_per_acre"] * 98.8418
        # Values should match within 0.5 kg/ha due to rounding
        diff = (df["yield_kg_per_ha"] - expected_kg).abs()
        assert diff.max() < 0.5

    def test_district_series_and_baseline(self):
        loader = YieldDataLoader()
        faisalabad_series = loader.get_district_series("Faisalabad")
        assert len(faisalabad_series) == 10
        
        stats = loader.get_district_baseline("Faisalabad")
        assert 3000.0 < stats["mean_yield_kgha"] < 4200.0
        assert stats["min_yield_kgha"] < stats["mean_yield_kgha"] < stats["max_yield_kgha"]


class TestWeatherClient:
    """Tests for Open-Meteo weather client with caching."""

    def test_historical_weather_fetch_and_cache(self, temp_cache_dir: Path):
        client = WeatherClient(cache_dir=temp_cache_dir)
        lat, lon = 31.4289, 73.0782
        
        # 1. Fetch data
        df = client.get_historical_daily(lat, lon, start_date="2022-11-01", end_date="2022-11-15")
        assert len(df) == 15
        assert "temperature_2m_mean" in df.columns
        assert "precipitation_sum" in df.columns
        assert "et0_fao_evapotranspiration" in df.columns
        assert "source" in df.columns

        # 2. Check that cache file was generated
        cache_files = list(temp_cache_dir.glob("hist_*.json"))
        assert len(cache_files) == 1

        # 3. Second call hits cache
        df_cached = client.get_historical_daily(lat, lon, start_date="2022-11-01", end_date="2022-11-15")
        assert len(df_cached) == 15
        pd.testing.assert_frame_equal(df, df_cached)

    def test_forecast_daily(self, temp_cache_dir: Path):
        client = WeatherClient(cache_dir=temp_cache_dir)
        df_fcst = client.get_forecast_daily(31.4289, 73.0782, forecast_days=7)
        assert len(df_fcst) == 7
        assert "temperature_2m_max" in df_fcst.columns
        assert "relative_humidity_2m_mean" in df_fcst.columns


class TestSoilGridsClient:
    """Tests for SoilGrids client and soil hydraulic parameter estimation."""

    def test_soil_profile_fetch_and_cache(self, temp_cache_dir: Path):
        client = SoilGridsClient(cache_dir=temp_cache_dir)
        profile = client.get_soil_profile(31.4289, 73.0782)
        
        assert "clay_pct" in profile
        assert "sand_pct" in profile
        assert "silt_pct" in profile
        assert "field_capacity_pct" in profile
        assert "wilting_point_pct" in profile
        assert "taw_mm_per_m" in profile
        assert "source" in profile

        # Physical sanity: Field Capacity must exceed Wilting Point
        assert profile["field_capacity_pct"] > profile["wilting_point_pct"]
        assert profile["taw_mm_per_m"] > 0

        # Texture proportions sum close to 100%
        texture_sum = profile["clay_pct"] + profile["sand_pct"] + profile["silt_pct"]
        assert pytest.approx(texture_sum, abs=2.0) == 100.0

        # Verify cache file created
        cache_files = list(temp_cache_dir.glob("soil_*.json"))
        assert len(cache_files) == 1


class TestSatelliteClient:
    """Tests for Sentinel-2 NDVI satellite trajectory pipeline."""

    def test_seasonal_ndvi_trajectory(self, temp_cache_dir: Path):
        client = SatelliteClient(cache_dir=temp_cache_dir)
        df = client.get_seasonal_ndvi(
            target_id="pilot-faisalabad-01",
            season_year=2023,
            latitude=31.4289,
            longitude=73.0782
        )

        assert len(df) == 27  # 27 weekly steps for Rabi season
        assert "week" in df.columns
        assert "ndvi_mean" in df.columns
        assert "evi" in df.columns
        assert "source" in df.columns

        # Sanity: NDVI bounded in [0, 1]
        assert (df["ndvi_mean"] >= 0.0).all()
        assert (df["ndvi_mean"] <= 1.0).all()

        # Phenology check: peak greenness in wheat occurs around heading (weeks 14-18, Feb)
        peak_idx = df["ndvi_mean"].idxmax()
        peak_week = df.loc[peak_idx, "week"]
        assert 13 <= peak_week <= 19
        assert df["ndvi_mean"].max() > 0.65  # Well-developed canopy
