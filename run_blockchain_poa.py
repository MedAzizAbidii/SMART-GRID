#!/usr/bin/env python3
"""Build a Proof-of-Authority blockchain from smart-meter CSV data."""

from __future__ import annotations

import argparse
from pathlib import Path

from blockchain.poa_ledger import ProofOfAuthorityLedger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Anchor smart-meter CSV data into a private Proof-of-Authority blockchain."
    )
    parser.add_argument(
        "--input",
        default="donnees_smart_meters.csv",
        help="Input smart-meter CSV file.",
    )
    parser.add_argument(
        "--output",
        default="data/blockchain/smart_meter_chain.json",
        help="Output blockchain JSON file.",
    )
    parser.add_argument(
        "--block-dir",
        default="",
        help=(
            "Optional directory for individual block JSON files. "
            "Leave empty to use a folder next to --output."
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    max_rows = None if args.max_rows <= 0 else args.max_rows
    output_path = Path(args.output)
    block_dir = Path(args.block_dir) if args.block_dir else output_path.parent / f"{output_path.stem}_blocks"
    ledger = ProofOfAuthorityLedger.from_csv(
        csv_path=args.input,
        block_size=args.block_size,
        max_rows=max_rows,
    )
    valid, errors = ledger.validate()
    output_path = ledger.save(output_path, block_dir=block_dir)

    summary = ledger.summary()
    print("=" * 72)
    print("SMART METER PROOF-OF-AUTHORITY LEDGER")
    print("=" * 72)
    print(f"Input file      : {Path(args.input).resolve()}")
    print(f"Output file     : {output_path.resolve()}")
    print(f"Authorities     : {', '.join(summary['authorities'])}")
    print(f"Block size      : {summary['block_size']}")
    print(f"Total blocks    : {summary['total_blocks']}")
    print(f"Data blocks     : {summary['data_blocks']}")
    print(f"Transactions    : {summary['total_transactions']}")
    print(f"Alerts          : {summary['total_alerts']}")
    print(f"Normals         : {summary['total_normals']}")
    print(f"Block folder    : {block_dir.resolve()}")
    print(f"Block files     : {summary['total_blocks']}")
    print(f"Hash file       : {(block_dir / 'block_hashes.csv').resolve()}")
    print(f"Validation      : {'OK' if valid else 'FAILED'}")
    if not valid:
        for error in errors[:10]:
            print(f"  - {error}")
    print("=" * 72)

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
