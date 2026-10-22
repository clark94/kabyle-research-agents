"""Canonical local SHA-256 integrity receipts.

These fingerprints are not IPFS CIDs. See web3.raw_cid and IPFSClient for actual
CIDv1 raw blocks and explicit Kubo publication; canonical bytes must be preserved.
"""

from __future__ import annotations

import hashlib
import json

HASHED_FIELDS = ("id", "title", "type", "description", "url", "languages", "keywords", "license")


def canonical_json(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def digest(obj: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj)).hexdigest()


def fiche_hash(record: dict) -> str:
    subset = {k: record.get(k, [] if k in ("languages", "keywords") else "") for k in HASHED_FIELDS}
    subset["languages"] = list(subset["languages"])
    subset["keywords"] = list(subset["keywords"])
    return digest(subset)
