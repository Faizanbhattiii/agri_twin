"""
FastAPI Endpoints for Climate-Risk "What-If" Scenario Simulator.
Provides presets and interactive multi-parameter simulation runs.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Query, status

from agritwin.api.schemas import (
    ScenarioPresetOut,
    ScenarioRunRequest,
    ScenarioRunResponse,
)
from agritwin.simulator.what_if import PRESET_SCENARIOS, WhatIfSimulator

router = APIRouter(prefix="/api/v1/scenarios", tags=["What-If Climate Simulator"])

# Global singleton simulator instance for low-latency in-memory inference
_simulator_instance = None


def get_simulator() -> WhatIfSimulator:
    """Retrieve or initialize singleton WhatIfSimulator."""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = WhatIfSimulator()
    return _simulator_instance


@router.get(
    "/presets",
    response_model=List[ScenarioPresetOut],
    summary="List pre-configured climate risk scenario presets",
    description="Returns pre-defined climate shock scenarios (e.g., terminal heatwave, severe drought, irrigation delay) with bilingual titles and descriptions.",
)
def list_scenario_presets() -> List[ScenarioPresetOut]:
    """Return all cataloged scenario presets."""
    return [ScenarioPresetOut(**preset) for preset in PRESET_SCENARIOS]


@router.post(
    "/run",
    response_model=ScenarioRunResponse,
    summary="Execute what-if simulation",
    description="Applies temperature, rainfall, and irrigation delay perturbations to baseline district data, predicts differential yield impact, and calculates agronomic stress indices.",
)
def run_scenario(request: ScenarioRunRequest) -> ScenarioRunResponse:
    """Execute scenario simulation with physics-based water balance and model inference."""
    try:
        simulator = get_simulator()
        result = simulator.run_scenario(
            district_id=request.district_id,
            temp_delta_c=request.temp_delta_c,
            precip_factor=request.precip_factor,
            irrigation_delay_days=request.irrigation_delay_days,
            target_stage=request.target_stage,
            model_name=request.model_name,
            baseline_season=request.baseline_season,
        )
        return ScenarioRunResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation failed: {str(e)}",
        )
