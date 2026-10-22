"""Catalog loading with integrity and security gates.

A fiche enters the index only if:
  * its stored ``content_hash`` (when present) matches the recomputed one (no tampering),
  * it passes the hidden-instruction scan (otherwise it is quarantined for human review).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from .models import Fiche
from .provenance import fiche_hash
from .security import is_invisible, scan_record

REQUIRED = ("id", "title", "type", "description", "url")


class CatalogFormatError(ValueError):
    pass


@dataclass
class LoadReport:
    total: int = 0
    accepted: int = 0
    quarantined: dict[str, list[str]] = field(default_factory=dict)
    tampered: list[str] = field(default_factory=list)
    unstamped: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not (self.quarantined or self.tampered)


class Catalog:
    def __init__(self, fiches: list[Fiche]):
        self._by_id = {f.id: f for f in fiches}

    def __iter__(self) -> Iterator[Fiche]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, fiche_id: str) -> Fiche | None:
        return self._by_id.get(fiche_id)


def dump_record(record: dict) -> str:
    """JSON line that keeps accents readable but escapes invisible characters, so that hidden
    payloads are visible in code review and git diffs."""
    raw = json.dumps(record, ensure_ascii=False)
    return "".join(json.dumps(c)[1:-1] if is_invisible(c) else c for c in raw)


def _read_records(path: Path) -> list[dict]:
    records = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CatalogFormatError(f"{path}:{n}: invalid JSON ({exc.msg})") from exc
        missing = [k for k in REQUIRED if not rec.get(k)]
        if missing:
            raise CatalogFormatError(f"{path}:{n}: missing field(s) {', '.join(missing)}")
        records.append(rec)
    return records


def load_catalog(path: str | Path) -> tuple[Catalog, LoadReport]:
    report = LoadReport()
    fiches: list[Fiche] = []
    seen = set()
    for rec in _read_records(Path(path)):
        report.total += 1
        fid = rec["id"]
        if fid in seen:
            raise CatalogFormatError(f'Duplicate fiche id: {fid}')
        seen.add(fid)
        if not isinstance(rec.get('validated', False), bool):
            raise CatalogFormatError(f'{fid}: validated must be a JSON boolean')
        computed = fiche_hash(rec)
        stored = rec.get("content_hash", "")
        if stored and stored != computed:
            report.tampered.append(fid)
            continue
        reasons = scan_record({k: v for k, v in rec.items() if k != "content_hash"})
        if reasons:
            report.quarantined[fid] = reasons
            continue
        if not stored:
            report.unstamped.append(fid)
        fiches.append(
            Fiche(
                id=fid,
                title=rec["title"],
                type=rec["type"],
                description=rec["description"],
                url=rec["url"],
                languages=tuple(rec.get("languages", ())),
                keywords=tuple(rec.get("keywords", ())),
                license=rec.get("license", "unknown"),
                validated=bool(rec.get("validated", False)),
                content_hash=computed,
            )
        )
        report.accepted += 1
    return Catalog(fiches), report


def stamp_file(path: str | Path, force: bool = False) -> int:
    """Write ``content_hash`` into every record that lacks one. Returns records changed."""
    path = Path(path)
    out, changed = [], 0
    for rec in _read_records(path):
        computed = fiche_hash(rec)
        if force or not rec.get("content_hash"):
            changed += rec.get("content_hash") != computed
            rec["content_hash"] = computed
        out.append(dump_record(rec))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed
