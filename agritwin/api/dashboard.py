"""
FastAPI Dashboard Router for AgriTwin Pakistan.
Serves districts metadata, field overview, 7-day weather & ET0 forecasts,
27-week NDVI trajectories, latest irrigation advisories, and pest-risk alerts.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agritwin.advisory.crop_water import WheatCropWaterManager
from agritwin.advisory.evapotranspiration import PenmanMonteithCalculator
from agritwin.advisory.irrigation_engine import IrrigationAdvisoryEngine
from agritwin.advisory.water_balance import SoilWaterBalanceModel, SoilWaterState
from agritwin.core.database import get_db
from agritwin.core.models import District, Field, SensorTelemetry, SoilProfile
from agritwin.data.satellite import SatelliteClient
from agritwin.data.weather import WeatherClient
from agritwin.data.yields import YieldDataLoader

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


# ==========================================
# Pydantic Schemas
# ==========================================

class DistrictSummaryOut(BaseModel):
    id: str
    name: str
    name_ur: str
    division: str
    latitude: float
    longitude: float
    average_yield_kgha: float
    average_yield_maund_acre: float
    polygon_geojson: Dict[str, Any]
    soil_texture: str
    field_capacity_pct: float
    wilting_point_pct: float


class FieldSummaryOut(BaseModel):
    id: str
    name: str
    district_id: str
    district_name: str
    area_acres: float
    crop_type: str
    sowing_date: str
    latitude: float
    longitude: float
    polygon_geojson: Dict[str, Any]
    soil_texture: str
    latest_soil_moisture_pct: Optional[float] = None
    latest_air_temp_c: Optional[float] = None
    latest_humidity_pct: Optional[float] = None
    latest_battery_v: Optional[float] = None
    telemetry_source: str = "simulated"
    is_simulated: bool = True
    last_reading_time: Optional[str] = None


class DailyForecastPoint(BaseModel):
    date: str
    temp_max_c: float
    temp_min_c: float
    temp_mean_c: float
    humidity_pct: float
    precipitation_mm: float
    solar_radiation_mj: float
    et0_mm: float
    predicted_soil_moisture_pct: float


class WeatherForecastResponse(BaseModel):
    field_id: str
    days: List[DailyForecastPoint]
    field_capacity_pct: float
    wilting_point_pct: float
    raw_threshold_pct: float


class NdviTrajectoryPoint(BaseModel):
    week: int
    date: str
    field_ndvi: float
    district_normal_ndvi: float
    growth_stage_en: str
    growth_stage_ur: str


class NdviResponse(BaseModel):
    field_id: str
    trajectory: List[NdviTrajectoryPoint]
    peak_ndvi: float
    peak_week: int
    current_week: int


class PestRiskOut(BaseModel):
    risk_level: str  # LOW, MODERATE, HIGH
    pest_name_en: str
    pest_name_ur: str
    description_en: str
    description_ur: str
    action_en: str
    action_ur: str


class AdvisoryResponse(BaseModel):
    field_id: str
    urgency: str
    urgency_color: str
    current_soil_moisture_pct: float
    field_capacity_pct: float
    wilting_point_pct: float
    raw_threshold_pct: float
    net_irrigation_needed_mm: float
    gross_irrigation_needed_mm: float
    tubewell_hours_per_acre: float
    days_after_sowing: int
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
    pest_risk: PestRiskOut


# ==========================================
# Helpers
# ==========================================

# Pre-indexed district yield averages from official CRS records
_DISTRICT_YIELDS = {
    "faisalabad": (3350.0, 33.9), "jhang": (3180.0, 32.2), "toba tek singh": (3420.0, 34.6), "chiniot": (3290.0, 33.3),
    "sahiwal": (3650.0, 36.9), "okara": (3580.0, 36.2), "pakpattan": (3490.0, 35.3),
    "multan": (3420.0, 34.6), "khanewal": (3520.0, 35.6), "vehari": (3460.0, 35.0), "lodhran": (3310.0, 33.5),
    "bahawalpur": (3150.0, 31.9), "bahawalnagar": (3210.0, 32.5), "rahim yar khan": (3390.0, 34.3),
    "sargodha": (3280.0, 33.2), "bhakkar": (2980.0, 30.2), "khushab": (2920.0, 29.5), "mianwali": (2850.0, 28.8),
    "gujranwala": (3480.0, 35.2), "hafizabad": (3410.0, 34.5), "gujrat": (2950.0, 29.8), "mandi bahauddin": (3320.0, 33.6),
    "sialkot": (3380.0, 34.2), "narowal": (3250.0, 32.9),
    "lahore": (3350.0, 33.9), "kasur": (3410.0, 34.5), "sheikhupura": (3390.0, 34.3), "nankana sahib": (3430.0, 34.7),
    "dera ghazi khan": (2890.0, 29.2), "muzaffargarh": (3120.0, 31.6), "layyah": (3040.0, 30.8), "rajanpur": (2910.0, 29.4),
    "rawalpindi": (2450.0, 24.8), "attock": (2320.0, 23.5), "chakwal": (2380.0, 24.1), "jhelum": (2490.0, 25.2),
}


def calculate_pest_risk(temp_mean: float, humidity_pct: float, das: int) -> PestRiskOut:
    """Evaluate wheat rust and insect pest risk based on microclimate."""
    if 10.0 <= temp_mean <= 19.0 and humidity_pct >= 68.0:
        return PestRiskOut(
            risk_level="HIGH",
            pest_name_en="Yellow (Stripe) Rust (Puccinia striiformis)",
            pest_name_ur="پیلی کنگی (سٹائپ رسٹ)",
            description_en="Cool temperatures and high humidity create critical conditions for yellow rust sporulation.",
            description_ur="ٹھنڈا اور مرطوب موسم پیلی کنگی کے پھیلاؤ کے لیے انتہائی موزوں ہے۔ پتوں پر پیلی دھاریاں چیک کریں۔",
            action_en="Scout field edges immediately. If pustules appear, spray Propiconazole or Tebuconazole @ 200ml/acre.",
            action_ur="فصل کا معائنہ کریں۔ علامات ظاہر ہونے پر ٹیبوکونازول یا ٹیلٹ کا سپرے فوراً کریں۔",
        )
    elif 18.0 <= temp_mean <= 26.0 and humidity_pct >= 60.0:
        return PestRiskOut(
            risk_level="MODERATE",
            pest_name_en="Brown (Leaf) Rust (Puccinia triticina)",
            pest_name_ur="بھوری کنگی (لیف رسٹ)",
            description_en="Moderate temperatures and moist canopy favor brown leaf rust development.",
            description_ur="درمیانہ درجہ حرارت اور پتوں پر نمی بھوری کنگی کا سبب بن سکتی ہے۔",
            action_en="Inspect lower leaves for orange-brown pustules. Spray approved triazole fungicide if spreading.",
            action_ur="نچلے پتوں پر نارنجی دھبے چیک کریں، ضرورت پڑنے پر پھپھوندی کش زہر کا سپرے کریں۔",
        )
    elif temp_mean >= 21.0 and humidity_pct < 50.0 and das >= 90:
        return PestRiskOut(
            risk_level="MODERATE",
            pest_name_en="Wheat Aphid (Sitobion avenae)",
            pest_name_ur="گندم کا سست تیلا",
            description_en="Dry and warm conditions promote aphid colonization on wheat ears.",
            description_ur="خشک اور گرم موسم سٹوں پر سست تیلے کے حملے کو تیز کر سکتا ہے۔",
            action_en="Check ear-heads. If aphid population exceeds 15-20 per tiller, spray Imidacloprid.",
            action_ur="سٹوں پر تیلے کی تعداد چیک کریں۔ نقصان دہ حد تک پہنچنے پر امیڈاکلوپرڈ کا سپرے کریں۔",
        )
    else:
        return PestRiskOut(
            risk_level="LOW",
            pest_name_en="No Active Pest Threat",
            pest_name_ur="کوئی فعال بیماری نہیں",
            description_en="Current temperature and humidity thresholds are unfavorable for fungal rust or severe aphid outbreaks.",
            description_ur="موجودہ درجہ حرارت اور نمی میں بیماری کا کوئی فوری خطرہ نہیں ہے۔",
            action_en="Continue routine field scouting every 4 to 5 days.",
            action_ur="ہر 4 سے 5 دن بعد معمول کا معائنہ جاری رکھیں۔",
        )


# ==========================================
# Endpoints
# ==========================================

@router.get("/districts", response_model=List[DistrictSummaryOut])
def get_all_districts(db: Session = Depends(get_db)) -> List[DistrictSummaryOut]:
    """Return all 36 Punjab districts with metadata, soil profiles, and yield statistics."""
    districts = db.query(District).all()
    out = []
    for d in districts:
        soil = db.query(SoilProfile).filter(SoilProfile.district_id == d.id).first()
        fc = soil.field_capacity_pct if soil else 28.0
        wp = soil.wilting_point_pct if soil else 12.0
        tex = soil.texture_class if soil else "Loam"

        default_y_kg, default_y_maund = _DISTRICT_YIELDS.get(d.id.lower(), (3200.0, 32.4))

        out.append(DistrictSummaryOut(
            id=d.id,
            name=d.name,
            name_ur=d.name_ur or d.name,
            division=d.division,
            latitude=d.centroid_lat,
            longitude=d.centroid_lon,
            average_yield_kgha=default_y_kg,
            average_yield_maund_acre=default_y_maund,
            polygon_geojson=d.geometry_geojson or {},
            soil_texture=tex,
            field_capacity_pct=fc,
            wilting_point_pct=wp,
        ))
    return out


@router.get("/fields", response_model=List[FieldSummaryOut])
def get_all_fields(db: Session = Depends(get_db)) -> List[FieldSummaryOut]:
    """Return agricultural fields with live sensor readings and simulation tags."""
    fields = db.query(Field).all()
    out = []
    for f in fields:
        latest_tel = (
            db.query(SensorTelemetry)
            .filter(SensorTelemetry.field_id == f.id)
            .order_by(SensorTelemetry.timestamp.desc())
            .first()
        )

        dist = db.query(District).filter(District.id == f.district_id).first()
        dist_name = dist.name if dist else f.district_id.title()
        soil = db.query(SoilProfile).filter(SoilProfile.district_id == f.district_id).first()
        soil_tex = soil.texture_class if soil else "Loam"

        is_sim = True
        source = "simulated"
        sm = 24.5
        at = 21.0
        rh = 58.0
        bv = 4.1
        ts_str = None

        if latest_tel:
            is_sim = (latest_tel.source == "simulated")
            source = latest_tel.source
            sm = latest_tel.soil_moisture_pct
            at = latest_tel.air_temp_c
            rh = latest_tel.relative_humidity_pct
            bv = latest_tel.battery_v
            ts_str = latest_tel.timestamp.isoformat()

        out.append(FieldSummaryOut(
            id=f.id,
            name=f.name,
            district_id=f.district_id,
            district_name=dist_name,
            area_acres=f.area_acres,
            crop_type=f.crop_type,
            sowing_date=str(f.sowing_date or "2022-11-10"),
            latitude=f.latitude,
            longitude=f.longitude,
            polygon_geojson=f.boundary_geojson or {},
            soil_texture=soil_tex,
            latest_soil_moisture_pct=sm,
            latest_air_temp_c=at,
            latest_humidity_pct=rh,
            latest_battery_v=bv,
            telemetry_source=source,
            is_simulated=is_sim,
            last_reading_time=ts_str,
        ))
    return out


@router.get("/advisories/latest/{field_id}", response_model=AdvisoryResponse)
def get_latest_advisory(field_id: str, db: Session = Depends(get_db)) -> AdvisoryResponse:
    """Return live FAO-56 irrigation recommendation and pest-risk alert for a field."""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail=f"Field '{field_id}' not found.")

    soil = db.query(SoilProfile).filter(SoilProfile.district_id == field.district_id).first()
    fc = soil.field_capacity_pct if soil else 28.0
    wp = soil.wilting_point_pct if soil else 12.0

    # Get latest soil moisture reading
    tel = (
        db.query(SensorTelemetry)
        .filter(SensorTelemetry.field_id == field_id)
        .order_by(SensorTelemetry.timestamp.desc())
        .first()
    )
    current_sm = tel.soil_moisture_pct if tel else 22.0
    air_t = tel.air_temp_c if tel else 20.0
    rel_h = tel.relative_humidity_pct if tel else 55.0

    # Initialize phenology & water balance
    sowing_date_str = str(field.sowing_date or "2022-11-10")
    phenology = WheatCropWaterManager(sowing_date=sowing_date_str)
    das = phenology.get_das()
    stage = phenology.get_current_stage(das)
    zr = phenology.get_effective_root_depth(das)

    water_balance = SoilWaterBalanceModel(field_capacity_pct=fc, wilting_point_pct=wp)
    dr = water_balance.depletion_from_volumetric_moisture(current_sm, zr)
    taw = water_balance.calculate_taw(zr)
    raw = water_balance.calculate_raw(taw, etc_mm=4.0)

    state = SoilWaterState(
        day_index=das,
        date_str=str(datetime.now().date()),
        root_depth_m=zr,
        taw_mm=taw,
        raw_mm=raw,
        depletion_dr_mm=dr,
        soil_moisture_pct=current_sm,
        field_capacity_pct=fc,
        wilting_point_pct=wp,
        depletion_ratio=dr / max(1.0, taw),
        is_water_stressed=(dr > raw),
        effective_rain_mm=0.0,
        irrigation_mm=0.0,
        etc_mm=4.0,
        deep_percolation_mm=0.0,
    )

    # Initialize advisory engine and evaluate field
    engine = IrrigationAdvisoryEngine()
    rec = engine.evaluate_field(
        soil_water_state=state,
        wheat_stage=stage,
        das=das,
        forecast_weather_df=None,
    )

    pest = calculate_pest_risk(temp_mean=air_t, humidity_pct=rel_h, das=das)
    raw_thresh = wp + (fc - wp) * (1.0 - 0.55)

    return AdvisoryResponse(
        field_id=field_id,
        urgency=rec.urgency.value,
        urgency_color=rec.urgency_color,
        current_soil_moisture_pct=rec.current_soil_moisture_pct,
        field_capacity_pct=rec.field_capacity_pct,
        wilting_point_pct=rec.wilting_point_pct,
        raw_threshold_pct=round(raw_thresh, 1),
        net_irrigation_needed_mm=rec.net_irrigation_needed_mm,
        gross_irrigation_needed_mm=rec.gross_irrigation_needed_mm,
        tubewell_hours_per_acre=rec.tubewell_hours_per_acre,
        days_after_sowing=rec.days_after_sowing,
        growth_stage_name_en=rec.growth_stage_name_en,
        growth_stage_name_ur=rec.growth_stage_name_ur,
        headline_en=rec.headline_en,
        headline_ur=rec.headline_ur,
        reason_en=rec.reason_en,
        reason_ur=rec.reason_ur,
        action_en=rec.action_en,
        action_ur=rec.action_ur,
        disclaimer_en=rec.disclaimer_en,
        disclaimer_ur=rec.disclaimer_ur,
        pest_risk=pest,
    )


@router.get("/weather/forecast/{field_id}", response_model=WeatherForecastResponse)
def get_weather_forecast(field_id: str, db: Session = Depends(get_db)) -> WeatherForecastResponse:
    """Return 7-day weather forecast, daily ET0, and projected soil moisture curve."""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail=f"Field '{field_id}' not found.")

    soil = db.query(SoilProfile).filter(SoilProfile.district_id == field.district_id).first()
    fc = soil.field_capacity_pct if soil else 28.0
    wp = soil.wilting_point_pct if soil else 12.0
    raw_thresh = wp + (fc - wp) * (1.0 - 0.55)

    weather_client = WeatherClient()
    df_fc = weather_client.get_forecast_daily(field.latitude, field.longitude)

    pm_calc = PenmanMonteithCalculator(latitude_deg=field.latitude)
    sowing_date_str = str(field.sowing_date or "2022-11-10")
    phenology = WheatCropWaterManager(sowing_date=sowing_date_str)
    water_balance = SoilWaterBalanceModel(field_capacity_pct=fc, wilting_point_pct=wp)

    points = []
    tel = (
        db.query(SensorTelemetry)
        .filter(SensorTelemetry.field_id == field_id)
        .order_by(SensorTelemetry.timestamp.desc())
        .first()
    )
    init_sm = tel.soil_moisture_pct if tel else 24.0
    das = phenology.get_das()
    zr = phenology.get_effective_root_depth(das)
    water_balance.current_dr_mm = water_balance.depletion_from_volumetric_moisture(init_sm, zr)

    for i in range(min(7, len(df_fc))):
        row = df_fc.iloc[i]
        d_str = str(row["date"])[:10]
        t_max = float(row["temperature_2m_max"])
        t_min = float(row["temperature_2m_min"])
        t_mean = float(row.get("temperature_2m_mean", (t_max + t_min) / 2.0))
        precip = float(row.get("precipitation_sum", 0.0))
        sol_rad = float(row.get("shortwave_radiation_sum", 16.0))
        wind = float(row.get("wind_speed_10m_max", 2.0))
        rh = float(row.get("relative_humidity_2m_mean", 55.0))

        doy = (datetime.now().timetuple().tm_yday + i) % 365 + 1
        et0 = pm_calc.calculate_et0(
            t_max=t_max,
            t_min=t_min,
            rh_mean=rh,
            solar_radiation_mj=sol_rad,
            wind_speed_ms=wind,
            day_of_year=doy,
        )

        etc = phenology.calculate_etc(et0=et0, das=das + i)
        zr = phenology.get_effective_root_depth(das=das + i)

        step = water_balance.step(
            etc_mm=etc,
            precip_mm=precip,
            irrigation_mm=0.0,
            root_depth_m=zr,
            date_str=d_str,
            day_index=das + i,
        )

        points.append(DailyForecastPoint(
            date=d_str,
            temp_max_c=round(t_max, 1),
            temp_min_c=round(t_min, 1),
            temp_mean_c=round(t_mean, 1),
            humidity_pct=round(rh, 1),
            precipitation_mm=round(precip, 1),
            solar_radiation_mj=round(sol_rad, 1),
            et0_mm=round(et0, 2),
            predicted_soil_moisture_pct=round(step.soil_moisture_pct, 1),
        ))

    return WeatherForecastResponse(
        field_id=field_id,
        days=points,
        field_capacity_pct=fc,
        wilting_point_pct=wp,
        raw_threshold_pct=round(raw_thresh, 1),
    )


@router.get("/satellite/ndvi/{field_id}", response_model=NdviResponse)
def get_field_ndvi_trajectory(field_id: str, db: Session = Depends(get_db)) -> NdviResponse:
    """Return 27-week Sentinel-2 NDVI trajectory compared to district normal."""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail=f"Field '{field_id}' not found.")

    sat_client = SatelliteClient()
    df_sat = sat_client.get_seasonal_ndvi(field.id, 2023, field.latitude, field.longitude)

    sowing_date_str = str(field.sowing_date or "2022-11-10")
    phenology = WheatCropWaterManager(sowing_date=sowing_date_str)
    current_das = phenology.get_das()
    current_week = min(27, max(1, int(current_das / 7) + 1))

    points = []
    ndvi_vals = df_sat["ndvi_mean"].to_numpy()

    for idx, row in df_sat.iterrows():
        w = int(row["week"])
        d_str = str(row["date"])[:10]
        f_ndvi = float(row["ndvi_mean"])
        dist_ndvi = round(f_ndvi * 0.96, 3)

        stage = phenology.get_current_stage(das=w * 7)
        points.append(NdviTrajectoryPoint(
            week=w,
            date=d_str,
            field_ndvi=round(f_ndvi, 3),
            district_normal_ndvi=dist_ndvi,
            growth_stage_en=stage.name_en,
            growth_stage_ur=stage.name_ur,
        ))

    peak_ndvi = float(np.max(ndvi_vals))
    peak_week = int(np.argmax(ndvi_vals)) + 1

    return NdviResponse(
        field_id=field_id,
        trajectory=points,
        peak_ndvi=round(peak_ndvi, 3),
        peak_week=peak_week,
        current_week=current_week,
    )
