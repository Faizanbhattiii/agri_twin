# Changelog

All notable changes to the AgriTwin Pakistan project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

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
