"""Smart grid API server with live data streaming and dashboard support."""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from contextlib import asynccontextmanager
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from config import Config


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class GridData(BaseModel):
    timestamp: float
    bus_id: int
    voltage: float
    current: float
    frequency: float
    consumption: float
    consumer_type: str = "mixed"
    attack_type: str = "normal"


class AttackAlert(BaseModel):
    timestamp: float
    bus_id: int
    attack_type: str
    confidence: float
    description: str


class ExternalGridData(BaseModel):
    bus_id: int
    voltage: float
    current: float
    frequency: float
    consumption: float
    power: float | None = None
    timestamp: float | None = None
    attack_type: str = "normal"
    consumer_type: str = "mixed"


class SiliconApocalypseEvent(BaseModel):
    zone: str
    motion_detected: bool = True
    sensor_id: str = "unknown"
    severity: float = 0.6
    timestamp: float | None = None
    consumption_kw: float | None = None
    voltage_v: float | None = None


class PacketTracerEnergyPayload(BaseModel):
    gateways: Dict[str, str] = {}
    batteries: Dict[str, Any] = {}
    production: Dict[str, Any] = {}
    timestamp: float | None = None


class PacketTracerSecurityPayload(BaseModel):
    security: Dict[str, Any] = {}
    home_devices: Dict[str, Any] = {}
    timestamp: float | None = None


class PacketTracerCommand(BaseModel):
    type: str
    value: Any | None = None
    target: str | None = None
    timestamp: float | None = None


@dataclass
class BusCursor:
    bus_id: int
    frame: pd.DataFrame
    idx: int = 0

    def next_row(self) -> pd.Series:
        if self.frame.empty:
            raise ValueError(f"No data for bus {self.bus_id}")
        row = self.frame.iloc[self.idx % len(self.frame)]
        self.idx += 1
        return row


