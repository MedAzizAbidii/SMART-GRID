"""Packet Tracer bus telemetry sender for Smart Grid API.

Copy this script to each Packet Tracer PC and only change BUS_ID.
"""
from __future__ import annotations

import json
import os
import random
import time

import requests

# Change BUS_ID on each PC: 1..14 (or set BUS_ID env var)
BUS_ID = int(os.environ.get("BUS_ID", "1"))

# Update API_URL env var per deployment if needed.
API_URL = os.environ.get("API_URL", "http://192.168.100.2:8000/api/grid/data")
SEND_INTERVAL_SEC = float(os.environ.get("SEND_INTERVAL_SEC", "5"))


def generate_data() -> dict:
    """Generate realistic smart-grid telemetry values for one bus."""
    voltage = random.uniform(220.0, 240.0)
    current = random.uniform(0.0, 50.0)
    power = voltage * current / 1000.0
    frequency = random.uniform(59.9, 60.1)
    consumption = random.uniform(0.0, 10.0)

    return {
        "bus_id": BUS_ID,
        "voltage": round(voltage, 2),
        "current": round(current, 2),
        "power": round(power, 3),
        "frequency": round(frequency, 3),
        "consumption": round(consumption, 3),
        "timestamp": time.time(),
        "attack_type": "normal",
        "consumer_type": "mixed",
    }


def send_data(data: dict) -> None:
    """Send one telemetry payload to the API."""
    try:
        payload = json.dumps(data)
        response = requests.post(
            API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        if response.status_code == 200:
            print(
                f"[Bus {BUS_ID}] OK voltage={data['voltage']}V "
                f"current={data['current']}A consumption={data['consumption']}kW"
            )
        else:
            print(f"[Bus {BUS_ID}] HTTP {response.status_code}: {response.text}")
    except Exception as exc:
        print(f"[Bus {BUS_ID}] ERROR: {exc}")


def main() -> None:
    print(f"Starting bus sender for BUS_ID={BUS_ID}")
    print(f"Sending telemetry to {API_URL} every {SEND_INTERVAL_SEC} seconds")

    while True:
        payload = generate_data()
        send_data(payload)
        time.sleep(max(0.5, SEND_INTERVAL_SEC))


if __name__ == "__main__":
    main()
