#!/usr/bin/env python3
"""Upload a tiny plain-text payload to Pinata for a gateway test."""

from __future__ import annotations

import argparse
import os
import webbrowser
from typing import Any

from run_private_ipfs import DEFAULT_PINATA_API, DEFAULT_PINATA_JWT_API, load_local_environment, resolve_pinata_credentials


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload a tiny text file to Pinata to verify gateway access."
    )
    parser.add_argument(
        "--message",
        default="Pinata test upload from smartgrid_simulation",
        help="Text content to upload.",
    )
    parser.add_argument(
        "--name",
        default="pinata_test.txt",
        help="Filename to show in Pinata.",
    )
    parser.add_argument(
        "--env-file",
        default="",
        help="Optional KEY=VALUE file to load before reading Pinata credentials.",
    )
    parser.add_argument(
        "--pinata-jwt",
        default="",
        help="Pinata JWT. Falls back to PINATA_JWT in the environment.",
    )
    parser.add_argument(
        "--pinata-api-key",
        default="",
        help="Legacy Pinata API key. Falls back to PINATA_API_KEY in the environment.",
    )
    parser.add_argument(
        "--pinata-api-secret",
        default="",
        help="Legacy Pinata API secret. Falls back to PINATA_API_SECRET in the environment.",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the resulting gateway URL in your browser.",
    )
    return parser


def upload_text_to_pinata(message: str, file_name: str, credentials: dict[str, str]) -> dict[str, str]:
    try:
        import requests
    except ImportError as exc:
        raise SystemExit(
            "requests is required. Install dependencies with: pip install -r requirements.txt"
        ) from exc

    file_payload = (file_name, message.encode("utf-8"), "text/plain")
    if credentials.get("mode") == "jwt":
        response = requests.post(
            DEFAULT_PINATA_JWT_API,
            headers={"Authorization": f"Bearer {credentials['jwt']}"},
            files={"file": file_payload},
            timeout=120,
        )
    else:
        response = requests.post(
            DEFAULT_PINATA_API,
            headers={
                "pinata_api_key": credentials["api_key"],
                "pinata_secret_api_key": credentials["api_secret"],
            },
            files={"file": file_payload},
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

    url = data.get("pinning_url") or data.get("url") or data.get("gatewayUrl") or f"https://gateway.pinata.cloud/ipfs/{cid}"
    return {"cid": str(cid), "name": str(data.get("name", file_name)), "url": str(url)}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    load_local_environment(args)
    credentials = resolve_pinata_credentials(args)
    if not credentials:
        print("Missing Pinata credentials. Set PINATA_JWT or PINATA_API_KEY and PINATA_API_SECRET.")
        return 1

    result = upload_text_to_pinata(args.message, args.name, credentials)

    gateway_url = result.get("url") or f"https://gateway.pinata.cloud/ipfs/{result['cid']}"
    print("=" * 72)
    print("PINATA TEST UPLOAD")
    print("=" * 72)
    print(f"File name   : {result['name']}")
    print(f"CID         : {result['cid']}")
    print(f"Gateway URL  : {gateway_url}")
    print("=" * 72)

    if args.open:
        webbrowser.open(gateway_url)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())