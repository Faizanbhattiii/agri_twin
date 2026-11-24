# AgriTwin Pakistan — Master Implementation Plan

**Project ID:** CS-F26-15 · **Department:** Computer Science, SEAS, Bahria University Islamabad
**Supervisor:** Dr. Asifa Awan · **Group:** M Faizan Bhatti, Mohib Khan
**Source documents:** CP Form (signed 22-08-2026) and *AgriTwin Pakistan – Capstone Project Proposal (CP-2 Updated)*, 9 Sept 2026
**Plan version:** 1.0 · **Written:** 24 Nov 2026
**Audience:** an AI coding agent (Google Antigravity, Claude Code, Cursor, Codex, etc.) **and** the two students who own the project.

---

## 0. READ FIRST — Rules for the coding agent

This file is the **single source of truth**. Save it in the repo as `docs/IMPLEMENTATION_PLAN.md` and copy Section 0 into the agent's rules file (`AGENTS.md` at repo root; for Antigravity also `.agents/rules/agritwin.md`).

1. **Work phase by phase, in order** (Phase 0 → Phase 8). Do not start Phase N+1 until every item in Phase N's *Definition of Done* is ticked and the human has confirmed.
2. **Use Planning mode / produce a short plan before each phase**, then implement. Keep commits small. One branch per phase (`phase-1-pipeline`), merge to `main` at the end, tag `phase-N`.
3. **Tick checkboxes in this file as you go** (`- [x]`) and add a one-line note beside anything you deviate on. Log every decision in `docs/DECISIONS.md` and every change in `CHANGELOG.md`.
4. **Never fabricate data, metrics, citations, or results.** Every number that appears in the dashboard, README, or report must be produced by code actually run on real data. Anything simulated must be stored with `source='simulated'` and shown with a visible "SIMULATED" badge in the UI.
5. **Never commit secrets** (API keys, GEE service-account JSON, DB URLs, device keys). Use `.env` (git-ignored) and ship `.env.example`.
6. **When you hit a 🧑 HUMAN task, stop that thread.** Tell the user precisely what to do (copy-paste steps), then continue with everything that does *not* depend on it, using fixtures/mocks.
7. **Write the tests as you write the code, run them, and report results truthfully** (including failures). No "should work" claims without running.
8. **Keep code explainable.** Two students must defend this project. Prefer clear, boring code over clever code. Docstring every public function; add a short `README.md` in each major package explaining *what* and *why*.
9. **Train/serve parity:** feature engineering used for training and for live inference must be the *same code* (`agritwin/features`). No copy-pasted logic.
10. **Reproducibility:** pin dependency versions, fix random seeds, save data/version hashes with every trained model.
11. **Do not add paid services** or unlisted heavy dependencies. Free tiers only.
12. If a requirement is ambiguous, take the default in Section 2, record it in `DECISIONS.md`, and continue.

**Legend:** 🧑 = human-only task · 🤖 = agent task · `MUST` = stated in a project document · `SHOULD` = strongly recommended · `COULD` = stretch · ⚠️ = risk/caveat.

---

## 1. Project scope (what is being built)

**One-line:** A hybrid digital twin of Pakistani farmland that fuses satellite NDVI (Sentinel-2 via Google Earth Engine), weather (Open-Meteo), and soil properties (SoilGrids) with ground-truth readings from a low-cost ESP32 field node, and uses a deep sequence model (DeepAgroNet: hybrid 1D-CNN + LSTM) — benchmarked against Random Forest and XGBoost — to deliver crop-health tracking, irrigation advisories, yield forecasts, and a climate "what-if" simulator through an Urdu-friendly web dashboard.

### 1.1 Objectives (from the proposal)
| # | Objective | Where built |
|---|---|---|
| O1 | Hybrid digital-twin architecture: satellite NDVI + weather + SoilGrids + live ESP32 ground truth | Phases 1–3 |
| O2 | Multi-spectral crop-health monitoring (vegetation indices + micro-climate) for a selected crop/region | Phases 1, 2, 7 |
| O3 | DeepAgroNet (1D-CNN + LSTM) for yield forecasting, soil-moisture estimation & irrigation advisories; benchmark vs RF/XGBoost using R², RMSE, MAE | Phases 3, 4, 5 |
| O4 | Climate-risk "what-if" simulator (rainfall, heatwave/temperature, irrigation timing) | Phase 6 |
| O5 | Web dashboard: map, NDVI overlay, time-series charts, live sensor stream, Urdu advisory alerts, pest-risk indicator | Phases 2, 7 |

