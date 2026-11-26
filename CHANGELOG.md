# Changelog

All notable changes to the AgriTwin Pakistan project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

---

## [0.8.0] - 2026-11-26

### Phase 7: Responsive Web Dashboard (Bilingual English/Urdu)
- Scaffolded responsive Single Page Application (SPA) in `frontend/` powered by React 18, Vite, TypeScript, and Tailwind CSS.
- Implemented comprehensive internationalization (`frontend/src/i18n/`) with English and Urdu translation catalogs (`en.json`, `ur.json`), dynamic RTL layout toggling, and Noto Nastaliq Urdu typography.
- Developed Interactive Digital Twin Map (`frontend/src/components/Map/DigitalTwinMap.tsx`) leveraging Leaflet, rendering 36 Punjab district choropleths colored by wheat yield (maund/acre), interactive tooltips, pilot research field polygon overlay, and sensor node location markers.
- Built Live Telemetry panel (`frontend/src/components/Telemetry/TelemetryGauges.tsx`) with real-time WebSocket stream (`/ws/telemetry`), 4 visual gauges (soil moisture %, air temperature, humidity, battery), and prominent `SIMULATED` badge indicator.
- Built Multi-Spectral Crop-Health & Weather Charts (`frontend/src/components/Charts/CropHealthCharts.tsx`) rendering 27-week Sentinel-2 NDVI trajectory vs district normal, 7-day Open-Meteo weather forecast, and 7-day projected soil moisture depletion with Field Capacity, Wilting Point, and RAW thresholds.
- Built Irrigation Advisory & Pest Risk Cards (`frontend/src/components/Advisories/IrrigationCard.tsx`) displaying urgency status (OPTIMAL, MONITOR, CRITICAL_IRRIGATE), recommended water depth (mm), 1-cusec tubewell pumping hours, rust & aphid pest risk indicators, and ethical disclaimer.
- Built Interactive What-If Climate Playground (`frontend/src/components/Simulator/WhatIfPlayground.tsx`) with preset selectors, interactive temperature/rainfall/irrigation sliders, real-time yield comparison cards, agronomic stress indices, and bilingual mitigation advice.
- Built Dashboard REST API router (`agritwin/api/dashboard.py`) and mounted frontend static production bundle on FastAPI root (`/`), passing CORS and static asset resolution.
- Authored automated tests in `tests/test_dashboard.py` verifying all dashboard endpoints and static single-page application delivery (55/55 passing project-wide).
- Compiled clean production build (`npm run build`) in 9.66s without warnings or errors.

---

## [0.7.0] - 2026-11-26

### Phase 6: Climate-Risk "What-If" Scenario Simulator
- Implemented core interactive what-if simulation engine in `agritwin/simulator/what_if.py` supporting temperature offsets (-5C to +10C), precipitation scaling (0.0x to 3.0x), and irrigation delays (+0 to +45 days).
- Implemented catalog of 6 realistic presets in `PRESET_SCENARIOS` with bilingual English and Urdu descriptions (baseline, March terminal heatwave, severe winter drought, 14-day irrigation delay, compound crisis, late torrential rain).
- Integrated FAO-33 relative water deficit yield reduction function $(1 - Y_a/Y_m) = K_y(1 - ET_{c,adj}/ET_c)$ and physiological March terminal heat shock penalties ($T_{max} > 32^\circ	ext{C}$) into model inference.
- Implemented `AgronomicStressCalculator` computing heat stress degree-hours, grain-filling heat days, water deficit stress days, and bilingual mitigation advice.
- Built FastAPI simulation router in `agritwin/api/scenarios.py` mounted at `/api/v1/scenarios` (`GET /presets`, `POST /run`) with execution latency < 150ms.
- Authored Pydantic v2 validation schemas for scenarios in `agritwin/api/schemas.py`.
- Authored test suite `tests/test_simulator.py` covering preset metadata, baseline invariance, heatwave sensitivity, drought water stress, compound shock amplification, and API response latencies (49/49 passing project-wide).
- Documented package in `agritwin/simulator/README.md` and updated `HUMAN_TASKS.md` for Task H-07 review readiness.

---

## [0.6.0] - 2026-11-26

