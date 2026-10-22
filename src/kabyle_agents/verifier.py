"""Citation verification: the enforcement point of the golden rule.

Independent from whoever composed the answer (a template today, an LLM tomorrow). A citation is
valid only if it points to a real, validated fiche, with the exact URL and content hash the
catalog holds, and its quote is a verbatim excerpt of that fiche.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import Catalog
from .models import Citation
from .provenance import fiche_hash


@dataclass
class Verification:
    checked: int = 0
    valid: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {"checked": self.checked, "valid": self.valid, "problems": list(self.problems)}


def _squash(text: str) -> str:
    return " ".join(text.split())


def check_citation(c: Citation, catalog: Catalog) -> list[str]:
    fiche = catalog.get(c.fiche_id)
    if fiche is None:
        return [f"{c.fiche_id}: unknown fiche"]
    problems = []
    if not fiche.validated:
        problems.append(f"{c.fiche_id}: fiche not validated by the committee")
    if c.url != fiche.url:
        problems.append(f"{c.fiche_id}: url differs from catalog")
    if c.content_hash != fiche.content_hash or fiche_hash(fiche.to_record()) != fiche.content_hash:
        problems.append(f"{c.fiche_id}: content hash mismatch")
    if not c.quote or _squash(c.quote) not in _squash(fiche.description):
        problems.append(f"{c.fiche_id}: quote is not a verbatim excerpt")
    return problems