class DataEngine:
    def __init__(self) -> None:
        self.config = Config()
        self.latest_data: Dict[int, GridData] = {}
        self.alert_history: List[AttackAlert] = []
        self.active_connections: List[WebSocket] = []
        self.last_alert_at: Dict[int, float] = {}
        self.refresh_hz = 2.0
        self.running = False
        self.source_mode = "dataset"
        self.packet_tracer_timeout_sec = 8.0
        self.smart_meter_timeout_sec = 6.0

        self.bus_cursors: Dict[int, BusCursor] = {}
        self.injected_attacks: Dict[int, Dict[str, Any]] = {}

        self.packet_tracer_state: Dict[str, Any] = {
            "gateways": {},
            "energy": {},
            "security": {},
            "home_devices": {},
            "last_update": None,
        }
        self.packet_tracer_history: List[Dict[str, Any]] = []
        self.packet_tracer_commands: List[Dict[str, Any]] = []
        self._load_datasets()

    def _packet_tracer_live(self) -> bool:
        if self.source_mode != "packet_tracer":
            return False
        last_update = self.packet_tracer_state.get("last_update")
        if last_update is None:
            return False
        return (time.time() - float(last_update)) <= self.packet_tracer_timeout_sec

    def _refresh_from_packet_tracer(self) -> None:
        energy = self.packet_tracer_state.get("energy", {})
        batteries = energy.get("batteries", {}) if isinstance(energy, dict) else {}
        production = energy.get("production", {}) if isinstance(energy, dict) else {}
        security = self.packet_tracer_state.get("security", {}) or {}
        home = self.packet_tracer_state.get("home_devices", {}) or {}

        solar_kw = float(production.get("solar", 0.0) or 0.0)
        wind_kw = float(production.get("wind", 0.0) or 0.0)
        total_prod_kw = float(production.get("total", solar_kw + wind_kw) or (solar_kw + wind_kw))

        total_capacity = max(1.0, float(batteries.get("total_capacity", 500.0) or 500.0))
        current_charge = max(0.0, float(batteries.get("current_charge", 250.0) or 250.0))
        charge_ratio = max(0.0, min(1.0, current_charge / total_capacity))

        home_load_kw = (
            float(home.get("ac_power", 0.0) or 0.0)
            + float(home.get("laptop1", 0.0) or 0.0)
            + float(home.get("laptop2", 0.0) or 0.0)
            + float(home.get("smartphone", 0.0) or 0.0)
        ) / 1000.0

        base_total_load = max(8.0, min(85.0, total_prod_kw * 0.34 + home_load_kw + 10.0))
        phase = (time.time() % 60.0) / 60.0
        frequency = 59.95 + max(-0.03, min(0.03, (total_prod_kw - base_total_load) / 250.0))

        zone_key = str(security.get("zone", "perimeter")).strip().lower().replace(" ", "_").replace("-", "_")
        zone_bus = SILICON_ZONE_TO_BUS.get(zone_key, 6)
        code_red = bool(security.get("code_red", False)) or bool(security.get("motion_detected", False))
        severity = max(0.01, min(1.0, float(security.get("severity", 0.6) or 0.6)))

        weights = [0.09, 0.08, 0.08, 0.07, 0.07, 0.07, 0.06, 0.07, 0.06, 0.06, 0.07, 0.08, 0.07, 0.07]
        consumer_types = {
            1: "industrial",
            2: "commercial",
            3: "residential",
            4: "commercial",
            5: "industrial",
            6: "industrial",
            7: "commercial",
            8: "industrial",
            9: "residential",
            10: "commercial",
            11: "residential",
            12: "commercial",
            13: "residential",
            14: "residential",
        }

        for bus_id in range(1, 15):
            weight = weights[bus_id - 1]
            wave = 0.92 + 0.16 * ((phase + bus_id * 0.07) % 1.0)
            consumption = round(base_total_load * weight * wave, 3)
            voltage = round(0.992 + 0.03 * charge_ratio - 0.015 * max(0.0, consumption / 10.0 - 1.0), 4)
            current = round((consumption * 1000.0) / (230.0 * max(voltage, 0.1)), 2)

            entry = GridData(
                timestamp=time.time(),
                bus_id=bus_id,
                voltage=voltage,
                current=current,
                frequency=round(frequency, 3),
                consumption=consumption,
                consumer_type=consumer_types.get(bus_id, "mixed"),
                attack_type="normal",
            )

            if code_red and bus_id == zone_bus:
                attack_type = "dos" if severity >= 0.75 else "fdia"
                entry.attack_type = attack_type
                entry.consumption = round(entry.consumption * (1.0 + 0.6 * severity), 3)
                entry.current = round((entry.consumption * 1000.0) / (230.0 * max(entry.voltage, 0.1)), 2)
                self._maybe_add_alert(entry)

            entry = self._apply_injected_attack(entry)
            self.latest_data[bus_id] = entry

    def _dataset_paths(self) -> Dict[str, str]:
        clean_fast = os.path.join(self.config.CLEAN_DIR, "smartgrid_clean_fast.csv")
        attack_fast = os.path.join(self.config.ATTACK_DIR, "attacks_fast.csv")
        clean_std = os.path.join(self.config.CLEAN_DIR, "smartgrid_clean_24h.csv")
        attack_std = os.path.join(self.config.ATTACK_DIR, "attacks_complete.csv")

        clean_path = clean_fast if os.path.exists(clean_fast) else clean_std
        attack_path = attack_fast if os.path.exists(attack_fast) else attack_std
        return {"clean": clean_path, "attack": attack_path}

    def _load_datasets(self) -> None:
        paths = self._dataset_paths()
        clean_exists = os.path.exists(paths["clean"])
        attack_exists = os.path.exists(paths["attack"])

        if not clean_exists and not attack_exists:
            raise FileNotFoundError(
                "No datasets found. Run run_simulation_fast.py first."
            )

        frames: List[pd.DataFrame] = []
        if clean_exists:
            clean_df = pd.read_csv(paths["clean"])
            clean_df["attack_type"] = "normal"
            frames.append(clean_df)
        if attack_exists:
            attack_df = pd.read_csv(paths["attack"])
            if "attack_type" not in attack_df.columns:
                attack_df["attack_type"] = "attack"
            frames.append(attack_df)

        combined = pd.concat(frames, ignore_index=True)
        required_cols = {
            "timestamp": 0.0,
            "bus_id": 1,
            "voltage_pu": 1.0,
            "frequency_hz": 60.0,
            "consumption_kw": 0.0,
            "consumer_type": "mixed",
            "attack_type": "normal",
        }
        for col, default in required_cols.items():
            if col not in combined.columns:
                combined[col] = default

        combined = combined.sort_values(["timestamp", "bus_id"]).reset_index(drop=True)

        for bus_id in range(1, 15):
            bus_frame = combined[combined["bus_id"] == bus_id].copy()
            if bus_frame.empty:
                bus_frame = pd.DataFrame(
                    [
                        {
                            "timestamp": time.time(),
                            "bus_id": bus_id,
                            "voltage_pu": 1.0,
                            "frequency_hz": 60.0,
                            "consumption_kw": 0.0,
                            "consumer_type": "mixed",
                            "attack_type": "normal",
                        }
                    ]
                )
            self.bus_cursors[bus_id] = BusCursor(bus_id=bus_id, frame=bus_frame)

    def _smart_meter_paths(self) -> Dict[str, str]:
        base_dir = os.path.dirname(__file__)
        return {
            "data": os.path.join(base_dir, "donnees_smart_meters.csv"),
            "alerts": os.path.join(base_dir, "alertes_smart_meters.csv"),
            "state": os.path.join(base_dir, "smart_meters_state.json"),
        }

    def _read_csv_safe(self, path: str) -> pd.DataFrame:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return pd.DataFrame()

        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()

    def _read_json_safe(self, path: str) -> Dict[str, Any]:
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            return {}

        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload if isinstance(payload, dict) else {}
        except Exception:
            return {}

    def _is_file_fresh(self, path: str, timeout_sec: float) -> bool:
        if not os.path.exists(path):
            return False

        try:
            modified_at = os.path.getmtime(path)
        except OSError:
            return False

        return (time.time() - float(modified_at)) <= timeout_sec

    def smart_meter_status(self, limit: int = 8) -> Dict[str, Any]:
        paths = self._smart_meter_paths()
        data_df = self._read_csv_safe(paths["data"])
        alert_df = self._read_csv_safe(paths["alerts"])
        state_data = self._read_json_safe(paths["state"])
        data_fresh = self._is_file_fresh(paths["data"], self.smart_meter_timeout_sec)
        alerts_fresh = self._is_file_fresh(paths["alerts"], self.smart_meter_timeout_sec)
        state_fresh = self._is_file_fresh(paths["state"], self.smart_meter_timeout_sec)
        state_running = state_data.get("running") if state_data else None

        def _clean(value: Any, default: str = "") -> str:
            if value is None:
                return default
            if pd.isna(value):
                return default
            text = str(value).strip()
            if not text or text.lower() == "nan":
                return default
            return text

        total_readings = int(len(data_df))
        status_counts: Dict[str, int] = {}
        if not data_df.empty and "statut" in data_df.columns:
            status_counts = {
                str(key): int(value)
                for key, value in data_df["statut"].fillna("NORMAL").astype(str).value_counts().items()
            }

        if status_counts:
            total_alerts = int(status_counts.get("ALERTE", 0))
        else:
            total_alerts = int(len(alert_df))

        alert_rate = round((total_alerts / total_readings) * 100.0, 2) if total_readings else 0.0

        latest_reading: Dict[str, Any] = {}
        if not data_df.empty and data_fresh:
            latest_row = data_df.iloc[-1]
            latest_reading = {
                "timestamp": _clean(latest_row.get("timestamp", ""), ""),
                "meter_id": _clean(latest_row.get("meter_id", ""), "n/a"),
                "zone": _clean(latest_row.get("zone", ""), "n/a"),
                "type": _clean(latest_row.get("type", ""), "n/a"),
                "consommation_kw": float(latest_row.get("consommation_kw", 0.0) or 0.0),
                "tension_v": float(latest_row.get("tension_v", 0.0) or 0.0),
                "courant_a": float(latest_row.get("courant_a", 0.0) or 0.0),
                "statut": _clean(latest_row.get("statut", "NORMAL"), "NORMAL") or "NORMAL",
                "anomalies": _clean(latest_row.get("anomalies", ""), "none") or "none",
            }

        recent_alerts: List[Dict[str, Any]] = []
        if not alert_df.empty:
            for _, row in alert_df.tail(limit).iterrows():
                recent_alerts.append(
                    {
                        "timestamp": _clean(row.get("timestamp", ""), ""),
                        "meter_id": _clean(row.get("meter_id", ""), "n/a"),
                        "zone": _clean(row.get("zone", ""), "n/a"),
                        "type": _clean(row.get("type", ""), "n/a"),
                        "consommation_kw": float(row.get("consommation_kw", 0.0) or 0.0),
                        "tension_v": float(row.get("tension_v", 0.0) or 0.0),
                        "courant_a": float(row.get("courant_a", 0.0) or 0.0),
                        "alerte": _clean(row.get("alerte", ""), "unknown") or "unknown",
                    }
                )

        latest_alert = recent_alerts[-1] if recent_alerts else {}
        meter_types: Dict[str, int] = {}
        if not data_df.empty and "type" in data_df.columns:
            meter_types = {
                str(key): int(value)
                for key, value in data_df["type"].fillna("unknown").astype(str).value_counts().items()
            }

        last_update = latest_reading.get("timestamp") or latest_alert.get("timestamp") or None
        if state_data:
            source_live = bool(state_running) and state_fresh
        else:
            source_live = bool(total_readings or len(alert_df)) and data_fresh

        if not source_live:
            latest_reading = {}
            latest_alert = {}
            recent_alerts = []
            last_update = None

        return {
            "source": {
                "data_file": paths["data"],
                "alert_file": paths["alerts"],
                "available": source_live,
                "data_fresh": data_fresh,
                "alerts_fresh": alerts_fresh,
                "state_running": state_running,
                "state_fresh": state_fresh,
                "last_update": last_update,
            },
            "summary": {
                "total_readings": total_readings,
                "total_alerts": total_alerts,
                "alert_rate": alert_rate,
                "status_counts": status_counts,
                "meter_types": meter_types,
            },
            "latest_reading": latest_reading,
            "latest_alert": latest_alert,
            "recent_alerts": recent_alerts,
        }

    def _to_grid_data(self, row: pd.Series) -> GridData:
        consumption = float(row.get("consumption_kw", 0.0))
        voltage = float(row.get("voltage_pu", 1.0))
        frequency = float(row.get("frequency_hz", 60.0))
        current = 0.0 if voltage <= 0 else (consumption * 1000.0) / (230.0 * max(voltage, 0.1))

        attack_type = str(row.get("attack_type", "normal"))
        if attack_type == "attack":
            attack_type = "fdia"

        return GridData(
            timestamp=time.time(),
            bus_id=int(row.get("bus_id", 1)),
            voltage=round(voltage, 4),
            current=round(current, 2),
            frequency=round(frequency, 3),
            consumption=round(consumption, 3),
            consumer_type=str(row.get("consumer_type", "mixed")),
            attack_type=attack_type,
        )

    def ingest_external_data(self, payload: ExternalGridData) -> GridData:
        # Packet Tracer devices usually report voltage in volts (220-240V).
        # The dashboard uses per-unit voltage, so normalize when needed.
        voltage = float(payload.voltage)
        voltage_pu = voltage / 230.0 if voltage > 10 else voltage

        entry = GridData(
            timestamp=float(payload.timestamp or time.time()),
            bus_id=int(payload.bus_id),
            voltage=round(voltage_pu, 4),
            current=round(float(payload.current), 2),
            frequency=round(float(payload.frequency), 3),
            consumption=round(float(payload.consumption), 3),
            consumer_type=str(payload.consumer_type),
            attack_type=str(payload.attack_type),
        )

        self.latest_data[entry.bus_id] = entry
        self._maybe_add_alert(entry)
        return entry

    def update_packet_tracer_energy(self, payload: PacketTracerEnergyPayload) -> Dict[str, Any]:
        entry = {
            "timestamp": float(payload.timestamp or time.time()),
            "gateways": dict(payload.gateways),
            "batteries": dict(payload.batteries),
            "production": dict(payload.production),
        }
        self.packet_tracer_state["gateways"] = entry["gateways"]
        self.packet_tracer_state["energy"] = {
            "batteries": entry["batteries"],
            "production": entry["production"],
            "timestamp": entry["timestamp"],
        }
        self.source_mode = "packet_tracer"
        self.packet_tracer_state["last_update"] = entry["timestamp"]
        self.packet_tracer_history.append({"type": "energy", **entry})
        self.packet_tracer_history = self.packet_tracer_history[-500:]
        self._refresh_from_packet_tracer()
        return entry

    def update_packet_tracer_security(self, payload: PacketTracerSecurityPayload) -> Dict[str, Any]:
        entry = {
            "timestamp": float(payload.timestamp or time.time()),
            "security": dict(payload.security),
            "home_devices": dict(payload.home_devices),
        }
        self.packet_tracer_state["security"] = entry["security"]
        self.packet_tracer_state["home_devices"] = entry["home_devices"]
        self.source_mode = "packet_tracer"
        self.packet_tracer_state["last_update"] = entry["timestamp"]
        self.packet_tracer_history.append({"type": "security", **entry})
        self.packet_tracer_history = self.packet_tracer_history[-500:]
        self._refresh_from_packet_tracer()
        return entry

    def queue_packet_tracer_command(self, command: PacketTracerCommand) -> Dict[str, Any]:
        queued = {
            "type": command.type,
            "value": command.value,
            "target": command.target,
            "timestamp": float(command.timestamp or time.time()),
        }
        self.packet_tracer_commands.append(queued)
        self.packet_tracer_commands = self.packet_tracer_commands[-200:]
        return queued

    def pop_packet_tracer_commands(self, limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        commands = self.packet_tracer_commands[:limit]
        self.packet_tracer_commands = self.packet_tracer_commands[limit:]
        return commands

    def _apply_injected_attack(self, data: GridData) -> GridData:
        attack = self.injected_attacks.get(data.bus_id)
        if not attack:
            return data

        now = time.time()
        if now - attack["start"] > attack["duration"]:
            self.injected_attacks.pop(data.bus_id, None)
            return data

        magnitude = float(attack["magnitude"])
        attack_type = str(attack["type"])

        if attack_type == "fdia":
            data.voltage = round(data.voltage * (1.0 + magnitude * 0.2), 4)
            data.consumption = round(data.consumption * (1.0 + magnitude), 3)
            data.current = round(data.current * (1.0 + magnitude), 2)
            data.attack_type = "fdia"
        elif attack_type == "dos":
            data.attack_type = "dos"

        return data

    def _maybe_add_alert(self, data: GridData) -> None:
        if data.attack_type == "normal":
            return

        now = time.time()
        cooldown = 5.0
        last = self.last_alert_at.get(data.bus_id, 0.0)
        if now - last < cooldown:
            return

        alert = AttackAlert(
            timestamp=now,
            bus_id=data.bus_id,
            attack_type=data.attack_type,
            confidence=0.8 if data.attack_type == "fdia" else 0.7,
            description=f"{data.attack_type.upper()} detected on bus {data.bus_id}",
        )
        self.alert_history.append(alert)
        self.alert_history = self.alert_history[-200:]
        self.last_alert_at[data.bus_id] = now

    async def tick(self) -> None:
        if self._packet_tracer_live():
            self._refresh_from_packet_tracer()
            await self._broadcast_update()
            return

        self.source_mode = "dataset"
        for bus_id, cursor in self.bus_cursors.items():
            row = cursor.next_row()
            data = self._to_grid_data(row)
            data = self._apply_injected_attack(data)
            self.latest_data[bus_id] = data
            self._maybe_add_alert(data)

        await self._broadcast_update()

    async def _broadcast_update(self) -> None:
        if not self.active_connections:
            return

        payload = {
            "type": "update",
            "timestamp": time.time(),
            "data": [_model_dump(d) for d in self.latest_data.values()],
        }
        stale: List[WebSocket] = []
        for ws in self.active_connections:
            try:
                await ws.send_json(payload)
            except Exception:
                stale.append(ws)

        if stale:
            self.active_connections = [ws for ws in self.active_connections if ws not in stale]

    async def run_loop(self) -> None:
        self.running = True
        period = 1.0 / self.refresh_hz
        while self.running:
            await self.tick()
            await asyncio.sleep(period)


engine = DataEngine()

SILICON_ZONE_TO_BUS: Dict[str, int] = {
    "sector_a": 5,
    "sector_b": 8,
    "sector_c": 11,
    "sector_d": 14,
    "perimeter": 6,
    "garage": 4,
    "entrance": 3,
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(engine.run_loop())
    try:
        yield
    finally:
        engine.running = False
        task.cancel()


app = FastAPI(title="Smart Grid Simulation API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "name": "Smart Grid Simulation API",
        "version": "1.0.0",
        "status": "running",
        "solver_mode": "mock_or_dataset_replay",
        "endpoints": [
            "/api/grid/all",
            "/api/grid/bus/{bus_id}",
            "/api/grid/data",
                "/api/smart-meters/status",
            "/api/packet-tracer/energy",
            "/api/packet-tracer/security",
            "/api/packet-tracer/status",
            "/api/packet-tracer/commands",
            "/api/alerts",
            "/api/simulate/attack",
            "/ws",
            "/dashboard",
        ],
    }


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "packet_tracer_dashboard.html")
    return FileResponse(dashboard_path)


@app.get("/packet-tracer-dashboard")
async def packet_tracer_dashboard() -> FileResponse:
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "packet_tracer_dashboard.html")
    return FileResponse(dashboard_path)