### Phase 5: Soil-Moisture Forecaster & Irrigation Advisory Engine
- Implemented FAO-56 Penman-Monteith daily reference evapotranspiration (ET0) calculator in gritwin/advisory/evapotranspiration.py including solar declination, extraterrestrial radiation, albedo, net radiation, psychrometric constant, and elevation/latitude physics, with Hargreaves-Samani fallback.
- Implemented crop water requirement calculator in gritwin/advisory/crop_water.py with 4-stage phenological $ curve (Initial 0.35, Development 0.35->1.15, Mid-season 1.15, Late-season 1.15->0.40), root depth expansion (0.3m to 1.2m), and water stress coefficient $.
- Implemented daily root-zone soil water balance model in gritwin/advisory/water_balance.py tracking Total Available Water ($), Readily Available Water ($), root depletion ($), effective rainfall runoff, deep percolation, and telemetry sensor fusion.
- Implemented 7-day soil moisture and water stress trajectory forecaster in gritwin/models/soil_moisture_forecaster.py simulating depletion forward using weather forecasts.
- Implemented irrigation advisory rule engine in gritwin/advisory/irrigation_engine.py producing 4 urgency statuses (OPTIMAL, MONITOR, CRITICAL_IRRIGATE, RAIN_DEFERRED), gross depth, volume (^3$), tubewell hours (1-cusec / 101.94 ^3$/hr), bilingual English & Urdu Nastaliq action texts, and mandatory ethical disclaimer.
- Added comprehensive unit tests in 	ests/test_advisory.py verifying mathematical correctness, agronomic scaling, sensor fusion, and rain deferral (41/41 passing project-wide).
- Documented advisory architecture in gritwin/advisory/README.md and updated HUMAN_TASKS.md for local agronomic validation.

---

## [0.5.0] - 2026-11-26

### Phase 4: Feature Engineering, DeepAgroNet & Baseline Benchmarks
- Implemented unified feature pipeline in `agritwin/features/pipeline.py` enforcing strict train/serve parity (Rule 9) across training and live inference.
- Engineered 27-week temporal sequence (GDD with $T_{base}=5^\circ\text{C}$, precipitation, $T_{mean}$, $T_{max}$, $T_{min}$, solar radiation, VPD, extreme heat days $T_{max} > 32^\circ\text{C}$, interpolated Sentinel-2 NDVI/EVI).
- Engineered 9 static soil & geospatial features (clay, sand, silt, SOC, pH, bulk density, TAW, latitude, longitude) and 49-dimensional tabular dataset with 4 growth-stage aggregations.
- Implemented `PunjabWheatDataset` in `agritwin/features/dataset.py` with multi-threaded prefetching, processed NPZ/CSV disk caching, and Leave-One-Season-Out (LOSO) and Leave-Districts-Out (LDO) cross-validation iterators.
- Implemented baseline regressors in `agritwin/models/baselines.py` (RidgeCV, Random Forest, XGBoost) with unified fit/predict, feature importances, and serialization.
- Implemented `DeepAgroNet` in `agritwin/models/deepagronet.py` combining 1D-CNN temporal feature extractors, 2-layer Bidirectional LSTM, parametric temporal attention pooling across 27 weeks, static soil MLP branch, and multimodal fusion head with calibrated Gaussian uncertainty prediction ($\mu, \sigma$) and 95% confidence intervals.
- Implemented evaluation metrics and unit conversions in `agritwin/models/metrics.py`.
- Built cross-validation and benchmark harness in `agritwin/models/train.py` executing 10-season LOSO temporal cross-validation without data leakage.
- Generated genuine benchmark report in `docs/MODEL_BENCHMARK.md` (RF: $R^2=0.9185$, $RMSE=161.8\text{ kg/ha}$; XGBoost: $R^2=0.9080$, $RMSE=171.9\text{ kg/ha}$; DeepAgroNet: $R^2=0.8697$, $RMSE=204.6\text{ kg/ha}$; Ridge: $R^2=0.5904$, $RMSE=362.8\text{ kg/ha}$).
- Serialized production models under `models/` (`deepagronet_best.pt`, `rf_best.joblib`, `xgb_best.json`, `ridge_best.joblib`, `pipeline_scaler.pkl`, `model_manifest.json`).
- Authored package documentation in `agritwin/features/README.md` and `agritwin/models/README.md`.
- Authored automated tests in `tests/test_feature_parity.py` and `tests/test_models.py` (34/34 passing project-wide).
- Updated `HUMAN_TASKS.md` for task H-05 review readiness.

---

## [0.4.0] - 2026-11-24

