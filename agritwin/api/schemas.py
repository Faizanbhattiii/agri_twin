"""
Pydantic v2 Request & Response Schemas for AgriTwin FastAPI endpoints.
Includes strict physical sensor range validation to reject corrupted hardware readings.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TelemetryIn(BaseModel):
    """Incoming telemetry payload from ESP32 node or software simulator."""
    field_id: str = Field(..., min_length=1, max_length=50)
    timestamp: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of reading; defaults to server receipt time if omitted."
    )
    soil_moisture_pct: float = Field(..., ge=0.0, le=100.0)
    air_temp_c: float = Field(..., ge=-10.0, le=60.0)
    relative_humidity_pct: float = Field(..., ge=0.0, le=100.0)
    soil_temp_c: Optional[float] = Field(default=None, ge=-10.0, le=60.0)
    battery_v: float = Field(default=4.1, ge=2.0, le=5.5)
    source: str = Field(default="esp32-node", max_length=50)


class TelemetryOut(BaseModel):
    """Serialized telemetry record returned by REST and WebSocket APIs."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    field_id: str
    timestamp: datetime
    soil_moisture_pct: float
    air_temp_c: float
    relative_humidity_pct: float
    soil_temp_c: Optional[float] = None
    battery_v: float
    source: str
    created_at: datetime


class TelemetryIngestResponse(BaseModel):
    """Confirmation response for successful telemetry ingestion."""
    status: str = "accepted"
    reading: TelemetryOut
    is_simulated: bool
