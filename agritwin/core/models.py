"""
SQLAlchemy 2.0 Relational Data Models for AgriTwin Pakistan.
Supports both PostgreSQL (JSONB) and SQLite (JSON) via SQLAlchemy JSON abstraction.
Designed per Decision D4: GeoJSON boundaries stored as JSON without heavy PostGIS requirements.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class District(Base):
    """Administrative district in Punjab, Pakistan."""
    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "faisalabad"
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name_ur: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    division: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[str] = mapped_column(String(50), default="Punjab")
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    geometry_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Relationships
    fields: Mapped[List["Field"]] = relationship("Field", back_populates="district", cascade="all, delete-orphan")
    soil_profile: Mapped[Optional["SoilProfile"]] = relationship("SoilProfile", back_populates="district", uselist=False)
    weather_observations: Mapped[List["WeatherObservation"]] = relationship("WeatherObservation", back_populates="district")

    def __repr__(self) -> str:
        return f"<District {self.name} ({self.division})>"


class SoilProfile(Base):
    """Soil physical, chemical, and hydraulic characteristics."""
    __tablename__ = "soil_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[Optional[str]] = mapped_column(ForeignKey("districts.id"), nullable=True, unique=True)
    field_id: Mapped[Optional[str]] = mapped_column(ForeignKey("fields.id"), nullable=True, unique=True)

    texture_class: Mapped[str] = mapped_column(String(50), default="Loam")
    clay_pct: Mapped[float] = mapped_column(Float, nullable=False)
    sand_pct: Mapped[float] = mapped_column(Float, nullable=False)
    silt_pct: Mapped[float] = mapped_column(Float, nullable=False)
    soc_pct: Mapped[float] = mapped_column(Float, nullable=False)
    ph: Mapped[float] = mapped_column(Float, nullable=False)
    bulk_density_g_cm3: Mapped[float] = mapped_column(Float, nullable=False)
    cec_cmol_kg: Mapped[float] = mapped_column(Float, default=15.0)

    # Hydraulic limits
    field_capacity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wilting_point_pct: Mapped[float] = mapped_column(Float, nullable=False)
    taw_mm_per_m: Mapped[float] = mapped_column(Float, nullable=False)  # Total Available Water
    raw_mm_per_m: Mapped[float] = mapped_column(Float, nullable=False)  # Readily Available Water

    source: Mapped[str] = mapped_column(String(50), default="SoilGrids-2.0")

    # Relationships
    district: Mapped[Optional["District"]] = relationship("District", back_populates="soil_profile")
    field: Mapped[Optional["Field"]] = relationship("Field", back_populates="soil_profile")


class Field(Base):
    """Agricultural parcel or pilot research plot."""
    __tablename__ = "fields"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g. "pilot-faisalabad-01"
    district_id: Mapped[str] = mapped_column(ForeignKey("districts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_ur: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    boundary_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    crop_type: Mapped[str] = mapped_column(String(50), default="wheat")
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_pilot: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    # Relationships
    district: Mapped["District"] = relationship("District", back_populates="fields")
    soil_profile: Mapped[Optional["SoilProfile"]] = relationship("SoilProfile", back_populates="field", uselist=False)
    telemetry: Mapped[List["SensorTelemetry"]] = relationship("SensorTelemetry", back_populates="field", cascade="all, delete-orphan")
    satellite_readings: Mapped[List["SatelliteReading"]] = relationship("SatelliteReading", back_populates="field", cascade="all, delete-orphan")
    advisories: Mapped[List["IrrigationAdvisory"]] = relationship("IrrigationAdvisory", back_populates="field", cascade="all, delete-orphan")
    yield_forecasts: Mapped[List["YieldForecast"]] = relationship("YieldForecast", back_populates="field", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Field {self.name} ({self.area_acres} acres)>"


class WeatherObservation(Base):
    """Daily observed or historical weather records."""
    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[Optional[str]] = mapped_column(ForeignKey("districts.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    temp_min_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_max_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_mean_c: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    solar_radiation_mj: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_mean_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[float] = mapped_column(Float, default=5.0)
    et0_mm: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="open-meteo")

    district: Mapped[Optional["District"]] = relationship("District", back_populates="weather_observations")


class WeatherForecast(Base):
    """7-day forward weather forecast."""
    __tablename__ = "weather_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[str] = mapped_column(String(50), index=True)  # district_id or field_id
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    temp_min_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_max_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_mean_c: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Float, default=0.0)
    humidity_mean_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[float] = mapped_column(Float, default=5.0)
    et0_mm: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="open-meteo-forecast")


class SatelliteReading(Base):
    """Weekly Sentinel-2 satellite vegetation index observation."""
    __tablename__ = "satellite_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(ForeignKey("fields.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    week_number: Mapped[int] = mapped_column(Integer, nullable=False)

    ndvi_mean: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_min: Mapped[float] = mapped_column(Float, nullable=False)
    ndvi_max: Mapped[float] = mapped_column(Float, nullable=False)
    evi: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="copernicus-s2")

    field: Mapped["Field"] = relationship("Field", back_populates="satellite_readings")


class SensorTelemetry(Base):
    """Live ground-truth telemetry from ESP32 field node."""
    __tablename__ = "sensor_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(ForeignKey("fields.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    soil_moisture_pct: Mapped[float] = mapped_column(Float, nullable=False)
    air_temp_c: Mapped[float] = mapped_column(Float, nullable=False)
    relative_humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    soil_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_v: Mapped[float] = mapped_column(Float, default=4.1)

    source: Mapped[str] = mapped_column(String(50), default="esp32-node")  # or 'simulated'
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    field: Mapped["Field"] = relationship("Field", back_populates="telemetry")

    def __repr__(self) -> str:
        return f"<Telemetry {self.timestamp}: Moisture={self.soil_moisture_pct}% Temp={self.air_temp_c}C>"


class IrrigationAdvisory(Base):
    """Daily irrigation recommendations generated by the water balance engine."""
    __tablename__ = "irrigation_advisories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(ForeignKey("fields.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    urgency: Mapped[str] = mapped_column(String(30), nullable=False)  # OPTIMAL, MONITOR, CRITICAL_IRRIGATE
    soil_moisture_pct: Mapped[float] = mapped_column(Float, nullable=False)
    depletion_mm: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_depth_mm: Mapped[float] = mapped_column(Float, default=0.0)
    tubewell_hours: Mapped[float] = mapped_column(Float, default=0.0)

    reason_en: Mapped[str] = mapped_column(Text, nullable=False)
    reason_ur: Mapped[str] = mapped_column(Text, nullable=False)
    disclaimer: Mapped[str] = mapped_column(String(200), default="Advisory only; verify with field conditions")

    field: Mapped["Field"] = relationship("Field", back_populates="advisories")


class YieldForecast(Base):
    """End-of-season wheat yield prediction generated by AI models."""
    __tablename__ = "yield_forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    field_id: Mapped[str] = mapped_column(ForeignKey("fields.id"), nullable=False, index=True)
    season: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)  # DeepAgroNet, RandomForest, XGBoost

    predicted_yield_kgha: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_yield_maund_acre: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound_kgha: Mapped[float] = mapped_column(Float, nullable=False)
    upper_bound_kgha: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    field: Mapped["Field"] = relationship("Field", back_populates="yield_forecasts")
