"""Domain models for scenario-driven smart meter simulation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimeWindow:
    start_hour: float
    end_hour: float

    def contains(self, hour: float) -> bool:
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour


@dataclass(frozen=True)
class DeviceProfile:
    device_id: str
    name: str
    category: str
    nominal_kw: float
    active_windows: list[TimeWindow]
    usage_probability: float = 1.0
    variability: float = 0.08
    standby_kw: float = 0.0


@dataclass(frozen=True)
class SmartMeterDefinition:
    meter_id: str
    bus_id: int
    site_name: str
    consumer_type: str
    devices: list[DeviceProfile]
    solar_capacity_kw: float = 0.0


@dataclass(frozen=True)
class IncidentDefinition:
    incident_id: str
    meter_id: str
    incident_type: str
    start_hour: float
    end_hour: float
    severity: float
    description: str
    extra_load_kw: float = 0.0
    hidden_load_kw: float = 0.0
    voltage_drop_v: float = 0.0
    communication_drop: float = 0.0
    current_multiplier: float = 1.0

    def contains(self, hour: float) -> bool:
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    description: str
    meters: list[SmartMeterDefinition]
    incidents: list[IncidentDefinition]
    duration_hours: int = 24
    interval_minutes: int = 15
    base_voltage_v: float = 230.0
    base_frequency_hz: float = 50.0
    phone_recipient: str = "phone_mock"