@app.get("/blockchain-dashboard")
async def blockchain_dashboard() -> FileResponse:
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "cyber_dashboard.html")
    return FileResponse(dashboard_path)


@app.get("/api/smart-meters/status")
async def get_smart_meter_status(limit: int = Query(default=8, ge=1, le=50)) -> Dict[str, Any]:
    return engine.smart_meter_status(limit=limit)


@app.get("/api/grid/all")
async def get_all_data() -> Dict[str, Any]:
    return {
        "timestamp": time.time(),
        "buses": [_model_dump(data) for _, data in sorted(engine.latest_data.items())],
        "count": len(engine.latest_data),
    }


@app.get("/api/grid/bus/{bus_id}")
async def get_bus_data(bus_id: int) -> JSONResponse:
    data = engine.latest_data.get(bus_id)
    if data is None:
        return JSONResponse(status_code=404, content={"error": f"Bus {bus_id} not found"})
    return JSONResponse(content=_model_dump(data))


@app.post("/api/grid/data")
async def ingest_grid_data(payload: ExternalGridData) -> Dict[str, Any]:
    if payload.bus_id < 1 or payload.bus_id > 14:
        return {
            "status": "error",
            "message": "bus_id must be between 1 and 14",
            "received": _model_dump(payload),
        }

    entry = engine.ingest_external_data(payload)
    await engine._broadcast_update()
    return {
        "status": "ok",
        "bus_id": entry.bus_id,
        "stored": _model_dump(entry),
    }