### 1.2 Deliverables
1. Working web application (frontend + backend + database), deployed and also runnable offline via Docker.
2. ESP32 sensor node: firmware, wiring guide, calibration procedure, and a software simulator.
3. Data pipelines (Sentinel-2/GEE, Open-Meteo, SoilGrids, yield records).
4. Trained & versioned models (RF, XGBoost, DeepAgroNet) with a reproducible benchmark report.
5. Irrigation engine, pest-risk rule set, alert engine, what-if simulator.
6. Documentation set (README, architecture, API, data dictionary, model cards, hardware guide, user guides EN/UR, validation report).
7. Defense kit (demo script, backup video, Q&A bank) and material for the final report.

### 1.3 ⚠️ Inconsistencies between your two documents — resolve before coding
| Topic | CP Form (22-08-2026) | Updated Proposal (09-09-2026) | Decision used in this plan |
|---|---|---|---|
| Project type | CP-2 says *Software*, methodology says "fully software-based, no physical sensor deployment" — yet objectives, expected outcomes, budget and tools all include the ESP32 node | **Hardware + Software** | **Build hardware + software**, with a *simulator fallback* so nothing is blocked if the node is delayed. 🧑 H-01: confirm with supervisor and correct the CP form if needed. |
| DL targets | Yield **and soil-moisture estimation** | Yield forecasting **and irrigation advisories** | Implement **both**: yield model + soil-moisture forecaster feeding the irrigation engine. |
| Expected outcome | DL model "**outperforming** baseline tree models" | "Benchmarking its accuracy against baselines" | **Benchmark honestly.** With district-level yield data, DL may *not* beat RF/XGBoost. The plan reports whatever is found; success = rigorous, reproducible comparison. 🧑 Agree this framing with supervisor. |
| Sprints | Sprint 8 (wk 15–16) and 9 (wk 17–18) separate | Merged "Sprint 8–9" | Phase 8 covers weeks 15–18. |
| Pest risk | Rule-based/statistical from temperature–humidity | "Pest risk indicator rule set" (Sprint 7) | Rule-based, config-driven (Phase 7). |
| Map/DB | Leaflet/Mapbox; PostgreSQL/Firebase | Leaflet/Mapbox GL; PostgreSQL/Firebase | **Leaflet** (no token) + **PostgreSQL** (see Section 2). |

---

## 2. Key decisions & defaults (agent: use these; change only via `DECISIONS.md`)

| ID | Decision | Rationale |
|---|---|---|
| D1 | **Crop = wheat (Rabi), region = Punjab, Pakistan.** Crop logic is config-driven (`config/crops/wheat.yaml`); other crops are `COULD`. | Best official yield data (Punjab Crop Reporting Service, district-wise), most literature, clear Nov→Apr season. |
| D2 | **Two spatial scales:** (a) *district-level* multi-season dataset (Punjab districts) to train the yield model, because official yield ground truth exists only at district level; (b) *one pilot field* (polygon + ESP32 node) for the live digital twin and calibration. | A single field has no yield history; districts give enough samples. |
| D3 | Python **3.11**; **PyTorch** (CPU is enough; GPU optional on Colab); scikit-learn; XGBoost; Optuna; pandas/pyarrow. | Proposal allows PyTorch/TensorFlow; pick one. |
| D4 | **PostgreSQL 15/16** via SQLAlchemy 2.x + Alembic. Geometry stored as GeoJSON (JSONB); PostGIS not required. **No Firebase.** | Relational joins & time-series queries. |
| D5 | **FastAPI** backend (Pydantic v2); **WebSocket** for live sensor stream; APScheduler for jobs. | |
| D6 | **React 18 + Vite + TypeScript + Tailwind + react-leaflet + Chart.js (react-chartjs-2) + TanStack Query + react-i18next.** | SPA is sufficient; proposal allows React/Next.js. |
| D7 | Firmware: **ESP32 DevKit (30-pin) + PlatformIO/Arduino C++**. Sensors: **capacitive soil-moisture v1.2** (ADC1 pin), **DHT22** (air temp + RH), **DS18B20** waterproof (soil temp, optional). Transport: Wi-Fi → HTTPS POST (JSON). | Matches proposal; DHT22 gives humidity needed by the pest-risk rules. |
| D8 | Telemetry every **15 min** (configurable), deep-sleep between readings, offline buffer on flash. | Battery life. |
| D9 | Refresh cadence: forecast weather every 6 h; observed weather daily; NDVI daily check (new Sentinel-2 pass ≈ every 5 days); SoilGrids once. | API limits & usefulness. |
| D10 | Timezone **Asia/Karachi (UTC+5)** for display; **store UTC**. | |
| D11 | Units: yield stored as **kg/ha**, displayed also as **maund/acre** (CRS unit). `1 maund = 40 kg`, `1 acre = 0.404686 ha` → `1 maund/acre ≈ 98.84 kg/ha`. | Farmers/officials use maund/acre. |
| D12 | Yield target = **total (irrigated + unirrigated) district yield**; irrigated-only yield is a secondary target/ablation. | Cropland NDVI mask can't separate irrigated from rainfed. |
| D13 | Season window for wheat features: **1 Nov → 10 May**, weekly steps (≈27), configurable per crop. | Covers sowing → harvest incl. late sowing. |
| D14 | Evaluation protocol: **leave-one-season-out** (primary) and **leave-districts-out** (secondary) CV; metrics **R², RMSE, MAE** (+ bias). All models use identical folds. | Prevents leakage; fair comparison. |
| D15 | Never call GEE or Open-Meteo from the browser. Pipelines write to the DB; the API serves cached data. Show "data as of …" and a stale banner when ingestion is old. | Resilience, quota, demo reliability. |
| D16 | Open-Meteo free tier is **non-commercial, CC BY 4.0, attribution required, < 10,000 calls/day, 5,000/h, 600/min** — cache everything, batch locations. GEE must be a **noncommercial-registered Cloud project**. Show attributions in the UI footer. | Licence compliance (verified Nov 2026). |
| D17 | Language: UI and alerts in **English + Urdu (RTL)**; simple wording; icons/colours for low-literacy users. | Proposal objective. |
| D18 | Advisory-only disclaimer everywhere: recommendations support, not replace, farmer/agronomist judgement. | Ethics/liability. |



