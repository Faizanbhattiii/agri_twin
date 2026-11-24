"""
FastAPI Telemetry Ingestion & WebSocket Streaming Router.
Receives JSON payloads from ESP32 nodes or the software simulator,
validates sensor bounds, persists to DB, and broadcasts over WebSocket.
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from agritwin.api.schemas import TelemetryIn, TelemetryIngestResponse, TelemetryOut
from agritwin.api.websocket import ws_manager
from agritwin.core.config import settings
from agritwin.core.database import get_db
from agritwin.core.models import Field, SensorTelemetry

router = APIRouter(tags=["Telemetry"])


def verify_node_api_key(x_node_api_key: Optional[str] = Header(default=None)) -> str:
    """Validate the X-Node-API-Key header against configured device key."""
    if not x_node_api_key or x_node_api_key != settings.field_node_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Node-API-Key"
        )
    return x_node_api_key


@router.post(
    "/api/v1/telemetry",
    response_model=TelemetryIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_telemetry(
    payload: TelemetryIn,
    db: Session = Depends(get_db),
    _api_key: str = Depends(verify_node_api_key),
) -> TelemetryIngestResponse:
    """
    Ingest a ground-truth or simulated sensor reading for a field.
    Persists to database and broadcasts live to connected WebSocket clients.
    """
    field = db.query(Field).filter(Field.id == payload.field_id).first()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field '{payload.field_id}' not found."
        )

    reading_ts = payload.timestamp or datetime.now(timezone.utc)
    if reading_ts.tzinfo is not None:
        reading_ts = reading_ts.astimezone(timezone.utc).replace(tzinfo=None)

    record = SensorTelemetry(
        field_id=payload.field_id,
        timestamp=reading_ts,
        soil_moisture_pct=payload.soil_moisture_pct,
        air_temp_c=payload.air_temp_c,
        relative_humidity_pct=payload.relative_humidity_pct,
        soil_temp_c=payload.soil_temp_c,
        battery_v=payload.battery_v,
        source=payload.source,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    out = TelemetryOut.model_validate(record)

    # Broadcast JSON-serializable dict to WebSocket listeners
    await ws_manager.broadcast({
        "event": "telemetry_update",
        "is_simulated": record.source == "simulated",
        "data": out.model_dump(mode="json"),
    })

    return TelemetryIngestResponse(
        status="accepted",
        reading=out,
        is_simulated=(record.source == "simulated"),
    )


@router.get("/api/v1/telemetry/{field_id}", response_model=List[TelemetryOut])
def get_field_telemetry(
    field_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[TelemetryOut]:
    """Retrieve recent telemetry readings for a specific field ordered newest first."""
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field '{field_id}' not found."
        )

    rows = (
        db.query(SensorTelemetry)
        .filter(SensorTelemetry.field_id == field_id)
        .order_by(SensorTelemetry.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [TelemetryOut.model_validate(r) for r in rows]


@router.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint streaming live telemetry updates to dashboard clients."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection open; ignore client pings/messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
