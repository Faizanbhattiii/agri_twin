"""
FAO-56 Penman-Monteith Reference Evapotranspiration (ET0) Engine.
Reference: Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998).
Crop evapotranspiration-Guidelines for computing crop water requirements-FAO Irrigation and drainage paper 56.

Computes:
- Saturation and actual vapor pressure (e_s, e_a)
- Slope of saturation vapor pressure curve (Delta)
- Atmospheric pressure and psychrometric constant (gamma)
- Net radiation (R_n) from solar radiation (R_s)
- Daily reference evapotranspiration (ET_0 in mm/day)
- Hargreaves-Samani temperature-based fallback when solar/wind data is incomplete
"""

import math
from typing import Optional, Union
import numpy as np


class PenmanMonteithCalculator:
    """
    Standard FAO-56 Penman-Monteith daily reference evapotranspiration (ET0) calculator.
    """

    ALBEDO_GRASS = 0.23  # Canopy reflection coefficient for reference grass
    STEFAN_BOLTZMANN = 4.903e-9  # MJ / K^4 / m^2 / day

    def __init__(self, elevation_m: float = 184.0, latitude_deg: float = 31.42) -> None:
        """
        Initialize calculator for a specific elevation and latitude.
        Default: Faisalabad, Punjab (elevation 184m, latitude 31.42° N).
        """
        self.elevation_m = elevation_m
        self.latitude_deg = latitude_deg
        self.latitude_rad = math.radians(latitude_deg)
        self.atmospheric_pressure = self._calculate_atmospheric_pressure(elevation_m)
        self.psychrometric_constant = 0.000665 * self.atmospheric_pressure

    def _calculate_atmospheric_pressure(self, z: float) -> float:
        """Calculate atmospheric pressure (P in kPa) at elevation z (meters). FAO-56 Eq. 7."""
        return 101.3 * ((293.0 - 0.0065 * z) / 293.0) ** 5.26

    @staticmethod
    def saturation_vapor_pressure(t_c: float) -> float:
        """Saturation vapor pressure e°(T) in kPa at temperature T in Celsius. FAO-56 Eq. 11."""
        return 0.61078 * math.exp((17.27 * t_c) / (t_c + 237.3))

    def mean_saturation_vapor_pressure(self, t_max: float, t_min: float) -> float:
        """Mean saturation vapor pressure e_s in kPa. FAO-56 Eq. 12."""
        return (self.saturation_vapor_pressure(t_max) + self.saturation_vapor_pressure(t_min)) / 2.0

    @staticmethod
    def actual_vapor_pressure(e_s: float, rh_mean: float) -> float:
        """Actual vapor pressure e_a in kPa from relative humidity. FAO-56 Eq. 19."""
        rh = max(0.0, min(100.0, rh_mean))
        return e_s * (rh / 100.0)

    @staticmethod
    def slope_vapor_pressure_curve(t_mean: float) -> float:
        """Slope of saturation vapor pressure curve Delta in kPa / C. FAO-56 Eq. 13."""
        es_t = 0.61078 * math.exp((17.27 * t_mean) / (t_mean + 237.3))
        return (4098.0 * es_t) / ((t_mean + 237.3) ** 2)

    @staticmethod
    def wind_speed_2m(u_z: float, z: float = 10.0) -> float:
        """Convert wind speed measured at height z (default 10m for weather models) to 2m height. FAO-56 Eq. 47."""
        if z == 2.0 or u_z <= 0.0:
            return max(0.5, float(u_z))
        return float(u_z * (4.87 / math.log(67.8 * z - 5.42)))

    def extraterrestrial_radiation(self, day_of_year: int) -> float:
        """
        Extraterrestrial radiation for daily periods (R_a in MJ / m^2 / day). FAO-56 Eq. 21, 23-28.
        """
        # Inverse relative distance Earth-Sun, d_r (Eq. 23)
        dr = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
        # Solar declination, delta (Eq. 24)
        solar_dec = 0.409 * math.sin((2.0 * math.pi * day_of_year / 365.0) - 1.39)
        # Sunset hour angle, omega_s (Eq. 25)
        x = -math.tan(self.latitude_rad) * math.tan(solar_dec)
        omega_s = math.acos(max(-1.0, min(1.0, x)))

        # Solar constant G_sc = 0.0820 MJ / m^2 / min
        g_sc = 0.0820
        term1 = omega_s * math.sin(self.latitude_rad) * math.sin(solar_dec)
        term2 = math.cos(self.latitude_rad) * math.cos(solar_dec) * math.sin(omega_s)
        ra = (24.0 * 60.0 / math.pi) * g_sc * dr * (term1 + term2)
        return max(0.0, float(ra))

    def clear_sky_radiation(self, ra: float) -> float:
        """Clear-sky solar radiation (R_so in MJ / m^2 / day). FAO-56 Eq. 37."""
        return (0.75 + 2e-5 * self.elevation_m) * ra

    def net_radiation(
        self,
        rs: float,
        t_max: float,
        t_min: float,
        ea: float,
        day_of_year: int,
    ) -> float:
        """
        Net radiation at crop surface (R_n in MJ / m^2 / day). FAO-56 Eq. 38, 39, 40.
        """
        # Net shortwave radiation (R_ns)
        r_ns = (1.0 - self.ALBEDO_GRASS) * rs

        # Net longwave radiation (R_nl)
        ra = self.extraterrestrial_radiation(day_of_year)
        r_so = self.clear_sky_radiation(ra)
        rs_rso = min(1.0, max(0.3, rs / r_so)) if r_so > 0.0 else 0.7

        t_max_k = t_max + 273.16
        t_min_k = t_min + 273.16
        rad_term = self.STEFAN_BOLTZMANN * ((t_max_k ** 4 + t_min_k ** 4) / 2.0)
        vapor_term = 0.34 - 0.14 * math.sqrt(max(0.0, ea))
        cloud_term = 1.35 * rs_rso - 0.35

        r_nl = rad_term * vapor_term * cloud_term
        r_n = r_ns - r_nl
        return max(0.0, float(r_n))

    def calculate_et0(
        self,
        t_max: float,
        t_min: float,
        rh_mean: float,
        solar_radiation_mj: float,
        wind_speed_ms: float,
        day_of_year: int,
        wind_measurement_height_m: float = 10.0,
    ) -> float:
        """
        Calculate daily reference evapotranspiration ET_0 (mm / day) using FAO-56 Penman-Monteith.
        Equation:
            ET0 = [0.408 * Delta * (R_n - G) + gamma * (900 / (T + 273)) * u_2 * (e_s - e_a)] /
                  [Delta + gamma * (1 + 0.34 * u_2)]
        """
        t_mean = (t_max + t_min) / 2.0
        u2 = self.wind_speed_2m(wind_speed_ms, z=wind_measurement_height_m)

        es = self.mean_saturation_vapor_pressure(t_max, t_min)
        ea = self.actual_vapor_pressure(es, rh_mean)
        delta = self.slope_vapor_pressure_curve(t_mean)
        gamma = self.psychrometric_constant

        rn = self.net_radiation(
            rs=solar_radiation_mj,
            t_max=t_max,
            t_min=t_min,
            ea=ea,
            day_of_year=day_of_year,
        )
        g = 0.0  # Soil heat flux density for daily period is negligible

        numerator = 0.408 * delta * (rn - g) + gamma * (900.0 / (t_mean + 273.0)) * u2 * (es - ea)
        denominator = delta + gamma * (1.0 + 0.34 * u2)

        et0 = numerator / denominator
        return max(0.1, float(et0))

    def hargreaves_et0(
        self,
        t_max: float,
        t_min: float,
        day_of_year: int,
    ) -> float:
        """
        Hargreaves-Samani temperature-based fallback equation for ET0 when solar/wind data is unavailable.
        FAO-56 Eq. 52:
            ET0 = 0.0023 * (T_mean + 17.8) * (T_max - T_min)^0.5 * R_a
        """
        t_mean = (t_max + t_min) / 2.0
        td = max(0.0, t_max - t_min)
        ra = self.extraterrestrial_radiation(day_of_year)
        # Convert Ra from MJ/m^2/day to mm/day equivalent: 1 mm = 2.45 MJ/m^2
        ra_mm = ra / 2.45
        et0 = 0.0023 * (t_mean + 17.8) * (td ** 0.5) * ra_mm
        return max(0.1, float(et0))