---

## 3. Phase-by-Phase Roadmap & Checklists

### Phase 0: Project Scaffolding, Tooling & Verification Harness
**Branch:** `phase-0-setup` · **Tag:** `phase-0`
**Objective:** Set up project structure, agent rules, configuration management, automated testing harness, and git tracking.

#### Tasks:
- [x] 🤖 **P0.1**: Initialize git repository, configure `.gitignore` (ignore `.env`, `__pycache__`, virtualenvs, credentials, node_modules, build artifacts, SQLite/PostgreSQL local files).
- [x] 🤖 **P0.2**: Create Agent rules files: `AGENTS.md` at repo root and `.agents/rules/agritwin.md` capturing all guidelines from Section 0.
- [x] 🤖 **P0.3**: Create directory hierarchy:
  - `agritwin/` (core python package: `data`, `features`, `models`, `advisory`, `simulator`, `api`, `core`)
  - `frontend/` (React + Vite + Tailwind + TypeScript application)
  - `firmware/` (ESP32 C++ PlatformIO / Arduino source code)
  - `simulator/` (ESP32 software telemetry generator)
  - `config/` (crop definitions: `crops/wheat.yaml`, system settings: `settings.yaml`)
  - `data/` (`raw/`, `processed/`, `fixtures/`)
  - `tests/` (unit, integration, parity tests)
  - `docs/` (`DECISIONS.md`, `CHANGELOG.md`, `ARCHITECTURE.md`)
- [x] 🤖 **P0.4**: Set up dependency definitions: `requirements.txt` (pinned versions), `pyproject.toml`, and `.env.example`.
- [x] 🤖 **P0.5**: Write crop configuration `config/crops/wheat.yaml` (wheat growth stages, GDD thresholds, crop coefficients $K_c$, critical moisture levels, season window Nov 1 – May 10).
- [x] 🤖 **P0.6**: Set up initial test suite (`pytest`) verifying configuration loading, environment integrity, and package imports.
- [x] 🤖 **P0.7**: Initialize `docs/DECISIONS.md` and `CHANGELOG.md`.

#### Definition of Done (Phase 0):
1. `pytest tests/` runs cleanly with 100% pass rate.
2. `AGENTS.md` and `.agents/rules/agritwin.md` match Section 0.
3. `.env.example` lists all required environment variables with non-secret defaults.
4. Git branch `phase-0-setup` created, committed, merged to `main`, tagged `phase-0`, and pushed to remote.

---

### Phase 1: Multi-Source Data Pipeline & Punjab Dataset
**Branch:** `phase-1-data-pipeline` · **Tag:** `phase-1`
**Objective:** Build reproducible data acquisition, caching, and preprocessing pipelines for Weather (Open-Meteo), Soil (SoilGrids), Satellite NDVI (Sentinel-2 via Google Earth Engine), and Punjab District Wheat Yields (Crop Reporting Service).