@app.post("/api/integrations/silicon-apocalypse/event")
async def ingest_silicon_apocalypse_event(payload: SiliconApocalypseEvent) -> Dict[str, Any]:
    zone_key = payload.zone.strip().lower().replace(" ", "_").replace("-", "_")
    bus_id = SILICON_ZONE_TO_BUS.get(zone_key)
    if bus_id is None:
        return {
            "status": "error",
            "message": "unknown zone",
            "zone": payload.zone,
            "known_zones": sorted(SILICON_ZONE_TO_BUS.keys()),
        }

    severity = max(0.01, min(1.0, float(payload.severity)))

    # Keep the Packet Tracer dashboard in sync with direct Silicon Apocalypse events.
    # The dashboard reads /api/packet-tracer/status, so we mirror the zone state here.
    zone_security = {
        "zone": zone_key,
        "motion_detected": bool(payload.motion_detected),
        "code_red": bool(payload.motion_detected),
        "sensor_id": payload.sensor_id,
        "severity": severity,
        "consumption_kw": float(payload.consumption_kw) if payload.consumption_kw is not None else None,
        "voltage_v": float(payload.voltage_v) if payload.voltage_v is not None else None,
    }
    engine.packet_tracer_state["security"] = zone_security
    engine.packet_tracer_state["last_update"] = float(payload.timestamp or time.time())
    engine.source_mode = "packet_tracer"

    if payload.motion_detected:
        attack_type = "fdia" if severity < 0.75 else "dos"
        engine.injected_attacks[bus_id] = {
            "type": attack_type,
            "magnitude": severity,
            "duration": round(10.0 + 40.0 * severity, 1),
            "start": time.time(),
        }

        alert = AttackAlert(
            timestamp=time.time(),
            bus_id=bus_id,
            attack_type="silicon_code_red",
            confidence=round(0.5 + 0.5 * severity, 2),
            description=(
                f"Code Red from zone={payload.zone} sensor={payload.sensor_id} "
                f"mapped to bus {bus_id}"
            ),
        )
        engine.alert_history.append(alert)
        engine.alert_history = engine.alert_history[-200:]

        voltage = float(payload.voltage_v) if payload.voltage_v is not None else 228.0
        consumption = (
            float(payload.consumption_kw)
            if payload.consumption_kw is not None
            else round(2.0 + 8.0 * severity, 3)
        )
        current = (consumption * 1000.0) / max(voltage, 1.0)

        external = ExternalGridData(
            bus_id=bus_id,
            voltage=voltage,
            current=round(current, 2),
            frequency=60.0,
            consumption=consumption,
            timestamp=float(payload.timestamp or time.time()),
            attack_type=attack_type,
            consumer_type="silicon_zone",
        )
        stored = engine.ingest_external_data(external)
        await engine._broadcast_update()

        return {
            "status": "ok",
            "mode": "code_red",
            "zone": payload.zone,
            "bus_id": bus_id,
            "attack_type": attack_type,
            "stored": _model_dump(stored),
        }

    external = ExternalGridData(
        bus_id=bus_id,
        voltage=float(payload.voltage_v) if payload.voltage_v is not None else 230.0,
        current=2.5,
        frequency=60.0,
        consumption=float(payload.consumption_kw) if payload.consumption_kw is not None else 1.2,
        timestamp=float(payload.timestamp or time.time()),
        attack_type="normal",
        consumer_type="silicon_zone",
    )
    stored = engine.ingest_external_data(external)
    await engine._broadcast_update()
    return {
        "status": "ok",
        "mode": "safe",
        "zone": payload.zone,
        "bus_id": bus_id,
        "stored": _model_dump(stored),
    }


