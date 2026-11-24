"""
Open-Meteo Weather Data Client.
Fetches historical agro-meteorological data and 7-day forecasts.
Features local disk caching, rate limit consideration, and offline fixture fallbacks.
License: Open-Meteo free non-commercial API is licensed under CC BY 4.0.
Attribution: 'Weather data by Open-Meteo.com'
"""

import hashlib
import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import requests

from agritwin.core.config import DATA_DIR, settings

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "cache" / "weather"
FIXTURES_DIR = DATA_DIR / "fixtures" / "weather"


class WeatherClient:
    """Client for Open-Meteo Historical & Forecast Weather APIs with caching."""

    ATTRIBUTION = "Weather data provided by Open-Meteo.com (CC BY 4.0)"

    DAILY_VARS = [
        "temperature_2m_max",
        "temperature_2m_min",
        "temperature_2m_mean",
        "precipitation_sum",
        "shortwave_radiation_sum",
        "relative_humidity_2m_mean",
        "wind_speed_10m_max",
        "et0_fao_evapotranspiration"
    ]

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 15):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.archive_url = settings.open_meteo_base_url
        self.forecast_url = settings.open_meteo_forecast_url

    def _cache_key(self, prefix: str, lat: float, lon: float, extra: str) -> Path:
        """Create a deterministic cache filepath for given coordinates and query parameters."""
        raw = f"{prefix}_{lat:.4f}_{lon:.4f}_{extra}".encode("utf-8")
        hash_val = hashlib.md5(raw).hexdigest()
        return self.cache_dir / f"{prefix}_{hash_val}.json"

    def get_historical_daily(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch historical daily weather between start_date and end_date (YYYY-MM-DD).
        Returns a pandas DataFrame with daily observations.
        """
        cache_file = self._cache_key("hist", latitude, longitude, f"{start_date}_{end_date}")

        if use_cache and cache_file.exists():
            logger.debug(f"Loading weather from cache: {cache_file.name}")
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._format_response(data, source="open-meteo")

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "start_date": start_date,
            "end_date": end_date,
            "daily": ",".join(self.DAILY_VARS),
            "timezone": settings.timezone
        }

        try:
            resp = requests.get(self.archive_url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return self._format_response(data, source="open-meteo")
            else:
                logger.warning(f"Open-Meteo returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.warning(f"Failed to query Open-Meteo API ({e}). Falling back to simulation fixture.")

        # Offline / Failure fallback (Rule 4: source='simulated')
        return self._generate_simulated_weather(latitude, longitude, start_date, end_date)

    def get_forecast_daily(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 7,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        Fetch 7-day daily weather forecast.
        Returns DataFrame with forecast days.
        """
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_file = self._cache_key("fcst", latitude, longitude, f"{today_str}_{forecast_days}")

        if use_cache and cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self._format_response(data, source="open-meteo-forecast")

        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "daily": ",".join(self.DAILY_VARS),
            "forecast_days": forecast_days,
            "timezone": settings.timezone
        }

        try:
            resp = requests.get(self.forecast_url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                return self._format_response(data, source="open-meteo-forecast")
        except Exception as e:
            logger.warning(f"Failed to query Open-Meteo forecast ({e}). Generating simulated forecast.")

        start_date = today_str
        end_date = (datetime.now() + timedelta(days=forecast_days - 1)).strftime("%Y-%m-%d")
        return self._generate_simulated_weather(latitude, longitude, start_date, end_date, is_forecast=True)

    def _format_response(self, raw_data: Dict[str, Any], source: str) -> pd.DataFrame:
        """Convert Open-Meteo daily JSON dictionary to pandas DataFrame."""
        daily = raw_data.get("daily", {})
        if not daily or "time" not in daily:
            raise ValueError("Malformed Open-Meteo response: 'daily.time' missing.")

        df = pd.DataFrame(daily)
        df.rename(columns={"time": "date"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"])
        df["source"] = source
        return df

    def _generate_simulated_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        is_forecast: bool = False
    ) -> pd.DataFrame:
        """
        Generate realistic simulated weather series for Punjab wheat region.
        Marks records with source='simulated' (Rule 4).
        """
        import numpy as np

        dates = pd.date_range(start=start_date, end=end_date, freq="D")
        n = len(dates)
        
        # Day of year calculation for seasonal thermal curve
        doy = dates.dayofyear.values
        # Punjab temperature curve: peak cold in Jan (doy ~15), warm up through March/April
        base_tmean = 20.0 - 9.0 * np.cos(2 * np.pi * (doy - 15) / 365.0)
        t_noise = np.sin(doy * 0.1) * 2.0
        
        tmean = np.round(base_tmean + t_noise, 1)
        tmin = np.round(tmean - 6.0, 1)
        tmax = np.round(tmean + 6.0, 1)
        
        # Occasional winter rain in Punjab (Western disturbances)
        rain = np.where((doy > 10) & (doy < 90) & (np.sin(doy * 0.3) > 0.8), np.round(np.abs(np.sin(doy)) * 12.0, 1), 0.0)
        
        # Solar radiation in MJ/m2
        solar_rad = np.round(12.0 + 8.0 * np.sin(np.pi * doy / 365.0), 1)
        
        # Humidity (%): higher in winter mornings (65-80%), dropping in spring
        humidity = np.clip(np.round(75.0 - (tmax - 15.0) * 1.5, 1), 30.0, 95.0)
        
        # Wind speed (km/h)
        wind = np.round(6.0 + 4.0 * np.abs(np.sin(doy * 0.2)), 1)
        
        # ET0 (mm/day) rough estimation
        et0 = np.clip(np.round(0.0023 * (tmean + 17.8) * np.sqrt(np.maximum(1.0, tmax - tmin)) * solar_rad * 0.408, 2), 1.0, 8.0)

        df = pd.DataFrame({
            "date": dates,
            "temperature_2m_max": tmax,
            "temperature_2m_min": tmin,
            "temperature_2m_mean": tmean,
            "precipitation_sum": rain,
            "shortwave_radiation_sum": solar_rad,
            "relative_humidity_2m_mean": humidity,
            "wind_speed_10m_max": wind,
            "et0_fao_evapotranspiration": et0,
            "source": "simulated"
        })
        return df
