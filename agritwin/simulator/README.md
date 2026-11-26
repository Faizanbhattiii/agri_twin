# AgriTwin Pakistan — Climate-Risk "What-If" Scenario Simulator

The `agritwin.simulator` package delivers an interactive simulation engine allowing farmers, researchers, and agronomists to model climate shocks and evaluate potential impacts on wheat yield and root-zone water balance.

---

## 1. What It Simulates

### 1.1 Temperature / Heatwave Perturbations
- **Perturbation Range:** $-5^\circ\text{C}$ to $+10^\circ\text{C}$ (Standard: $+1^\circ\text{C}$ to $+5^\circ\text{C}$).
- **Target Stages:**
  - `all`: Applied across the entire 189-day Rabi season.
  - `grain_filling`: Applied during March terminal grain filling (weeks 18 to 26), capturing the South Asian terminal heat stress phenomenon.
  - `flowering`: Applied during mid-season anthesis (weeks 12 to 17).
- **Physics & Biology:** Automatically updates Growing Degree Days (GDD), Vapor Pressure Deficit (VPD), and accumulates extreme heat days ($T_{max} > 32^\circ\text{C}$).

### 1.2 Precipitation Anomalies
- **Perturbation Range:** $0.0\times$ (total drought) to $3.0\times$ ($+200\%$ heavy rainfall).
- **Physics:** Direct modulation of daily precipitation series impacting the soil water balance.

### 1.3 Irrigation Delay Perturbations
- **Perturbation Range:** $+0$ to $+45$ days (Standard: $+7, +14, +21$ days).
- **Physics:** Shifts scheduled canal (*warabandi*) or tubewell water applications, causing soil water depletion $D_r$ to surpass Readily Available Water ($RAW$) and accumulating active water deficit stress days.

### 1.4 Compound Shocks
- Evaluates non-linear compound impacts (e.g. $+3.0^\circ\text{C}$ March heatwave combined with $-50\%$ rainfall and $+14$-day irrigation delay).

---

## 2. Agronomic Stress Indices

1. **Heat Stress Hours:** Accumulated hours of exposure above $32^\circ\text{C}$, calculated as $\sum \max(0, T_{max} - 32) \times 8\text{ hrs}$.
2. **Grain-Filling Heat Days:** Total days with $T_{max} > 32^\circ\text{C}$ during weeks 18-26.
3. **Water Deficit Stress Days:** Number of days where root depletion $D_r > RAW$, indicating transpiration restriction ($K_s < 1.0$).
4. **Severity Classifications:** `NONE`, `MILD`, `MODERATE`, `SEVERE`, `EXTREME` for both terminal heat shock and drought.
5. **Mitigation Advisory:** Targeted, actionable recommendations in English and Urdu Nastaliq.

---

## 3. Train/Serve Parity (Rule 9)

All feature extraction for simulated scenarios passes through `WheatFeaturePipeline`:
- 27-week temporal matrix $(27, 10)$
- 9-dimensional static soil vector $(9,)$
- 49-dimensional tabular vector $(49,)$

Inference can be executed across all three production models:
- **DeepAgroNet:** 1D-CNN + BiLSTM + Attention + Soil MLP with 95% Gaussian uncertainty intervals.
- **Random Forest:** Baseline regressor with tabular feature importances.
- **XGBoost:** Gradient boosted tree regressor.

---

## 4. API Endpoints

- `GET /api/v1/scenarios/presets`: List predefined scenario catalog.
- `POST /api/v1/scenarios/run`: Execute interactive simulation. Returns baseline vs scenario yields ($\text{kg/ha}$ and $\text{maund/acre}$), $\Delta\text{Yield}\%$, uncertainty bounds, stress indices, 27-week trajectories, and bilingual advisory text.
