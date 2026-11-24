"""
ESP32 Field Node Software Simulator for AgriTwin Pakistan.
Simulates realistic diurnal temperature/humidity cycles and soil moisture drying curves
for Punjab wheat farmland when physical hardware is unavailable or for testing.
All generated payloads carry source='simulated' per Rule 4.
"""

import argparse
import math
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import requests

from agritwin.core.config import settings


class ESP32Simulator:
    """Generates realistic 15-minute sensor telemetry readings for a simulated ESP32 node."""

    def __init__(
        self,
        field_id: str = settings.pilot_field_id,
        initial_moisture_pct: float = 26.0,
        seed: int = 42,
    ) -> None:
        self.field_id = field_id
        self.moisture_pct = initial_moisture_pct
        self.rng = random.Random(seed)
        self.battery_v = 4.18

    def step(self, timestamp: Optional[datetime] = None, inject_fault: bool = False) -> Dict[str, Any]:
        """Advance simulation by one 15-minute step and return JSON-ready payload."""
        ts = timestamp or datetime.now(timezone.utc)

        if inject_fault:
            return {
                "field_id": self.field_id,
                "timestamp": ts.isoformat(),
                "soil_moisture_pct": 145.0,  # Out-of-bounds fault
                "air_temp_c": -999.0,        # DHT22 read failure sentinel
                "relative_humidity_pct": -10.0,
                "soil_temp_c": 20.0,
                "battery_v": 4.1,
                "source": "simulated",
            }

        # Diurnal temperature curve (peak at 14:30 local UTC+5 -> 09:30 UTC)
        local_hour = (ts.hour + 5 + ts.minute / 60.0) % 24.0
        temp_mean = 19.5
        temp_amp = 7.5
        air_temp = temp_mean + temp_amp * math.sin(2 * math.pi * (local_hour - 8.5) / 24.0)
        air_temp = round(air_temp + self.rng.uniform(-0.3, 0.3), 1)

        # Relative humidity inversely correlated with temperature
        humidity = 72.0 - (air_temp - 15.0) * 2.1 + self.rng.uniform(-1.5, 1.5)
        humidity = round(max(25.0, min(95.0, humidity)), 1)

        # Soil temperature lags air temp and has smaller amplitude
        soil_temp = round(17.5 + 2.5 * math.sin(2 * math.pi * (local_hour - 11.0) / 24.0), 1)

        # Soil moisture drying (~0.04% per 15-min step during daytime, triggers simulated irrigation < 15%)
        evap_rate = 0.05 if 8.0 <= local_hour <= 17.0 else 0.015
        self.moisture_pct = max(12.0, self.moisture_pct - evap_rate + self.rng.uniform(-0.02, 0.02))
        if self.moisture_pct <= 14.5:
            # Simulate irrigation event bringing soil back near Field Capacity (28%)
            self.moisture_pct = 28.0

        self.battery_v = round(max(3.4, self.battery_v - 0.0005), 2)

        return {
            "field_id": self.field_id,
            "timestamp": ts.isoformat(),
            "soil_moisture_pct": round(self.moisture_pct, 1),
            "air_temp_c": air_temp,
            "relative_humidity_pct": humidity,
            "soil_temp_c": soil_temp,
            "battery_v": self.battery_v,
            "source": "simulated",
        }

    def generate_batch(self, count: int = 10, start_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Generate a chronological batch of `count` 15-minute readings."""
        base = start_time or (datetime.now(timezone.utc) - timedelta(minutes=15 * count))
        return [
            self.step(timestamp=base + timedelta(minutes=15 * i))
            for i in range(count)
        ]


def post_reading(url: str, api_key: str, payload: Dict[str, Any]) -> requests.Response:
    """Send a single telemetry payload to the FastAPI backend."""
    headers = {
        "Content-Type": "application/json",
        "X-Node-API-Key": api_key,
    }
    return requests.post(url, json=payload, headers=headers, timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description="AgriTwin ESP32 Software Telemetry Simulator")
    parser.add_argument("--url", default=f"http://localhost:{settings.app_port}/api/v1/telemetry")
    parser.add_argument("--field-id", default=settings.pilot_field_id)
    parser.add_argument("--api-key", default=settings.field_node_api_key)
    parser.add_argument("--mode", choices=["burst", "stream"], default="burst")
    parser.add_argument("--count", type=int, default=5, help="Number of readings in burst mode")
    parser.add_argument("--interval-sec", type=float, default=900.0, help="Interval in stream mode (seconds)")
    parser.add_argument("--fault", action="store_true", help="Inject a corrupted sensor fault reading")
    args = parser.parse_args()

    sim = ESP32Simulator(field_id=args.field_id)

    if args.mode == "burst":
        batch = sim.generate_batch(count=args.count)
        if args.fault:
            batch.append(sim.step(inject_fault=True))
        for idx, payload in enumerate(batch, start=1):
            resp = post_reading(args.url, args.api_key, payload)
            print(f"[{idx}/{len(batch)}] POST -> {resp.status_code}: {payload['soil_moisture_pct']}% moisture")
    else:
        print(f"Streaming simulated telemetry to {args.url} every {args.interval_sec}s...")
        while True:
            payload = sim.step(inject_fault=args.fault)
            try:
                resp = post_reading(args.url, args.api_key, payload)
                print(f"[{payload['timestamp']}] POST -> {resp.status_code}")
            except Exception as exc:
                print(f"POST error: {exc}")
            time.sleep(args.interval_sec)


if __name__ == "__main__":
    main()
