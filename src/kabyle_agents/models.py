"""Plain data structures shared by all agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Status = Literal["answered", "partial", "no_answer"]


@dataclass(frozen=True)
class Fiche:
    """One catalog entry, as validated by the editorial committee."""

    id: str
    title: str
    type: str
    description: str
    url: str
    languages: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    license: str = "unknown"
    validated: bool = False
    content_hash: str = ""

    def to_record(self) -> dict:
        """Fields covered by the content hash (committee state is excluded on purpose)."""
        return {
            "id": self.id,
            "title": self.title,
            "type": self.type,
            "description": self.description,
            "url": self.url,
            "languages": list(self.languages),
            "keywords": list(self.keywords),
            "license": self.license,
        }


@dataclass(frozen=True)
class Citation:
    fiche_id: str
    url: str
    content_hash: str
    quote: str  # verbatim excerpt of the fiche description
    license: str
    truncated: bool = False


@dataclass(frozen=True)
class Result:
    title: str
    type: str
    why: tuple[str, ...]  # query needs this fiche satisfies
    missing: tuple[str, ...]  # query needs it does NOT satisfy
    citation: Citation


@dataclass
class Answer:
    question: str
    query_language: str
    answer_language: str
    status: Status
    message: str
    results: list[Result] = field(default_factory=list)
    verification: dict = field(default_factory=dict)
    receipt: str = ""
    trace: list[dict] = field(default_factory=list)
