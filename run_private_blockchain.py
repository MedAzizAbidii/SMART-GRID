#!/usr/bin/env python3
"""Copy a smart-meter CSV to a private folder and build the PoA ledger there."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from blockchain.poa_ledger import ProofOfAuthorityLedger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a smart-meter CSV into a private folder and generate the "
            "Proof-of-Authority ledger in one command."
        )
    )
    parser.add_argument(
        "--source",
        default="donnees_smart_meters.csv",
        help="Source CSV file to copy before building the ledger.",
    )
    parser.add_argument(
        "--private-root",
        default=str(Path.home() / "SMARTGRID_PRIVATE" / "smartgrid_simulation"),
        help=(
            "Private folder where the CSV copy, ledger JSON, and block files "
            "will be stored."
        ),
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=100,
        help="Number of CSV rows to seal into each block.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Optional maximum number of CSV rows to load. Use 0 for all rows.",
    )
    parser.add_argument(
        "--output-name",
        default="",
        help="Optional output JSON file name. Defaults to <source_stem>_chain.json.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    source_path = Path(args.source).expanduser()
    if not source_path.exists():
        print(f"Source CSV not found: {source_path}")
        return 1

    private_root = Path(args.private_root).expanduser()
    input_dir = private_root / "inputs"
    blockchain_dir = private_root / "blockchain"
    input_dir.mkdir(parents=True, exist_ok=True)
    blockchain_dir.mkdir(parents=True, exist_ok=True)

    copied_csv = input_dir / source_path.name
    if source_path.resolve() != copied_csv.resolve():
        shutil.copy2(source_path, copied_csv)

    output_name = args.output_name.strip() or f"{source_path.stem}_chain.json"
    output_path = blockchain_dir / output_name
    block_dir = blockchain_dir / f"{source_path.stem}_blocks"

    max_rows = None if args.max_rows <= 0 else args.max_rows
    ledger = ProofOfAuthorityLedger.from_csv(
        csv_path=copied_csv,
        block_size=args.block_size,
        max_rows=max_rows,
    )
    valid, errors = ledger.validate()
    ledger.save(output_path, block_dir=block_dir)

    summary = ledger.summary()
    print("=" * 72)
    print("PRIVATE SMART METER BLOCKCHAIN WORKFLOW")
    print("=" * 72)
    print(f"Source file     : {source_path.resolve()}")
    print(f"Copied CSV      : {copied_csv.resolve()}")
    print(f"Private root    : {private_root.resolve()}")
    print(f"Ledger file     : {output_path.resolve()}")
    print(f"Block folder    : {block_dir.resolve()}")
    print(f"Block size      : {summary['block_size']}")
    print(f"Total blocks    : {summary['total_blocks']}")
    print(f"Data blocks     : {summary['data_blocks']}")
    print(f"Transactions    : {summary['total_transactions']}")
    print(f"Alerts          : {summary['total_alerts']}")
    print(f"Normals         : {summary['total_normals']}")
    print(f"Hash file       : {(block_dir / 'block_hashes.csv').resolve()}")
    print(f"Validation      : {'OK' if valid else 'FAILED'}")
    if not valid:
        for error in errors[:10]:
            print(f"  - {error}")
    print("=" * 72)

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())