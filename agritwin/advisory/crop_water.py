"""
Wheat Crop Evapotranspiration (ETc) and Phenological Kc Module.
Implements the dynamic dual and single crop coefficient (Kc) curve for Pakistani wheat
following FAO-56 standards and Punjab Agricultural Department recommendations.

Key stages:
1. Initial (Germination / CRI): Kc = 0.35, Root depth = 0.20m
2. Development (Tillering / Jointing): Kc ramps from 0.35 to 1.15, Root depth expands to 0.80m
3. Mid-Season (Heading / Flowering / Anthesis): Kc = 1.15, Root depth = 1.0 - 1.20m
4. Late-Season (Milk / Dough / Ripening): Kc declines from 1.15 to 0.40
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Optional, Tuple, Union


@dataclass
class WheatGrowthStage:
    """Agronomic growth stage parameters."""
    stage_id: str
    name_en: str
    name_ur: str
    start_das: int  # Days after sowing
    end_das: int
    kc_start: float
    kc_end: float
    root_depth_m: float
    critical_irrigation: bool
    irrigation_note_en: str
    irrigation_note_ur: str


# Pakistani Punjab Rabi Wheat Stages (Sown Nov 1-15, Harvested April-May)
WHEAT_STAGES = [
    WheatGrowthStage(
        stage_id="initial",
        name_en="Germination & Crown Root Initiation (CRI)",
        name_ur="اگاؤ اور تاج جڑوں کی شروعات",
        start_das=1,
        end_das=25,
        kc_start=0.35,
        kc_end=0.35,
        root_depth_m=0.25,
        critical_irrigation=True,
        irrigation_note_en="First critical irrigation at 20-25 days after sowing (CRI stage)",
        irrigation_note_ur="پہلا لازمی پانی بوائی کے 20 سے 25 دن بعد (تاج جڑوں کے بننے پر)",
    ),
    WheatGrowthStage(
        stage_id="development",
        name_en="Tillering & Stem Elongation (Jointing)",
        name_ur="شاخیں نکلنا اور گانٹھیں بننا",
        start_das=26,
        end_das=75,
        kc_start=0.35,
        kc_end=1.15,
        root_depth_m=0.75,
        critical_irrigation=False,
        irrigation_note_en="Vegetative growth; irrigate if soil moisture drops below readily available threshold",
        irrigation_note_ur="سبز نشوونما؛ اگر نمی ضروری حد سے کم ہو تو پانی لگائیں",
    ),
    WheatGrowthStage(
        stage_id="mid_season",
        name_en="Booting, Heading & Anthesis (Flowering)",
        name_ur="سٹہ نکلنا اور پھول آنا",
        start_das=76,
        end_das=115,
        kc_start=1.15,
        kc_end=1.15,
        root_depth_m=1.10,
        critical_irrigation=True,
        irrigation_note_en="Second critical irrigation during heading/flowering to protect grain count",
        irrigation_note_ur="دوسرا انتہائی اہم پانی سٹہ اور پھول آنے کے وقت دانوں کی تعداد بڑھانے کیلئے",
    ),
    WheatGrowthStage(
        stage_id="late_season",
        name_en="Grain Filling (Milk & Dough) to Maturity",
        name_ur="دانہ بھرائی (دودھیا حالت) اور پکاؤ",
        start_das=116,
        end_das=160,
        kc_start=1.15,
        kc_end=0.40,
        root_depth_m=1.10,
        critical_irrigation=True,
        irrigation_note_en="Third critical irrigation at milky stage (115-125 days). Stop 15 days before harvest.",
        irrigation_note_ur="تیسرا اہم پانی دودھیا حالت میں۔ کٹائی سے 15 دن پہلے ہر قسم کا پانی بند کر دیں۔",
    ),
]


class WheatCropWaterManager:
    """
    Manages wheat phenological Kc, root depth, and crop evapotranspiration (ETc).
    """

    def __init__(self, sowing_date: Optional[Union[str, date, datetime]] = None) -> None:
        """
        Initialize with a field's sowing date. Defaults to Nov 10 of current/previous Rabi season.
        """
        if sowing_date is None:
            today = datetime.now()
            year = today.year if today.month >= 11 else today.year - 1
            self.sowing_date = date(year, 11, 10)
        elif isinstance(sowing_date, str):
            self.sowing_date = datetime.strptime(sowing_date[:10], "%Y-%m-%d").date()
        elif isinstance(sowing_date, datetime):
            self.sowing_date = sowing_date.date()
        else:
            self.sowing_date = sowing_date

    def get_das(self, current_date: Optional[Union[str, date, datetime]] = None) -> int:
        """Calculate Days After Sowing (DAS). Clamped between 1 and 180."""
        if current_date is None:
            curr = date.today()
        elif isinstance(current_date, str):
            curr = datetime.strptime(current_date[:10], "%Y-%m-%d").date()
        elif isinstance(current_date, datetime):
            curr = current_date.date()
        else:
            curr = current_date

        diff = (curr - self.sowing_date).days + 1
        return max(1, min(180, diff))

    def get_current_stage(self, das: int) -> WheatGrowthStage:
        """Return the active WheatGrowthStage for a given DAS."""
        for stage in WHEAT_STAGES:
            if stage.start_das <= das <= stage.end_das:
                return stage
        return WHEAT_STAGES[-1]

    def get_crop_coefficient(self, das: int) -> float:
        """
        Calculate continuous crop coefficient (Kc) for the specified DAS.
        Interpolates linearly during development and late-season stages.
        """
        stage = self.get_current_stage(das)
        if stage.stage_id in ("initial", "mid_season"):
            return stage.kc_start

        # Linear interpolation for transition stages
        progress = (das - stage.start_das) / float(stage.end_das - stage.start_das)
        progress = max(0.0, min(1.0, progress))
        kc = stage.kc_start + progress * (stage.kc_end - stage.kc_start)
        return round(kc, 3)

    def get_effective_root_depth(self, das: int) -> float:
        """
        Calculate effective root depth (Zr in meters) for a given DAS.
        Ramps from 0.20m at emergence to 1.10m at flowering.
        """
        if das <= 25:
            return 0.25
        elif das >= 110:
            return 1.10
        # Continuous sigmoid or linear root expansion
        progress = (das - 25) / 85.0
        return round(0.25 + progress * (1.10 - 0.25), 2)

    def calculate_etc(self, et0: float, das: int) -> float:
        """
        Calculate potential Crop Evapotranspiration ETc = Kc * ET0 (mm/day).
        """
        kc = self.get_crop_coefficient(das)
        etc = kc * float(et0)
        return max(0.0, round(etc, 2))

    def calculate_water_stress_coefficient(
        self,
        taw_mm: float,
        depletion_dr_mm: float,
        depletion_factor_p: float = 0.55,
    ) -> float:
        """
        Calculate water stress coefficient Ks (0.0 to 1.0). FAO-56 Eq. 84:
            Ks = (TAW - Dr) / ((1 - p) * TAW)
        When Dr <= RAW (p * TAW), Ks = 1.0 (no stress).
        When Dr >= TAW, Ks = 0.0 (wilting point).
        """
        raw_mm = depletion_factor_p * taw_mm
        if depletion_dr_mm <= raw_mm:
            return 1.0
        if depletion_dr_mm >= taw_mm:
            return 0.0
        ks = (taw_mm - depletion_dr_mm) / ((1.0 - depletion_factor_p) * taw_mm)
        return max(0.0, min(1.0, float(ks)))

    def calculate_adjusted_etc(
        self,
        et0: float,
        das: int,
        taw_mm: float,
        depletion_dr_mm: float,
    ) -> float:
        """
        Calculate actual water-stressed crop evapotranspiration ETc_adj = Ks * Kc * ET0.
        """
        etc = self.calculate_etc(et0, das)
        ks = self.calculate_water_stress_coefficient(taw_mm, depletion_dr_mm)
        return round(ks * etc, 2)
