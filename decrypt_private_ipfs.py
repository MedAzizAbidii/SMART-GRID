#!/usr/bin/env python3
"""Decrypt a smart-meter .enc file produced by run_private_ipfs.py."""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
from pathlib import Path


PBKDF2_ITERATIONS = 390_000
DEFAULT_ENV_FILES = (
    Path.home() / "SMARTGRID_PRIVATE" / "smartgrid_simulation" / "ipfs" / ".env",
    Path(__file__).resolve().parent / ".env",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Decrypt an encrypted smart-meter file and write the original CSV back to disk."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the encrypted .enc file or to the manifest JSON file.",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional manifest JSON file. If omitted, the script tries to find it automatically.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output CSV path. Defaults to a decrypted CSV next to the encrypted file.",
    )
    parser.add_argument(
        "--passphrase",
        default="",
        help="Passphrase used to decrypt the file.",
    )
    parser.add_argument(
        "--passphrase-env",
        default="SMARTGRID_IPFS_PASSPHRASE",
        help="Environment variable that can hold the passphrase.",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help="Optional KEY=VALUE file to load before reading the passphrase.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the decrypted file after writing it.",
    )
    return parser


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue

            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]

            existing_value = os.environ.get(key)
            if existing_value is None or not existing_value.strip():
                os.environ[key] = value


def load_local_environment(args: argparse.Namespace) -> None:
    if args.env_file.strip():
        _load_env_file(Path(args.env_file).expanduser())

    for env_path in DEFAULT_ENV_FILES:
        _load_env_file(env_path)


def resolve_passphrase(args: argparse.Namespace) -> str:
    if args.passphrase.strip():
        return args.passphrase.strip()

    env_value = os.environ.get(args.passphrase_env, "").strip()
    if env_value:
        return env_value

    return getpass.getpass("IPFS passphrase: ").strip()


def derive_fernet(passphrase: str, salt: bytes):
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:
        raise SystemExit(
            "cryptography is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode("utf-8")))
    return Fernet(key)


def load_manifest(manifest_path: Path) -> dict[str, object]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    with manifest_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def find_manifest_for_encrypted(encrypted_path: Path) -> Path:
    source_base = Path(Path(encrypted_path.name).stem).stem
    manifest_dir = encrypted_path.parents[1] / "manifests"
    return manifest_dir / f"{source_base}_ipfs_manifest.json"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    load_local_environment(args)

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    if input_path.suffix.lower() == ".json" and not args.manifest.strip():
        manifest_path = input_path
        manifest = load_manifest(manifest_path)
        encrypted_path = Path(str(manifest.get("encrypted_file", ""))).expanduser()
    else:
        encrypted_path = input_path
        manifest_path = Path(args.manifest).expanduser() if args.manifest.strip() else find_manifest_for_encrypted(encrypted_path)
        manifest = load_manifest(manifest_path)

    if not encrypted_path.exists():
        raise FileNotFoundError(f"Encrypted file not found: {encrypted_path}")

    encryption_data = manifest.get("encryption")
    if not isinstance(encryption_data, dict):
        raise RuntimeError("Manifest is missing the encryption section.")

    salt_b64 = str(encryption_data.get("salt_b64", "")).strip()
    if not salt_b64:
        raise RuntimeError("Manifest is missing the encryption salt.")

    passphrase = resolve_passphrase(args)
    if not passphrase:
        print("Missing passphrase. Set --passphrase or SMARTGRID_IPFS_PASSPHRASE.")
        return 1

    salt = base64.b64decode(salt_b64)
    fernet = derive_fernet(passphrase, salt)
    decrypted_bytes = fernet.decrypt(encrypted_path.read_bytes())

    source_name = str(manifest.get("source_name") or encrypted_path.stem)
    default_output_name = f"{Path(source_name).stem}.decrypted{Path(source_name).suffix or '.csv'}"
    output_path = Path(args.output).expanduser() if args.output.strip() else encrypted_path.with_name(default_output_name)
    output_path.write_bytes(decrypted_bytes)

    print("=" * 72)
    print("PRIVATE IPFS DECRYPTION WORKFLOW")
    print("=" * 72)
    print(f"Manifest        : {manifest_path.resolve()}")
    print(f"Encrypted file  : {encrypted_path.resolve()}")
    print(f"Decrypted file  : {output_path.resolve()}")
    print("=" * 72)

    if args.open:
        opener = getattr(os, "startfile", None)
        if opener is None:
            print("Open command is not available on this platform.")
        else:
            opener(str(output_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())