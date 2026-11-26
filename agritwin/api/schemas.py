"""
Pydantic v2 Request & Response Schemas for AgriTwin FastAPI endpoints.
Includes strict physical sensor range validation to reject corrupted hardware readings,
and schemas for the Climate-Risk "What-If" Scenario Simulator.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
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


# ==========================================
# Phase 6: Scenario Simulator Schemas
# ==========================================

class ScenarioPresetOut(BaseModel):
    """Pre-configured scenario preset definition."""
    id: str
    name_en: str
    name_ur: str
    description_en: str
    description_ur: str
    temp_delta_c: float
    precip_factor: float
    irrigation_delay_days: int
    target_stage: str


class ScenarioRunRequest(BaseModel):
    """Request payload for running a climate what-if simulation."""
    district_id: str = Field(default="faisalabad", description="Punjab district identifier or name")
    temp_delta_c: float = Field(default=0.0, ge=-5.0, le=10.0, description="Temperature perturbation in Celsius (-5 to +10 C)")
    precip_factor: float = Field(default=1.0, ge=0.0, le=3.0, description="Precipitation multiplier (0.0 to 3.0x)")
    irrigation_delay_days: int = Field(default=0, ge=0, le=45, description="Days scheduled irrigation is delayed (0 to 45)")
    target_stage: str = Field(default="all", description="Stage affected: 'all', 'grain_filling', 'flowering', 'late_season'")
    model_name: str = Field(default="deepagronet", description="Predictive model: 'deepagronet', 'random_forest', 'xgboost'")
    baseline_season: str = Field(default="2022-23", description="Historical baseline season")


class StressIndicesOut(BaseModel):
    """Agronomic stress indices produced by simulation."""
    heat_stress_hours: float
    heat_days_total: int
    grain_filling_heat_days: int
    water_deficit_stress_days: int
    terminal_heat_shock_severity: str
    drought_severity: str


class WeeklyTrajectoryPointOut(BaseModel):
    """Weekly snapshot comparing baseline and perturbed conditions."""
    week: int
    baseline_temp_mean_c: float
    scenario_temp_mean_c: float
    baseline_precip_mm: float
    scenario_precip_mm: float
    baseline_ndvi: float
    scenario_ndvi: float
    soil_moisture_pct: float
    water_stress_active: bool


class ScenarioRunResponse(BaseModel):
    """Complete simulation result returned by API."""
    district_id: str
    district_name: str
    model_used: str
    baseline_yield_kgha: float
    scenario_yield_kgha: float
    delta_kgha: float
    delta_pct: float
    baseline_yield_maund_acre: float
    scenario_yield_maund_acre: float
    delta_maund_acre: float
    uncertainty_bounds: Optional[Dict[str, float]] = None
    stress_indices: StressIndicesOut
    mitigation_advice_en: str
    mitigation_advice_ur: str
    weekly_trajectory: List[WeeklyTrajectoryPointOut]
    disclaimer_en: str
    disclaimer_ur: str
    execution_time_ms: float
