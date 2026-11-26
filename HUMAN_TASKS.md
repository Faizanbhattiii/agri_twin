# AgriTwin Pakistan — Human Tasks & Action Guide

This file tracks every manual or external task required from the project owners (**M Faizan Bhatti** and **Mohib Khan**).
Whenever an agent hits a human task (`🧑`), the automated workflow falls back to fixtures/mocks so development is never blocked. Use this guide to complete the real-world tasks at your own pace.

---

## Progress Overview

| Phase | Task ID | Description | Status | Critical / Optional |
|---|---|---|---|---|
| **Phase 0** | H-00 | Supervisor framing alignment (Hardware + Software, honest benchmark) | ⏳ Pending human check | Recommended |
| **Phase 1** | H-01 (P1.5) | Register Google Earth Engine (GEE) non-commercial project | ⚪ Optional (Mock fallback active) | Optional |
| **Phase 2** | H-02 | (Optional) Configure PostgreSQL database instance | ⚪ Optional (SQLite active) | Optional |
| **Phase 3** | H-03 (P3.3) | Physical ESP32 sensor node wiring and assembly (irmware/README.md ready) | ⏳ Ready for hardware build | Recommended (Simulator active) |
| **Phase 3** | H-04 | Flash firmware to ESP32 (irmware/src/config.h.example ready) | ⏳ Ready for hardware build | Recommended (Simulator active) |
| **Phase 4** | H-05 | Review model benchmark report (`docs/MODEL_BENCHMARK.md`) with supervisor | 🟢 Ready for review (Report & models trained) | Recommended |
| **Phase 5** | H-06 | Review irrigation recommendations against local farming practices | ⏳ Pending Phase 5 | Recommended |
| **Phase 6** | H-07 | Validate climate stress simulation scenarios | 🟢 Ready for review (Simulator, stress indices & API complete) | Recommended |
| **Phase 7** | H-08 | Review Urdu translations and UI in browser | ⏳ Pending Phase 7 | Recommended |
| **Phase 8** | H-09 | Final Capstone defense rehearsal using `docs/DEMO_SCRIPT.md` & `docs/VIVA_QA.md` | ⏳ Pending Phase 8 | Critical |

---

## Phase-by-Phase Task Details & Step-by-Step Instructions

### Phase 0: Foundations & Scope
#### 🧑 Task H-00: Supervisor Framing Alignment
- **Objective:** Ensure Dr. Asifa Awan is aligned with the project scope:
  1. The project is **Hardware + Software** (ESP32 sensor node + Web digital twin + AI models), with a software simulator as a fail-safe.
  2. The Deep Learning model (DeepAgroNet) will be **honestly benchmarked** against Random Forest and XGBoost using district-level yields. If baseline tree models perform equally well or better on tabular district data, that is scientifically valid and defended as a rigorous comparison.

---

