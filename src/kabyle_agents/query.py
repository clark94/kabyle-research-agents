"""Query understanding: glossary-based cross-lingual expansion.

A question is reduced to *needs* (e.g. "dictionary", "medicine"). Each need knows the words that
express it in kab/fr/en, so « amawal n ddwa », « dictionnaire de médecine » and « medicine
dictionary » all produce the same needs. Glossary entries are *curated data*: the model never
translates on its own, which would be a hallucination vector for a low-resource language.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .lang import STOPWORDS
from .normalize import dice, normalize, tokenize

FUZZY_THRESHOLD = 0.8
FUZZY_MIN_LEN = 6


@dataclass(frozen=True)
class Need:
    label: str
    origin: tuple[str, ...]  # normalized forms found in the question
    expanded: tuple[str, ...] = ()  # normalized forms added by the glossary / fuzzy match
    residual: bool = False  # True when the word is not in the glossary

    @property
    def forms(self) -> tuple[str, ...]:
        return self.origin + self.expanded

    def satisfied_by(self, tokens: frozenset[str], padded: str) -> bool:
        return any(_form_in(f, tokens, padded) for f in self.forms)


def _form_in(form: str, tokens: frozenset[str], padded: str) -> bool:
    if " " in form:
        return f" {form} " in padded
    return form in tokens or form + "s" in tokens or form + "x" in tokens


@dataclass(frozen=True)
class Concept:
    name: str
    forms: tuple[str, ...]
    generic: bool = False  # e.g. "kabyle": true of the whole catalog, not a real constraint


class Glossary:
    def __init__(self, concepts: dict[str, dict]):
        self.concepts: list[Concept] = []
        for name, spec in concepts.items():
            forms: list[str] = []
            for lang in ("kab", "fr", "en"):
                forms += [normalize(f) for f in spec.get(lang, [])]
            self.concepts.append(Concept(name, tuple(dict.fromkeys(forms)), spec.get("generic", False)))

    @classmethod
    def from_file(cls, path: str | Path) -> Glossary:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data["concepts"])


@dataclass
class QueryPlan:
    question: str
    tokens: list[str]
    needs: list[Need] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)  # generic concepts (e.g. "kabyle")


def understand(question: str, glossary: Glossary) -> QueryPlan:
    tokens = tokenize(question)
    token_set = frozenset(tokens)
    padded = " " + " ".join(tokens) + " "
    plan = QueryPlan(question, tokens)
    consumed: set[str] = set()
    seen: set[str] = set()

    def add_concept(c: Concept, matched: list[str]) -> None:
        if c.name in seen:
            return
        seen.add(c.name)
        for f in matched:
            consumed.update(f.split())
            consumed.update({f + "s", f + "x"})  # plural spellings of a matched form
        if c.generic:
            plan.ignored.append(c.name)
            return
        expanded = tuple(f for f in c.forms if f not in matched)
        plan.needs.append(Need(c.name, tuple(matched), expanded))

    for c in glossary.concepts:
        matched = [f for f in c.forms if _form_in(f, token_set, padded)]
        if matched:
            add_concept(c, matched)

    for tok in tokens:
        if tok in consumed or tok in STOPWORDS or len(tok) < 2:
            continue
        fuzzy = _fuzzy_concept(tok, glossary) if len(tok) >= FUZZY_MIN_LEN else None
        if fuzzy:
            concept, form = fuzzy
            add_concept(concept, [form])
            consumed.add(tok)
            continue
        origin = (tok, tok[:-1]) if tok.endswith(("s", "x")) and len(tok) > 3 else (tok,)
        plan.needs.append(Need(tok, origin, residual=True))
        consumed.add(tok)
    return plan


def _fuzzy_concept(token: str, glossary: Glossary) -> tuple[Concept, str] | None:
    best: tuple[float, Concept, str] | None = None
    for c in glossary.concepts:
        for form in c.forms:
            if " " in form or len(form) < FUZZY_MIN_LEN:
                continue
            score = dice(token, form)
            if score >= FUZZY_THRESHOLD and (best is None or score > best[0]):
                best = (score, c, form)
    return (best[1], best[2]) if best else None
