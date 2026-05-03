#!/usr/bin/env python3
"""Display the Pinata upload log produced by run_private_ipfs.py."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from run_private_ipfs import DEFAULT_LOG_FILE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show the Pinata upload log and optionally follow new entries live."
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Upload log file to display.",
    )
    parser.add_argument(
        "--tail",
        type=int,
        default=40,
        help="Number of recent log lines to print before following.",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Keep watching the file for new upload log entries.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=1.0,
        help="Polling interval used in follow mode.",
    )
    return parser


def read_tail(log_path: Path, line_count: int) -> list[str]:
    if not log_path.exists() or log_path.stat().st_size == 0:
        return []

    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return lines[-max(1, line_count) :]


def print_log_lines(lines: list[str]) -> None:
    for line in lines:
        print(line.rstrip("\n"))


def follow_log(log_path: Path, poll_seconds: float) -> None:
    position = 0
    if log_path.exists():
        position = log_path.stat().st_size

    try:
        while True:
            if not log_path.exists():
                time.sleep(poll_seconds)
                continue

            current_size = log_path.stat().st_size
            if current_size < position:
                position = 0

            with log_path.open("r", encoding="utf-8", errors="replace") as handle:
                handle.seek(position)
                while True:
                    line = handle.readline()
                    if not line:
                        position = handle.tell()
                        break
                    print(line.rstrip("\n"))

            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        print("\nStopped following Pinata upload logs.")


def main() -> int:
    args = build_parser().parse_args()
    log_path = Path(args.log_file).expanduser()

    print("=" * 72)
    print("PINATA UPLOAD LOG VIEWER")
    print("=" * 72)
    print(f"Log file: {log_path.resolve()}")
    print("=" * 72)

    tail_lines = read_tail(log_path, args.tail)
    if tail_lines:
        print_log_lines(tail_lines)
    else:
        print("No log entries yet. Run the workflow or upload script first.")

    if args.follow:
        follow_log(log_path, args.poll_seconds)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())