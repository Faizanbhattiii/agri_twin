"""
Irrigation advisory, FAO-56 Penman-Monteith ET0, root zone water balance, and bilingual advice engine.
"""

from agritwin.advisory.evapotranspiration import PenmanMonteithCalculator
from agritwin.advisory.crop_water import (
    WheatCropWaterManager,
    WheatGrowthStage,
    WHEAT_STAGES,
)
from agritwin.advisory.water_balance import (
    SoilWaterBalanceModel,
    SoilWaterState,
)
from agritwin.advisory.irrigation_engine import (
    AdvisoryUrgency,
    IrrigationRecommendation,
    IrrigationAdvisoryEngine,
)

__all__ = [
    "PenmanMonteithCalculator",
    "WheatCropWaterManager",
    "WheatGrowthStage",
    "WHEAT_STAGES",
    "SoilWaterBalanceModel",
    "SoilWaterState",
    "AdvisoryUrgency",
    "IrrigationRecommendation",
    "IrrigationAdvisoryEngine",
]
