#!/usr/bin/env python3
"""Live terminal diagram for smart-grid providers, devices and detection."""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from components.smart_grid_components import Producer
from config import Config
from smart_meter_scenarios import ScenarioSimulator, get_scenario


DEFAULT_DATA_FILE = Path("donnees_smart_meters.csv")
DEFAULT_ALERT_FILE = Path("alertes_smart_meters.csv")


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def build_producers() -> list[Producer]:
    config = Config()
    producers: list[Producer] = []
    for producer_config in config.PRODUCERS:
        producers.append(
            Producer(
                producer_id=producer_config["id"],
                name=producer_config["name"],
                bus_id=producer_config["bus"],
                producer_type=producer_config["type"],
                capacity_mw=producer_config["capacity_mw"],
                cost_per_mwh=producer_config["cost_per_mwh"],
            )
        )
    return producers


def format_provider_line(name: str, bus_id: int, output_mw: float) -> str:
    return f"  - {name:<14} bus {bus_id:<2} -> {output_mw:6.2f} MW"


def format_device_line(device_row: pd.Series) -> str:
    status = "ON" if int(device_row["device_active"]) else "STBY"
    power_kw = float(device_row["device_power_kw"])
    device_name = str(device_row["device_name"])
    category = str(device_row["device_category"])
    return f"    - {device_name:<15} [{category:<10}] {status:<4} {power_kw:6.3f} kW"


def read_csv_frame(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def clean_display_value(value: object, default: str = "none") -> str:
    if value is None:
        return default

    if pd.isna(value):
        return default

    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def render_waiting_state(
    producer_outputs: list[tuple[str, int, float]],
    data_file: Path,
    alert_file: Path,
    clear_before: bool = True,
) -> None:
    if clear_before:
        clear_screen()

    total_generation = sum(output for _, _, output in producer_outputs)
    print("=" * 86)
    print("SMART GRID LIVE NETWORK DIAGRAM")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}   Mode: LIVE MONITOR")
    print("=" * 86)
    print()

    print("ELECTRICITY PROVIDERS")
    for name, bus_id, output_mw in producer_outputs:
        print(format_provider_line(name, bus_id, output_mw))
    print(f"  - TOTAL SUPPLY    -> {total_generation:6.2f} MW")
    print()

    print("FLOW")
    print("  [PROVIDERS] -> [IEEE 14-BUS GRID] -> [SMART METERS] -> [DETECTOR]")
    print("                                   |")
    print("                                   +-> [CSV OUTPUT]")
    print()

    print("STATUS")
    print(f"  Waiting for data in: {data_file}")
    print(f"  Alert file         : {alert_file}")
    print("  Start smart_meters_simulator.py in another terminal.")
    print("  The workflow will update as soon as rows appear.")
    print()
    print("Legend: NORMAL = reading inside thresholds | ALERTE = anomaly detected")
    print("Press Ctrl+C to stop.")


