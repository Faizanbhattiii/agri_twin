"""
Climate-Risk "What-If" Scenario Simulator for AgriTwin Pakistan.
Enables farmers, researchers, and agronomists to model climate shocks:
- Heatwave perturbations (+1C to +5C offset, focused on March grain-filling or whole season)
- Precipitation anomalies (-100% drought to +150% heavy rainfall)
- Irrigation delays (+7, +14, +21 days shift in watering schedule)
- Compound climate risk scenarios

Maintains strict train/serve parity (Rule 9) using WheatFeaturePipeline
and authentic DeepAgroNet / Baseline tree models.
Integrates physics-based FAO-56 Penman-Monteith daily water balance and
FAO-33 crop water production function for authentic agro-climatic simulation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

from agritwin.advisory.crop_water import WheatCropWaterManager
from agritwin.advisory.evapotranspiration import PenmanMonteithCalculator
from agritwin.advisory.water_balance import SoilWaterBalanceModel
from agritwin.core.config import BASE_DIR, DATA_DIR
from agritwin.data.satellite import SatelliteClient
from agritwin.data.soil import SoilGridsClient
from agritwin.data.weather import WeatherClient
from agritwin.data.yields import YieldDataLoader
from agritwin.features.pipeline import (
    HEAT_STRESS_THRESHOLD,
    SEASON_WEEKS,
    DAYS_PER_WEEK,
    WheatFeaturePipeline,
)
from agritwin.models.baselines import BaselineRandomForest, BaselineXGBoost
from agritwin.models.deepagronet import DeepAgroNet
from agritwin.models.metrics import to_maund_per_acre

logger = logging.getLogger(__name__)

# Catalog of Pre-configured What-If Scenarios
PRESET_SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "baseline",
        "name_en": "Historical Baseline (Normal Season)",
        "name_ur": "تاریخی معمول کا سیزن",
        "description_en": "Standard historical weather and scheduled irrigations without climate anomalies.",
        "description_ur": "بغیر کسی موسمی شدت کے معیاری تاریخی موسم اور بروقت آبپاشی۔",
        "temp_delta_c": 0.0,
        "precip_factor": 1.0,
        "irrigation_delay_days": 0,
        "target_stage": "all",
    },
    {
        "id": "terminal_heatwave",
        "name_en": "March Terminal Heatwave (+3.5°C)",
        "name_ur": "مارچ میں شدید گرمی کی لہر (+3.5°C)",
        "description_en": "Sudden temperature surge during March grain-filling, causing terminal heat stress and shriveling.",
        "description_ur": "مارچ میں دانے کے بننے کے دوران درجہ حرارت میں اچانک اضافہ جو دانے کے سکڑنے کا سبب بنتا ہے۔",
        "temp_delta_c": 3.5,
        "precip_factor": 1.0,
        "irrigation_delay_days": 0,
        "target_stage": "grain_filling",
    },
    {
        "id": "severe_drought",
        "name_en": "Winter Drought (-70% Rainfall)",
        "name_ur": "موسم سرما کی شدید خشکسالی (-70% بارش)",
        "description_en": "Failure of Western Disturbance winter rains, forcing reliance on depleted ground reserves.",
        "description_ur": "موسم سرما کی بارشوں کی شدید کمی جس سے زیر زمین نمی ختم ہو جاتی ہے۔",
        "temp_delta_c": 0.5,
        "precip_factor": 0.3,
        "irrigation_delay_days": 0,
        "target_stage": "all",
    },
    {
        "id": "delayed_irrigation_14d",
        "name_en": "14-Day Tubewell/Canal Delay",
        "name_ur": "آبپاشی میں 14 دن کی تاخیر",
        "description_en": "Canal closure or power outages delaying scheduled irrigation by two weeks during heading.",
        "description_ur": "نہر بندی یا بجلی کے تعطل کی وجہ سے نازک مرحلے پر آبپاشی میں دو ہفتے کی تاخیر۔",
        "temp_delta_c": 0.0,
        "precip_factor": 1.0,
        "irrigation_delay_days": 14,
        "target_stage": "all",
    },
    {
        "id": "compound_climate_shock",
        "name_en": "Compound Crisis: Heatwave + Drought + Delay",
        "name_ur": "مشترکہ موسمی بحران (گرمی + خشکسالی + تاخیر)",
        "description_en": "+3.0°C March heatwave combined with -50% rainfall and 14-day delayed irrigation.",
        "description_ur": "مارچ میں 3 ڈگری زیادہ گرمی، 50 فیصد کم بارش اور 14 دن تاخیر سے پانی کا مشترکہ بحران۔",
        "temp_delta_c": 3.0,
        "precip_factor": 0.5,
        "irrigation_delay_days": 14,
        "target_stage": "grain_filling",
    },
    {
        "id": "excessive_late_rain",
        "name_en": "Late Season Heavy Rain (+100% Rain)",
        "name_ur": "فصل پکنے پر غیر معمولی بارش (+100% بارش)",
        "description_en": "Unseasonal heavy rainfall and thunderstorms near harvest, raising lodging and fungal disease risks.",
        "description_ur": "کٹائی کے قریب بے وقت شدید بارش اور آندھی جس سے فصل گرنے اور بیماریوں کا خدشہ ہوتا ہے۔",
        "temp_delta_c": -1.0,
        "precip_factor": 2.0,
        "irrigation_delay_days": 0,
        "target_stage": "late_season",
    },
]


@dataclass
class AgronomicStressResult:
    """Stress indices and mitigation advice resulting from simulation."""
    heat_stress_hours: float
    heat_days_total: int
    grain_filling_heat_days: int
    water_deficit_stress_days: int
    terminal_heat_shock_severity: str  # NONE, MILD, MODERATE, SEVERE, EXTREME
    drought_severity: str  # NONE, MILD, MODERATE, SEVERE, EXTREME
    mitigation_advice_en: str
    mitigation_advice_ur: str


class AgronomicStressCalculator:
    """
    Computes agronomic stress indices from perturbed weather sequences
    and soil moisture deficit trajectories.
    """

    @staticmethod
    def compute_stress_indices(
        df_weather: pd.DataFrame,
        water_stress_days_count: int,
        temp_delta_c: float,
        grain_filling_start_day: int = 120,
    ) -> AgronomicStressResult:
        """
        Calculate heat hours above 32C, total heat days, grain-filling heat days,
        and assess severity with bilingual mitigation advice.
        """
        t_max = df_weather["temperature_2m_max"].to_numpy()
        heat_days = (t_max > HEAT_STRESS_THRESHOLD).astype(int)
        heat_days_total = int(np.sum(heat_days))

        # Grain filling period: approximately day 120 to 189 (March 1 to mid-April)
        gf_slice = t_max[grain_filling_start_day:]
        gf_heat_days = int(np.sum(gf_slice > HEAT_STRESS_THRESHOLD))

        # Degree-hours estimation: each degree above 32C represents ~8 active hot midday hours
        excess_degrees = np.maximum(0.0, t_max - HEAT_STRESS_THRESHOLD)
        heat_stress_hours = float(np.sum(excess_degrees) * 8.0)

        # Classify Terminal Heat Shock
        if gf_heat_days >= 14 or temp_delta_c >= 3.5:
            heat_severity = "EXTREME"
        elif gf_heat_days >= 8 or temp_delta_c >= 2.5:
            heat_severity = "SEVERE"
        elif gf_heat_days >= 3 or temp_delta_c >= 1.0:
            heat_severity = "MODERATE"
        elif gf_heat_days >= 1 or temp_delta_c > 0.0:
            heat_severity = "MILD"
        else:
            heat_severity = "NONE"

        # Classify Drought Severity based on water deficit days
        if water_stress_days_count >= 30:
            drought_severity = "EXTREME"
        elif water_stress_days_count >= 18:
            drought_severity = "SEVERE"
        elif water_stress_days_count >= 8:
            drought_severity = "MODERATE"
        elif water_stress_days_count >= 2:
            drought_severity = "MILD"
        else:
            drought_severity = "NONE"

        # Formulate Targeted Mitigation Advice
        adv_en_parts = []
        adv_ur_parts = []

        if heat_severity in ["SEVERE", "EXTREME"]:
            adv_en_parts.append(
                "Apply light canopy-cooling irrigation during early morning hours to lower microclimate temperature. "
                "Foliar application of Potassium Nitrate (KNO3 @ 1.5-2%) or Zinc EDTA can mitigate terminal heat injury."
            )
            adv_ur_parts.append(
                "درجہ حرارت کم رکھنے کے لیے صبح سویرے ہلکا پانی لگائیں۔ گرمی کے دباؤ کو کم کرنے کے لیے پوٹاشیم نائٹریٹ یا زنک کا سپرے کریں۔"
            )
        elif heat_severity == "MODERATE":
            adv_en_parts.append(
                "Monitor midday canopy temperature and ensure soil profile remains moist to support transpiration cooling."
            )
            adv_ur_parts.append(
                "فصل کو گرمی سے بچانے کے لیے زمین میں مناسب وتر برقرار رکھیں تاکہ پودے کا درجہ حرارت اعتدال میں رہے۔"
            )

        if drought_severity in ["SEVERE", "EXTREME"]:
            adv_en_parts.append(
                "Acute water deficit detected. Prioritize tubewell pumping immediately. "
                "Employ alternate furrow irrigation or laser-leveled flood basins to maximize water use efficiency."
            )
            adv_ur_parts.append(
                "شدید خشک سالی کی صورت میں فوراً ٹیوب ویل چلائیں۔ پانی کے ضیاع سے بچنے کے لیے ایک کیاری چھوڑ کر ایک کیاری کو پانی دیں۔"
            )
        elif drought_severity == "MODERATE":
            adv_en_parts.append(
                "Soil moisture is depleting below readily available threshold. Schedule irrigation within the next 48 to 72 hours."
            )
            adv_ur_parts.append(
                "زمین میں نمی مطلوبہ حد سے کم ہو رہی ہے۔ اگلے 2 سے 3 دنوں کے اندر آبپاشی کا بندوبست کریں۔"
            )

        if not adv_en_parts:
            adv_en_parts.append(
                "Conditions are within optimal agronomic thresholds. Continue standard farm management."
            )
            adv_ur_parts.append(
                "موسمی اور زمینی حالات معمول کے مطابق ہیں۔ معمول کی دیکھ بھال جاری رکھیں۔"
            )

        return AgronomicStressResult(
            heat_stress_hours=round(heat_stress_hours, 1),
            heat_days_total=heat_days_total,
            grain_filling_heat_days=gf_heat_days,
            water_deficit_stress_days=water_stress_days_count,
            terminal_heat_shock_severity=heat_severity,
            drought_severity=drought_severity,
            mitigation_advice_en=" ".join(adv_en_parts),
            mitigation_advice_ur=" ".join(adv_ur_parts),
        )


class WhatIfSimulator:
    """
    Core interactive simulation engine for AgriTwin Pakistan.
    Applies climate and management perturbations to baseline data,
    evaluates soil moisture depletion, and calculates differential yield
    impacts using DeepAgroNet and tree baselines.
    """

    def __init__(
        self,
        models_dir: Optional[Path] = None,
        device: Optional[str] = None,
    ) -> None:
        self.models_dir = models_dir or (BASE_DIR / "models")
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # Lazy loaded components
        self._pipeline: Optional[WheatFeaturePipeline] = None
        self._deepagronet: Optional[DeepAgroNet] = None
        self._rf_model: Optional[BaselineRandomForest] = None
        self._xgb_model: Optional[BaselineXGBoost] = None

        self.weather_client = WeatherClient()
        self.soil_client = SoilGridsClient()
        self.satellite_client = SatelliteClient()

    def get_pipeline(self) -> WheatFeaturePipeline:
        """Load or return cached feature pipeline."""
        if self._pipeline is None:
            scaler_path = self.models_dir / "pipeline_scaler.pkl"
            if scaler_path.exists():
                self._pipeline = WheatFeaturePipeline.load_pipeline(scaler_path)
            else:
                self._pipeline = WheatFeaturePipeline()
        return self._pipeline

    def get_deepagronet(self) -> DeepAgroNet:
        """Load or return cached DeepAgroNet model."""
        if self._deepagronet is None:
            ckpt_path = self.models_dir / "deepagronet_best.pt"
            dan = DeepAgroNet().to(self.device)
            if ckpt_path.exists():
                ckpt = torch.load(ckpt_path, map_location=self.device, weights_only=False)
                dan.load_state_dict(ckpt["model_state_dict"])
                dan.set_target_normalizer(ckpt.get("target_mean", 0.0), ckpt.get("target_std", 1.0))
            dan.eval()
            self._deepagronet = dan
        return self._deepagronet

    def get_rf_model(self) -> BaselineRandomForest:
        """Load or return cached Random Forest model."""
        if self._rf_model is None:
            rf = BaselineRandomForest()
            rf_path = self.models_dir / "rf_best.joblib"
            if rf_path.exists():
                rf.load(rf_path)
            self._rf_model = rf
        return self._rf_model

    def get_xgb_model(self) -> BaselineXGBoost:
        """Load or return cached XGBoost model."""
        if self._xgb_model is None:
            xgb = BaselineXGBoost()
            xgb_path = self.models_dir / "xgb_best.json"
            if xgb_path.exists():
                xgb.load(xgb_path)
            self._xgb_model = xgb
        return self._xgb_model

    def get_baseline_inputs(
        self,
        district_name: str = "faisalabad",
        season: str = "2022-23",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any], float, float]:
        """
        Fetch or construct baseline daily weather, satellite NDVI series,
        soil profile, and geographic coordinates for a district.
        """
        dist_norm = district_name.strip().lower()
        try:
            yd_loader = YieldDataLoader()
            df_yd = yd_loader.get_all()
            matched = df_yd[df_yd["district"].str.lower() == dist_norm]
            if len(matched) > 0:
                lat = float(matched.iloc[0]["latitude"])
                lon = float(matched.iloc[0]["longitude"])
            else:
                lat, lon = 31.418, 73.079
        except Exception:
            lat, lon = 31.418, 73.079

        start_year = int(season.split("-")[0])
        start_date = f"{start_year}-11-01"
        end_date = f"{start_year + 1}-05-10"
        harvest_year = start_year + 1

        # 1. Weather series
        df_weather = self.weather_client.get_historical_daily(lat, lon, start_date, end_date)

        # 2. Satellite trajectory
        df_sat = self.satellite_client.get_seasonal_ndvi(dist_norm, harvest_year, lat, lon)

        # 3. Soil profile
        soil_profile = self.soil_client.get_soil_profile(lat, lon)

        return df_weather, df_sat, soil_profile, lat, lon

    def apply_perturbations(
        self,
        df_weather: pd.DataFrame,
        df_sat: pd.DataFrame,
        soil_profile: Dict[str, Any],
        temp_delta_c: float = 0.0,
        precip_factor: float = 1.0,
        irrigation_delay_days: int = 0,
        target_stage: str = "all",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, int, float, List[Dict[str, Any]]]:
        """
        Apply climate and management perturbations to weather and satellite series.
        Simulates soil water balance to derive water stress days and moisture trajectory.

        Returns:
            w_df, s_df, water_stress_days, water_stress_ratio, daily_trajectory
        """
        w_df = df_weather.copy()
        s_df = df_sat.copy()

        n_days = len(w_df)
        temp_mask = np.zeros(n_days, dtype=bool)

        if target_stage == "grain_filling":
            temp_mask[min(126, n_days):] = True
        elif target_stage == "flowering":
            temp_mask[min(84, n_days):min(126, n_days)] = True
        elif target_stage == "late_season":
            temp_mask[min(140, n_days):] = True
        else:  # 'all'
            temp_mask[:] = True

        # 1. Apply Temperature Perturbation
        if temp_delta_c != 0.0:
            w_df.loc[temp_mask, "temperature_2m_mean"] += temp_delta_c
            w_df.loc[temp_mask, "temperature_2m_max"] += temp_delta_c
            w_df.loc[temp_mask, "temperature_2m_min"] += temp_delta_c

        # 2. Apply Precipitation Perturbation
        if precip_factor != 1.0:
            w_df["precipitation_sum"] = np.maximum(0.0, w_df["precipitation_sum"] * precip_factor)

        # 3. Simulate Root-Zone Water Balance over Season
        baseline_irrigation_days = {25: 75.0, 60: 75.0, 95: 75.0, 125: 75.0}
        actual_irrigation_schedule = {}
        for d, amt in baseline_irrigation_days.items():
            actual_day = min(d + irrigation_delay_days, n_days - 1)
            actual_irrigation_schedule[actual_day] = amt

        lat = float(soil_profile.get("latitude", 31.42))
        pm_calc = PenmanMonteithCalculator(latitude_deg=lat)
        phenology = WheatCropWaterManager(sowing_date="2022-11-01")
        water_balance = SoilWaterBalanceModel(
            field_capacity_pct=float(soil_profile.get("field_capacity_pct", 28.0)),
            wilting_point_pct=float(soil_profile.get("wilting_point_pct", 12.0)),
            soil_texture=str(soil_profile.get("soil_texture", "Loam")),
        )

        daily_trajectory = []
        water_stress_days = 0
        total_etc = 0.0
        total_etc_adj = 0.0

        for day_idx in range(n_days):
            row = w_df.iloc[day_idx]
            day_of_season = day_idx + 1

            t_max = float(row["temperature_2m_max"])
            t_min = float(row["temperature_2m_min"])
            rh = float(row.get("relative_humidity_2m_mean", 55.0))
            wind = float(row.get("wind_speed_10m_max", 2.0))
            sol_rad = float(row.get("shortwave_radiation_sum", 15.0))
            precip = float(row["precipitation_sum"])

            # Compute FAO-56 reference ET0
            doy = (day_idx + 305) % 365 + 1
            et0 = pm_calc.calculate_et0(
                t_max=t_max,
                t_min=t_min,
                rh_mean=rh,
                solar_radiation_mj=sol_rad,
                wind_speed_ms=wind,
                day_of_year=doy,
            )

            # Crop ETc and root depth
            etc = phenology.calculate_etc(et0=et0, das=day_of_season)
            root_depth = phenology.get_effective_root_depth(das=day_of_season)
            irrigation_applied = actual_irrigation_schedule.get(day_idx, 0.0)

            # Water balance daily step
            state = water_balance.step(
                etc_mm=etc,
                precip_mm=precip,
                irrigation_mm=irrigation_applied,
                root_depth_m=root_depth,
                date_str=str(row.get("date", f"Day {day_of_season}")),
                day_index=day_of_season,
            )

            # Water stress calculation
            ks = phenology.calculate_water_stress_coefficient(
                taw_mm=state.taw_mm,
                depletion_dr_mm=state.depletion_dr_mm,
            )
            etc_adj = etc * ks
            total_etc += etc
            total_etc_adj += etc_adj

            if state.is_water_stressed:
                water_stress_days += 1

            daily_trajectory.append({
                "day": day_of_season,
                "date": state.date_str,
                "temp_mean": float(row["temperature_2m_mean"]),
                "temp_max": t_max,
                "precip": precip,
                "et0": et0,
                "depletion_mm": state.depletion_dr_mm,
                "raw_mm": state.raw_mm,
                "taw_mm": state.taw_mm,
                "soil_moisture_pct": state.soil_moisture_pct,
                "water_stress": state.is_water_stressed,
            })

        # Calculate relative cumulative transpiration deficit
        water_stress_ratio = max(0.0, 1.0 - (total_etc_adj / max(1.0, total_etc)))

        # 4. Phenological Feedback to Satellite NDVI Trajectory
        ndvi_arr = s_df["ndvi_mean"].to_numpy().copy()
        is_baseline = (temp_delta_c == 0.0 and precip_factor == 1.0 and irrigation_delay_days == 0)
        if not is_baseline and (temp_delta_c > 1.0 or water_stress_days > 10):
            stress_penalty = min(0.30, (temp_delta_c * 0.03) + (water_stress_ratio * 0.15))
            for w in range(18, len(ndvi_arr)):
                decay_factor = 1.0 - stress_penalty * ((w - 17) / 10.0)
                ndvi_arr[w] = max(0.12, ndvi_arr[w] * decay_factor)
            s_df["ndvi_mean"] = ndvi_arr
            if "evi" in s_df.columns:
                s_df["evi"] = ndvi_arr * 0.78

        return w_df, s_df, water_stress_days, water_stress_ratio, daily_trajectory

    def run_scenario(
        self,
        district_id: str = "faisalabad",
        temp_delta_c: float = 0.0,
        precip_factor: float = 1.0,
        irrigation_delay_days: int = 0,
        target_stage: str = "all",
        model_name: str = "deepagronet",
        baseline_season: str = "2022-23",
    ) -> Dict[str, Any]:
        """
        Execute an end-to-end what-if climate perturbation simulation.
        """
        start_time = datetime.now(timezone.utc)
        pipeline = self.get_pipeline()
        is_baseline = (temp_delta_c == 0.0 and precip_factor == 1.0 and irrigation_delay_days == 0)

        # 1. Fetch baseline inputs
        w_base, s_base, soil_profile, lat, lon = self.get_baseline_inputs(district_id, baseline_season)

        # Baseline water balance
        w_base_sim, s_base_sim, base_stress_days, base_water_ratio, _ = self.apply_perturbations(
            df_weather=w_base,
            df_sat=s_base,
            soil_profile=soil_profile,
            temp_delta_c=0.0,
            precip_factor=1.0,
            irrigation_delay_days=0,
            target_stage="all",
        )

        # 2. Extract baseline features
        base_temp_mat = pipeline.extract_temporal_matrix(w_base_sim, s_base_sim)
        base_stat_vec = pipeline.extract_static_vector(soil_profile, lat, lon)
        base_tab_vec = pipeline.extract_tabular_features(base_temp_mat, base_stat_vec)

        # 3. Apply perturbations
        w_scen, s_scen, scen_stress_days, scen_water_ratio, daily_traj = self.apply_perturbations(
            df_weather=w_base,
            df_sat=s_base,
            soil_profile=soil_profile,
            temp_delta_c=temp_delta_c,
            precip_factor=precip_factor,
            irrigation_delay_days=irrigation_delay_days,
            target_stage=target_stage,
        )

        excess_water_ratio = max(0.0, scen_water_ratio - base_water_ratio)
        extra_stress_days = max(0, scen_stress_days - base_stress_days)

        # 4. Extract perturbed features
        scen_temp_mat = pipeline.extract_temporal_matrix(w_scen, s_scen)
        scen_stat_vec = pipeline.extract_static_vector(soil_profile, lat, lon)
        scen_tab_vec = pipeline.extract_tabular_features(scen_temp_mat, scen_stat_vec)

        # 5. Predict Yields with Selected Model
        model_clean = model_name.lower().strip()
        uncertainty_bounds = None

        if model_clean == "random_forest":
            rf = self.get_rf_model()
            X_base = pipeline.scale_tabular(base_tab_vec).reshape(1, -1)
            X_scen = pipeline.scale_tabular(scen_tab_vec).reshape(1, -1)
            base_yield_kg = float(rf.predict(X_base)[0])
            raw_scen_yield_kg = float(rf.predict(X_scen)[0])
        elif model_clean == "xgboost":
            xgb = self.get_xgb_model()
            X_base = pipeline.scale_tabular(base_tab_vec).reshape(1, -1)
            X_scen = pipeline.scale_tabular(scen_tab_vec).reshape(1, -1)
            base_yield_kg = float(xgb.predict(X_base)[0])
            raw_scen_yield_kg = float(xgb.predict(X_scen)[0])
        else:
            dan = self.get_deepagronet()
            t_base_sc = torch.tensor(pipeline.scale_temporal(base_temp_mat)).unsqueeze(0).to(self.device)
            s_base_sc = torch.tensor(pipeline.scale_static(base_stat_vec)).unsqueeze(0).to(self.device)
            t_scen_sc = torch.tensor(pipeline.scale_temporal(scen_temp_mat)).unsqueeze(0).to(self.device)
            s_scen_sc = torch.tensor(pipeline.scale_static(scen_stat_vec)).unsqueeze(0).to(self.device)

            base_pred = dan.predict_yield(t_base_sc, s_base_sc)
            scen_pred = dan.predict_yield(t_scen_sc, s_scen_sc)

            base_yield_kg = float(base_pred["yield_kgha"][0])
            raw_scen_yield_kg = float(scen_pred["yield_kgha"][0])

            uncertainty_bounds = {
                "base_lower_kgha": float(base_pred["lower_kgha"][0]),
                "base_upper_kgha": float(base_pred["upper_kgha"][0]),
                "scen_lower_kgha": float(scen_pred["lower_kgha"][0]),
                "scen_upper_kgha": float(scen_pred["upper_kgha"][0]),
                "base_lower_maund": float(base_pred["lower_maund_acre"][0]),
                "base_upper_maund": float(base_pred["upper_maund_acre"][0]),
                "scen_lower_maund": float(scen_pred["lower_maund_acre"][0]),
                "scen_upper_maund": float(scen_pred["upper_maund_acre"][0]),
                "sigma_kgha": float(scen_pred["sigma_kgha"][0]),
            }

        # 6. Hybrid Digital Twin Yield Modulation
        # Integrates physical FAO-33 water production function and terminal heat stress biology
        if is_baseline:
            scen_yield_kg = base_yield_kg
            stress_yield_factor = 1.0
        else:
            # FAO-33 water deficit yield reduction factor: Ky * (1 - ETc_adj / ETc)
            # Ky for wheat = 1.05 applied to excess deficit beyond baseline
            water_stress_penalty = 1.05 * excess_water_ratio + (extra_stress_days * 0.003)

            # Terminal heat stress penalty during March grain filling (Asseng et al. 2015)
            # ~4% yield reduction per degree Celsius heat shock
            gf_slice = w_scen["temperature_2m_max"].to_numpy()[120:]
            gf_excess = np.maximum(0.0, gf_slice - HEAT_STRESS_THRESHOLD)
            heat_penalty = min(0.35, float(np.sum(gf_excess) * 0.007))

            # Direct temperature offset penalty during grain filling
            if target_stage in ["grain_filling", "all"] and temp_delta_c > 0:
                heat_penalty += (temp_delta_c * 0.035)

            stress_yield_factor = max(0.30, 1.0 - water_stress_penalty - heat_penalty)
            scen_yield_kg = raw_scen_yield_kg * stress_yield_factor

        # Adjust uncertainty bounds if present
        if uncertainty_bounds:
            if is_baseline:
                uncertainty_bounds["scen_lower_kgha"] = uncertainty_bounds["base_lower_kgha"]
                uncertainty_bounds["scen_upper_kgha"] = uncertainty_bounds["base_upper_kgha"]
                uncertainty_bounds["scen_lower_maund"] = uncertainty_bounds["base_lower_maund"]
                uncertainty_bounds["scen_upper_maund"] = uncertainty_bounds["base_upper_maund"]
            else:
                uncertainty_bounds["scen_lower_kgha"] = round(uncertainty_bounds["scen_lower_kgha"] * stress_yield_factor, 1)
                uncertainty_bounds["scen_upper_kgha"] = round(uncertainty_bounds["scen_upper_kgha"] * stress_yield_factor, 1)
                uncertainty_bounds["scen_lower_maund"] = round(float(to_maund_per_acre(uncertainty_bounds["scen_lower_kgha"])), 2)
                uncertainty_bounds["scen_upper_maund"] = round(float(to_maund_per_acre(uncertainty_bounds["scen_upper_kgha"])), 2)

        # 7. Compute Differences
        delta_kg = 0.0 if is_baseline else (scen_yield_kg - base_yield_kg)
        delta_pct = 0.0 if is_baseline else ((delta_kg / base_yield_kg) * 100.0 if base_yield_kg > 0 else 0.0)

        base_maund = float(to_maund_per_acre(base_yield_kg))
        scen_maund = float(to_maund_per_acre(scen_yield_kg))
        delta_maund = 0.0 if is_baseline else (scen_maund - base_maund)

        # 8. Compute Agronomic Stress Indices
        stress_res = AgronomicStressCalculator.compute_stress_indices(
            df_weather=w_scen,
            water_stress_days_count=extra_stress_days,
            temp_delta_c=temp_delta_c,
        )

        # 9. Aggregate 27-Week Trajectory for Frontend Charts
        weekly_trajectory = []
        for w in range(SEASON_WEEKS):
            base_t = float(base_temp_mat[w, 2])
            scen_t = float(scen_temp_mat[w, 2])
            base_p = float(base_temp_mat[w, 1])
            scen_p = float(scen_temp_mat[w, 1])
            base_n = float(base_temp_mat[w, 8])
            scen_n = float(scen_temp_mat[w, 8])

            start_d = w * DAYS_PER_WEEK
            end_d = min((w + 1) * DAYS_PER_WEEK, len(daily_traj))
            week_days = daily_traj[start_d:end_d] if start_d < len(daily_traj) else []
            sm_avg = float(np.mean([d["soil_moisture_pct"] for d in week_days])) if week_days else 22.0
            stress_active = any(d["water_stress"] for d in week_days)

            weekly_trajectory.append({
                "week": w + 1,
                "baseline_temp_mean_c": round(base_t, 1),
                "scenario_temp_mean_c": round(scen_t, 1),
                "baseline_precip_mm": round(base_p, 1),
                "scenario_precip_mm": round(scen_p, 1),
                "baseline_ndvi": round(base_n, 3),
                "scenario_ndvi": round(scen_n, 3),
                "soil_moisture_pct": round(sm_avg, 1),
                "water_stress_active": stress_active,
            })

        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0

        return {
            "district_id": district_id,
            "district_name": district_id.replace("_", " ").title(),
            "model_used": model_clean,
            "baseline_yield_kgha": round(base_yield_kg, 1),
            "scenario_yield_kgha": round(scen_yield_kg, 1),
            "delta_kgha": round(delta_kg, 1),
            "delta_pct": round(delta_pct, 2),
            "baseline_yield_maund_acre": round(base_maund, 2),
            "scenario_yield_maund_acre": round(scen_maund, 2),
            "delta_maund_acre": round(delta_maund, 2),
            "uncertainty_bounds": uncertainty_bounds,
            "stress_indices": {
                "heat_stress_hours": stress_res.heat_stress_hours,
                "heat_days_total": stress_res.heat_days_total,
                "grain_filling_heat_days": stress_res.grain_filling_heat_days,
                "water_deficit_stress_days": stress_res.water_deficit_stress_days,
                "terminal_heat_shock_severity": stress_res.terminal_heat_shock_severity,
                "drought_severity": stress_res.drought_severity,
            },
            "mitigation_advice_en": stress_res.mitigation_advice_en,
            "mitigation_advice_ur": stress_res.mitigation_advice_ur,
            "weekly_trajectory": weekly_trajectory,
            "disclaimer_en": "Simulation for advisory and risk exploration only. Not guaranteed yield outcome.",
            "disclaimer_ur": "یہ پیشین گوئی محض آزمائشی اور معلوماتی مقاصد کے لیے ہے۔ حتمی پیداوار کے لیے مقامی ماہرین زراعت سے مشورہ کریں۔",
            "execution_time_ms": round(duration_ms, 1),
        }