#### Tasks:
- [x] 🤖 **P1.1**: Build Punjab Wheat Yield historical dataset (`data/raw/punjab_wheat_yields_2013_2023.csv`) covering Punjab wheat-producing districts (Faisalabad, Multan, Bahawalpur, Sargodha, Sahiwal, Rahim Yar Khan, Sheikhupura, Gujranwala, Khanewal, Kasur, Jhang, Toba Tek Singh, etc.) with acreage, production, and yield (kg/ha and maund/acre) sourced from Punjab Crop Reporting Service records.
- [x] 🤖 **P1.2**: Implement Open-Meteo weather pipeline (`agritwin/data/weather.py`) supporting historical weather (temperature min/max/mean, precipitation sum, solar radiation, relative humidity, wind speed) and 7-day forecast. Add persistent file/DB caching and rate limit handling complying with CC BY 4.0.
- [x] 🤖 **P1.3**: Implement SoilGrids REST API pipeline (`agritwin/data/soil.py`) extracting clay, sand, silt, soil organic carbon (SOC), pH, bulk density, and cation exchange capacity (CEC) for specified coordinates with local disk caching.
- [x] 🤖 **P1.4**: Implement Sentinel-2 NDVI pipeline (`agritwin/data/satellite.py`) connecting to Google Earth Engine with automated fallback to verified historical NDVI fixtures/composites when GEE credentials are not configured.
- [ ] 🧑 **P1.5** *(HUMAN)*: Optionally register Google Cloud project for Google Earth Engine (free non-commercial) and set `GEE_SERVICE_ACCOUNT` / `GEE_KEY_FILE` in `.env`. (If skipped, agent pipeline uses verified satellite fixtures).
- [x] 🤖 **P1.6**: Implement synthetic/fixture generator for offline development ensuring `source='simulated'` flag is populated.
- [x] 🤖 **P1.7**: Write unit and integration tests (`tests/test_data_pipeline.py`) verifying pipeline data extraction, schema validation, and cache hits.

#### Definition of Done (Phase 1):
1. All pipelines (Weather, SoilGrids, Satellite NDVI, District Yields) execute reliably and cache outputs.
2. Punjab district yield dataset loaded and validated for 10+ seasons (2013–2023) across Punjab districts.
3. Automated tests pass without requiring external network calls when using cache/fixtures.
4. Changes documented in `CHANGELOG.md` and pushed to remote branch & tag `phase-1`.

---

### Phase 2: Relational Data Model, Migrations & Seed Geometry
**Branch:** `phase-2-database` · **Tag:** `phase-2`
**Objective:** Implement relational schema (PostgreSQL with SQLite test compatibility) via SQLAlchemy 2.0 and Alembic, with seed geometries for Punjab districts and pilot research field.

#### Tasks:
- [ ] 🤖 **P2.1**: Design SQLAlchemy 2.0 ORM models (`agritwin/core/models.py`):
  - `District` (name, division, geometry GeoJSON, centroid lat/lon, soil profile)
  - `Field` (name, district_id, boundary GeoJSON, area_acres, crop_type, sowing_date, is_pilot)
  - `WeatherObservation` & `WeatherForecast` (timestamp, temp, humidity, rain, solar radiation, et0)
  - `SoilProfile` (sand, silt, clay, organic_carbon, ph, bulk_density, taw, raw)
  - `SatelliteReading` (date, field_id / district_id, ndvi_mean, ndvi_min, ndvi_max, evi, source)
  - `SensorTelemetry` (timestamp, field_id, soil_moisture_pct, air_temp_c, relative_humidity_pct, soil_temp_c, battery_v, source)
  - `IrrigationAdvisory` (timestamp, field_id, urgency, recommended_depth_mm, tubewell_hours, reason_en, reason_ur)
  - `YieldForecast` (field_id / district_id, season, model_name, predicted_yield_kgha, predicted_yield_maund_acre, lower_bound, upper_bound)
- [ ] 🤖 **P2.2**: Configure Alembic migration environment (`alembic/`) supporting dynamic database URL (PostgreSQL default, SQLite fallback for unit testing).
- [ ] 🤖 **P2.3**: Generate initial database migration script.
- [ ] 🤖 **P2.4**: Create database seeder script (`agritwin/core/seed.py`):
  - Seed all Punjab wheat districts with coordinates and representative soil characteristics.
  - Seed Pilot Research Field (e.g. Faisalabad Agricultural Research Farm, 5 acres polygon).
- [ ] 🤖 **P2.5**: Write database tests (`tests/test_database.py`) validating model creation, cascade deletes, GeoJSON serialization, and query efficiency.

