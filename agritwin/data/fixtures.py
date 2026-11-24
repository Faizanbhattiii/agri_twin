"""
Offline fixtures generator for test suites and offline demo environments.
Ensures all simulated datasets explicitly carry source='simulated' (Rule 4).
Pre-populates baseline weather, soil, and satellite data in data/fixtures/.
"""

import json
from pathlib import Path
from agritwin.core.config import DATA_DIR
from agritwin.data.weather import WeatherClient
from agritwin.data.soil import SoilGridsClient
from agritwin.data.satellite import SatelliteClient

FIXTURES_DIR = DATA_DIR / "fixtures"


def generate_all_fixtures() -> None:
    """Generate and store deterministic fixtures for testing and offline execution."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Pilot field (Faisalabad)
    pilot_lat, pilot_lon = 31.4289, 73.0782
    
    # Weather fixture (2022-23 wheat season)
    weather_client = WeatherClient(cache_dir=FIXTURES_DIR / "weather")
    df_weather = weather_client.get_historical_daily(
        pilot_lat, pilot_lon,
        start_date="2022-11-01",
        end_date="2023-05-10",
        use_cache=False
    )
    df_weather.to_csv(FIXTURES_DIR / "pilot_weather_2022_2023.csv", index=False)
    
    # Soil fixture
    soil_client = SoilGridsClient(cache_dir=FIXTURES_DIR / "soil")
    soil_profile = soil_client.get_soil_profile(pilot_lat, pilot_lon, use_cache=False)
    with open(FIXTURES_DIR / "pilot_soil_profile.json", "w", encoding="utf-8") as f:
        json.dump(soil_profile, f, indent=2)

    # Satellite NDVI fixture
    sat_client = SatelliteClient(cache_dir=FIXTURES_DIR / "satellite")
    df_ndvi = sat_client.get_seasonal_ndvi(
        target_id="pilot-faisalabad-01",
        season_year=2023,
        latitude=pilot_lat,
        longitude=pilot_lon,
        use_cache=False
    )
    df_ndvi.to_csv(FIXTURES_DIR / "pilot_ndvi_2022_2023.csv", index=False)


if __name__ == "__main__":
    generate_all_fixtures()
    print("All offline fixtures successfully generated under data/fixtures/")
