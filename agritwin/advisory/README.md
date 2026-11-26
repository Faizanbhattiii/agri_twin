# AgriTwin Advisory: Evapotranspiration & Irrigation Advisory Engine

## Overview
The `agritwin/advisory` package implements the scientific crop water requirement, root zone water balance, and irrigation advisory engine for the AgriTwin digital twin platform.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FAO-56 Penman-Monteith (ET0)                        │
│   (Solar Radiation, Temperature, Relative Humidity, Wind Speed at 2m)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ ET0 (mm/day)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   Wheat Crop Water Manager (ETc)                       │
│    (Dynamic Kc curve: Initial 0.35 -> Jointing 0.95 -> Mid 1.15)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ ETc = Kc * ET0
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Root-Zone Soil Water Balance (Dr)                      │
│        (P_eff, Irrigation, Deep Percolation, ESP32 Sensor Fusion)       │
│                TAW = 1000 * (FC - WP) * Zr, RAW = p * TAW              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Depletion Status (Dr, TAW, RAW)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  Irrigation Advisory Rule Engine                       │
│    (Rain Deferral Check, Urgency, Depth mm, Tubewell Hours/Acre)       │
│            Bilingual Output: English & Urdu (Nastaliq RTL)             │
└────────────────────────────────────────────────────────────────────────┘
```

## 1. FAO-56 Penman-Monteith Calculator (`evapotranspiration.py`)
Computes reference evapotranspiration ($ET_0$ in $mm/\text{day}$) according to the standard FAO Irrigation and Drainage Paper 56:
$$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$
- Elevation and latitude adjustments (atmospheric pressure $P$, psychrometric constant $\gamma$).
- Net radiation $R_n$ derived from shortwave solar radiation $R_s$, albedo $\alpha = 0.23$, and net longwave radiation $R_{nl}$.
- Automatic Hargreaves-Samani fallback when wind or solar radiation data is missing.

## 2. Crop Water Dynamics (`crop_water.py`)
- **Phenological Stages for Pakistani Rabi Wheat**:
  - **Initial (CRI)**: Days 1–25, $K_c = 0.35$, Root depth $Z_r = 0.25\text{ m}$ (Critical irrigation window).
  - **Development (Tillering & Jointing)**: Days 26–75, $K_c$ ramps linearly from $0.35$ to $1.15$, $Z_r$ reaches $0.75\text{ m}$.
  - **Mid-Season (Booting, Heading & Anthesis)**: Days 76–115, $K_c = 1.15$, $Z_r = 1.10\text{ m}$ (Critical irrigation window).
  - **Late-Season (Grain Filling & Maturity)**: Days 116–160, $K_c$ declines from $1.15$ to $0.40$, irrigation stops 15 days before harvest.
- Water stress reduction coefficient $K_s = \frac{TAW - D_r}{(1 - p) TAW}$ yielding actual $ET_{c,adj} = K_s K_c ET_0$.

## 3. Soil Water Balance & Depletion (`water_balance.py`)
- **Total Available Water**: $TAW = 1000 \times (\theta_{FC} - \theta_{WP}) \times Z_r$ ($mm$).
- **Readily Available Water**: $RAW = p \times TAW$, with depletion factor $p = 0.55$ for wheat.
- Daily depletion step:
  $$D_{r,t} = D_{r,t-1} - P_{eff} - I + ET_{c} + DP$$
  where $DP$ is deep percolation below root zone when soil moisture exceeds Field Capacity ($D_r < 0$).
- Ground telemetry sensor fusion: integrates capacitive probe readings to calibrate moisture depletion.

## 4. 7-Day Soil Moisture Forecaster (`models/soil_moisture_forecaster.py`)
Couples the 7-day Open-Meteo weather forecast with daily forward water balance simulations to predict volumetric soil moisture (%) and depletion over the upcoming week.

## 5. Irrigation Advisory Engine (`irrigation_engine.py`)
- **Urgency Categories**:
  - `OPTIMAL` (Green): Depletion is safe ($D_r < 0.6 \times RAW$).
  - `MONITOR` (Amber): Moisture nearing limit ($0.6 \times RAW \le D_r < RAW$).
  - `CRITICAL_IRRIGATE` (Red): $D_r \ge RAW$ or critical stage threshold reached.
  - `RAIN_DEFERRED` (Blue): Rain $\ge 12\text{ mm}$ predicted within 48 hours; irrigation held off to conserve resources.
- **Tubewell Operating Hours**:
  - Standard 1-cusec tubewell ($1 \text{ cusec} = 28.317 \text{ L/s} = 101.94 \text{ m}^3/\text{hr}$).
  - Considers 75% surface application efficiency.
  - A standard 3-inch irrigation ($75\text{ mm}$ gross) requires $\approx 3.0$ pumping hours per acre.
- **Bilingual Advice**: Actionable messages in both English and clear Urdu Nastaliq text.