#### Definition of Done (Phase 2):
1. Migrations run cleanly from scratch (`alembic upgrade head`).
2. Seeder populates Punjab districts and the pilot field.
3. Tests confirm database integrity under both SQLite and PostgreSQL.
4. Changes logged and pushed to GitHub under `phase-2-database` and tagged `phase-2`.

---

### Phase 3: Field Node Firmware, Simulator & Telemetry Ingestion
**Branch:** `phase-3-telemetry` · **Tag:** `phase-3`
**Objective:** Deliver ESP32 microcontroller firmware, hardware wiring guide, realistic software telemetry simulator, and FastAPI ingestion endpoint with real-time WebSocket broadcasting.

#### Tasks:
- [ ] 🤖 **P3.1**: Create ESP32 firmware source code (`firmware/src/main.cpp` and `firmware/platformio.ini`):
  - Capacitive Soil Moisture Sensor v1.2 reading on ADC1 (with two-point calibration: dry air vs wet soil)
  - DHT22 temperature and relative humidity sensor reading
  - DS18B20 OneWire soil temperature reading (optional probe)
  - Wi-Fi connection manager with exponential backoff
  - HTTPS POST JSON payload dispatcher to backend `/api/v1/telemetry`
  - Deep-sleep cycle management (15-minute wake interval)
  - Flash SPIFFS offline ring buffer to queue up to 200 readings when disconnected
- [ ] 🤖 **P3.2**: Write comprehensive hardware documentation (`firmware/README.md`) detailing schematics, bill of materials (BOM), breadboard pinout table, voltage divider considerations, and field waterproofing tips.
- [ ] 🧑 **P3.3** *(HUMAN)*: Physical hardware assembly (ESP32 DevKit, capacitive sensor, DHT22, power supply) following `firmware/README.md` (or use simulator).
- [ ] 🤖 **P3.4**: Build standalone Python ESP32 software simulator (`simulator/esp32_simulator.py`):
  - Simulates diurnal temperature cycles, relative humidity variations, and soil drying curve punctuated by irrigation events
  - Marks all readings with `source='simulated'`
  - CLI options for burst mode, continuous 15-min interval streaming, and simulated sensor fault injection
- [ ] 🤖 **P3.5**: Implement FastAPI telemetry ingestion endpoint (`POST /api/v1/telemetry`) with Pydantic validation, anomaly detection (out-of-range sensor values), and persistence.
- [ ] 🤖 **P3.6**: Implement real-time WebSocket broadcaster (`/ws/telemetry`) pushing new readings to connected dashboard clients.
- [ ] 🤖 **P3.7**: Write integration tests (`tests/test_telemetry.py`) testing ingestion, validation, buffer playback, and WebSocket broadcast.

#### Definition of Done (Phase 3):
1. Firmware compiles cleanly under PlatformIO.
2. Software simulator generates realistic diurnal patterns and posts to FastAPI backend.
3. Telemetry endpoint accepts valid payloads, rejects corrupted data, and broadcasts over WebSocket.
4. Changes documented and pushed to remote branch `phase-3-telemetry`, tagged `phase-3`.

---

### Phase 4: Feature Engineering, DeepAgroNet & Baseline Benchmarks
**Branch:** `phase-4-models` · **Tag:** `phase-4`
**Objective:** Build unified feature engineering module (strict train/serve parity) and develop, train, evaluate, and benchmark DeepAgroNet (1D-CNN + LSTM) against Random Forest and XGBoost for wheat yield forecasting.

#### Tasks:
- [ ] 🤖 **P4.1**: Build unified feature engineering module (`agritwin/features/pipeline.py`):
  - Weekly temporal aggregation aligned with wheat season window (Nov 1 to May 10, weeks 1 to 27)
  - Accumulated Growing Degree Days ($GDD = \sum \max(0, \frac{T_{max} + T_{min}}{2} - T_{base})$ with $T_{base}=5^\circ C$)
  - Cumulative rainfall, extreme heat days ($T_{max} > 32^\circ C$ during grain filling), Vapor Pressure Deficit (VPD)
  - Weekly Sentinel-2 NDVI trajectory interpolation and peak NDVI timing
  - Static soil feature vector (clay %, sand %, SOC, pH, water capacity)
  - Identical pipeline code for both offline batch training and live field inference
- [ ] 🤖 **P4.2**: Implement baseline regression models (`agritwin/models/baselines.py`):
  - Ridge / Lasso Regression baseline
  - Random Forest Regressor with hyperparameter tuning
  - XGBoost Regressor with early stopping
