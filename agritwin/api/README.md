# AgriTwin Pakistan — FastAPI Backend & WebSocket Layer

This package (`agritwin.api`) provides the REST and WebSocket endpoints connecting IoT field nodes, data pipelines, AI models, and the React web dashboard.

## Current Endpoints (Phase 3)
- `GET /health` — Service health & timezone check.
- `POST /api/v1/telemetry` — Authenticated (`X-Node-API-Key`) ingestion endpoint for ESP32 nodes and the Python simulator. Validates physical sensor bounds, stores UTC timestamps, and broadcasts live updates.
- `GET /api/v1/telemetry/{field_id}` — Chronological sensor telemetry history.
- `WS /ws/telemetry` — Real-time WebSocket stream pushing `telemetry_update` events to connected dashboard clients.
