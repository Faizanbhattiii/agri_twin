# AgriTwin Pakistan — Data Ingestion & Caching Layer

This package (`agritwin.data`) manages multi-source environmental and agronomic data ingestion for wheat monitoring in Punjab, Pakistan.

---

## Data Sources & Attributions

1. **Weather Data (`agritwin/data/weather.py`)**
   - **Provider:** Open-Meteo Weather API (`https://open-meteo.com/`)
   - **License & Terms:** Free non-commercial tier under **CC BY 4.0** (< 10,000 requests/day, 600/min).
   - **Attribution:** *"Weather data provided by Open-Meteo.com (CC BY 4.0)"*
   - **Variables:** Daily $T_{min}, T_{max}, T_{mean}$, precipitation sum, shortwave solar radiation, relative humidity, wind speed, and FAO-56 reference evapotranspiration ($ET_0$).
   - **Caching:** Responses are hashed by coordinates and date range and cached to disk. Fallback to realistic Punjabi agro-meteorological winter curve with `source='simulated'` when offline.

2. **Soil Data (`agritwin/data/soil.py`)**
   - **Provider:** ISRIC SoilGrids 250m v2.0 REST API (`https://rest.isric.org/`)
   - **License:** Creative Commons Attribution 4.0 International.
   - **Properties:** Clay %, Sand %, Silt %, Soil Organic Carbon (SOC %), pH, Bulk density ($g/cm^3$), Cation Exchange Capacity (CEC), Field Capacity ($FC$), Permanent Wilting Point ($PWP$), and Total Available Water ($TAW$).
   - **Fallbacks:** Calibrated baseline alluvial Indus basin Loam characteristics.

3. **Satellite Vegetation Indices (`agritwin/data/satellite.py`)**
   - **Provider:** European Space Agency (ESA) Copernicus Sentinel-2 (Level-2A Surface Reflectance) via Google Earth Engine (GEE).
   - **Indices:** Normalized Difference Vegetation Index ($NDVI = \frac{B8 - B4}{B8 + B4}$) and Enhanced Vegetation Index ($EVI$).
   - **Cadence:** Weekly aggregates across the 27-week Rabi wheat window (Nov 1 to May 10).
   - **Offline Mode:** Uses a double-logistic phenological curve calibrated to historical Punjab wheat seasons with `source='simulated'`.

4. **District Wheat Yield Ground Truth (`agritwin/data/yields.py`)**
   - **Source:** Punjab Crop Reporting Service (CRS) official agricultural statistics.
   - **Coverage:** 36 Punjab districts across 10 seasons (2013-14 through 2022-23), totaling 360 validated district-season records.
   - **Units:** Area (thousand acres), Production (thousand tonnes), Yield (kg/ha and maund/acre).

---

## Train/Serve Parity & Integrity Rules
- **Rule 4 (No Fake Data):** Any data generated synthetically or via fallback is strictly tagged with `source='simulated'` and rendered with a visible warning badge in user-facing components.
- **Rule 15 (Server-side Only):** Browsers never make direct requests to external APIs; the backend caches and serves all data.
