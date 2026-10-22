"""Pipeline orchestration: language -> query -> search -> composer -> verifier."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .agents import (
    ComposerAgent,
    Context,
    LanguageAgent,
    QueryAgent,
    SearchAgent,
    VerifierAgent,
)
from .catalog import Catalog, LoadReport, load_catalog
from .models import Answer
from .provenance import digest
from .query import Glossary
from .retrieval import Index


class Orchestrator:
    def __init__(self, catalog: Catalog, glossary: Glossary, report: LoadReport | None = None,
                 top_k: int = 5):
        self.catalog, self.glossary = catalog, glossary
        self.report = report or LoadReport()
        self.index = Index([f for f in catalog])
        self.top_k = top_k
        self.agents = [LanguageAgent(), QueryAgent(), SearchAgent(), ComposerAgent(), VerifierAgent()]

    @classmethod
    def from_files(cls, catalog_path: str | Path, glossary_path: str | Path,
                   top_k: int = 5) -> Orchestrator:
        catalog, report = load_catalog(catalog_path)
        return cls(catalog, Glossary.from_file(glossary_path), report, top_k)

    def ask(self, question: str) -> Answer:
        ctx = Context(question, self.catalog, self.glossary, self.index, self.top_k)
        for agent in self.agents:
            agent.run(ctx)
        answer = ctx.answer
        answer.trace = [asdict(s) for s in ctx.trace]
        # The receipt covers what was said and why, not timings: it is reproducible and
        # ready to be anchored on a ledger later.
        answer.receipt = digest({
            "question": answer.question,
            "status": answer.status,
            "citations": [asdict(r.citation) for r in answer.results],
        })
        return answer
