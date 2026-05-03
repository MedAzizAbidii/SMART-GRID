#!/usr/bin/env python3
"""Run the smart-meter simulator, dashboard, blockchain export, and Pinata sync."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_PYTHON = PROJECT_ROOT / "venv64" / "Scripts" / "python.exe"
PYTHON_EXECUTABLE = str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))
DEFAULT_CSV = PROJECT_ROOT / "donnees_smart_meters.csv"
DEFAULT_ALERTS = PROJECT_ROOT / "alertes_smart_meters.csv"
DEFAULT_STATE = PROJECT_ROOT / "smart_meters_state.json"
DEFAULT_LEDGER = PROJECT_ROOT / "data" / "blockchain" / "smart_meter_chain.json"
DEFAULT_PINATA_LOG = Path.home() / "SMARTGRID_PRIVATE" / "smartgrid_simulation" / "ipfs" / "pinata_upload.log"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Launch the smart-meter simulator, open the dashboard, build the PoA ledger, "
            "and upload the CSV, blockchain blocks, and blockchain hash file to Pinata automatically."
        )
    )
    parser.add_argument(
        "--csv-file",
        default=str(DEFAULT_CSV),
        help="Live CSV file written by smart_meters_simulator.py.",
    )
    parser.add_argument(
        "--alerts-file",
        default=str(DEFAULT_ALERTS),
        help="Alert CSV file written by smart_meters_simulator.py.",
    )
    parser.add_argument(
        "--ledger-output",
        default=str(DEFAULT_LEDGER),
        help="Blockchain ledger JSON output path.",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=100,
        help="Number of CSV rows per blockchain block.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional CSV row limit for the blockchain export. Use 0 for all rows.",
    )
    parser.add_argument(
        "--sync-seconds",
        type=float,
        default=0.5,
        help="How often to poll for a completed simulator iteration before refreshing the blockchain export and Pinata uploads.",
    )
    parser.add_argument(
        "--initial-sync-delay",
        type=int,
        default=1,
        help="Seconds to wait before the first blockchain sync.",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE),
        help="State JSON file updated by smart_meters_simulator.py after each iteration.",
    )
    parser.add_argument(
        "--upload-target",
        choices=["csv", "hash", "both"],
        default="both",
        help="Which snapshot files to upload to Pinata. Blockchain block uploads are always enabled.",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not launch the FastAPI dashboard.",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Skip Pinata uploads and only build the blockchain export.",
    )
    parser.add_argument(
        "--passphrase",
        default="",
        help="Passphrase forwarded to run_private_ipfs.py.",
    )
    parser.add_argument(
        "--passphrase-env",
        default="SMARTGRID_IPFS_PASSPHRASE",
        help="Environment variable used by run_private_ipfs.py for the passphrase.",
    )
    parser.add_argument(
        "--pinata-jwt",
        default="",
        help="Optional Pinata JWT forwarded to run_private_ipfs.py.",
    )
    parser.add_argument(
        "--pinata-api-key",
        default="",
        help="Optional Pinata API key forwarded to run_private_ipfs.py.",
    )
    parser.add_argument(
        "--pinata-api-secret",
        default="",
        help="Optional Pinata API secret forwarded to run_private_ipfs.py.",
    )
    parser.add_argument(
        "--provider",
        choices=["pinata", "local"],
        default="pinata",
        help="Upload backend to use when uploads are enabled.",
    )
    parser.add_argument(
        "--pinata-log-file",
        default=str(DEFAULT_PINATA_LOG),
        help="Log file used by run_private_ipfs.py for Pinata uploads.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Set NO_BROWSER=1 before launching the dashboard.",
    )
    return parser


def launch_process(script_name: str, extra_env: dict[str, str] | None = None) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(extra_env or {})
    command = [PYTHON_EXECUTABLE, "-u", script_name]
    creationflags = 0
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    return subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        env=env,
        creationflags=creationflags,
    )


def terminate_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def snapshot_file(source_path: Path, snapshot_dir: Path) -> Path:
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = snapshot_dir / source_path.name
    if source_path.exists():
        shutil.copy2(source_path, snapshot_path)
    return snapshot_path


def run_command(args: list[str]) -> None:
    subprocess.run(args, cwd=PROJECT_ROOT, check=True)


def blockchain_args(csv_path: Path, ledger_output: Path, block_size: int, max_rows: int) -> list[str]:
    args = [
        PYTHON_EXECUTABLE,
        "-u",
        "run_blockchain_poa.py",
        "--input",
        str(csv_path),
        "--output",
        str(ledger_output),
        "--block-size",
        str(block_size),
    ]
    if max_rows > 0:
        args.extend(["--max-rows", str(max_rows)])
    return args


def private_ipfs_args(source_path: Path, provider: str, args: argparse.Namespace, no_encrypt: bool) -> list[str]:
    upload_args = [
        PYTHON_EXECUTABLE,
        "-u",
        "run_private_ipfs.py",
        "--source",
        str(source_path),
        "--upload",
        "--provider",
        provider,
        "--passphrase-env",
        args.passphrase_env,
        "--log-file",
        args.pinata_log_file,
    ]

    if no_encrypt:
        upload_args.append("--no-encrypt")
    elif args.passphrase.strip():
        upload_args.extend(["--passphrase", args.passphrase.strip()])
    if args.pinata_jwt.strip():
        upload_args.extend(["--pinata-jwt", args.pinata_jwt.strip()])
    if args.pinata_api_key.strip():
        upload_args.extend(["--pinata-api-key", args.pinata_api_key.strip()])
    if args.pinata_api_secret.strip():
        upload_args.extend(["--pinata-api-secret", args.pinata_api_secret.strip()])

    return upload_args


def has_upload_backend(args: argparse.Namespace) -> bool:
    if args.no_upload:
        return False

    if args.provider == "local":
        return True

    has_jwt = args.pinata_jwt.strip() or os.environ.get("PINATA_JWT", "").strip()
    has_key_secret = (
        (args.pinata_api_key.strip() or os.environ.get("PINATA_API_KEY", "").strip())
        and (args.pinata_api_secret.strip() or os.environ.get("PINATA_API_SECRET", "").strip())
    )
    return bool(has_jwt or has_key_secret)


def can_upload_csv(args: argparse.Namespace) -> bool:
    if not has_upload_backend(args):
        return False

    return bool(args.passphrase.strip() or os.environ.get(args.passphrase_env, "").strip())


def can_upload_raw(args: argparse.Namespace) -> bool:
    return has_upload_backend(args)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return None

    return (stat_result.st_mtime_ns, stat_result.st_size)


def run_upload_command(command: list[str], label: str) -> bool:
    try:
        run_command(command)
        return True
    except subprocess.CalledProcessError as exc:
        print(f"[sync] {label} failed with exit code {exc.returncode}")
        return False


def sync_exports(
    args: argparse.Namespace,
    csv_path: Path,
    ledger_output: Path,
    snapshot_root: Path,
    upload_state: dict[str, object],
) -> None:
    snapshot_csv = snapshot_file(csv_path, snapshot_root)
    if not snapshot_csv.exists() or snapshot_csv.stat().st_size == 0:
        print("Waiting for the simulator to create the CSV file...")
        return

    print(f"[sync] Building blockchain from {snapshot_csv.name}")
    run_command(blockchain_args(snapshot_csv, ledger_output, args.block_size, args.max_rows))

    block_dir = ledger_output.parent / f"{ledger_output.stem}_blocks"
    hash_file = block_dir / "block_hashes.csv"
    block_files = sorted(
        path
        for path in block_dir.glob("block_*.json")
        if path.name != "block_hashes.csv"
    )

    if args.upload_target in {"csv", "both"} and can_upload_csv(args):
        print("[sync] Uploading encrypted CSV snapshot")
        run_upload_command(
            private_ipfs_args(snapshot_csv, args.provider, args, no_encrypt=False),
            f"CSV upload {snapshot_csv.name}",
        )
    elif args.upload_target in {"csv", "both"} and has_upload_backend(args):
        print("[sync] CSV upload skipped until passphrase is available.")
    elif args.upload_target in {"csv", "both"}:
        print("[sync] CSV upload skipped because upload credentials are missing.")

    if not can_upload_raw(args):
        print("[sync] Block uploads skipped because upload credentials are missing.")
        return

    uploaded_block_hashes = upload_state.setdefault("block_hashes", {})
    if not isinstance(uploaded_block_hashes, dict):
        raise TypeError("upload_state['block_hashes'] must be a dict")

    for block_file in block_files:
        digest = file_sha256(block_file)
        if uploaded_block_hashes.get(block_file.name) == digest:
            continue

        print(f"[sync] Uploading blockchain block to Pinata: {block_file.name}")
        if run_upload_command(
            private_ipfs_args(block_file, args.provider, args, no_encrypt=True),
            f"block upload {block_file.name}",
        ):
            uploaded_block_hashes[block_file.name] = digest

    if args.upload_target in {"hash", "both"} and hash_file.exists():
        hash_digest = file_sha256(hash_file)
        previous_hash_digest = str(upload_state.get("hash_digest", ""))
        if hash_digest != previous_hash_digest:
            print("[sync] Uploading blockchain hash file to Pinata")
            if run_upload_command(
                private_ipfs_args(hash_file, args.provider, args, no_encrypt=True),
                f"hash upload {hash_file.name}",
            ):
                upload_state["hash_digest"] = hash_digest


def main() -> int:
    args = build_parser().parse_args()

    csv_path = Path(args.csv_file).expanduser()
    ledger_output = Path(args.ledger_output).expanduser()
    state_path = Path(args.state_file).expanduser()
    ledger_output.parent.mkdir(parents=True, exist_ok=True)

    dashboard_process: subprocess.Popen | None = None
    simulator_process: subprocess.Popen | None = None
    upload_state: dict[str, object] = {"block_hashes": {}, "hash_digest": ""}
    poll_interval = max(0.25, float(args.sync_seconds))

    try:
        if not args.no_dashboard:
            dashboard_env = {"NO_BROWSER": "1"} if args.no_browser else {}
            print("Starting dashboard at http://127.0.0.1:8000/dashboard")
            dashboard_process = launch_process("run_demo.py", dashboard_env)

        print("Starting smart-meter simulator")
        simulator_process = launch_process("smart_meters_simulator.py")

        snapshot_root = Path(tempfile.mkdtemp(prefix="smartgrid_sync_", dir=str(PROJECT_ROOT)))
        time.sleep(max(0, args.initial_sync_delay))
        sync_exports(args, csv_path, ledger_output, snapshot_root, upload_state)

        last_state_signature = file_signature(state_path)
        while True:
            if simulator_process.poll() is not None:
                raise RuntimeError("smart_meters_simulator.py stopped unexpectedly")

            if dashboard_process is not None and dashboard_process.poll() is not None:
                raise RuntimeError("run_demo.py stopped unexpectedly")

            current_state_signature = file_signature(state_path)
            if current_state_signature is not None and current_state_signature != last_state_signature:
                print("[sync] New simulator iteration detected; rebuilding blockchain and uploads")
                sync_exports(args, csv_path, ledger_output, snapshot_root, upload_state)
                last_state_signature = file_signature(state_path)

            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("\nStopping smart-meter workflow...")
    finally:
        terminate_process(simulator_process)
        terminate_process(dashboard_process)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())