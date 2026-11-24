"""
SoilGrids (ISRIC 250m v2.0) Data Pipeline.
Queries global digital soil properties via REST API for specified coordinates.
Caches responses and provides representative Punjab alluvial soil profile fallbacks.
Attribution: 'ISRIC — World Soil Information (SoilGrids 2.0)'
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import requests

from agritwin.core.config import DATA_DIR, settings

logger = logging.getLogger(__name__)

CACHE_DIR = DATA_DIR / "cache" / "soil"


class SoilGridsClient:
    """Client for SoilGrids v2.0 REST API with disk caching and Punjab defaults."""

    ATTRIBUTION = "Soil properties by ISRIC SoilGrids 2.0 (CC BY 4.0)"

    PROPERTIES = ["clay", "sand", "silt", "soc", "phh2o", "bdod", "cec"]
    DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]

    def __init__(self, cache_dir: Optional[Path] = None, timeout: int = 15):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.base_url = settings.soilgrids_base_url

    def _cache_path(self, latitude: float, longitude: float) -> Path:
        """Generate deterministic cache path for given lat/lon."""
        key = f"soil_{latitude:.4f}_{longitude:.4f}".encode("utf-8")
        hash_val = hashlib.md5(key).hexdigest()
        return self.cache_dir / f"soil_{hash_val}.json"

    def get_soil_profile(
        self,
        latitude: float,
        longitude: float,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Query topsoil (0-30cm) properties for a coordinate.
        Returns normalized dictionary with clay %, sand %, silt %, pH, SOC %, bulk density, and TAW.
        """
        cache_file = self._cache_path(latitude, longitude)

        if use_cache and cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)

        params: Dict[str, Any] = {
            "lat": round(latitude, 4),
            "lon": round(longitude, 4),
            "property": self.PROPERTIES,
            "depth": self.DEPTHS,
            "value": "mean"
        }

        try:
            resp = requests.get(self.base_url, params=params, timeout=self.timeout)
            if resp.status_code == 200:
                raw_data = resp.json()
                profile = self._parse_soilgrids_response(raw_data, latitude, longitude)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(profile, f, indent=2)
                return profile
        except Exception as e:
            logger.warning(f"SoilGrids query failed ({e}). Falling back to Punjab baseline profile.")

        # Fallback profile (Rule 4: source='simulated')
        profile = self._generate_punjab_soil_profile(latitude, longitude)
        return profile

    def _parse_soilgrids_response(
        self,
        data: Dict[str, Any],
        latitude: float,
        longitude: float
    ) -> Dict[str, Any]:
        """Convert raw SoilGrids JSON to calibrated physical percentages."""
        props = {}
        layers = data.get("properties", {}).get("layers", [])

        for layer in layers:
            name = layer.get("name")
            depths = layer.get("depths", [])
            vals = [d.get("values", {}).get("mean") for d in depths if d.get("values", {}).get("mean") is not None]
            if vals:
                props[name] = sum(vals) / len(vals)

        # SoilGrids units conversions:
        # clay/sand/silt: g/kg -> % (divide by 10)
        clay_pct = round(props.get("clay", 220) / 10.0, 1)
        sand_pct = round(props.get("sand", 430) / 10.0, 1)
        silt_pct = round(props.get("silt", 350) / 10.0, 1)
        # soc: dg/kg -> % (divide by 100)
        soc_pct = round(props.get("soc", 80) / 100.0, 2)
        # phh2o: pH * 10 -> pH (divide by 10)
        ph = round(props.get("phh2o", 81) / 10.0, 1)
        # bdod: cg/cm3 -> g/cm3 (divide by 100)
        bulk_density = round(props.get("bdod", 142) / 100.0, 2)
        # cec: mmol(c)/kg -> cmol(c)/kg (divide by 10)
        cec = round(props.get("cec", 150) / 10.0, 1)

        # Compute hydraulic properties (Saxton-Rawls pedotransfer estimates)
        fc_pct, wp_pct = self._estimate_hydraulic_limits(clay_pct, sand_pct, soc_pct)
        # Total Available Water (TAW in mm per meter of soil depth)
        taw_mm_m = round(10.0 * (fc_pct - wp_pct), 1)

        return {
            "latitude": latitude,
            "longitude": longitude,
            "clay_pct": clay_pct,
            "sand_pct": sand_pct,
            "silt_pct": silt_pct,
            "soil_texture_class": self._classify_texture(clay_pct, sand_pct, silt_pct),
            "soc_pct": soc_pct,
            "ph": ph,
            "bulk_density_g_cm3": bulk_density,
            "cec_cmol_kg": cec,
            "field_capacity_pct": fc_pct,
            "wilting_point_pct": wp_pct,
            "taw_mm_per_m": taw_mm_m,
            "source": "SoilGrids-2.0"
        }

    def _generate_punjab_soil_profile(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Representative alluvial Indus basin soil characteristics for Punjab farmland."""
        # Central Punjab alluvial loam
        clay_pct = 22.0
        sand_pct = 42.0
        silt_pct = 36.0
        soc_pct = 0.75  # typically low organic carbon in semi-arid Punjab
        ph = 8.1        # typically slightly alkaline
        bulk_density = 1.42
        cec = 14.5
        fc_pct, wp_pct = self._estimate_hydraulic_limits(clay_pct, sand_pct, soc_pct)
        taw_mm_m = round(10.0 * (fc_pct - wp_pct), 1)

        return {
            "latitude": latitude,
            "longitude": longitude,
            "clay_pct": clay_pct,
            "sand_pct": sand_pct,
            "silt_pct": silt_pct,
            "soil_texture_class": "Loam",
            "soc_pct": soc_pct,
            "ph": ph,
            "bulk_density_g_cm3": bulk_density,
            "cec_cmol_kg": cec,
            "field_capacity_pct": fc_pct,
            "wilting_point_pct": wp_pct,
            "taw_mm_per_m": taw_mm_m,
            "source": "simulated"
        }

    def _estimate_hydraulic_limits(self, clay: float, sand: float, soc: float) -> tuple[float, float]:
        """Estimate Field Capacity (FC) and Permanent Wilting Point (PWP) using empirical pedotransfer functions."""
        # Simplified Saxton-Rawls equations for volumetric %
        wp = 0.0001 + 0.302 * (clay / 100.0) + 0.005 * (soc / 100.0)
        fc = 0.078 + 0.426 * (clay / 100.0) - 0.088 * (sand / 100.0) + 0.05 * (soc / 100.0)
        fc_pct = round(max(15.0, min(45.0, fc * 100.0 + 12.0)), 1)
        wp_pct = round(max(5.0, min(25.0, wp * 100.0 + 6.0)), 1)
        return fc_pct, wp_pct

    def _classify_texture(self, clay: float, sand: float, silt: float) -> str:
        """USDA soil texture classification."""
        if clay >= 40:
            return "Clay"
        elif sand >= 70:
            return "Sandy Loam"
        elif silt >= 50:
            return "Silt Loam"
        elif 20 <= clay < 40 and sand < 50:
            return "Clay Loam"
        else:
            return "Loam"
