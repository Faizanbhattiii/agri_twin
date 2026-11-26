"""
Unit & Integration Tests for Advisory Engine:
- FAO-56 Penman-Monteith ET0 and Hargreaves calculation
- Wheat phenological Kc curve and root expansion
- Root zone soil water balance and deep percolation
- 7-day soil moisture sequence forecasting
- Irrigation advisory rule engine and rain deferral
- Tubewell pumping hour calculations and bilingual Urdu/English output
"""

from datetime import date, datetime
import numpy as np
import pandas as pd
import pytest

from agritwin.advisory.crop_water import (
    WheatCropWaterManager,
    WHEAT_STAGES,
)
from agritwin.advisory.evapotranspiration import PenmanMonteithCalculator
from agritwin.advisory.irrigation_engine import (
    AdvisoryUrgency,
    IrrigationAdvisoryEngine,
)
from agritwin.advisory.water_balance import (
    SoilWaterBalanceModel,
)
from agritwin.models.soil_moisture_forecaster import SoilMoistureForecaster


def test_fao56_penman_monteith_calculation():
    """Verify FAO-56 Penman-Monteith produces realistic ET0 values for Punjab climate."""
    calc = PenmanMonteithCalculator(elevation_m=184.0, latitude_deg=31.42)

    # Typical sunny March day in Faisalabad (wheat heading/flowering stage)
    et0 = calc.calculate_et0(
        t_max=28.0,
        t_min=14.0,
        rh_mean=50.0,
        solar_radiation_mj=19.5,
        wind_speed_ms=2.8,
        day_of_year=75,
    )

    # Expected ET0 for Punjab spring is between 3.5 and 5.5 mm/day
    assert 3.5 <= et0 <= 5.5
    assert isinstance(et0, float)

    # Hargreaves fallback
    hg_et0 = calc.hargreaves_et0(t_max=28.0, t_min=14.0, day_of_year=75)
    assert 3.0 <= hg_et0 <= 6.0


def test_wheat_growth_stages_and_kc():
    """Verify dynamic Kc progression across Pakistani wheat stages."""
    mgr = WheatCropWaterManager(sowing_date="2022-11-10")

    # Day 15: Initial stage
    stage_init = mgr.get_current_stage(15)
    assert stage_init.stage_id == "initial"
    assert mgr.get_crop_coefficient(15) == 0.35
    assert mgr.get_effective_root_depth(15) == 0.25

    # Day 50: Development stage (Tillering / Jointing)
    stage_dev = mgr.get_current_stage(50)
    assert stage_dev.stage_id == "development"
    kc_dev = mgr.get_crop_coefficient(50)
    assert 0.35 < kc_dev < 1.15

    # Day 90: Mid-season (Heading / Flowering / Anthesis)
    stage_mid = mgr.get_current_stage(90)
    assert stage_mid.stage_id == "mid_season"
    assert mgr.get_crop_coefficient(90) == 1.15
    assert mgr.get_effective_root_depth(90) >= 0.90

    # Day 145: Late season (Grain maturity)
    stage_late = mgr.get_current_stage(145)
    assert stage_late.stage_id == "late_season"
    assert mgr.get_crop_coefficient(145) < 1.15


def test_soil_water_balance_and_percolation():
    """Verify daily depletion tracking, TAW, RAW, and deep percolation."""
    model = SoilWaterBalanceModel(
        field_capacity_pct=28.0,
        wilting_point_pct=12.0,
        depletion_factor_p=0.55,
    )

    root_depth = 0.80  # meters
    taw = model.calculate_taw(root_depth)
    # TAW = 1000 * (0.28 - 0.12) * 0.80 = 128 mm
    assert pytest.approx(taw, abs=1.0) == 128.0

    raw = model.calculate_raw(taw, etc_mm=4.0)
    # RAW = ~0.55 * 128 = ~70.4 mm
    assert 60.0 <= raw <= 80.0

    # Step 1: 5 days of evapotranspiration without rain or irrigation
    model.current_dr_mm = 0.0
    for day in range(1, 6):
        state = model.step(etc_mm=4.0, precip_mm=0.0, irrigation_mm=0.0, root_depth_m=root_depth)

    # 5 days * 4mm = 20mm depletion
    assert pytest.approx(state.depletion_dr_mm, abs=0.5) == 20.0
    assert not state.is_water_stressed

    # Step 2: Over-irrigation causes deep percolation and resets depletion to 0
    state = model.step(etc_mm=2.0, precip_mm=0.0, irrigation_mm=40.0, root_depth_m=root_depth)
    # Dr had 20mm + 2mm ETc - 40mm Irr = -18mm -> 18mm deep percolation, Dr = 0
    assert state.deep_percolation_mm > 15.0
    assert state.depletion_dr_mm == 0.0


def test_sensor_telemetry_fusion():
    """Verify physical ESP32 soil moisture sensor reading calibrates water balance."""
    model = SoilWaterBalanceModel(field_capacity_pct=30.0, wilting_point_pct=14.0)
    model.current_dr_mm = 40.0  # Model thinks soil is dry

    # Sensor reports wet soil: 28% volumetric moisture (near FC 30%)
    state = model.step(
        etc_mm=3.0,
        precip_mm=0.0,
        irrigation_mm=0.0,
        root_depth_m=0.80,
        sensor_moisture_pct=28.0,
        sensor_fusion_weight=0.7,
    )

    # Sensor reading pulls depletion down significantly
    assert state.depletion_dr_mm < 30.0


