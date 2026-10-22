"""The five cooperating agents.

Each agent has one job, reads and writes a shared :class:`Context`, and leaves a trace line, so a
run can be audited step by step. They are plain objects with a ``run`` method: wrapping them as
MCP tools or A2A servers (see ``docs/ARCHITECTURE.md``) does not change their logic.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .catalog import Catalog
from .lang import Detection, detect_language
from .models import Answer, Citation, Result
from .query import Glossary, QueryPlan, understand
from .retrieval import Hit, Index
from .verifier import Verification, check_citation

MESSAGES = {
    "fr": {
        "answered": "J'ai trouvé {n} fiche(s) du catalogue qui répondent à votre demande.",
        "partial": "Aucune fiche ne couvre toute la demande. Résultats approchants (il manque : {missing}).",
        "no_answer": "Je n'ai trouvé aucune fiche correspondante dans le catalogue. "
        "Je préfère ne rien proposer plutôt que d'inventer.",
        "vague": "La question est trop générale pour chercher dans le catalogue. "
        "Précisez un type de ressource ou un domaine.",
        "dropped": "Aucune fiche n'a passé la vérification des sources : je ne réponds pas.",
    },
    "en": {
        "answered": "I found {n} catalog entry(ies) matching your request.",
        "partial": "No entry covers the whole request. Closest results (missing: {missing}).",
        "no_answer": "I found no matching entry in the catalog. "
        "I would rather return nothing than make something up.",
        "vague": "The question is too general to search the catalog. "
        "Please name a resource type or a domain.",
        "dropped": "No entry passed source verification, so I am not answering.",
    },
}
QUOTE_LIMIT = 240


@dataclass
class TraceStep:
    agent: str
    summary: str
    ms: float


@dataclass
class Context:
    question: str
    catalog: Catalog
    glossary: Glossary
    index: Index
    top_k: int = 5
    detection: Detection | None = None
    plan: QueryPlan | None = None
    hits: list[Hit] = field(default_factory=list)
    answer: Answer | None = None
    verification: Verification | None = None
    trace: list[TraceStep] = field(default_factory=list)


class _Agent:
    name = "agent"
    description = ""

    def run(self, ctx: Context) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def _log(self, ctx: Context, summary: str, started: float) -> None:
        ctx.trace.append(TraceStep(self.name, summary, round((time.perf_counter() - started) * 1000, 2)))


class LanguageAgent(_Agent):
    name = "language"
    description = "Detects whether the question is written in Kabyle, French or English."

    def run(self, ctx: Context) -> None:
        t = time.perf_counter()
        ctx.detection = detect_language(ctx.question)
        d = ctx.detection
        self._log(ctx, f"lang={d.lang} script={d.script} confidence={d.confidence}", t)


class QueryAgent(_Agent):
    name = "query"
    description = "Turns the question into language-independent needs using the curated glossary."

    def run(self, ctx: Context) -> None:
        t = time.perf_counter()
        ctx.plan = understand(ctx.question, ctx.glossary)
        needs = ", ".join(n.label for n in ctx.plan.needs) or "none"
        self._log(ctx, f"needs=[{needs}] ignored={ctx.plan.ignored}", t)


class SearchAgent(_Agent):
    name = "search"
    description = "Searches the validated catalog; ranks by need coverage, then BM25."

    def run(self, ctx: Context) -> None:
        t = time.perf_counter()
        hits = ctx.index.search(ctx.plan, top_k=50) if ctx.plan else []
        if hits:
            best = hits[0].coverage
            hits = [h for h in hits if h.coverage == best][: ctx.top_k]
            if best < 0.5:
                hits = []
        ctx.hits = hits
        top = f"{hits[0].coverage:.2f}" if hits else "-"
        self._log(ctx, f"hits={len(hits)} top_coverage={top}", t)


class ComposerAgent(_Agent):
    name = "composer"
    description = "Builds an extractive answer: titles, links and verbatim excerpts only."

    def run(self, ctx: Context) -> None:
        t = time.perf_counter()
        lang = ctx.detection.lang if ctx.detection and ctx.detection.lang in MESSAGES else "fr"
        msgs = MESSAGES[lang]
        qlang = ctx.detection.lang if ctx.detection else "und"
        if not ctx.plan or not ctx.plan.needs:
            ctx.answer = Answer(ctx.question, qlang, lang, "no_answer", msgs["vague"])
        elif not ctx.hits:
            ctx.answer = Answer(ctx.question, qlang, lang, "no_answer", msgs["no_answer"])
        else:
            results = [self._result(h) for h in ctx.hits]
            if ctx.hits[0].coverage == 1.0:
                status, msg = "answered", msgs["answered"].format(n=len(results))
            else:
                missing = ", ".join(ctx.hits[0].unmatched)
                status, msg = "partial", msgs["partial"].format(missing=missing)
            ctx.answer = Answer(ctx.question, qlang, lang, status, msg, results)
        self._log(ctx, f"status={ctx.answer.status} results={len(ctx.answer.results)}", t)

    @staticmethod
    def _result(h: Hit) -> Result:
        desc = " ".join(h.fiche.description.split())
        truncated = len(desc) > QUOTE_LIMIT
        quote = desc[:QUOTE_LIMIT].rsplit(" ", 1)[0] if truncated else desc
        cite = Citation(h.fiche.id, h.fiche.url, h.fiche.content_hash, quote, h.fiche.license, truncated)
        return Result(h.fiche.title, h.fiche.type, h.matched, h.unmatched, cite)


class VerifierAgent(_Agent):
    name = "verifier"
    description = "Re-checks every citation against the catalog; drops anything unverifiable."

    def run(self, ctx: Context) -> None:
        t = time.perf_counter()
        ans, ver = ctx.answer, Verification()
        kept = []
        for r in ans.results:
            problems = check_citation(r.citation, ctx.catalog)
            ver.checked += 1
            if problems:
                ver.problems += problems
            else:
                ver.valid += 1
                kept.append(r)
        ans.results = kept
        if ver.checked and not kept:
            ans.status, ans.message = "no_answer", MESSAGES[ans.answer_language]["dropped"]
        ans.verification = ver.to_dict()
        ctx.verification = ver
        self._log(ctx, f"valid={ver.valid}/{ver.checked}", t)