def render_monitor_frame(
    producer_outputs: list[tuple[str, int, float]],
    data_df: pd.DataFrame,
    alert_df: pd.DataFrame,
    data_file: Path,
    alert_file: Path,
    clear_before: bool = True,
) -> None:
    if clear_before:
        clear_screen()

    now = datetime.now()
    hour_of_day = now.hour + now.minute / 60.0 + now.second / 3600.0
    total_generation = sum(output for _, _, output in producer_outputs)

    latest_row = None if data_df.empty else data_df.iloc[-1]
    total_readings = len(data_df)
    total_alerts = 0 if data_df.empty or "statut" not in data_df.columns else int((data_df["statut"] == "ALERTE").sum())
    alert_rate = (total_alerts / total_readings * 100.0) if total_readings else 0.0
    last_update = datetime.fromtimestamp(data_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if data_file.exists() else "n/a"

    if latest_row is None:
        render_waiting_state(producer_outputs, data_file, alert_file, clear_before=False)
        return

    meter_id = clean_display_value(latest_row.get("meter_id", "n/a"), "n/a")
    zone = clean_display_value(latest_row.get("zone", "n/a"), "n/a")
    meter_type = clean_display_value(latest_row.get("type", "n/a"), "n/a")
    consumption_kw = float(latest_row.get("consommation_kw", 0.0))
    tension_v = float(latest_row.get("tension_v", 0.0))
    courant_a = float(latest_row.get("courant_a", 0.0))
    status = clean_display_value(latest_row.get("statut", "NORMAL"), "NORMAL")
    anomalies = clean_display_value(latest_row.get("anomalies", ""), "none")
    latest_timestamp = clean_display_value(latest_row.get("timestamp", "n/a"), "n/a")

    recent_alerts = alert_df.tail(5) if not alert_df.empty else pd.DataFrame()

    print("=" * 86)
    print("SMART GRID LIVE NETWORK DIAGRAM")
    print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}   Mode: LIVE MONITOR   Hour: {hour_of_day:05.2f}")
    print(f"Data updated: {last_update}")
    print("=" * 86)
    print()

    print("ELECTRICITY PROVIDERS")
    for name, bus_id, output_mw in producer_outputs:
        print(format_provider_line(name, bus_id, output_mw))
    print(f"  - TOTAL SUPPLY    -> {total_generation:6.2f} MW")
    print()

    print("LIVE FLOW")
    if status == "ALERTE":
        print("  [PROVIDERS] -> [GRID] -> [SMART METER] -> [DETECTOR: ALERTE] -> [alertes_smart_meters.csv]")
    else:
        print("  [PROVIDERS] -> [GRID] -> [SMART METER] -> [DETECTOR: NORMAL] -> [donnees_smart_meters.csv]")
    print("                                   |")
    print("                                   +-> [LOG FILE]")
    print()

    print("LATEST READING")
    print(f"  timestamp     : {latest_timestamp}")
    print(f"  meter         : {meter_id} | {zone} | {meter_type}")
    print(f"  consumption   : {consumption_kw:7.3f} kW")
    print(f"  voltage       : {tension_v:7.2f} V")
    print(f"  current       : {courant_a:7.3f} A")
    print(f"  detector      : {status}")
    print(f"  anomalies     : {anomalies if anomalies else 'none'}")
    print()

    print("LIVE STATS")
    print(f"  total readings : {total_readings}")
    print(f"  total alerts   : {total_alerts}")
    print(f"  alert rate     : {alert_rate:.2f}%")
    print()

    print("RECENT ALERTS")
    if recent_alerts.empty:
        print("  No alerts yet.")
    else:
        for _, alert_row in recent_alerts.iterrows():
            print(
                f"  - {clean_display_value(alert_row.get('timestamp', 'n/a'), 'n/a')} | "
                f"{clean_display_value(alert_row.get('meter_id', 'n/a'), 'n/a')} | "
                f"{clean_display_value(alert_row.get('zone', 'n/a'), 'n/a')} | "
                f"{clean_display_value(alert_row.get('alerte', 'n/a'), 'n/a')}"
            )
    print()
    print("Legend: NORMAL = reading inside thresholds | ALERTE = anomaly detected")
    print("Press Ctrl+C to stop.")