### Phase 3: Field Node Firmware, Simulator & Telemetry Ingestion
- Authored ESP32 PlatformIO firmware in `firmware/src/main.cpp`, `firmware/platformio.ini`, and `firmware/src/config.h.example` featuring ADC1 two-point capacitive soil moisture calibration, DHT22 + optional DS18B20 sensing, Wi-Fi exponential backoff, SPIFFS 200-entry offline ring buffer, and 15-minute deep-sleep cycle.
- Authored comprehensive hardware wiring guide, BOM, and calibration instructions in `firmware/README.md`.
- Implemented standalone Python ESP32 software simulator in `simulator/esp32_simulator.py` with diurnal Punjab climate curves, irrigation drying cycles, fault injection, and `source='simulated'` tagging.
- Implemented Pydantic v2 validation schemas (`agritwin/api/schemas.py`), real-time WebSocket broadcaster (`agritwin/api/websocket.py`), FastAPI telemetry endpoints (`agritwin/api/telemetry.py`), and main FastAPI app (`agritwin/api/app.py`).
- Added API package documentation in `agritwin/api/README.md`.
- Updated `HUMAN_TASKS.md` for Phase 3 hardware assembly and flashing readiness.
- Authored integration test suite `tests/test_telemetry.py` (24/24 tests passing across project).

---

## [0.3.0] - 2026-11-24

### Phase 2: Relational Data Model, Migrations & Seed Geometry
- Designed and implemented SQLAlchemy 2.0 ORM models in `agritwin/core/models.py` (`District`, `Field`, `SoilProfile`, `WeatherObservation`, `WeatherForecast`, `SatelliteReading`, `SensorTelemetry`, `IrrigationAdvisory`, `YieldForecast`).
- Implemented multi-dialect database engine and session factory in `agritwin/core/database.py` with automatic SQLite foreign key enforcement and PostgreSQL compatibility.
- Initialized and configured Alembic migration environment (`alembic/`) with dynamic URL resolution from `AppSettings`.
- Generated initial migration script `alembic/versions/90dcf677a8e1_initial_schema.py` and executed `alembic upgrade head`.
- Implemented database seeder `agritwin/core/seed.py` seeding all 36 Punjab districts, administrative divisions, representative polygon geometries, baseline soil profiles, and the Pilot Research Field in Faisalabad.
- Authored manual action guide in `HUMAN_TASKS.md` tracking all student responsibilities across all project phases.
- Authored integration test suite in `tests/test_database.py` (17/17 tests passing across the project).

---

## [0.2.0] - 2026-11-24

### Phase 1: Multi-Source Data Pipeline & Punjab Dataset
- Built Punjab wheat yield ground-truth dataset (`data/raw/punjab_wheat_yields_2013_2023.csv`) spanning 360 records across 36 districts and 10 seasons (2013-14 through 2022-23) based on Punjab Crop Reporting Service records.
- Implemented `agritwin/data/yields.py` for schema validation, unit conversions, and district baseline calculation.
- Implemented `agritwin/data/weather.py` with Open-Meteo API integration, 7-day forecast, disk caching, CC BY 4.0 attribution, and realistic Punjab climate fallback.
- Implemented `agritwin/data/soil.py` querying ISRIC SoilGrids 2.0 REST API with Saxton-Rawls pedotransfer function estimating Field Capacity, Wilting Point, and Total Available Water (TAW).
- Implemented `agritwin/data/satellite.py` for Sentinel-2 NDVI/EVI trajectory with double-logistic wheat phenology and GEE connector.
- Implemented offline fixtures generator in `agritwin/data/fixtures.py`.
- Authored package documentation in `agritwin/data/README.md`.
- Added automated integration tests in `tests/test_data_pipeline.py`.

---

## [0.1.0] - 2026-11-24

### Phase 0: Project Scaffolding, Tooling & Verification Harness
- Completed Phase 0–8 master plan specifications in `docs/IMPLEMENTATION_PLAN.md`.
- Established Agent rules in `AGENTS.md` and `.agents/rules/agritwin.md` adhering to Section 0.
- Logged key decisions D1–D19 in `docs/DECISIONS.md`.
- Set up repository structure (`agritwin/`, `config/`, `data/`, `firmware/`, `simulator/`, `frontend/`, `tests/`, `docs/`).
- Added pinned dependencies in `requirements.txt` and `pyproject.toml`.
- Added `.env.example` with non-secret defaults.
- Authored crop configuration in `config/crops/wheat.yaml` with GDD thresholds, crop coefficients $K_c$, critical stages, and conversion factors.
- Implemented core settings loader in `agritwin/core/config.py`.
- Implemented and passed configuration test suite (`tests/test_config.py`).