- [ ] 🤖 **P4.3**: Implement DeepAgroNet architecture in PyTorch (`agritwin/models/deepagronet.py`):
  - 1D-CNN temporal convolutional blocks (extracting multi-week agronomic phase patterns)
  - Bidirectional LSTM layer (capturing full-season sequential growth dynamics)
  - Multi-layer Perceptron (MLP) fusion branch combining sequential features with static soil properties
  - Prediction head for district/field yield (kg/ha and maund/acre) with uncertainty interval
- [ ] 🤖 **P4.4**: Build rigorous Cross-Validation & Benchmark Harness (`agritwin/models/train.py`):
  - Leave-One-Season-Out (LOSO) cross-validation across all seasons (2014–2023)
  - Leave-Districts-Out (LDO) cross-validation evaluating geographic generalization
  - Strict calculation of $R^2$, $RMSE$, $MAE$, and Mean Bias Error ($MBE$) across identical folds
- [ ] 🤖 **P4.5**: Run model training, hyperparameter optimization, and generate benchmark report (`docs/MODEL_BENCHMARK.md`) with genuine computed metrics without fabricating numbers.
- [ ] 🤖 **P4.6**: Save serialized model artifacts (`models/deepagronet_best.pt`, `models/rf_best.joblib`, `models/xgb_best.json`) with version hash and feature manifest.
- [ ] 🤖 **P4.7**: Write unit and parity tests (`tests/test_models.py` and `tests/test_feature_parity.py`).

#### Definition of Done (Phase 4):
1. Feature pipeline transforms raw data into sequence and tabular tensors identically for training and inference.
2. DeepAgroNet, RF, and XGBoost are trained and evaluated on identical cross-validation folds.
3. Authentic benchmark report generated and stored in `docs/MODEL_BENCHMARK.md`.
4. Model inference runs deterministically under PyTorch CPU.
5. Changes committed, merged to `main`, tagged `phase-4`, and pushed to GitHub.

---

### Phase 5: Soil-Moisture Forecaster & Irrigation Advisory Engine
**Branch:** `phase-5-advisory` · **Tag:** `phase-5`
**Objective:** Develop short-term soil moisture forecasting, FAO-56 Penman-Monteith daily water balance engine, and bilingual irrigation advisory generation.

#### Tasks:
- [ ] 🤖 **P5.1**: Implement FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$) calculator (`agritwin/advisory/evapotranspiration.py`) using net solar radiation, temperature, wind speed, and vapor pressure.
- [ ] 🤖 **P5.2**: Implement Crop Evapotranspiration ($ET_c = K_c \times ET_0$) module utilizing dynamic $K_c$ curve for Pakistani wheat stages (Initial: 0.35, Crop Development: 0.75, Mid-Season: 1.15, Late Season: 0.45).
- [ ] 🤖 **P5.3**: Build Soil Moisture Balance & Depletion Model (`agritwin/advisory/water_balance.py`):
  - Total Available Water ($TAW = 1000 \times (\theta_{FC} - \theta_{WP}) \times Z_r$)
  - Readily Available Water ($RAW = p \times TAW$, with depletion factor $p \approx 0.55$ for wheat)
  - Daily root zone depletion tracking fusing rainfall, irrigation events, $ET_c$, and ground ESP32 moisture readings
- [ ] 🤖 **P5.4**: Implement 7-day Soil Moisture Sequence Forecaster (`agritwin/models/soil_moisture_forecaster.py`) predicting volumetric soil water content over next 7 days based on weather forecast.
- [ ] 🤖 **P5.5**: Implement Irrigation Advisory Rule Engine (`agritwin/advisory/irrigation_engine.py`):
  - Urgency categorization: `OPTIMAL` (green), `MONITOR` (yellow), `CRITICAL_IRRIGATE` (red)
  - Recommendation outputs: Recommended water depth (mm), volume per acre ($m^3$/acre), tubewell pumping hours (based on standard 1-cusec tubewell)
  - Bilingual advisory messages (English & Urdu Nastaliq-friendly text)
  - Mandatory disclaimer: "Advisory only; calibrate with local field conditions"
- [ ] 🤖 **P5.6**: Write comprehensive tests (`tests/test_advisory.py`) covering edge cases (heavy rain forecast, extreme heat, probe failure fallback).

#### Definition of Done (Phase 5):
1. FAO-56 Penman-Monteith formulas tested and verified against standard benchmark values.
2. Soil moisture depletion tracks root zone changes accurately and triggers irrigation alerts at $RAW$ threshold.
3. Bilingual advisories output clear English and Urdu recommendations with tubewell hours.
4. Changes committed, merged, tagged `phase-5`, and pushed to GitHub.

---

