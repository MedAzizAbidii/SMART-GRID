"""Bridge Silicon Apocalypse events into the Smart Grid API.

This script simulates or forwards Packet Tracer "Code Red" zone events to:
POST /api/integrations/silicon-apocalypse/event
"""
from __future__ import annotations

import argparse
import random
import time
from typing import List

import requests

DEFAULT_API = "http://127.0.0.1:8000/api/integrations/silicon-apocalypse/event"
KNOWN_ZONES: List[str] = ["sector_a", "sector_b", "sector_c", "sector_d", "perimeter", "garage", "entrance"]


def send_event(api_url: str, zone: str, motion: bool, severity: float) -> None:
    payload = {
        "zone": zone,
        "motion_detected": motion,
        "sensor_id": f"{zone}_sensor",
        "severity": round(severity, 3),
        "consumption_kw": round(1.0 + severity * 10.0, 3),
        "voltage_v": round(226.0 + random.uniform(-3.0, 3.0), 2),
        "timestamp": time.time(),
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=5)
        if resp.ok:
            data = resp.json()
            print(
                f"OK zone={zone} motion={motion} severity={severity:.2f} "
                f"bus={data.get('bus_id')} mode={data.get('mode')}"
            )
        else:
            print(f"HTTP {resp.status_code} zone={zone}: {resp.text}")
    except Exception as exc:
        print(f"ERROR zone={zone}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Silicon Apocalypse -> Smart Grid bridge")
    parser.add_argument("--api-url", default=DEFAULT_API, help="Target Smart Grid API integration endpoint")
    parser.add_argument("--zone", default="sector_a", choices=KNOWN_ZONES, help="Source Silicon Apocalypse zone")
    parser.add_argument("--motion", action="store_true", help="Send a Code Red (motion detected) event")
    parser.add_argument("--safe", action="store_true", help="Send a SAFE event (motion cleared)")
    parser.add_argument("--severity", type=float, default=0.65, help="Threat severity in range [0.01, 1.0]")
    parser.add_argument("--loop", action="store_true", help="Continuously emit random zone events")
    parser.add_argument("--interval", type=float, default=5.0, help="Loop interval in seconds")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.loop:
        print(f"Loop mode enabled, sending to {args.api_url} every {args.interval}s")
        while True:
            zone = random.choice(KNOWN_ZONES)
            motion = random.random() >= 0.25
            severity = random.uniform(0.2, 1.0)
            send_event(args.api_url, zone=zone, motion=motion, severity=severity)
            time.sleep(max(0.5, args.interval))

    if args.motion and args.safe:
        raise SystemExit("Choose only one of --motion or --safe")

    motion = True
    if args.safe:
        motion = False

    severity = max(0.01, min(1.0, float(args.severity)))
    send_event(args.api_url, zone=args.zone, motion=motion, severity=severity)


if __name__ == "__main__":
    main()
