#!/usr/bin/env python3
"""Run a scenario-driven smart meter dataset export."""

from __future__ import annotations

import argparse
from pathlib import Path

from smart_meter_scenarios import ScenarioSimulator, get_scenario, list_scenarios


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate smart meter datasets from a business scenario with multiple devices, "
            "incidents and phone-style alerts."
        )
    )
    parser.add_argument(
        "--scenario",
        default="residential_block_incident_day",
        help="Scenario name to run.",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Scenario duration in hours.",
    )
    parser.add_argument(
        "--interval_minutes",
        type=int,
        default=15,
        help="Sampling interval in minutes.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible CSV generation.",
    )
    parser.add_argument(
        "--output_dir",
        default="./data/scenario_datasets",
        help="Base directory where scenario outputs will be saved.",
    )
    parser.add_argument(
        "--list-scenarios",
        action="store_true",
        help="List available scenarios and exit.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_scenarios:
        print("Available scenarios:")
        for name, description in list_scenarios().items():
            print(f" - {name}: {description}")
        return 0

    scenario = get_scenario(
        name=args.scenario,
        duration_hours=args.hours,
        interval_minutes=args.interval_minutes,
    )
    simulator = ScenarioSimulator(seed=args.seed)
    frames = simulator.simulate(scenario)

    scenario_output_dir = Path(args.output_dir) / scenario.name
    paths = simulator.export(frames, scenario, scenario_output_dir)

    meter_rows = len(frames["meter_readings"])
    alert_rows = len(frames["phone_alerts"])
    anomaly_rows = int(frames["meter_readings"]["is_anomaly"].sum()) if not frames["meter_readings"].empty else 0

    print("=" * 70)
    print("SMART METER SCENARIO DATASET GENERATED")
    print("=" * 70)
    print(f"Scenario: {scenario.name}")
    print(f"Description: {scenario.description}")
    print(f"Duration: {scenario.duration_hours} hours")
    print(f"Interval: {scenario.interval_minutes} minutes")
    print(f"Meter rows: {meter_rows}")
    print(f"Anomaly rows: {anomaly_rows}")
    print(f"Phone alerts: {alert_rows}")
    print(f"Meter CSV: {paths['meter_readings']}")
    print(f"Device CSV: {paths['device_readings']}")
    print(f"Alerts CSV: {paths['phone_alerts']}")
    print(f"Summary JSON: {paths['scenario_summary']}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
