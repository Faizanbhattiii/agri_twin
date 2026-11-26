# Architecture & Engineering Decisions Log (ADR)

This file tracks all key technical, architectural, and design decisions for AgriTwin Pakistan.

---

### Record of Initial Architectural Decisions (D1 – D18)

| ID | Decision | Context & Rationale | Status |
|---|---|---|---|
| **D1** | Crop = wheat (Rabi), region = Punjab, Pakistan | Best official district-level yield data from Punjab Crop Reporting Service; clear Rabi season (Nov to May). Config-driven in `config/crops/wheat.yaml`. | Accepted |
| **D2** | Two spatial scales: District-level + Pilot field | Multi-season district statistics provide sample size for DeepAgroNet/ML; Pilot field (polygon + ESP32) provides live digital twin & ground-truth telemetry. | Accepted |
| **D3** | Python 3.11/3.14 + PyTorch (CPU primary) + scikit-learn + XGBoost | Stable, reproducible machine learning stack; runnable on standard developer laptops and Colab. | Accepted |
| **D4** | PostgreSQL 15/16 + SQLAlchemy 2.0 + Alembic (GeoJSON via JSONB, SQLite test fallback) | Standardized relational persistence for time-series and geometries without heavyweight GIS server requirement. | Accepted |
| **D5** | FastAPI Backend + WebSocket + APScheduler | High performance async REST API, OpenAPI docs, and real-time sensor broadcasting. | Accepted |
| **D6** | React 18 + Vite + TypeScript + Tailwind CSS + Leaflet + Chart.js | Modern, fast developer experience, responsive UI, zero-token map tiles, lightweight chart rendering. | Accepted |
| **D7** | ESP32 DevKit (30-pin) + Capacitive Soil Moisture v1.2 + DHT22 (+ DS18B20) + Python Simulator | Standard low-cost IoT hardware, non-corrosive capacitive probe, with robust software simulation fallback. | Accepted |
| **D8** | 15-minute telemetry cadence, deep-sleep cycle, SPIFFS offline buffer | Balances battery/solar longevity with sufficient temporal resolution. | Accepted |
| **D9** | Pipeline refresh intervals (Weather: 6h/daily, NDVI: ~5 days, SoilGrids: once) | Aligns with natural satellite revisit cycles and API rate limit constraints. | Accepted |
| **D10** | Timezone `Asia/Karachi` (UTC+5) for display, store all timestamps in UTC | Prevents daylight/timezone bugs while providing natural farmer-facing timestamps. | Accepted |
| **D11** | Dual units: kg/ha internal/metric and maund/acre local display | $1 \text{ maund} = 40 \text{ kg}$, $1 \text{ acre} = 0.404686 \text{ ha} \implies 1 \text{ maund/acre} \approx 98.84 \text{ kg/ha}$. | Accepted |
| **D12** | Target yield = total district yield | Official Punjab crop reporting aggregates total yield per district; cropland masks cannot cleanly separate water sources at scale. | Accepted |
| **D13** | Wheat season window: Nov 1 to May 10 (27 weekly intervals) | Configurable per crop; captures sowing, tillering, jointing, booting, heading, grain filling, and harvest. | Accepted |
| **D14** | Leave-One-Season-Out (LOSO) primary CV protocol | Prevents temporal data leakage and tests multi-year generalization across weather variations. | Accepted |
| **D15** | Server-side API caching (no direct browser calls to external GEE/Open-Meteo) | Ensures stability, offline demo capability, and API quota conservation. | Accepted |
| **D16** | Strict Open-Meteo CC BY 4.0 attribution & non-commercial GEE project usage | Full compliance with free API terms of service. | Accepted |
| **D17** | Bilingual UI: English and Urdu RTL | Accessibility for local Pakistani extension workers and farmers. | Accepted |
| **D18** | Advisory-only disclaimer banner | Ethical transparency: AI recommendations support rather than replace human agronomist judgement. | Accepted |
| **D19** | Dynamic roadmap completion | User approved completing detailed Phases 0 to 8 in `docs/IMPLEMENTATION_PLAN.md` based on initial scope and architecture specifications. | Accepted |
| **D20** | DeepAgroNet target standardization & uncertainty calibration | Standardize target yields during deep neural network optimization to guarantee gradient stability under Huber loss, and register `target_mean` and `target_std` model buffers to automatically output real kg/ha and maund/acre bounds in inference. | Accepted |
