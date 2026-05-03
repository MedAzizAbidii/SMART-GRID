"""Simulation engine for scenario-driven smart meter datasets."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .models import DeviceProfile, IncidentDefinition, ScenarioDefinition, SmartMeterDefinition


class ScenarioSimulator:
    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def simulate(
        self,
        scenario: ScenarioDefinition,
        start_time: datetime | None = None,
    ) -> dict[str, pd.DataFrame]:
        base_time = start_time or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_steps = int((scenario.duration_hours * 60) / scenario.interval_minutes)

        meter_rows: list[dict[str, object]] = []
        device_rows: list[dict[str, object]] = []
        alert_rows: list[dict[str, object]] = []
        sent_alerts: set[str] = set()

        for step in range(total_steps):
            timestamp = base_time + timedelta(minutes=step * scenario.interval_minutes)
            hour = ((timestamp - base_time).total_seconds() / 3600.0) % 24.0
            outdoor_temp_c = self._outdoor_temperature(hour)
            solar_factor = self._solar_factor(hour)

            for meter in scenario.meters:
                incident = self._active_incident(scenario.incidents, meter.meter_id, hour)
                (
                    declared_load_kw,
                    active_device_count,
                    peak_device_kw,
                    device_payloads,
                ) = self._simulate_devices(scenario, meter, timestamp, hour, incident)

                device_rows.extend(device_payloads)

                solar_generation_kw = round(
                    max(0.0, meter.solar_capacity_kw * solar_factor * (0.85 + 0.15 * self.rng.random())),
                    3,
                )
                unexplained_load_kw = 0.0
                voltage_v = scenario.base_voltage_v + self.rng.normal(0.0, 1.8)
                frequency_hz = scenario.base_frequency_hz + self.rng.normal(0.0, 0.03)
                communication_quality = float(np.clip(0.98 - abs(self.rng.normal(0.0, 0.02)), 0.0, 1.0))
                incident_type = "normal"
                incident_severity = 0.0
                incident_description = ""
                phone_alert_sent = False

                if incident is not None:
                    incident_type = incident.incident_type
                    incident_severity = incident.severity
                    incident_description = incident.description
                    unexplained_load_kw = round(
                        max(0.0, incident.hidden_load_kw * (0.85 + 0.25 * self.rng.random())),
                        3,
                    )
                    voltage_v -= incident.voltage_drop_v * (0.80 + 0.20 * self.rng.random())
                    frequency_hz -= 0.02 * incident.severity
                    communication_quality = float(
                        np.clip(
                            communication_quality - incident.communication_drop - (0.05 * incident.severity),
                            0.0,
                            1.0,
                        )
                    )

                    if incident.incident_id not in sent_alerts:
                        phone_alert_sent = True
                        sent_alerts.add(incident.incident_id)
                        alert_rows.append(
                            {
                                "timestamp": timestamp.isoformat(),
                                "scenario_name": scenario.name,
                                "meter_id": meter.meter_id,
                                "bus_id": meter.bus_id,
                                "incident_id": incident.incident_id,
                                "incident_type": incident.incident_type,
                                "severity": round(incident.severity, 3),
                                "channel": scenario.phone_recipient,
                                "message": self._build_phone_message(meter, incident),
                            }
                        )

                meter_consumption_kw = max(0.0, declared_load_kw - solar_generation_kw + unexplained_load_kw)
                if incident is not None and incident.extra_load_kw > 0:
                    meter_consumption_kw += incident.extra_load_kw * (0.80 + 0.35 * self.rng.random())

                current_a = (meter_consumption_kw * 1000.0) / max(voltage_v, 1.0)
                if incident is not None:
                    current_a *= incident.current_multiplier

                power_factor = float(
                    np.clip(0.96 - (0.02 * active_device_count) + self.rng.normal(0.0, 0.01), 0.75, 0.99)
                )

                meter_rows.append(
                    {
                        "timestamp": timestamp.isoformat(),
                        "scenario_name": scenario.name,
                        "meter_id": meter.meter_id,
                        "bus_id": meter.bus_id,
                        "site_name": meter.site_name,
                        "consumer_type": meter.consumer_type,
                        "hour_of_day": round(hour, 2),
                        "outdoor_temp_c": round(outdoor_temp_c, 2),
                        "active_device_count": active_device_count,
                        "peak_device_kw": round(peak_device_kw, 3),
                        "declared_device_load_kw": round(declared_load_kw, 3),
                        "solar_generation_kw": solar_generation_kw,
                        "unexplained_load_kw": unexplained_load_kw,
                        "meter_consumption_kw": round(meter_consumption_kw, 3),
                        "voltage_v": round(voltage_v, 3),
                        "current_a": round(current_a, 3),
                        "frequency_hz": round(frequency_hz, 3),
                        "power_factor": round(power_factor, 3),
                        "communication_quality": round(communication_quality, 3),
                        "incident_type": incident_type,
                        "incident_severity": round(incident_severity, 3),
                        "phone_alert_sent": int(phone_alert_sent),
                        "is_anomaly": int(incident is not None),
                        "incident_description": incident_description,
                    }
                )

        return {
            "meter_readings": pd.DataFrame(meter_rows),
            "device_readings": pd.DataFrame(device_rows),
            "phone_alerts": pd.DataFrame(alert_rows),
        }

    def export(
        self,
        frames: dict[str, pd.DataFrame],
        scenario: ScenarioDefinition,
        output_dir: str | Path,
    ) -> dict[str, Path]:
        target_dir = Path(output_dir).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        meter_path = target_dir / "meter_readings.csv"
        device_path = target_dir / "device_readings.csv"
        alerts_path = target_dir / "phone_alerts.csv"
        summary_path = target_dir / "scenario_summary.json"

        frames["meter_readings"].to_csv(meter_path, index=False)
        frames["device_readings"].to_csv(device_path, index=False)
        frames["phone_alerts"].to_csv(alerts_path, index=False)

        summary = {
            "scenario_name": scenario.name,
            "description": scenario.description,
            "seed": self.seed,
            "duration_hours": scenario.duration_hours,
            "interval_minutes": scenario.interval_minutes,
            "meters": [asdict(meter) for meter in scenario.meters],
            "incidents": [asdict(incident) for incident in scenario.incidents],
            "row_counts": {
                "meter_readings": len(frames["meter_readings"]),
                "device_readings": len(frames["device_readings"]),
                "phone_alerts": len(frames["phone_alerts"]),
            },
            "files": {
                "meter_readings": str(meter_path),
                "device_readings": str(device_path),
                "phone_alerts": str(alerts_path),
            },
        }
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        return {
            "meter_readings": meter_path,
            "device_readings": device_path,
            "phone_alerts": alerts_path,
            "scenario_summary": summary_path,
        }

    def _simulate_devices(
        self,
        scenario: ScenarioDefinition,
        meter: SmartMeterDefinition,
        timestamp: datetime,
        hour: float,
        incident: IncidentDefinition | None,
    ) -> tuple[float, int, float, list[dict[str, object]]]:
        declared_load_kw = 0.0
        active_device_count = 0
        peak_device_kw = 0.0
        device_rows: list[dict[str, object]] = []

        for device in meter.devices:
            device_power_kw, active = self._sample_device_power(device, hour)
            declared_load_kw += device_power_kw
            if active:
                active_device_count += 1
            peak_device_kw = max(peak_device_kw, device_power_kw)

            device_rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "scenario_name": scenario.name,
                    "meter_id": meter.meter_id,
                    "bus_id": meter.bus_id,
                    "device_id": device.device_id,
                    "device_name": device.name,
                    "device_category": device.category,
                    "device_active": int(active),
                    "device_power_kw": round(device_power_kw, 3),
                    "incident_type": incident.incident_type if incident else "normal",
                    "is_anomaly": int(incident is not None),
                }
            )

        return declared_load_kw, active_device_count, peak_device_kw, device_rows

    def _sample_device_power(self, device: DeviceProfile, hour: float) -> tuple[float, bool]:
        active_window = any(window.contains(hour) for window in device.active_windows)
        if not active_window:
            return device.standby_kw, False

        if self.rng.random() > device.usage_probability:
            return device.standby_kw, False

        power_kw = device.nominal_kw * (1.0 + self.rng.normal(0.0, device.variability))
        power_kw = max(device.standby_kw, power_kw)
        return float(power_kw), True

    def _active_incident(
        self,
        incidents: list[IncidentDefinition],
        meter_id: str,
        hour: float,
    ) -> IncidentDefinition | None:
        for incident in incidents:
            if incident.meter_id == meter_id and incident.contains(hour):
                return incident
        return None

    def _solar_factor(self, hour: float) -> float:
        if hour < 6.0 or hour >= 18.0:
            return 0.0
        return float(max(0.0, np.sin(np.pi * (hour - 6.0) / 12.0)))

    def _outdoor_temperature(self, hour: float) -> float:
        base = 20.0 + 8.0 * np.sin(np.pi * (hour - 6.0) / 12.0)
        return float(base + self.rng.normal(0.0, 1.2))

    def _build_phone_message(self, meter: SmartMeterDefinition, incident: IncidentDefinition) -> str:
        return (
            f"ALERT for {meter.meter_id} at {meter.site_name}: "
            f"{incident.incident_type} detected. {incident.description}"
        )
