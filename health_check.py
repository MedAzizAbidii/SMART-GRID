#!/usr/bin/env python3
"""Quick health check for smart grid simulation."""
from __future__ import annotations

import os
import traceback

from components.grid_connection import HAS_PYPOWSYBL, PyPowSyBlInterface


def main() -> int:
    print("=" * 60)
    print("SMART GRID HEALTH CHECK")
    print("=" * 60)

    # 1) Grid interface / network check
    try:
        grid = PyPowSyBlInterface()
        power_flow_ok = grid.run_power_flow()
        buses = grid.get_bus_voltages()
        bus_count = len(buses)

        print(f"solver_mode: {'REAL (PyPowSyBl)' if HAS_PYPOWSYBL else 'MOCK'}")
        print(f"power_flow_ok: {power_flow_ok}")
        print(f"bus_count: {bus_count}")

        if not power_flow_ok or bus_count != 14:
            print("network_status: FAIL")
            return 1
        print("network_status: PASS")
    except Exception as exc:
        print(f"network_status: FAIL ({exc})")
        traceback.print_exc()
        return 1

    # 2) Dataset output check (fast mode outputs)
    clean_file = os.path.join("data", "clean", "smartgrid_clean_fast.csv")
    attack_file = os.path.join("data", "attacks", "attacks_fast.csv")

    clean_exists = os.path.exists(clean_file)
    attack_exists = os.path.exists(attack_file)

    print(f"clean_file_exists: {clean_exists} ({clean_file})")
    print(f"attack_file_exists: {attack_exists} ({attack_file})")

    if clean_exists and attack_exists:
        print("pipeline_status: PASS")
        print("overall_status: PASS")
        return 0

    print("pipeline_status: WARN (run run_simulation_fast.py to generate files)")
    print("overall_status: PASS_WITH_WARNINGS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
