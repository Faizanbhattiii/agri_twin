# AgriTwin Features: Unified Feature Engineering Pipeline

## Overview
The `agritwin/features` module provides the unified feature engineering pipeline for crop yield forecasting and digital twin modeling. It strictly enforces **Train/Serve Parity (Rule 9)**: the exact same feature transformation logic is shared between offline historical model training and live field inference.

## Season Window & Timesteps
- **Target Crop**: Rabi Season Wheat (*Triticum aestivum*)
- **Season Bounds**: November 1 to May 10 (27 weekly timesteps, 189 calendar days)
- **Time Representation**: Discrete 7-day intervals matching physiological wheat growth stages.

## Temporal Features (27 weeks × 10 channels)
For each of the 27 weeks, the following 10 channels are computed:
1. `gdd`: Weekly Growing Degree Days with $T_{base} = 5.0^\circ\text{C}$:
   $$\text{GDD} = \sum_{d=1}^{7} \max\left(0, \frac{T_{max,d} + T_{min,d}}{2} - 5.0\right)$$
2. `precipitation_mm`: Total weekly precipitation ($mm$).
3. `temp_mean_c`: Weekly average 2-meter air temperature ($^\circ\text{C}$).
4. `temp_max_c`: Weekly maximum air temperature ($^\circ\text{C}$).
5. `temp_min_c`: Weekly minimum air temperature ($^\circ\text{C}$).
6. `solar_radiation_mj`: Weekly cumulative shortwave solar radiation ($MJ/m^2$).
7. `vpd_kpa`: Mean Vapor Pressure Deficit in $kPa$, calculated via the Tetens formula:
   $$e_s(T) = 0.61078 \times \exp\left(\frac{17.27 \times T}{T + 237.3}\right)$$
   $$e_a = e_s \times \frac{RH}{100}, \quad VPD = \max(0, e_s - e_a)$$
8. `extreme_heat_days`: Count of days per week with $T_{max} > 32.0^\circ\text{C}$ (critical heat stress threshold during anthesis and grain filling).
9. `ndvi`: Interpolated weekly Sentinel-2 Normalized Difference Vegetation Index.
10. `evi`: Interpolated weekly Enhanced Vegetation Index.

## Static Features (9 channels)
Pedotransfer properties and geospatial coordinates:
1. `clay_pct`: Soil clay content (%)
2. `sand_pct`: Soil sand content (%)
3. `silt_pct`: Soil silt content (%)
4. `soc_pct`: Soil Organic Carbon (%)
5. `ph`: Soil pH in $H_2O$
6. `bulk_density`: Dry bulk density ($g/cm^3$)
7. `taw_mm`: Total Available Water capacity ($mm/m$)
8. `latitude`: Geographic latitude
9. `longitude`: Geographic longitude

## Tabular Features (49 dimensions)
Derived automatically for tree and linear baseline models (Ridge, Random Forest, XGBoost):
- Full-season aggregates (total GDD, total rainfall, extreme heat day counts).
- Phenological stage aggregations:
  - **Stage 1 (Emergence & Tillering)**: Weeks 1 to 6
  - **Stage 2 (Jointing & Stem Elongation)**: Weeks 7 to 12
  - **Stage 3 (Heading & Flowering / Anthesis)**: Weeks 13 to 18
  - **Stage 4 (Grain Filling & Ripening)**: Weeks 19 to 27
- NDVI trajectory metrics (peak NDVI value, peak week timing, seasonal area under curve, maturity drop).
- All 9 static soil and geospatial parameters.