def test_soil_moisture_forecaster_7day():
    """Verify 7-day forward forecasting engine generates realistic sequence."""
    forecaster = SoilMoistureForecaster()

    dates = pd.date_range("2023-03-01", periods=7, freq="D")
    df_fcst = pd.DataFrame({
        "date": dates,
        "temperature_2m_max": [26.0, 27.0, 28.0, 25.0, 26.0, 27.0, 29.0],
        "temperature_2m_min": [12.0, 13.0, 14.0, 12.0, 13.0, 14.0, 15.0],
        "precipitation_sum": [0.0, 0.0, 0.0, 5.0, 0.0, 0.0, 0.0],
        "shortwave_radiation_sum": [18.0, 19.0, 19.5, 12.0, 18.5, 19.0, 20.0],
        "wind_speed_10m_max": [3.2, 2.8, 3.5, 4.0, 2.5, 3.0, 3.1],
        "relative_humidity_2m_mean": [50.0, 48.0, 45.0, 70.0, 55.0, 50.0, 44.0],
    })

    traj = forecaster.forecast_7day(
        current_moisture_pct=22.0,
        field_capacity_pct=28.0,
        wilting_point_pct=12.0,
        forecast_weather_df=df_fcst,
        sowing_date="2022-11-15",
    )

    assert len(traj) == 7
    for day in traj:
        assert "date" in day
        assert "projected_moisture_pct" in day
        assert "depletion_dr_mm" in day
        assert "et0_mm" in day
        assert "etc_mm" in day
        assert day["et0_mm"] > 0.0


def test_irrigation_advisory_rules_and_rain_deferral():
    """Verify advisory engine triggers correct urgency, tubewell hours, and rain deferral."""
    engine = IrrigationAdvisoryEngine(application_efficiency=0.75, tubewell_cusec=1.0)
    mgr = WheatCropWaterManager(sowing_date="2022-11-10")
    stage_cri = mgr.get_current_stage(22)  # Critical stage: CRI

    model = SoilWaterBalanceModel(field_capacity_pct=28.0, wilting_point_pct=12.0)
    taw = model.calculate_taw(root_depth_m=0.30)
    raw = model.calculate_raw(taw, etc_mm=3.0)

    # 1. OPTIMAL: Minimal depletion
    state_opt = model.step(etc_mm=2.0, precip_mm=10.0, irrigation_mm=0.0, root_depth_m=0.30)
    rec_opt = engine.evaluate_field(state_opt, stage_cri, das=22)
    assert rec_opt.urgency == AdvisoryUrgency.OPTIMAL
    assert rec_opt.tubewell_hours_per_acre == 0.0

    # 2. CRITICAL_IRRIGATE: Severe depletion above RAW
    state_crit = model.step(etc_mm=50.0, precip_mm=0.0, irrigation_mm=0.0, root_depth_m=0.30)
    rec_crit = engine.evaluate_field(state_crit, stage_cri, das=22)
    assert rec_crit.urgency == AdvisoryUrgency.CRITICAL_IRRIGATE
    assert rec_crit.tubewell_hours_per_acre > 0.5
    assert "آبپاشی کی فوری ضرورت ہے" in rec_crit.headline_ur
    assert "Immediate Irrigation Required" in rec_crit.headline_en

    # 3. RAIN_DEFERRED: Heavy rainfall forecast in next 48 hours
    df_rain_fcst = pd.DataFrame({"precipitation_sum": [18.0, 10.0, 0.0, 0.0]})
    rec_rain = engine.evaluate_field(state_crit, stage_cri, das=22, forecast_weather_df=df_rain_fcst)
    assert rec_rain.urgency == AdvisoryUrgency.RAIN_DEFERRED
    assert "بارش متوقع ہے" in rec_rain.headline_ur
    assert rec_rain.tubewell_hours_per_acre == 0.0


def test_tubewell_hours_agronomic_scaling():
    """Verify tubewell pumping hours match Punjab agronomic standards (3 inches ≈ 3.0-3.5 hrs/acre)."""
    engine = IrrigationAdvisoryEngine(application_efficiency=0.75, tubewell_cusec=1.0)
    mgr = WheatCropWaterManager()
    stage = mgr.get_current_stage(85)  # Heading stage

    model = SoilWaterBalanceModel(field_capacity_pct=28.0, wilting_point_pct=12.0)
    # Simulate a depletion of 56.25 mm net with 0.60m root depth (TAW = 96mm, RAW = 52.8mm -> Dr > RAW)
    # Gross depth = 56.25 / 0.75 = 75.0 mm (3 inches standard irrigation)
    model.current_dr_mm = 56.25
    state = model.step(etc_mm=0.0, precip_mm=0.0, irrigation_mm=0.0, root_depth_m=0.60)

    rec = engine.evaluate_field(state, stage, das=85)

    # 75 mm gross on 1 acre = 303.5 m^3
    # 1 cusec = 101.94 m^3/hr -> ~2.98 hours
    assert pytest.approx(rec.gross_irrigation_needed_mm, abs=0.5) == 75.0
    assert pytest.approx(rec.tubewell_hours_per_acre, abs=0.2) == 2.98
    assert "ٹیوب ویل" in rec.action_ur
