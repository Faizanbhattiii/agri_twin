"""
Root Zone Soil Water Balance & Depletion Engine (FAO-56 Dual/Single Layer).
Tracks daily soil moisture depletion, Total Available Water (TAW), Readily Available Water (RAW),
deep percolation, and fuses ground ESP32 telemetry with water accounting.

Key Formulations:
1. TAW = 1000 * (theta_FC - theta_WP) * Zr  [mm]
2. RAW = p * TAW                             [mm]
3. D_{r,t} = D_{r,t-1} - (P_t - RO_t) - I_t + ET_{c,t} + DP_t  [mm]
4. Volumetric moisture theta_v = theta_FC - (D_r / (1000 * Zr))
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np


@dataclass
class SoilWaterState:
    """Snapshot of root zone soil water status for a single day."""
    day_index: int
    date_str: str
    root_depth_m: float
    taw_mm: float
    raw_mm: float
    depletion_dr_mm: float
    soil_moisture_pct: float
    field_capacity_pct: float
    wilting_point_pct: float
    depletion_ratio: float  # Dr / TAW
    is_water_stressed: bool  # Dr > RAW
    effective_rain_mm: float
    irrigation_mm: float
    etc_mm: float
    deep_percolation_mm: float


class SoilWaterBalanceModel:
    """
    Daily root-zone soil water balance accountant adhering to FAO-56.
    """

    def __init__(
        self,
        field_capacity_pct: float = 28.0,
        wilting_point_pct: float = 12.0,
        depletion_factor_p: float = 0.55,
        soil_texture: str = "Loam",
    ) -> None:
        self.theta_fc = float(field_capacity_pct) / 100.0
        self.theta_wp = float(wilting_point_pct) / 100.0
        self.p_base = float(depletion_factor_p)
        self.soil_texture = soil_texture

        if self.theta_fc <= self.theta_wp:
            raise ValueError(f"Field capacity ({field_capacity_pct}%) must exceed wilting point ({wilting_point_pct}%)")

        self.current_dr_mm: float = 0.0  # Initial depletion: 0 = at field capacity

    def calculate_taw(self, root_depth_m: float) -> float:
        """Calculate Total Available Water (TAW in mm). FAO-56 Eq. 82: TAW = 1000 * (theta_FC - theta_WP) * Zr."""
        taw = 1000.0 * (self.theta_fc - self.theta_wp) * float(root_depth_m)
        return max(5.0, round(taw, 2))

    def calculate_raw(self, taw_mm: float, etc_mm: float = 4.0) -> float:
        """
        Calculate Readily Available Water (RAW in mm). FAO-56 Eq. 83: RAW = p * TAW.
        Adjusts depletion factor p for high evaporative demand: p = p_base + 0.04 * (5.0 - ETc).
        """
        adj_p = self.p_base + 0.04 * (5.0 - float(etc_mm))
        adj_p = max(0.10, min(0.80, adj_p))
        raw = adj_p * taw_mm
        return max(2.0, round(raw, 2))

    def depletion_from_volumetric_moisture(self, theta_pct: float, root_depth_m: float) -> float:
        """
        Convert volumetric soil moisture percentage (e.g. from ESP32 capacitive probe) to depletion (mm).
        Dr = 1000 * (theta_FC - theta_v) * Zr
        """
        theta_v = float(theta_pct) / 100.0
        dr = 1000.0 * (self.theta_fc - theta_v) * float(root_depth_m)
        taw = self.calculate_taw(root_depth_m)
        return max(0.0, min(taw * 1.2, float(dr)))

    def volumetric_moisture_from_depletion(self, dr_mm: float, root_depth_m: float) -> float:
        """
        Convert depletion (mm) to volumetric moisture percentage (%).
        theta_v = theta_FC - (Dr / (1000 * Zr))
        """
        zr = max(0.1, float(root_depth_m))
        theta_v = self.theta_fc - (float(dr_mm) / (1000.0 * zr))
        # Clamp between oven-dry (~0%) and saturation (~theta_fc * 1.3)
        theta_v = max(self.theta_wp * 0.4, min(self.theta_fc * 1.25, theta_v))
        return round(theta_v * 100.0, 2)

    def calculate_effective_rain(self, precip_mm: float) -> float:
        """
        Estimate effective rainfall (P_eff in mm) available to root zone.
        Uses USDA-SCS empirical monthly / daily method:
        P_eff = 0 for P < 2mm (canopy interception); 0.8 * (P - 2) for P >= 2mm.
        """
        p = float(precip_mm)
        if p <= 2.0:
            return 0.0
        p_eff = 0.8 * (p - 2.0)
        return max(0.0, min(p, round(p_eff, 2)))

    def step(
        self,
        etc_mm: float,
        precip_mm: float,
        irrigation_mm: float,
        root_depth_m: float,
        date_str: str = "",
        day_index: int = 0,
        sensor_moisture_pct: Optional[float] = None,
        sensor_fusion_weight: float = 0.5,
    ) -> SoilWaterState:
        """
        Advance soil water balance by 1 day.
        Optionally fuses ground ESP32 sensor telemetry if available.
        """
        taw = self.calculate_taw(root_depth_m)
        raw = self.calculate_raw(taw, etc_mm)
        p_eff = self.calculate_effective_rain(precip_mm)
        irr = max(0.0, float(irrigation_mm))

        # FAO-56 Water Balance Equation:
        # Dr,t = Dr,t-1 - P_eff - I + ETc
        dr_new = self.current_dr_mm - p_eff - irr + float(etc_mm)

        # Deep percolation occurs when soil is wetter than field capacity (Dr < 0)
        deep_percolation = 0.0
        if dr_new < 0.0:
            deep_percolation = abs(dr_new)
            dr_new = 0.0

        # Maximum depletion cannot exceed TAW by more than wilting point limit
        dr_new = min(taw * 1.15, dr_new)

        # Fuse with physical sensor reading if provided
        if sensor_moisture_pct is not None and not np.isnan(sensor_moisture_pct):
            dr_sensor = self.depletion_from_volumetric_moisture(sensor_moisture_pct, root_depth_m)
            w = max(0.0, min(1.0, float(sensor_fusion_weight)))
            dr_new = (1.0 - w) * dr_new + w * dr_sensor

        self.current_dr_mm = max(0.0, round(dr_new, 2))
        vol_pct = self.volumetric_moisture_from_depletion(self.current_dr_mm, root_depth_m)

        return SoilWaterState(
            day_index=day_index,
            date_str=date_str,
            root_depth_m=round(root_depth_m, 2),
            taw_mm=taw,
            raw_mm=raw,
            depletion_dr_mm=self.current_dr_mm,
            soil_moisture_pct=vol_pct,
            field_capacity_pct=round(self.theta_fc * 100.0, 1),
            wilting_point_pct=round(self.theta_wp * 100.0, 1),
            depletion_ratio=round(min(1.0, self.current_dr_mm / taw), 3),
            is_water_stressed=(self.current_dr_mm > raw),
            effective_rain_mm=p_eff,
            irrigation_mm=irr,
            etc_mm=round(etc_mm, 2),
            deep_percolation_mm=round(deep_percolation, 2),
        )
