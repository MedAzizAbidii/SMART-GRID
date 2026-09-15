"""production/blockchain/pinata_bridge.py

Optional off-chain-storage layer: pins the local PoA ledger's block
content (blockchain/poa_ledger.py's PoABlock.to_dict()) to IPFS via
Pinata, so a block's data survives independently of this process's
memory — the local PoA ledger otherwise lives only in the running
backend's RAM and is lost on restart. Fully additive and OFF by default
(no PINATA_JWT configured), the same pattern already used for
onchain_bridge.py's SGRID_ONCHAIN_ENABLED gate — nothing here changes
local PoA behavior when disabled.

What this does NOT do: it does not make Pinata/IPFS the ledger's source
of truth, and it does not encrypt anything before pinning (block content
already excludes secrets — see poa_ledger.py's canonical JSON). It is a
durability/transparency add-on: anyone with a block's IPFS CID can fetch
its exact pinned JSON from any IPFS gateway, independent of this backend.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger("smartgrid.pinata")

PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
# Public gateway; a CID resolves here without any Pinata credentials —
# this is what the "view on IPFS" link in the UI points at.
PINATA_GATEWAY_URL = "https://gateway.pinata.cloud/ipfs/"


def pinata_enabled() -> bool:
    return bool(os.environ.get("PINATA_JWT"))


def fetch_from_gateway(cid: str) -> dict[str, Any]:
    """Fetch a pinned block's JSON content back from a public IPFS gateway.

    No Pinata credentials needed — this is the point: anyone, including
    someone with no relationship to this backend, can independently fetch
    the same content from any IPFS gateway using only the CID, which is
    what makes the integrity check in /api/blockchain/blocks/{i}/verify
    meaningful rather than just re-trusting this server.
    """
    resp = requests.get(f"{PINATA_GATEWAY_URL}{cid}", timeout=15)
    resp.raise_for_status()
    return resp.json()


def pin_block_json(block_dict: dict[str, Any]) -> dict[str, Any]:
    """Pin one PoA block's dict (from PoABlock.to_dict()) to IPFS via Pinata.

    Returns {"cid": ..., "gateway_url": ...} on success, or raises on
    failure — callers (api_server.py) wrap this so a Pinata outage never
    blocks the local PoA ledger itself from working.
    """
    jwt = os.environ.get("PINATA_JWT")
    if not jwt:
        raise RuntimeError("PINATA_JWT not configured — pinata_enabled() should be checked first")

    payload = {
        "pinataContent": block_dict,
        "pinataMetadata": {
            "name": f"smartgrid-poa-block-{block_dict.get('index')}",
        },
    }
    resp = requests.post(
        PINATA_PIN_JSON_URL,
        json=payload,
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    cid = data["IpfsHash"]
    return {"cid": cid, "gateway_url": f"{PINATA_GATEWAY_URL}{cid}"}
