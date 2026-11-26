"""
7-Day Soil Moisture Sequence Forecaster.
Projects daily volumetric soil moisture (%) and root-zone depletion (mm) over a 7-day horizon
by coupling the FAO-56 Penman-Monteith ET0 engine, wheat Kc dynamics, and daily water balance.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from agritwin.advisory.crop_water import WheatCropWaterManager
from agritwin.advisory.evapotranspiration import PenmanMonteithCalculator
from agritwin.advisory.water_balance import SoilWaterBalanceModel, SoilWaterState


class SoilMoistureForecaster:
    """
    Forecaster generating 7-day forward soil moisture and depletion trajectories.
    """

    def __init__(
        self,
        elevation_m: float = 184.0,
        latitude_deg: float = 31.42,
    ) -> None:
        self.et0_calc = PenmanMonteithCalculator(elevation_m, latitude_deg)

    def forecast_7day(
        self,
        current_moisture_pct: float,
        field_capacity_pct: float,
        wilting_point_pct: float,
        forecast_weather_df: pd.DataFrame,
        sowing_date: Optional[str] = None,
        depletion_factor_p: float = 0.55,
        planned_irrigation_schedule: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Project 7-day soil moisture and water stress trajectory.

        Parameters:
            current_moisture_pct: Initial soil moisture % (e.g. from telemetry or latest model state)
            field_capacity_pct: Soil field capacity % (e.g. 28.0)
            wilting_point_pct: Soil permanent wilting point % (e.g. 12.0)
            forecast_weather_df: 7-day daily weather forecast with columns:
                ['date', 'temperature_2m_max', 'temperature_2m_min', 'precipitation_sum',
                 'shortwave_radiation_sum', 'wind_speed_10m_max', 'relative_humidity_2m_mean']
            sowing_date: Sowing date YYYY-MM-DD
            depletion_factor_p: Wheat depletion fraction (default 0.55)
            planned_irrigation_schedule: Dict mapping date string 'YYYY-MM-DD' -> mm of water

        Returns:
            List of 7 daily forecast dicts with projected moisture, depletion, and stress status.
        """
        crop_mgr = WheatCropWaterManager(sowing_date)
        model = SoilWaterBalanceModel(
            field_capacity_pct=field_capacity_pct,
            wilting_point_pct=wilting_point_pct,
            depletion_factor_p=depletion_factor_p,
        )

        planned_irrig = planned_irrigation_schedule or {}

        # Initialize model's current depletion from starting volumetric moisture
        first_date_str = str(forecast_weather_df["date"].iloc[0])[:10]
        init_das = crop_mgr.get_das(first_date_str)
        init_zr = crop_mgr.get_effective_root_depth(init_das)
        model.current_dr_mm = model.depletion_from_volumetric_moisture(current_moisture_pct, init_zr)

        results: List[Dict[str, Any]] = []

        for idx, row in forecast_weather_df.iterrows():
            date_str = str(row["date"])[:10]
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            doy = dt.timetuple().tm_yday
            das = crop_mgr.get_das(date_str)
            zr = crop_mgr.get_effective_root_depth(das)

            t_max = float(row.get("temperature_2m_max", 24.0))
            t_min = float(row.get("temperature_2m_min", 10.0))
            rh = float(row.get("relative_humidity_2m_mean", 55.0))
            sol_rad = float(row.get("shortwave_radiation_sum", 16.0))
            wind = float(row.get("wind_speed_10m_max", 3.0))
            precip = float(row.get("precipitation_sum", 0.0))

            # 1. ET0 calculation
            et0 = self.et0_calc.calculate_et0(
                t_max=t_max,
                t_min=t_min,
                rh_mean=rh,
                solar_radiation_mj=sol_rad,
                wind_speed_ms=wind,
                day_of_year=doy,
            )

            # 2. Potential and adjusted ETc
            taw = model.calculate_taw(zr)
            etc = crop_mgr.calculate_adjusted_etc(et0, das, taw, model.current_dr_mm)

            # 3. Check planned irrigation
            irr = planned_irrig.get(date_str, 0.0)

            # 4. Advance 1 day
            state: SoilWaterState = model.step(
                etc_mm=etc,
                precip_mm=precip,
                irrigation_mm=irr,
                root_depth_m=zr,
                date_str=date_str,
                day_index=idx,
            )

            stage = crop_mgr.get_current_stage(das)

            results.append({
                "day_offset": idx + 1,
                "date": date_str,
                "das": das,
                "growth_stage_id": stage.stage_id,
                "growth_stage_en": stage.name_en,
                "growth_stage_ur": stage.name_ur,
                "root_depth_m": state.root_depth_m,
                "projected_moisture_pct": state.soil_moisture_pct,
                "depletion_dr_mm": state.depletion_dr_mm,
                "taw_mm": state.taw_mm,
                "raw_mm": state.raw_mm,
                "is_water_stressed": state.is_water_stressed,
                "et0_mm": round(et0, 2),
                "etc_mm": state.etc_mm,
                "precip_mm": precip,
                "irrigation_applied_mm": irr,
            })

        return results
