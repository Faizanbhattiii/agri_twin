"""
Configuration manager for AgriTwin Pakistan.
Loads settings from environment variables, .env file, and YAML configuration files.
Designed with zero heavy dependencies for cross-platform and Python 3.11+ / 3.14 stability.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import os
import yaml

# Base directory for the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"


def load_env_file(env_path: Path) -> Dict[str, str]:
    """Parse .env file into key-value pairs without external dependency."""
    env_vars: Dict[str, str] = {}
    if not env_path.exists():
        return env_vars
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            env_vars[key] = val
    return env_vars


@dataclass
class AppSettings:
    """Application-wide settings loaded from environment or .env file."""
    environment: str = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    secret_key: str = "agritwin-dev-secret-key"
    timezone: str = "Asia/Karachi"

    # Database
    database_url: str = field(default_factory=lambda: f"sqlite:///{DATA_DIR / 'agritwin.db'}")

    # Open-Meteo API
    open_meteo_base_url: str = "https://archive-api.open-meteo.com/v1/archive"
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"

    # Google Earth Engine
    gee_project_id: Optional[str] = None
    gee_service_account: Optional[str] = None
    gee_private_key_path: Optional[str] = None

    # SoilGrids
    soilgrids_base_url: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"

    # Field Node Telemetry Security
    field_node_api_key: str = "dev-node-api-key-test-12345"
    telemetry_interval_minutes: int = 15

    # Pilot Field defaults
    pilot_field_id: str = "pilot-faisalabad-01"
    pilot_latitude: float = 31.4289
    pilot_longitude: float = 73.0782
    pilot_area_acres: float = 5.0

    @classmethod
    def load(cls) -> "AppSettings":
        """Load settings merging .env file and active environment variables."""
        env_dict = load_env_file(BASE_DIR / ".env")
        
        def get_val(key: str, default: Any, cast_type: type = str) -> Any:
            val = os.getenv(key, env_dict.get(key))
            if val is None:
                return default
            return cast_type(val)

        return cls(
            environment=get_val("ENVIRONMENT", "development", str),
            log_level=get_val("LOG_LEVEL", "INFO", str),
            app_host=get_val("APP_HOST", "0.0.0.0", str),
            app_port=get_val("APP_PORT", 8000, int),
            secret_key=get_val("SECRET_KEY", "agritwin-dev-secret-key", str),
            timezone=get_val("TIMEZONE", "Asia/Karachi", str),
            database_url=get_val("DATABASE_URL", f"sqlite:///{DATA_DIR / 'agritwin.db'}", str),
            open_meteo_base_url=get_val("OPEN_METEO_BASE_URL", "https://archive-api.open-meteo.com/v1/archive", str),
            open_meteo_forecast_url=get_val("OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast", str),
            gee_project_id=get_val("GEE_PROJECT_ID", None, str),
            gee_service_account=get_val("GEE_SERVICE_ACCOUNT", None, str),
            gee_private_key_path=get_val("GEE_PRIVATE_KEY_PATH", None, str),
            soilgrids_base_url=get_val("SOILGRIDS_BASE_URL", "https://rest.isric.org/soilgrids/v2.0/properties/query", str),
            field_node_api_key=get_val("FIELD_NODE_API_KEY", "dev-node-api-key-test-12345", str),
            telemetry_interval_minutes=get_val("TELEMETRY_INTERVAL_MINUTES", 15, int),
            pilot_field_id=get_val("PILOT_FIELD_ID", "pilot-faisalabad-01", str),
            pilot_latitude=get_val("PILOT_LATITUDE", 31.4289, float),
            pilot_longitude=get_val("PILOT_LONGITUDE", 73.0782, float),
            pilot_area_acres=get_val("PILOT_AREA_ACRES", 5.0, float)
        )


def load_yaml(file_path: Path) -> Dict[str, Any]:
    """Safely load a YAML configuration file."""
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_crop_config(crop_name: str = "wheat") -> Dict[str, Any]:
    """Load crop specific configuration (e.g. config/crops/wheat.yaml)."""
    crop_file = CONFIG_DIR / "crops" / f"{crop_name}.yaml"
    return load_yaml(crop_file)


def get_system_settings() -> Dict[str, Any]:
    """Load system configuration from config/settings.yaml."""
    settings_file = CONFIG_DIR / "settings.yaml"
    return load_yaml(settings_file)


# Conversion constants (Decision D11)
MAUND_KG = 40.0
ACRE_HA = 0.404686
MAUND_PER_ACRE_TO_KG_PER_HA = 98.8418  # (40 / 0.404686)


def maund_per_acre_to_kg_per_ha(maund_acre: float) -> float:
    """Convert Pakistani maund/acre to international kg/ha."""
    return maund_acre * MAUND_PER_ACRE_TO_KG_PER_HA


def kg_per_ha_to_maund_per_acre(kg_ha: float) -> float:
    """Convert international kg/ha to Pakistani maund/acre."""
    return kg_ha / MAUND_PER_ACRE_TO_KG_PER_HA


# Singleton instance
settings = AppSettings.load()