### Phase 1: Multi-Source Data Pipelines
#### 🧑 Task H-01 (P1.5): Google Earth Engine (GEE) Registration *(Optional)*
- **Status:** *Optional.* The system currently uses verified Sentinel-2 historical NDVI fixtures for Punjab wheat.
- **When to do it:** If you want live satellite NDVI fetching for arbitrary coordinates in real time.
- **Step-by-step instructions:**
  1. Go to [Google Earth Engine Signup](https://earthengine.google.com/noncommercial/) and register with an academic/personal Google account.
  2. Create a Google Cloud Project (e.g. `agritwin-gee-project`).
  3. In Google Cloud Console, enable the **Earth Engine API**.
  4. Go to **IAM & Admin > Service Accounts**, create a service account named `agritwin-gee`, and grant it the role **Earth Engine Resource Viewer**.
  5. Under Keys, create a new JSON key and save it in your project root as `service_account.json` (it is git-ignored).
  6. Open `.env` and fill in:
     ```env
     GEE_PROJECT_ID=agritwin-gee-project
     GEE_SERVICE_ACCOUNT=agritwin-gee@agritwin-gee-project.iam.gserviceaccount.com
     GEE_PRIVATE_KEY_PATH=./service_account.json
     ```

---

### Phase 2: Relational Data Model & Database
#### 🧑 Task H-02: PostgreSQL Setup *(Optional)*
- **Status:** *Optional.* The system runs out-of-the-box on SQLite (`data/agritwin.db`).
- **When to do it:** Before final deployment or when running via Docker Compose.
- **Step-by-step instructions:**
  - If using local PostgreSQL or Docker:
    ```bash
    # Run postgres container
    docker run --name agritwin-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=agritwin -p 5432:5432 -d postgres:16
    ```
  - Update `.env`:
    ```env
    DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/agritwin
    ```

---

### Phase 3: Field Node Firmware & Telemetry
#### 🧑 Task H-03: Physical Hardware Node Assembly
- **Components to acquire:**
  1. ESP32 DevKit V1 (30-pin) (~Rs. 1,200 - 1,500)
  2. Capacitive Soil Moisture Sensor v1.2 (corrosion resistant) (~Rs. 300 - 450)
  3. DHT22 (AM2302) Temperature and Humidity sensor (~Rs. 600 - 800)
  4. 10kΩ pull-up resistor (for DHT22 data pin)
  5. Breadboard / Veroboard and jumper wires
  6. USB-to-MicroUSB cable or 5V battery pack / solar charge module (TP4056 + 18650 Li-ion)
- **Wiring instructions:** Full schematics and pinouts will be provided in `firmware/README.md`.

#### 🧑 Task H-04: Flash Firmware to ESP32
- **Step-by-step instructions:**
  1. Install VS Code and the **PlatformIO IDE** extension.
  2. Open the `firmware/` folder in PlatformIO.
  3. Edit `firmware/src/config.h` with your local Wi-Fi SSID, password, and laptop IP address.
  4. Plug in the ESP32 via USB and click **PlatformIO: Upload**.

---

### Phase 4: Feature Engineering & Model Training
#### 🧑 Task H-05: Review Model Benchmark Results
- **Objective:** Review the computed metrics ($R^2$, $RMSE$, $MAE$) in `docs/MODEL_BENCHMARK.md`.
- **Authentic Benchmark Summary (Leave-One-Season-Out across 10 seasons, 360 observations):**
  - **Random Forest**: $R^2 = 0.9185$, $RMSE = 161.8 \text{ kg/ha}$ ($1.64 \text{ maund/acre}$), $MAE = 130.1 \text{ kg/ha}$
  - **XGBoost**: $R^2 = 0.9080$, $RMSE = 171.9 \text{ kg/ha}$ ($1.74 \text{ maund/acre}$), $MAE = 137.1 \text{ kg/ha}$
  - **DeepAgroNet**: $R^2 = 0.8697$, $RMSE = 204.6 \text{ kg/ha}$ ($2.07 \text{ maund/acre}$), $MAE = 160.7 \text{ kg/ha}$, with 95% Gaussian uncertainty bounds
  - **Ridge (Linear baseline)**: $R^2 = 0.5904$, $RMSE = 362.8 \text{ kg/ha}$ ($3.67 \text{ maund/acre}$)
- **Action:** Discuss the findings with your supervisor Dr. Asifa Awan:
  1. Highlight that Random Forest and XGBoost excel on aggregated tabular features, while DeepAgroNet provides spatiotemporal sequence modeling and calibrated uncertainty intervals.
  2. Emphasize that all evaluations followed rigorous Leave-One-Season-Out (LOSO) temporal cross-validation without data leakage.

---

### Phase 5: Irrigation Advisory Engine
#### 🧑 Task H-06: Local Agronomic Validation
- **Objective:** Verify the advisory recommendations (e.g. tubewell hours) with a local farmer or agronomist in Faisalabad.
- **Standard rule of thumb:** A standard 1-cusec tubewell pumps $\approx 28.3 \text{ liters/sec}$ or $\approx 102 \text{ m}^3/\text{hr}$. Irrigating 1 acre with 3 inches ($75\text{ mm}$) takes $\approx 3 \text{ to } 3.5\text{ hours}$.

---

### Phase 6: Climate What-If Simulator
#### 🧑 Task H-07: Scenario Sanity Checks
- **Status:** 🟢 Ready for review. The What-If Scenario Simulator, FAO-33 water production coupling, heat stress indices, and FastAPI endpoints are fully implemented and verified with 49/49 passing project-wide tests.
- **Objective:** Validate simulation outputs with supervisor / agronomists:
  1. **Terminal Heatwave (+3.5°C in March):** Verifies predicted yield reduction (~12-15%) from terminal heat shock and accelerated senescence.
  2. **Winter Drought & Delayed Irrigation (-70% rain, +14d delay):** Verifies soil water depletion exceeding RAW, triggering acute water deficit stress days and ~14% yield reduction.
  3. **Compound Climate Shock (+3.0°C & -50% rain & +14d delay):** Verifies compounding stress yielding up to 20-25% crop decline.
  4. Test live API in Swagger docs (`/docs#/What-If%20Climate%20Simulator/run_scenario_api_v1_scenarios_run_post`).

---

### Phase 7: Web Dashboard & Urdu Translation Review
#### 🧑 Task H-08: UI & Language Review
- **Objective:** Launch the web dashboard, toggle between English and Urdu (RTL), and verify that fonts and terms are readable for farmers and extension agents.
- **Checklist:**
  - Verify "SIMULATED" badge appears when running on simulator data.
  - Verify charts, map layers, and advisory cards render correctly.

---

### Phase 8: Final Defense Preparation
#### 🧑 Task H-09: Defense Rehearsal
- **Objective:** Rehearse your final project defense presentation:
  1. Follow the timed 5-minute presentation walkthrough in `docs/DEMO_SCRIPT.md`.
  2. Review the technical viva questions and model architecture answers in `docs/VIVA_QA.md`.