def render_frame(
    frame_index: int,
    total_frames: int,
    timestamp_text: str,
    hour_of_day: float,
    producer_outputs: list[tuple[str, int, float]],
    meter_rows: pd.DataFrame,
    device_rows: pd.DataFrame,
    clear_before: bool = True,
) -> None:
    if clear_before:
        clear_screen()

    total_generation = sum(output for _, _, output in producer_outputs)
    total_demand = float(meter_rows["meter_consumption_kw"].sum())
    balance_mw = total_generation - (total_demand / 1000.0)

    print("=" * 86)
    print("SMART GRID LIVE NETWORK DIAGRAM")
    print(f"Frame: {frame_index + 1}/{total_frames}   Time: {timestamp_text}   Hour: {hour_of_day:05.2f}")
    print("=" * 86)
    print()

    print("ELECTRICITY PROVIDERS")
    for name, bus_id, output_mw in producer_outputs:
        print(format_provider_line(name, bus_id, output_mw))
    print(f"  - TOTAL SUPPLY    -> {total_generation:6.2f} MW")
    print()

    print("FLOW")
    print("  [PROVIDERS] -> [IEEE 14-BUS GRID] -> [SMART METERS] -> [DEVICES]")
    print("                                   |")
    print("                                   +-> [DETECTOR]")
    print()

    print("GRID BALANCE")
    print(f"  Demand from meters : {total_demand:7.2f} kW")
    print(f"  Supply from plants  : {total_generation:7.2f} MW")
    print(f"  Balance             : {balance_mw:7.2f} MW")
    print()

    for _, meter_row in meter_rows.sort_values(["bus_id", "meter_id"]).iterrows():
        meter_id = str(meter_row["meter_id"])
        meter_devices = device_rows[device_rows["meter_id"] == meter_id].sort_values("device_id")
        status = "ALERTE" if int(meter_row["is_anomaly"]) else "NORMAL"
        incident_type = str(meter_row["incident_type"])
        incident_description = str(meter_row.get("incident_description", ""))

        print("-" * 86)
        print(
            f"METER {meter_id} | {meter_row['site_name']} | bus {int(meter_row['bus_id'])} | "
            f"{meter_row['consumer_type']}"
        )
        print("  Devices")
        for _, device_row in meter_devices.iterrows():
            print(format_device_line(device_row))
        print("  Readings")
        print(f"    declared load   : {float(meter_row['declared_device_load_kw']):7.3f} kW")
        print(f"    solar generation: {float(meter_row['solar_generation_kw']):7.3f} kW")
        print(f"    meter load      : {float(meter_row['meter_consumption_kw']):7.3f} kW")
        print(f"    voltage         : {float(meter_row['voltage_v']):7.3f} V")
        print(f"    current         : {float(meter_row['current_a']):7.3f} A")
        print(f"    detector state  : {status}")
        print(f"    incident type   : {incident_type}")
        if incident_description and incident_type != "normal":
            print(f"    note            : {incident_description}")
        print(f"    phone alert     : {'yes' if int(meter_row['phone_alert_sent']) else 'no'}")

    print("-" * 86)
    print("DETECTOR LOGIC")
    print("  incident active -> ALERTE")
    print("  no incident     -> NORMAL")
    print("  phone alert     -> sent once per incident")
    print()
    print("Legend: NORMAL = reading inside thresholds | ALERTE = anomaly detected")
    print("Press Ctrl+C to stop.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Animate a terminal diagram showing electricity providers, the grid, devices, "
            "and the detection action in real time."
        )
    )
    parser.add_argument(
        "--scenario",
        default="residential_block_incident_day",
        help="Scenario name to replay.",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Follow the live smart-meter CSV files while smart_meters_simulator.py is running.",
    )
    parser.add_argument(
        "--data-file",
        default=str(DEFAULT_DATA_FILE),
        help="CSV file to monitor in live mode.",
    )
    parser.add_argument(
        "--alert-file",
        default=str(DEFAULT_ALERT_FILE),
        help="Alert CSV file to monitor in live mode.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used to generate the scenario.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=12,
        help="Number of frames to show before stopping.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.8,
        help="Delay in seconds between frames.",
    )
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Loop over the scenario forever until Ctrl+C.",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Keep previous frames on screen instead of clearing the terminal.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    producers = build_producers()

    if args.monitor:
        data_file = Path(args.data_file)
        alert_file = Path(args.alert_file)
        try:
            while True:
                data_df = read_csv_frame(data_file)
                alert_df = read_csv_frame(alert_file)
                hour_of_day = datetime.now().hour + datetime.now().minute / 60.0 + datetime.now().second / 3600.0
                producer_outputs = [
                    (producer.name, producer.bus_id, round(producer.get_output_at_hour(hour_of_day), 2))
                    for producer in producers
                ]
                if data_df.empty:
                    render_waiting_state(producer_outputs, data_file, alert_file)
                else:
                    render_monitor_frame(
                        producer_outputs,
                        data_df,
                        alert_df,
                        data_file,
                        alert_file,
                    )
                time.sleep(args.delay)
        except KeyboardInterrupt:
            print("\nLive monitor stopped by user.")
        return 0

    scenario = get_scenario(name=args.scenario)
    simulator = ScenarioSimulator(seed=args.seed)
    frames = simulator.simulate(scenario)

    meter_readings = frames["meter_readings"].sort_values(["timestamp", "meter_id"])
    device_readings = frames["device_readings"].sort_values(["timestamp", "meter_id", "device_id"])

    timestamps = list(dict.fromkeys(meter_readings["timestamp"].tolist()))
    if not timestamps:
        print("No readings available.")
        return 1

    total_frames = args.frames if args.frames > 0 else len(timestamps)
    if total_frames > len(timestamps):
        total_frames = len(timestamps)

    try:
        if args.repeat:
            frame_index = 0
            while True:
                timestamp = timestamps[frame_index % len(timestamps)]
                meter_rows = meter_readings[meter_readings["timestamp"] == timestamp]
                device_rows = device_readings[device_readings["timestamp"] == timestamp]
                hour_of_day = float(meter_rows.iloc[0]["hour_of_day"])
                producer_outputs = [
                    (producer.name, producer.bus_id, round(producer.get_output_at_hour(hour_of_day), 2))
                    for producer in producers
                ]
                timestamp_text = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                render_frame(
                    frame_index % len(timestamps),
                    len(timestamps),
                    timestamp_text,
                    hour_of_day,
                    producer_outputs,
                    meter_rows,
                    device_rows,
                    clear_before=not args.no_clear,
                )
                frame_index += 1
                time.sleep(args.delay)
        else:
            for frame_index, timestamp in enumerate(timestamps[:total_frames]):
                meter_rows = meter_readings[meter_readings["timestamp"] == timestamp]
                device_rows = device_readings[device_readings["timestamp"] == timestamp]
                hour_of_day = float(meter_rows.iloc[0]["hour_of_day"])
                producer_outputs = [
                    (producer.name, producer.bus_id, round(producer.get_output_at_hour(hour_of_day), 2))
                    for producer in producers
                ]
                timestamp_text = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                render_frame(
                    frame_index,
                    total_frames,
                    timestamp_text,
                    hour_of_day,
                    producer_outputs,
                    meter_rows,
                    device_rows,
                    clear_before=not args.no_clear,
                )
                if frame_index + 1 < total_frames:
                    time.sleep(args.delay)
    except KeyboardInterrupt:
        print("\nLive diagram stopped by user.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())