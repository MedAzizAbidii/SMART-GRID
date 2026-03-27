"""UDP forwarder from API stream to Packet Tracer or another UDP listener."""
from __future__ import annotations

import json
import socket
import time
from typing import Any, Dict, Optional

import requests


class PacketTracerClient:
    def __init__(self, packet_tracer_ip: str = "127.0.0.1", packet_tracer_port: int = 5000):
        self.packet_tracer_ip = packet_tracer_ip
        self.packet_tracer_port = packet_tracer_port
        self.simulation_api = "http://127.0.0.1:8000"
        self.running = False

    def send_to_packet_tracer(self, data: Dict[str, Any]) -> bool:
        try:
            payload = json.dumps(data).encode("utf-8")
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(payload, (self.packet_tracer_ip, self.packet_tracer_port))
            return True
        except Exception as exc:
            print(f"send error: {exc}")
            return False

    def fetch_and_forward(self) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.simulation_api}/api/grid/all", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if self.send_to_packet_tracer(data):
                print(f"forwarded {data.get('count', 0)} buses")
            return data
        except Exception as exc:
            print(f"fetch error: {exc}")
            return None

    def run(self, interval: float = 0.5) -> None:
        self.running = True
        print("Packet Tracer forwarder started")
        print(f"source: {self.simulation_api}")
        print(f"dest: {self.packet_tracer_ip}:{self.packet_tracer_port}")
        print(f"interval: {interval}s")

        while self.running:
            self.fetch_and_forward()
            time.sleep(interval)

    def stop(self) -> None:
        self.running = False


if __name__ == "__main__":
    PacketTracerClient().run(interval=0.5)