@app.post("/api/packet-tracer/energy")
async def ingest_packet_tracer_energy(payload: PacketTracerEnergyPayload) -> Dict[str, Any]:
    stored = engine.update_packet_tracer_energy(payload)
    return {
        "status": "ok",
        "message": "packet tracer energy updated",
        "stored": stored,
    }


@app.post("/api/packet-tracer/security")
async def ingest_packet_tracer_security(payload: PacketTracerSecurityPayload) -> Dict[str, Any]:
    stored = engine.update_packet_tracer_security(payload)

    security = payload.security or {}
    motion = bool(security.get("motion_detected", False))
    code_red = bool(security.get("code_red", False))
    zone = str(security.get("zone", "perimeter"))
    severity = max(0.01, min(1.0, float(security.get("severity", 0.8))))
    motion_state = motion or code_red

    integration_result: Dict[str, Any] | None = None
    integration_result = await ingest_silicon_apocalypse_event(
        SiliconApocalypseEvent(
            zone=zone,
            motion_detected=motion_state,
            sensor_id=str(security.get("sensor_id", f"{zone}_sensor")),
            severity=severity,
            timestamp=float(payload.timestamp or time.time()),
            consumption_kw=float(security.get("consumption_kw", 2.0 + 8.0 * severity)),
            voltage_v=float(security.get("voltage_v", 228.0)),
        )
    )

    return {
        "status": "ok",
        "message": "packet tracer security updated",
        "stored": stored,
        "integration": integration_result,
    }