### Phase 6: Climate-Risk "What-If" Scenario Simulator
**Branch:** `phase-6-simulator` · **Tag:** `phase-6`
**Objective:** Deliver an interactive simulation engine allowing farmers and agronomists to model climate shocks (heatwaves, drought, excessive rain, delayed irrigation) and observe projected impacts on crop yield and soil moisture.

#### Tasks:
- [ ] 🤖 **P6.1**: Implement scenario generator (`agritwin/simulator/what_if.py`):
  - Heatwave perturbation (+1°C to +5°C temperature offset, particularly during March terminal grain-filling stage)
  - Precipitation anomaly (-100% to +150% rainfall modification simulating drought vs heavy rain)
  - Irrigation delay perturbation (shifting scheduled irrigations by +7, +14, +21 days)
  - Compound scenario combinations
- [ ] 🤖 **P6.2**: Link perturbation engine to feature transformer and DeepAgroNet / baseline models to compute relative yield impact ($\Delta Yield\%$).
- [ ] 🤖 **P6.3**: Implement agronomic stress index calculators:
  - Heat Stress Index (accumulated hours with $T > 32^\circ C$ during flowering/anthesis)
  - Water Deficit Stress Days (consecutive days below $RAW$)
- [ ] 🤖 **P6.4**: Build FastAPI simulation endpoints (`POST /api/v1/scenarios/run` and `GET /api/v1/scenarios/presets`).
- [ ] 🤖 **P6.5**: Add unit and sensitivity tests (`tests/test_simulator.py`) confirming monotonic response to severe stressors (e.g., severe heatwave causes predicted yield drop).

#### Definition of Done (Phase 6):
1. What-If engine runs scenarios in < 1 second.
2. Realistic stress outputs produced for historical baseline vs perturbed scenarios.
3. API endpoints tested and verified.
4. Code committed, merged to `main`, tagged `phase-6`, and pushed to GitHub.

---

### Phase 7: Responsive Web Dashboard (Bilingual English/Urdu)
**Branch:** `phase-7-dashboard` · **Tag:** `phase-7`
**Objective:** Build a modern, responsive web application (React, Vite, TypeScript, Tailwind CSS, Leaflet, Chart.js) featuring digital twin map, live sensor stream, NDVI trajectory, yield forecast, irrigation cards, pest risk indicator, what-if playground, and English/Urdu bilingual RTL support.

#### Tasks:
- [ ] 🤖 **P7.1**: Scaffold React + Vite + TypeScript application in `frontend/` with Tailwind CSS, Lucide icons, and `react-i18next`.
- [ ] 🤖 **P7.2**: Implement internationalization (`frontend/src/i18n/`):
  - English (`en.json`) and Urdu (`ur.json`) translation dictionaries
  - Dynamic RTL / LTR layout switching and Urdu typography support
- [ ] 🤖 **P7.3**: Build Interactive Digital Twin Map (`frontend/src/components/Map/`):
  - Leaflet map rendering Punjab districts with choropleth yield stats
  - Pilot field polygon zoom-in with NDVI colormap layer overlay (Sentinel-2)
  - Sensor node location marker with live status badge
- [ ] 🤖 **P7.4**: Build Live Telemetry & Field Overview Panel (`frontend/src/components/Telemetry/`):
  - Real-time updates via WebSocket connection
  - Gauges for soil moisture %, air temperature, relative humidity, and battery level
  - Prominent "SIMULATED" badge indicator whenever telemetry source is simulated
- [ ] 🤖 **P7.5**: Build Multi-Spectral Crop-Health & Weather Charts (`frontend/src/components/Charts/`):
  - Multi-temporal NDVI seasonal curve compared to district normal
  - 7-day weather forecast and historical temperature/rainfall bar/line charts
  - Soil moisture forecast curve showing $FC$ (Field Capacity), $PWP$ (Permanent Wilting Point), and $RAW$ threshold
- [ ] 🤖 **P7.6**: Build Irrigation Advisory & Pest-Risk Alert Cards (`frontend/src/components/Advisories/`):
  - Visual urgency indicator (Green / Yellow / Red)
  - Actionable guidance: recommended water depth (mm) and tubewell hours
  - Pest-risk indicator (e.g. wheat rust risk based on high humidity + moderate temperature conditions)
  - Advisory disclaimer notice
- [ ] 🤖 **P7.7**: Build Interactive What-If Climate Playground (`frontend/src/components/Simulator/`):
  - Sliders for Temperature offset ($\Delta T$), Rainfall modifier (%), and Irrigation delay (days)
  - Real-time comparison card: Baseline vs Simulated Yield and Stress Index
