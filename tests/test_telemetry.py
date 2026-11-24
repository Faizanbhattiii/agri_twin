"""
Integration Tests for Phase 3: Telemetry Ingestion, Validation, Simulator, and WebSocket.
Uses FastAPI TestClient with an isolated temporary SQLite database.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agritwin.api.app import create_app
from agritwin.core.config import settings
from agritwin.core.database import get_db
from agritwin.core.models import Base, District, Field
from simulator.esp32_simulator import ESP32Simulator


@pytest.fixture
def test_client(tmp_path: Path):
    """Provide a FastAPI TestClient backed by an isolated SQLite test database."""
    db_file = tmp_path / "test_telemetry.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Seed district & pilot field
    with TestingSessionLocal() as session:
        dist = District(
            id="faisalabad",
            name="Faisalabad",
            division="Faisalabad",
            centroid_lat=31.4187,
            centroid_lon=73.0791,
        )
        field = Field(
            id=settings.pilot_field_id,
            district_id="faisalabad",
            name="Faisalabad Pilot",
            area_acres=5.0,
            latitude=31.4289,
            longitude=73.0782,
            is_pilot=True,
        )
        session.add_all([dist, field])
        session.commit()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client


def test_health_endpoint(test_client: TestClient):
    """Verify /health returns service status."""
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["timezone"] == "Asia/Karachi"


def test_ingest_valid_simulated_telemetry(test_client: TestClient):
    """Verify valid simulated payload is accepted, persisted, and flagged is_simulated=True."""
    sim = ESP32Simulator(field_id=settings.pilot_field_id)
    payload = sim.step()

    resp = test_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers={"X-Node-API-Key": settings.field_node_api_key},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["is_simulated"] is True
    assert body["reading"]["field_id"] == settings.pilot_field_id
    assert body["reading"]["source"] == "simulated"


def test_ingest_rejects_invalid_api_key(test_client: TestClient):
    """Verify unauthorized device requests are rejected with 401."""
    sim = ESP32Simulator(field_id=settings.pilot_field_id)
    payload = sim.step()

    resp = test_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers={"X-Node-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_ingest_rejects_corrupted_sensor_fault(test_client: TestClient):
    """Verify out-of-range / DHT22 failure sentinel payloads are rejected with 422."""
    sim = ESP32Simulator(field_id=settings.pilot_field_id)
    fault_payload = sim.step(inject_fault=True)

    resp = test_client.post(
        "/api/v1/telemetry",
        json=fault_payload,
        headers={"X-Node-API-Key": settings.field_node_api_key},
    )
    assert resp.status_code == 422


def test_ingest_unknown_field_returns_404(test_client: TestClient):
    """Verify posting telemetry for an unregistered field returns 404."""
    sim = ESP32Simulator(field_id="non-existent-field")
    payload = sim.step()

    resp = test_client.post(
        "/api/v1/telemetry",
        json=payload,
        headers={"X-Node-API-Key": settings.field_node_api_key},
    )
    assert resp.status_code == 404


def test_get_telemetry_history_batch(test_client: TestClient):
    """Verify batch ingestion and chronological retrieval."""
    sim = ESP32Simulator(field_id=settings.pilot_field_id)
    batch = sim.generate_batch(count=5)

    for item in batch:
        r = test_client.post(
            "/api/v1/telemetry",
            json=item,
            headers={"X-Node-API-Key": settings.field_node_api_key},
        )
        assert r.status_code == 201

    resp = test_client.get(f"/api/v1/telemetry/{settings.pilot_field_id}?limit=10")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 5
    # Ordered newest first
    assert rows[0]["timestamp"] >= rows[-1]["timestamp"]


def test_websocket_broadcast_on_ingest(test_client: TestClient):
    """Verify WebSocket listener receives live telemetry_update upon POST ingestion."""
    sim = ESP32Simulator(field_id=settings.pilot_field_id)
    payload = sim.step()

    with test_client.websocket_connect("/ws/telemetry") as websocket:
        resp = test_client.post(
            "/api/v1/telemetry",
            json=payload,
            headers={"X-Node-API-Key": settings.field_node_api_key},
        )
        assert resp.status_code == 201

        msg = websocket.receive_json()
        assert msg["event"] == "telemetry_update"
        assert msg["is_simulated"] is True
        assert msg["data"]["field_id"] == settings.pilot_field_id
        assert msg["data"]["soil_moisture_pct"] == payload["soil_moisture_pct"]