@app.get("/api/packet-tracer/status")
async def packet_tracer_status() -> Dict[str, Any]:
    return {
        "gateways": engine.packet_tracer_state.get("gateways", {}),
        "energy": engine.packet_tracer_state.get("energy", {}),
        "security": engine.packet_tracer_state.get("security", {}),
        "home_devices": engine.packet_tracer_state.get("home_devices", {}),
        "last_update": engine.packet_tracer_state.get("last_update"),
        "pending_commands": len(engine.packet_tracer_commands),
    }


@app.post("/api/packet-tracer/commands")
async def queue_packet_tracer_command(payload: PacketTracerCommand) -> Dict[str, Any]:
    queued = engine.queue_packet_tracer_command(payload)
    return {"status": "ok", "queued": queued}


@app.get("/api/packet-tracer/commands")
async def get_packet_tracer_commands(consume: bool = Query(default=True), limit: int = Query(default=20, ge=1, le=200)) -> Dict[str, Any]:
    if consume:
        commands = engine.pop_packet_tracer_commands(limit=limit)
    else:
        commands = engine.packet_tracer_commands[:limit]
    return {"commands": commands, "count": len(commands)}


@app.get("/api/alerts")
async def get_alerts(limit: int = Query(default=10, ge=1, le=200)) -> Dict[str, Any]:
    alerts = engine.alert_history[-limit:]
    return {
        "alerts": [_model_dump(a) for a in alerts],
        "count": len(engine.alert_history),
    }


