# Graph Report - agri_twin  (2026-11-24)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 313 nodes · 502 edges · 21 communities (6 shown, 15 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 25 edges (avg confidence: 0.89)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `82239842`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 20

## God Nodes (most connected - your core abstractions)
1. `YieldDataLoader` - 18 edges
2. `Base` - 17 edges
3. `seed_database()` - 15 edges
4. `WeatherClient` - 14 edges
5. `SatelliteClient` - 14 edges
6. `SoilGridsClient` - 14 edges
7. `pilot_field` - 13 edges
8. `growth_stages` - 12 edges
9. `District` - 11 edges
10. `Field` - 10 edges

## Surprising Connections (you probably didn't know these)
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `District`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `Field`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `IrrigationAdvisory`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py
- `test_database_seeder()` --uses--> `SensorTelemetry`  [INFERRED]
  tests/test_database.py → agritwin/core/models.py

## Import Cycles
- None detected.

## Communities (21 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (21): init_db(), Base, District, Field, IrrigationAdvisory, SatelliteReading, SensorTelemetry, SoilProfile (+13 more)

### Community 1 - "Community 1"
Cohesion: 0.05
Nodes (41): calendar, base_temperature_c, season_end_day, season_end_month, season_start_day, season_start_month, total_weeks, crop (+33 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (12): AppSettings, get_crop_config(), get_system_settings(), kg_per_ha_to_maund_per_acre(), load_env_file(), load_yaml(), maund_per_acre_to_kg_per_ha(), test_app_settings_defaults() (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (29): app, author, description, name, timezone, version, attribution, satellite (+21 more)

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (3): WeatherClient, temp_cache_dir(), TestWeatherClient

### Community 6 - "Community 6"
Cohesion: 0.10
Nodes (4): create_db_engine(), get_db(), run_migrations_offline(), run_migrations_online()

## Knowledge Gaps
- **1 isolated node(s):** `agritwin`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 180 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `YieldDataLoader` connect `Community 0` to `Community 9`, `Community 10`, `Community 5`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `Base` (e.g. with `init_db()` and `db_session()`) actually correct?**
  _`Base` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `agritwin` to the rest of the system?**
  _1 weakly-connected nodes found - possible missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06247086247086247 - nodes in this community are weakly interconnected._
- **Why does `SatelliteClient` connect `Community 7` to `Community 5`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.047619047619047616 - nodes in this community are weakly interconnected._
- **Why does `SoilGridsClient` connect `Community 8` to `Community 5`?**
  _High betweenness centrality (0.064) - this node is a cross-community bridge._