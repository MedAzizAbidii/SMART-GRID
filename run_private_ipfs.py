#!/usr/bin/env python3
"""Encrypt a smart-meter CSV and optionally pin the encrypted blob to IPFS."""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


PBKDF2_ITERATIONS = 390_000
DEFAULT_PRIVATE_ROOT = Path.home() / "SMARTGRID_PRIVATE" / "smartgrid_simulation" / "ipfs"
DEFAULT_LOG_FILE = DEFAULT_PRIVATE_ROOT / "pinata_upload.log"
DEFAULT_IPFS_API = "http://127.0.0.1:5001/api/v0/add"
DEFAULT_PINATA_API = "https://api.pinata.cloud/pinning/pinFileToIPFS"
DEFAULT_PINATA_JWT_API = "https://uploads.pinata.cloud/v3/files"
DEFAULT_ENV_VAR = "SMARTGRID_IPFS_PASSPHRASE"
DEFAULT_ENV_FILES = (
    Path.home() / "SMARTGRID_PRIVATE" / "smartgrid_simulation" / "ipfs" / ".env",
    Path(__file__).resolve().parent / ".env",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Encrypt a smart-meter CSV locally and optionally upload the encrypted "
            "blob to a private IPFS node."
        )
    )
    parser.add_argument(
        "--source",
        default="donnees_smart_meters.csv",
        help="Path to the raw CSV to protect.",
    )
    parser.add_argument(
        "--private-root",
        default=str(DEFAULT_PRIVATE_ROOT),
        help="Private folder for encrypted outputs.",
    )
    parser.add_argument(
        "--passphrase",
        default="",
        help="Passphrase used to encrypt the CSV.",
    )
    parser.add_argument(
        "--passphrase-env",
        default=DEFAULT_ENV_VAR,
        help="Environment variable that can hold the passphrase.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload the selected file to the local IPFS API.",
    )
    parser.add_argument(
        "--no-encrypt",
        action="store_true",
        help="Upload the source file as-is instead of encrypting it first.",
    )
    parser.add_argument(
        "--provider",
        choices=["local", "pinata"],
        default="local",
        help="Upload backend to use when --upload is set.",
    )
    parser.add_argument(
        "--ipfs-api",
        default=DEFAULT_IPFS_API,
        help="IPFS add API endpoint.",
    )
    parser.add_argument(
        "--pinata-jwt",
        default="",
        help="Pinata JWT. Falls back to the PINATA_JWT environment variable.",
    )
    parser.add_argument(
        "--pinata-api-key",
        default="",
        help="Legacy Pinata API key. Falls back to the PINATA_API_KEY environment variable.",
    )
    parser.add_argument(
        "--pinata-api-secret",
        default="",
        help="Legacy Pinata API secret. Falls back to the PINATA_API_SECRET environment variable.",
    )
    parser.add_argument(
        "--output-name",
        default="",
        help="Optional encrypted filename. Defaults to <source name>.enc.",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help=(
            "Optional KEY=VALUE file to load before reading the passphrase and "
            "Pinata credentials."
        ),
    )
    parser.add_argument(
        "--log-file",
        default=str(DEFAULT_LOG_FILE),
        help="Append human-readable upload logs to this file.",
    )
    return parser


def source_is_inside_repo(source_path: Path) -> bool:
    repo_root = Path(__file__).resolve().parent
    try:
        source_path.resolve().relative_to(repo_root)
        return True
    except ValueError:
        return False


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


def resolve_pinata_credentials(args: argparse.Namespace) -> dict[str, str]:
    api_key = args.pinata_api_key.strip() or os.environ.get("PINATA_API_KEY", "").strip()
    api_secret = args.pinata_api_secret.strip() or os.environ.get("PINATA_API_SECRET", "").strip()
    if api_key and api_secret:
        return {"mode": "key_secret", "api_key": api_key, "api_secret": api_secret}

    jwt = args.pinata_jwt.strip() or os.environ.get("PINATA_JWT", "").strip()
    if jwt:
        return {"mode": "jwt", "jwt": jwt}

    return {}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def append_log(log_path: Path | None, message: str) -> None:
    if log_path is None:
        return

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(f"[{_timestamp()}] {message}\n")
    except OSError:
        pass


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


