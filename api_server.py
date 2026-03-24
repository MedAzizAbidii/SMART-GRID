"""Smart grid API server with live data streaming and dashboard support."""
from __future__ import annotations

import asyncio
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

        self.bus_cursors: Dict[int, BusCursor] = {}
        self.injected_attacks: Dict[int, Dict[str, Any]] = {}
        self._load_datasets()

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
            "/api/alerts",
            "/api/simulate/attack",
            "/ws",
            "/dashboard",
        ],
    }


@app.get("/dashboard")
async def dashboard() -> FileResponse:
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard", "index.html")
    return FileResponse(dashboard_path)


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