@app.post("/api/simulate/attack")
async def trigger_attack(
    bus_id: int = Query(..., ge=1, le=14),
    attack_type: str = Query(..., pattern="^(fdia|dos)$"),
    magnitude: float = Query(default=0.2, ge=0.01, le=1.0),
    duration: float = Query(default=20.0, ge=1.0, le=300.0),
) -> Dict[str, Any]:
    engine.injected_attacks[bus_id] = {
        "type": attack_type,
        "magnitude": magnitude,
        "duration": duration,
        "start": time.time(),
    }

    alert = AttackAlert(
        timestamp=time.time(),
        bus_id=bus_id,
        attack_type=attack_type,
        confidence=round(min(1.0, 0.5 + magnitude), 2),
        description=f"Manual {attack_type.upper()} injected on bus {bus_id}",
    )
    engine.alert_history.append(alert)
    engine.alert_history = engine.alert_history[-200:]

    return {"status": "ok", "attack": _model_dump(alert)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    engine.active_connections.append(websocket)

    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "get_data":
                await websocket.send_json(
                    {
                        "type": "grid_data",
                        "timestamp": time.time(),
                        "data": [_model_dump(d) for d in engine.latest_data.values()],
                    }
                )
            elif msg == "get_alerts":
                await websocket.send_json(
                    {
                        "type": "alerts",
                        "data": [_model_dump(a) for a in engine.alert_history[-10:]],
                    }
                )
            elif msg == "ping":
                await websocket.send_json({"type": "pong", "timestamp": time.time()})
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in engine.active_connections:
            engine.active_connections.remove(websocket)


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("SMART GRID API SERVER")
    print("=" * 60)
    print("API: http://127.0.0.1:8000")
    print("Docs: http://127.0.0.1:8000/docs")
    print("Dashboard: http://127.0.0.1:8000/dashboard")
    print("WebSocket: ws://127.0.0.1:8000/ws")
    print("=" * 60)

    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