def upload_to_ipfs(encrypted_path: Path, api_url: str) -> dict[str, str]:
    try:
        import requests
    except ImportError as exc:
        raise SystemExit(
            "requests is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    with encrypted_path.open("rb") as handle:
        response = requests.post(
            api_url,
            params={"pin": "true", "cid-version": "1"},
            files={"file": (encrypted_path.name, handle)},
            timeout=120,
        )

    response.raise_for_status()
    payload = response.json()
    cid = payload.get("Hash") or payload.get("Cid") or payload.get("cid")
    if not cid:
        raise RuntimeError(f"Unexpected IPFS response: {payload}")

    return {"cid": str(cid), "name": str(payload.get("Name", encrypted_path.name))}


def upload_to_pinata(encrypted_path: Path, credentials: dict[str, str]) -> dict[str, str]:
    try:
        import requests
    except ImportError as exc:
        raise SystemExit(
            "requests is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    if credentials.get("mode") == "jwt":
        with encrypted_path.open("rb") as handle:
            response = requests.post(
                DEFAULT_PINATA_JWT_API,
                headers={"Authorization": f"Bearer {credentials['jwt']}"},
                files={"file": (encrypted_path.name, handle)},
                timeout=120,
            )
    else:
        with encrypted_path.open("rb") as handle:
            response = requests.post(
                DEFAULT_PINATA_API,
                headers={
                    "pinata_api_key": credentials["api_key"],
                    "pinata_secret_api_key": credentials["api_secret"],
                },
                files={"file": (encrypted_path.name, handle)},
                timeout=120,
            )

    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    cid = (
        data.get("cid")
        or data.get("IpfsHash")
        or data.get("ipfsHash")
        or data.get("Hash")
        or data.get("id")
    )
    if not cid:
        raise RuntimeError(f"Unexpected Pinata response: {payload}")

    url = data.get("pinning_url") or data.get("url") or data.get("gatewayUrl") or ""
    return {"cid": str(cid), "name": str(data.get("name", encrypted_path.name)), "url": str(url)}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    load_local_environment(args)

    source_path = Path(args.source).expanduser()
    if not source_path.exists():
        print(f"Source CSV not found: {source_path}")
        return 1

    private_root = Path(args.private_root).expanduser()
    manifest_dir = private_root / "manifests"
    log_path = Path(args.log_file).expanduser() if args.log_file.strip() else None
    manifest_dir.mkdir(parents=True, exist_ok=True)

    source_inside_repo = source_is_inside_repo(source_path)
    if source_inside_repo:
        print(
            "Warning: the source CSV is inside the repository. Move it outside the repo before public sharing."
        )

    append_log(
        log_path,
        f"START source={source_path.name} provider={args.provider} upload={str(bool(args.upload)).lower()}",
    )

    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()

    if args.no_encrypt:
        payload_kind = "raw"
        payload_dir = private_root / "raw"
        payload_dir.mkdir(parents=True, exist_ok=True)
        payload_name = args.output_name.strip() or source_path.name
        payload_path = payload_dir / payload_name
        if source_path.resolve() != payload_path.resolve():
            shutil.copy2(source_path, payload_path)
        payload_hash = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        encryption_info = {"scheme": "none"}
        append_log(
            log_path,
            f"RAW_STAGED source={source_path.name} payload={payload_path.name} payload_sha256={payload_hash}",
        )
    else:
        passphrase = resolve_passphrase(args)
        if not passphrase:
            print("Missing passphrase. Set --passphrase or SMARTGRID_IPFS_PASSPHRASE.")
            return 1

        payload_kind = "encrypted"
        payload_dir = private_root / "encrypted"
        payload_dir.mkdir(parents=True, exist_ok=True)

        salt = os.urandom(16)
        fernet = derive_fernet(passphrase, salt)
        payload_bytes = fernet.encrypt(source_bytes)
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        payload_name = args.output_name.strip() or f"{source_path.name}.enc"
        payload_path = payload_dir / payload_name
        payload_path.write_bytes(payload_bytes)
        encryption_info = {
            "scheme": "fernet",
            "passphrase_env": args.passphrase_env,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
            "pbkdf2_iterations": PBKDF2_ITERATIONS,
        }

        append_log(
            log_path,
            f"ENCRYPTED source={source_path.name} payload={payload_path.name} payload_sha256={payload_hash}",
        )

    storage_meta = {
        "uploaded": False,
        "provider": args.provider,
        "api": args.ipfs_api if args.provider == "local" else DEFAULT_PINATA_API,
        "cid": None,
        "url": None,
        "payload_kind": payload_kind,
        "payload_file": payload_path.name,
    }
    if args.upload:
        try:
            append_log(
                log_path,
                f"UPLOAD_ATTEMPT source={source_path.name} provider={args.provider} kind={payload_kind} target={payload_path.name}",
            )
            if args.provider == "local":
                upload_result = upload_to_ipfs(payload_path, args.ipfs_api)
                storage_meta = {
                    "uploaded": True,
                    "provider": "local",
                    "api": args.ipfs_api,
                    "cid": upload_result["cid"],
                    "name": upload_result["name"],
                    "url": f"ipfs://{upload_result['cid']}",
                    "payload_kind": payload_kind,
                    "payload_file": payload_path.name,
                }
            else:
                credentials = resolve_pinata_credentials(args)
                if not credentials:
                    print(
                        "Missing Pinata credentials. Set PINATA_JWT or PINATA_API_KEY and PINATA_API_SECRET, or pass them on the command line."
                    )
                    return 1

                upload_result = upload_to_pinata(payload_path, credentials)
                storage_meta = {
                    "uploaded": True,
                    "provider": "pinata",
                    "api": DEFAULT_PINATA_JWT_API if credentials.get("mode") == "jwt" else DEFAULT_PINATA_API,
                    "cid": upload_result["cid"],
                    "name": upload_result["name"],
                    "url": upload_result.get("url") or f"ipfs://{upload_result['cid']}",
                    "payload_kind": payload_kind,
                    "payload_file": payload_path.name,
                }

            append_log(
                log_path,
                "UPLOAD_OK "
                f"source={source_path.name} provider={storage_meta['provider']} "
                f"cid={storage_meta['cid']} url={storage_meta['url']} "
                f"kind={payload_kind} payload={payload_path.name}",
            )
        except Exception as exc:
            print(f"IPFS/Pinata upload failed: {exc}")
            append_log(
                log_path,
                f"UPLOAD_ERROR source={source_path.name} provider={args.provider} error={type(exc).__name__}: {exc}",
            )
            if args.provider == "local":
                print("Start a local IPFS daemon first: ipfs daemon")
            else:
                print("Check your Pinata credentials and network access.")
            return 1
    else:
        append_log(log_path, f"UPLOAD_SKIPPED source={source_path.name} reason=upload_flag_disabled")

    manifest = {
        "source_file": str(source_path.resolve()),
        "source_name": source_path.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload_file": str(payload_path.resolve()),
        "payload_kind": payload_kind,
        "source_sha256": source_hash,
        "payload_sha256": payload_hash,
        "encryption": encryption_info,
        "storage": storage_meta,
        "privacy": {
            "raw_csv_kept_outside_repo": not source_inside_repo,
            "raw_csv_not_stored": True,
        },
    }
    if args.no_encrypt:
        manifest["raw_file"] = str(payload_path.resolve())
        manifest["raw_sha256"] = payload_hash
    else:
        manifest["encrypted_file"] = str(payload_path.resolve())
        manifest["encrypted_sha256"] = payload_hash
    manifest_path = manifest_dir / f"{source_path.stem}_ipfs_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("=" * 72)
    print("PRIVATE IPFS UPLOAD WORKFLOW")
    print("=" * 72)
    print(f"Source file     : {source_path.resolve()}")
    print(f"Payload file    : {payload_path.resolve()}")
    print(f"Manifest        : {manifest_path.resolve()}")
    print(f"Source SHA256   : {source_hash}")
    print(f"Payload SHA256  : {payload_hash}")
    if storage_meta["cid"]:
        print(f"Storage provider: {storage_meta['provider']}")
        print(f"Content ID      : {storage_meta['cid']}")
    else:
        print(f"Storage provider: {storage_meta['provider']}")
        print("Content ID      : skipped")
    print("=" * 72)

    append_log(
        log_path,
        f"DONE source={source_path.name} manifest={manifest_path.name} storage_provider={storage_meta['provider']} kind={payload_kind}",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())