- [ ] 🤖 **P7.8**: Add footer with attribution badges: Open-Meteo (CC BY 4.0), Copernicus Sentinel-2 / GEE, SoilGrids ISRIC.
- [ ] 🤖 **P7.9**: Complete FastAPI backend API (`agritwin/api/`):
  - REST endpoints for fields, districts, NDVI, weather, telemetry, advisories, scenarios
  - CORS configuration, static frontend mounting option, OpenAPI `/docs` documentation
- [ ] 🤖 **P7.10**: Build frontend integration tests and verify full UI responsive layout on desktop and mobile viewports.

#### Definition of Done (Phase 7):
1. Web frontend builds cleanly (`npm run build`) without TypeScript or lint errors.
2. Map, charts, live telemetry, advisories, and what-if simulator operate smoothly.
3. Language toggle switches seamlessly between English (LTR) and Urdu (RTL).
4. All simulated data clearly display the "SIMULATED" badge.
5. Changes committed, merged to `main`, tagged `phase-7`, and pushed to GitHub.

---

### Phase 8: Containerization, Defense Kit & Final Validation
**Branch:** `phase-8-defense-prep` · **Tag:** `phase-8`
**Objective:** Package the entire system with Docker Compose for one-command deployment, execute end-to-end integration tests, produce capstone defense materials (demo script, viva Q&A bank, architecture diagrams), and finalize project documentation.

#### Tasks:
- [ ] 🤖 **P8.1**: Create production-ready Docker containers:
  - `backend.Dockerfile` (Python FastAPI, PyTorch CPU, data packages)
  - `frontend.Dockerfile` (Multi-stage Node build with Nginx web server)
  - `docker-compose.yml` orchestrating PostgreSQL database, FastAPI backend, React frontend, and optional ESP32 simulator container
- [ ] 🤖 **P8.2**: Write end-to-end integration test suite (`tests/test_e2e.py`) validating the entire flow: sensor ingestion → feature calculation → yield forecasting → advisory generation → API delivery.
- [ ] 🤖 **P8.3**: Author Comprehensive Architecture & System Guide (`docs/ARCHITECTURE.md`) with data flow diagrams, math formulations, and API specifications.
- [ ] 🤖 **P8.4**: Author Capstone Defense Kit:
  - `docs/DEMO_SCRIPT.md`: Step-by-step 5-minute presentation & live demonstration script for examiners
  - `docs/VIVA_QA.md`: Comprehensive bank of anticipated viva questions & technical answers (covering deep learning choices, 1D-CNN vs LSTM, FAO-56 math, hardware calibration, sensor drift, satellite limitations)
- [ ] 🤖 **P8.5**: Finalize root `README.md` with one-command launch instructions, screenshots guide, architecture summary, and research references.
- [ ] 🤖 **P8.6**: Perform final repository audit: ensure no secrets are committed, licenses and attributions are in order, all tests pass, and git history is organized.

#### Definition of Done (Phase 8):
1. Entire system starts cleanly with `docker compose up --build`.
2. All automated tests pass (100% pass rate).
3. Complete defense kit and documentation ready for academic evaluation.
4. Final branch merged to `main`, tagged `phase-8`, and pushed to GitHub.

---

## 4. Traceability Matrix

| Capstone Proposal Objective | Code Packages | Verification & Output |
|---|---|---|
| **O1: Hybrid Digital Twin Architecture** (Satellite + Weather + Soil + ESP32) | `agritwin/data/`, `agritwin/core/models.py`, `firmware/`, `simulator/` | Real-time sensor stream fused with Sentinel-2 NDVI, Open-Meteo, and SoilGrids in DB. |
| **O2: Multi-Spectral Crop-Health Monitoring** | `agritwin/data/satellite.py`, `frontend/src/components/Map/`, `frontend/src/components/Charts/` | Weekly NDVI trajectory, spatial map overlay, vegetation anomaly detection. |
| **O3: DeepAgroNet & Baseline Benchmarks** | `agritwin/features/`, `agritwin/models/`, `docs/MODEL_BENCHMARK.md` | PyTorch 1D-CNN + LSTM vs RF vs XGBoost benchmarked on Punjab wheat yields using LOSO CV ($R^2$, $RMSE$, $MAE$). |
| **O4: Climate-Risk "What-If" Simulator** | `agritwin/simulator/what_if.py`, `frontend/src/components/Simulator/` | Dynamic simulation of heatwave, rainfall change, and irrigation shifts. |
| **O5: Urdu-Friendly Web Dashboard** | `frontend/`, `agritwin/api/`, `agritwin/advisory/` | Responsive React SPA, Urdu RTL localization, irrigation advisories, pest-risk alerts. |
