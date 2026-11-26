"""
Bilingual Irrigation Advisory Engine for Punjab Wheat Digital Twin.
Combines root-zone soil water balance, weather forecast rain deferral, and wheat growth stage priorities
to produce actionable irrigation advice (urgency, required depth mm, and tubewell run hours).

Outputs bilingual recommendations (English and Urdu Nastaliq-friendly script) with mandatory
ethical disclaimer (Rule D18).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from agritwin.advisory.crop_water import WheatCropWaterManager, WheatGrowthStage
from agritwin.advisory.water_balance import SoilWaterBalanceModel, SoilWaterState


class AdvisoryUrgency(str, Enum):
    """Urgency category for irrigation advisory."""
    OPTIMAL = "OPTIMAL"                      # Green: Soil moisture adequate
    MONITOR = "MONITOR"                      # Yellow: Nearing depletion threshold, plan soon
    CRITICAL_IRRIGATE = "CRITICAL_IRRIGATE"  # Red: RAW breached, immediate irrigation needed
    RAIN_DEFERRED = "RAIN_DEFERRED"          # Blue: Rain expected, hold off irrigation


@dataclass
class IrrigationRecommendation:
    """Comprehensive irrigation advisory recommendation."""
    urgency: AdvisoryUrgency
    urgency_color: str  # Hex code for UI badge
    current_soil_moisture_pct: float
    field_capacity_pct: float
    wilting_point_pct: float
    depletion_mm: float
    taw_mm: float
    raw_mm: float
    net_irrigation_needed_mm: float
    gross_irrigation_needed_mm: float
    volume_m3_per_acre: float
    tubewell_hours_per_acre: float
    days_after_sowing: int
    growth_stage_id: str
    growth_stage_name_en: str
    growth_stage_name_ur: str
    headline_en: str
    headline_ur: str
    reason_en: str
    reason_ur: str
    action_en: str
    action_ur: str
    disclaimer_en: str
    disclaimer_ur: str


class IrrigationAdvisoryEngine:
    """
    Core rule engine determining irrigation decisions and translating them into farmer-facing bilingual advice.
    """

    STANDARD_TUBEWELL_CUSEC = 1.0  # 1 cusec = 28.317 L/s = 101.94 m^3/hr
    M3_PER_CUSEC_HOUR = 101.941
    ACRE_TO_M2 = 4046.86
    APPLICATION_EFFICIENCY = 0.75  # 75% for surface basin/border irrigation in Punjab

    DISCLAIMER_EN = "Advisory only; calibrate with local field observations and agricultural extension advice."
    DISCLAIMER_UR = "یہ صرف مشاورتی تخمینہ ہے؛ مقامی زمینی حالات اور زرعی ماہرین کے مشورے کے مطابق عمل کریں۔"

    def __init__(
        self,
        application_efficiency: float = APPLICATION_EFFICIENCY,
        tubewell_cusec: float = STANDARD_TUBEWELL_CUSEC,
    ) -> None:
        self.efficiency = max(0.50, min(0.95, application_efficiency))
        self.tubewell_capacity_m3_h = tubewell_cusec * self.M3_PER_CUSEC_HOUR

    def evaluate_field(
        self,
        soil_water_state: SoilWaterState,
        wheat_stage: WheatGrowthStage,
        das: int,
        forecast_weather_df: Optional[pd.DataFrame] = None,
        rain_threshold_mm: float = 12.0,
    ) -> IrrigationRecommendation:
        """
        Evaluate current field state and generate bilingual recommendation.
        """
        dr = soil_water_state.depletion_dr_mm
        taw = soil_water_state.taw_mm
        raw = soil_water_state.raw_mm
        theta_v = soil_water_state.soil_moisture_pct

        # 1. Check upcoming rain forecast (next 48 hours)
        next_48h_rain = 0.0
        if forecast_weather_df is not None and not forecast_weather_df.empty:
            rain_col = "precipitation_sum" if "precipitation_sum" in forecast_weather_df.columns else "precip_mm"
            if rain_col in forecast_weather_df.columns:
                next_48h_rain = float(forecast_weather_df[rain_col].iloc[:2].sum())

        is_rain_incoming = next_48h_rain >= rain_threshold_mm

        # 2. Determine Urgency Level
        if is_rain_incoming:
            urgency = AdvisoryUrgency.RAIN_DEFERRED
            color = "#3B82F6"  # Blue
        elif dr >= raw or (wheat_stage.critical_irrigation and dr >= 0.80 * raw):
            urgency = AdvisoryUrgency.CRITICAL_IRRIGATE
            color = "#EF4444"  # Red
        elif dr >= 0.60 * raw:
            urgency = AdvisoryUrgency.MONITOR
            color = "#F59E0B"  # Yellow / Amber
        else:
            urgency = AdvisoryUrgency.OPTIMAL
            color = "#10B981"  # Green

        # 3. Calculate Water Volumes and Tubewell Hours
        if urgency in (AdvisoryUrgency.OPTIMAL, AdvisoryUrgency.RAIN_DEFERRED):
            net_depth_mm = 0.0
            gross_depth_mm = 0.0
            vol_m3_acre = 0.0
            tubewell_hrs = 0.0
        else:
            net_depth_mm = round(dr, 1)
            # Gross depth accounts for application efficiency (evaporation + distribution losses)
            gross_depth_mm = round(net_depth_mm / self.efficiency, 1)
            # Depth in mm * 4046.86 m^2 / 1000 = m^3 per acre
            vol_m3_acre = round((gross_depth_mm * self.ACRE_TO_M2) / 1000.0, 1)
            # Tubewell run duration in hours
            tubewell_hrs = round(vol_m3_acre / self.tubewell_capacity_m3_h, 2)

        # 4. Generate Bilingual Text
        if urgency == AdvisoryUrgency.CRITICAL_IRRIGATE:
            headline_en = "Immediate Irrigation Required"
            headline_ur = "آبپاشی کی فوری ضرورت ہے"
            reason_en = (
                f"Soil moisture ({theta_v:.1f}%) has depleted below the readily available threshold ({raw:.1f} mm). "
                f"Crop is currently in the critical '{wheat_stage.name_en}' stage. Delaying irrigation will cause yield loss."
            )
            reason_ur = (
                f"زمین میں نمی کا تناسب ({theta_v:.1f} فیصد) پودے کی ضرورت سے نیچے گر چکا ہے۔ "
                f"فصل اس وقت '{wheat_stage.name_ur}' کے اہم مرحلے میں ہے۔ پانی میں تاخیر پیداوار کو شدید متاثر کر سکتی ہے۔"
            )
            action_en = f"Apply {gross_depth_mm} mm of irrigation ({tubewell_hrs} hours per acre with a 1-cusec tubewell)."
            action_ur = f"ایک ایکڑ کیلئے {gross_depth_mm} ملی میٹر پانی لگائیں (1 کیوسک ٹیوب ویل {tubewell_hrs} گھنٹے چلائیں)۔"

        elif urgency == AdvisoryUrgency.MONITOR:
            headline_en = "Plan Irrigation Within 2–3 Days"
            headline_ur = "اگلے 2 سے 3 دن میں پانی کی منصوبہ بندی کریں"
            reason_en = (
                f"Soil moisture ({theta_v:.1f}%) is nearing the depletion limit. "
                f"Current depletion is {dr:.1f} mm against RAW of {raw:.1f} mm."
            )
            reason_ur = (
                f"زمین میں نمی ({theta_v:.1f} فیصد) کم ہو رہی ہے۔ "
                f"موجودہ کمی {dr:.1f} ملی میٹر ہے جبکہ محفوظ حد {raw:.1f} ملی میٹر ہے۔"
            )
            action_en = f"Prepare tubewell/canal schedule for {gross_depth_mm} mm ({tubewell_hrs} hrs/acre) in 48-72 hours."
            action_ur = f"اگلے 48 سے 72 گھنٹوں میں {gross_depth_mm} ملی میٹر ({tubewell_hrs} گھنٹے ٹیوب ویل فی ایکڑ) پانی لگانے کی تیاری کریں۔"

        elif urgency == AdvisoryUrgency.RAIN_DEFERRED:
            headline_en = "Irrigation Deferred (Rainfall Expected)"
            headline_ur = "آبپاشی موخر کریں (بارش متوقع ہے)"
            reason_en = (
                f"Weather forecast predicts {next_48h_rain:.1f} mm of rainfall within the next 48 hours. "
                f"Applying water now risks waterlogging and fertilizer leaching."
            )
            reason_ur = (
                f"محکمہ موسمیات کے مطابق اگلے 48 گھنٹوں میں {next_48h_rain:.1f} ملی میٹر بارش متوقع ہے۔ "
                f"اس وقت پانی لگانے سے کھیت میں کھڑا پانی اور کھاد ضائع ہونے کا خطرہ ہے۔"
            )
            action_en = "Hold off on all irrigation until rainfall occurs and monitor soil drying."
            action_ur = "بارش ہونے تک آبپاشی روک دیں اور بارش کے بعد زمین کی نمی کا دوبارہ معائنہ کریں۔"

        else:  # OPTIMAL
            headline_en = "Soil Moisture Optimal — No Irrigation Needed"
            headline_ur = "زمین میں نمی تسلی بخش ہے — پانی کی ضرورت نہیں"
            reason_en = (
                f"Root zone soil moisture ({theta_v:.1f}%) is in the healthy zone above readily available water threshold. "
                f"Depletion is only {dr:.1f} mm."
            )
            reason_ur = (
                f"جڑوں میں نمی کا تناسب ({theta_v:.1f} فیصد) بالکل درست ہے۔ "
                f"پانی کی کمی صرف {dr:.1f} ملی میٹر ہے جو پودے کیلئے مکمل محفوظ ہے۔"
            )
            action_en = "Maintain regular crop monitoring; no irrigation needed at this time."
            action_ur = "فصل کا معمول کے مطابق معائنہ جاری رکھیں؛ فی الحال پانی لگانے کی قطعی ضرورت نہیں۔"

        return IrrigationRecommendation(
            urgency=urgency,
            urgency_color=color,
            current_soil_moisture_pct=round(theta_v, 1),
            field_capacity_pct=soil_water_state.field_capacity_pct,
            wilting_point_pct=soil_water_state.wilting_point_pct,
            depletion_mm=round(dr, 1),
            taw_mm=round(taw, 1),
            raw_mm=round(raw, 1),
            net_irrigation_needed_mm=net_depth_mm,
            gross_irrigation_needed_mm=gross_depth_mm,
            volume_m3_per_acre=vol_m3_acre,
            tubewell_hours_per_acre=tubewell_hrs,
            days_after_sowing=das,
            growth_stage_id=wheat_stage.stage_id,
            growth_stage_name_en=wheat_stage.name_en,
            growth_stage_name_ur=wheat_stage.name_ur,
            headline_en=headline_en,
            headline_ur=headline_ur,
            reason_en=reason_en,
            reason_ur=reason_ur,
            action_en=action_en,
            action_ur=action_ur,
            disclaimer_en=self.DISCLAIMER_EN,
            disclaimer_ur=self.DISCLAIMER_UR,
        )
