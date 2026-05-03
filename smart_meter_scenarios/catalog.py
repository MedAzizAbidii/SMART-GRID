"""Scenario catalog for smart meter dataset generation."""

from __future__ import annotations

from .models import (
    DeviceProfile,
    IncidentDefinition,
    ScenarioDefinition,
    SmartMeterDefinition,
    TimeWindow,
)


def _w(start_hour: float, end_hour: float) -> TimeWindow:
    return TimeWindow(start_hour=start_hour, end_hour=end_hour)


def build_residential_block_incident_day(
    duration_hours: int = 24,
    interval_minutes: int = 15,
) -> ScenarioDefinition:
    meters = [
        SmartMeterDefinition(
            meter_id="MTR-001",
            bus_id=5,
            site_name="Apartment A",
            consumer_type="residential",
            solar_capacity_kw=1.8,
            devices=[
                DeviceProfile("D-001", "Fridge", "cold_load", 0.18, [_w(0, 24)], 0.65, 0.10, 0.04),
                DeviceProfile("D-002", "Lighting", "lighting", 0.25, [_w(18, 23.5)], 0.95, 0.05, 0.02),
                DeviceProfile("D-003", "Water Heater", "heating", 1.80, [_w(6, 8), _w(19, 22)], 0.85, 0.07, 0.00),
                DeviceProfile("D-004", "Oven", "cooking", 2.20, [_w(12, 14), _w(18, 20)], 0.60, 0.06, 0.00),
                DeviceProfile("D-005", "Washing Machine", "appliance", 1.10, [_w(18, 21)], 0.35, 0.08, 0.00),
                DeviceProfile("D-006", "Air Conditioner", "hvac", 1.60, [_w(12, 23)], 0.55, 0.12, 0.05),
            ],
        ),
        SmartMeterDefinition(
            meter_id="MTR-002",
            bus_id=8,
            site_name="Home Office",
            consumer_type="commercial",
            solar_capacity_kw=2.4,
            devices=[
                DeviceProfile("D-101", "Router", "network", 0.04, [_w(0, 24)], 1.00, 0.03, 0.03),
                DeviceProfile("D-102", "Laptop 1", "office", 0.09, [_w(8, 18)], 0.90, 0.10, 0.01),
                DeviceProfile("D-103", "Laptop 2", "office", 0.09, [_w(8, 18)], 0.75, 0.10, 0.01),
                DeviceProfile("D-104", "Printer", "office", 0.30, [_w(9, 17)], 0.25, 0.12, 0.01),
                DeviceProfile("D-105", "Lighting", "lighting", 0.18, [_w(7, 19)], 0.85, 0.05, 0.02),
                DeviceProfile("D-106", "Air Conditioner", "hvac", 1.20, [_w(9, 18)], 0.60, 0.10, 0.04),
                DeviceProfile("D-107", "EV Charger", "mobility", 3.60, [_w(0, 6), _w(20, 24)], 0.40, 0.06, 0.00),
            ],
        ),
        SmartMeterDefinition(
            meter_id="MTR-003",
            bus_id=11,
            site_name="Corner Shop",
            consumer_type="commercial",
            solar_capacity_kw=0.0,
            devices=[
                DeviceProfile("D-201", "Display Fridge", "cold_load", 0.60, [_w(0, 24)], 0.90, 0.06, 0.10),
                DeviceProfile("D-202", "Indoor Lighting", "lighting", 0.40, [_w(7, 22)], 0.95, 0.05, 0.03),
                DeviceProfile("D-203", "Coffee Machine", "food_service", 1.40, [_w(7, 10), _w(15, 18)], 0.55, 0.08, 0.00),
                DeviceProfile("D-204", "POS Terminal", "office", 0.05, [_w(7, 22)], 1.00, 0.02, 0.02),
                DeviceProfile("D-205", "Air Conditioner", "hvac", 1.80, [_w(9, 20)], 0.70, 0.10, 0.06),
                DeviceProfile("D-206", "Signage", "lighting", 0.12, [_w(18, 23.5)], 1.00, 0.04, 0.04),
            ],
        ),
    ]

    incidents = [
        IncidentDefinition(
            incident_id="INC-001",
            meter_id="MTR-001",
            incident_type="overload",
            start_hour=18.0,
            end_hour=19.25,
            severity=0.88,
            description="Evening overload caused by oven, water heater and AC running together.",
            extra_load_kw=2.8,
            voltage_drop_v=11.0,
            current_multiplier=1.28,
        ),
        IncidentDefinition(
            incident_id="INC-002",
            meter_id="MTR-002",
            incident_type="power_theft",
            start_hour=13.0,
            end_hour=16.0,
            severity=0.72,
            description="Hidden midday load suggests tampering or unauthorized connection.",
            hidden_load_kw=1.9,
            communication_drop=0.18,
            current_multiplier=1.12,
        ),
        IncidentDefinition(
            incident_id="INC-003",
            meter_id="MTR-003",
            incident_type="voltage_sag",
            start_hour=20.5,
            end_hour=21.25,
            severity=0.67,
            description="Cooling line instability creates low-voltage behavior on the shop meter.",
            voltage_drop_v=14.0,
            communication_drop=0.08,
            current_multiplier=1.18,
        ),
    ]

    return ScenarioDefinition(
        name="residential_block_incident_day",
        description=(
            "Three smart meters monitor multiple devices across a residential block. "
            "The scenario injects overload, power theft and voltage sag incidents, "
            "and logs phone-style alerts for AI-ready CSV exports."
        ),
        meters=meters,
        incidents=incidents,
        duration_hours=duration_hours,
        interval_minutes=interval_minutes,
        base_voltage_v=230.0,
        base_frequency_hz=50.0,
        phone_recipient="phone_mock",
    )


SCENARIO_BUILDERS = {
    "residential_block_incident_day": build_residential_block_incident_day,
}


def list_scenarios() -> dict[str, str]:
    return {
        "residential_block_incident_day": (
            "Residential block with multi-device smart meters, phone alerts and CSV output "
            "for future AI anomaly detection."
        )
    }


def get_scenario(
    name: str,
    duration_hours: int | None = None,
    interval_minutes: int | None = None,
) -> ScenarioDefinition:
    builder = SCENARIO_BUILDERS.get(name)
    if builder is None:
        known = ", ".join(sorted(SCENARIO_BUILDERS))
        raise ValueError(f"Unknown scenario '{name}'. Available scenarios: {known}")

    return builder(
        duration_hours=duration_hours or 24,
        interval_minutes=interval_minutes or 15,
    )
