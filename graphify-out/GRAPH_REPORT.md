# Graph Report - agri_twin  (2026-11-24)

## Corpus Check
- 37 files · ~20,186 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 16 file(s) not represented in the graph (top: (none) 8, .csv 3, .example 2)

## Summary
- 421 nodes · 701 edges · 26 communities (9 shown, 17 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 38 edges (avg confidence: 0.88)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2d28a0e7`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- models.py
- growth_stages
- config.py
- pilot_field
- WeatherClient
- test_telemetry.py
- env.py
- main.cpp
- SoilGridsClient
- YieldDataLoader
- schemas.py
- agritwin
- app.py
- TelemetryConnectionManager
- .load
- telemetry_websocket

## God Nodes (most connected - your core abstractions)
1. `Base` - 18 edges
2. `YieldDataLoader` - 18 edges
3. `seed_database()` - 15 edges
4. `WeatherClient` - 14 edges
5. `SatelliteClient` - 14 edges
6. `SoilGridsClient` - 14 edges
7. `ESP32Simulator` - 13 edges
8. `District` - 13 edges
9. `Field` - 13 edges
10. `pilot_field` - 13 edges

## Surprising Connections (you probably didn't know these)
- `test_client()` --calls--> `District`  [EXTRACTED]
  tests/test_telemetry.py → agritwin/core/models.py
- `test_client()` --calls--> `Field`  [EXTRACTED]
  tests/test_telemetry.py → agritwin/core/models.py
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `District`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `Field`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py

## Import Cycles
- None detected.

## Communities (26 total, 17 thin omitted)

### Community 0 - "models.py"
Cohesion: 0.06
Nodes (22): verify_node_api_key(), create_db_engine(), get_db(), init_db(), Base, District, Field, IrrigationAdvisory (+14 more)

### Community 1 - "growth_stages"
Cohesion: 0.05
Nodes (41): calendar, base_temperature_c, season_end_day, season_end_month, season_start_day, season_start_month, total_weeks, crop (+33 more)

### Community 2 - "config.py"
Cohesion: 0.05
Nodes (13): get_crop_config(), get_system_settings(), kg_per_ha_to_maund_per_acre(), load_yaml(), maund_per_acre_to_kg_per_ha(), generate_all_fixtures(), SatelliteClient, test_app_settings_defaults() (+5 more)

### Community 3 - "pilot_field"
Cohesion: 0.07
Nodes (29): app, author, description, name, timezone, version, attribution, satellite (+21 more)

### Community 4 - "WeatherClient"
Cohesion: 0.14
Nodes (3): WeatherClient, temp_cache_dir(), TestWeatherClient

### Community 5 - "test_telemetry.py"
Cohesion: 0.10
Nodes (10): ESP32Simulator, main(), post_reading(), test_get_telemetry_history_batch(), test_health_endpoint(), test_ingest_rejects_corrupted_sensor_fault(), test_ingest_rejects_invalid_api_key(), test_ingest_unknown_field_returns_404() (+2 more)

### Community 7 - "main.cpp"
Cohesion: 0.14
Nodes (7): connectWiFi(), enqueueOffline(), flushOfflineQueue(), postPayload(), readBatteryVoltage(), readSoilMoisturePct(), setup()

### Community 10 - "schemas.py"
Cohesion: 0.15
Nodes (5): TelemetryIn, TelemetryIngestResponse, TelemetryOut, get_field_telemetry(), ingest_telemetry()

### Community 21 - "app.py"
Cohesion: 0.16
Nodes (3): create_app(), lifespan(), test_client()

## Knowledge Gaps
- **1 isolated node(s):** `agritwin`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 239 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YieldDataLoader` connect `YieldDataLoader` to `models.py`, `config.py`?**
  _High betweenness centrality (0.073) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Base` (e.g. with `init_db()` and `db_session()`) actually correct?**
  _`Base` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `agritwin` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `models.py` be split into smaller, more focused modules?**
  _Cohesion score 0.061457418788410885 - nodes in this community are weakly interconnected._
- **Why does `SoilGridsClient` connect `SoilGridsClient` to `config.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Should `growth_stages` be split into smaller, more focused modules?**
  _Cohesion score 0.047619047619047616 - nodes in this community are weakly interconnected._
- **Should `config.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05098934550989345 - nodes in this community are weakly interconnected._