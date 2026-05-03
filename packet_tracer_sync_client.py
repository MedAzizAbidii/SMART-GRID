"""Packet Tracer -> Smart Grid API sync client.

This client sends Packet Tracer-like energy/security telemetry to:
- POST /api/packet-tracer/energy
- POST /api/packet-tracer/security

It also pulls pending commands from:
- GET /api/packet-tracer/commands
"""
from __future__ import annotations

import argparse
import random
import time
from typing import Any, Dict, List

import requests


class PacketTracerSmartGridClient:
    def __init__(self, api_base: str = "http://127.0.0.1:8000", motion_prob: float = 0.01) -> None:
        self.api_base = api_base.rstrip("/")
        # Keep security state stable by default so manual Code Red / SAFE tests
        # from the bridge are not overwritten by random client output.
        self.motion_prob = max(0.0, min(1.0, float(motion_prob)))
        self.endpoints = {
            "energy": f"{self.api_base}/api/packet-tracer/energy",
            "security": f"{self.api_base}/api/packet-tracer/security",
            "commands": f"{self.api_base}/api/packet-tracer/commands",
        }

        self.gateways = {
            "security": "192.168.25.3",
            "energy": "192.168.25.5",
            "central": "192.168.25.4",
        }

        self.batteries = {
            "count": 470,
            "total_capacity": 500.0,
            "current_charge": 250.0,
        }

        self.production = {
            "solar": 0.0,
            "wind": 0.0,
            "total": 0.0,
        }

        self.home_devices = {
            "thermostat": 22,
            "fan_speed": 0,
            "ac_power": 0.0,
            "laptop1": 45.0,
            "laptop2": 45.0,
            "smartphone": 5.0,
        }

        self.security = {
            "zone": "perimeter",
            "gate_status": "unlocked",
            "fence_status": "normal",
            "motion_detected": False,
            "camera_active": True,
            "code_red": False,
            "severity": 0.5,
            "sensor_id": "perimeter_sensor",
        }

    def _post(self, url: str, data: Dict[str, Any]) -> Dict[str, Any]:
        resp = requests.post(url, json=data, timeout=5)
        resp.raise_for_status()
        return resp.json()

    def send_energy_data(self) -> None:
        payload = {
            "gateways": self.gateways,
            "batteries": self.batteries,
            "production": self.production,
            "timestamp": time.time(),
        }
        self._post(self.endpoints["energy"], payload)

    def send_security_data(self) -> None:
        payload = {
            "security": self.security,
            "home_devices": self.home_devices,
            "timestamp": time.time(),
        }
        self._post(self.endpoints["security"], payload)

    def get_commands(self) -> List[Dict[str, Any]]:
        resp = requests.get(self.endpoints["commands"], params={"consume": "true", "limit": 20}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return data.get("commands", [])

    def execute_command(self, command: Dict[str, Any]) -> None:
        ctype = str(command.get("type", "")).lower().strip()
        value = command.get("value")

        if ctype == "code_red":
            self.security["code_red"] = True
            self.security["motion_detected"] = True
            self.security["gate_status"] = "locked"
            self.security["fence_status"] = "electrified"
            self.security["severity"] = 0.9
        elif ctype == "code_green":
            self.security["code_red"] = False
            self.security["motion_detected"] = False
            self.security["gate_status"] = "unlocked"
            self.security["fence_status"] = "normal"
            self.security["severity"] = 0.2
        elif ctype == "set_thermostat" and value is not None:
            self.home_devices["thermostat"] = int(value)
        elif ctype == "set_fan" and value is not None:
            self.home_devices["fan_speed"] = max(0, min(100, int(value)))

    def simulate_realtime_data(self) -> None:
        self.production["solar"] = round(random.uniform(40, 160), 2)
        self.production["wind"] = round(random.uniform(20, 120), 2)
        self.production["total"] = round(self.production["solar"] + self.production["wind"], 2)

        charge_delta = (self.production["total"] - 110.0) / 18.0
        self.batteries["current_charge"] = max(
            0.0,
            min(self.batteries["total_capacity"], self.batteries["current_charge"] + charge_delta),
        )

        t = self.home_devices["thermostat"]
        self.home_devices["ac_power"] = 1200.0 if t <= 20 else (450.0 if t <= 22 else 0.0)
        self.home_devices["laptop1"] = round(random.uniform(30, 65), 2)
        self.home_devices["laptop2"] = round(random.uniform(30, 65), 2)

        # Only change security state when it is already active or when the caller
        # explicitly raises motion probability for a demo run.
        if self.motion_prob > 0:
            motion = random.random() < self.motion_prob
            if motion:
                zones = ["sector_a", "sector_b", "sector_c", "sector_d", "perimeter", "garage", "entrance"]
                self.security["zone"] = random.choice(zones)
                self.security["motion_detected"] = True
                self.security["code_red"] = True
                self.security["severity"] = round(random.uniform(0.45, 1.0), 2)
                self.security["gate_status"] = "locked"
                self.security["fence_status"] = "electrified"
                self.security["sensor_id"] = f"{self.security['zone']}_sensor"
            elif not self.security.get("code_red", False):
                self.security["motion_detected"] = False
                self.security["code_red"] = False
                self.security["severity"] = round(random.uniform(0.1, 0.4), 2)
                self.security["gate_status"] = "unlocked"
                self.security["fence_status"] = "normal"
        else:
            # Preserve the last manually injected security state.
            self.security["sensor_id"] = f"{self.security['zone']}_sensor"

    def run(self, interval: float = 2.0) -> None:
        print("=" * 60)
        print("PACKET TRACER SYNC CLIENT")
        print("=" * 60)
        print(f"API: {self.api_base}")
        print(f"Sync interval: {interval}s")

        while True:
            try:
                commands = self.get_commands()
                for command in commands:
                    self.execute_command(command)

                self.simulate_realtime_data()
                self.send_energy_data()
                self.send_security_data()

                print(
                    f"ok zone={self.security['zone']} red={self.security['code_red']} "
                    f"prod={self.production['total']:.1f}kW "
                    f"battery={self.batteries['current_charge']:.1f}/{self.batteries['total_capacity']:.1f}kWh"
                )
            except Exception as exc:
                print(f"sync error: {exc}")

            time.sleep(max(0.5, interval))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Packet Tracer to Smart Grid API sync client")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Smart Grid API base URL")
    parser.add_argument("--interval", type=float, default=2.0, help="Sync interval in seconds")
    parser.add_argument("--motion-prob", type=float, default=0.01, help="Random motion probability in range [0.0, 1.0]")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = PacketTracerSmartGridClient(api_base=args.api, motion_prob=args.motion_prob)
    client.run(interval=args.interval)


if __name__ == "__main__":
    main()
