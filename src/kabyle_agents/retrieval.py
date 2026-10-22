"""Lexical retrieval (BM25) with need-coverage gating.

Ranking alone cannot tell "best of a bad lot" from "a real answer", so each fiche also gets a
*coverage*: the share of the question's needs it satisfies. Coverage decides whether we answer,
answer partially, or abstain. Dense multilingual retrieval can later be fused here, but the
coverage gate must stay: it is what makes the system refuse instead of improvise.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, replace

from .lang import STOPWORDS
from .models import Fiche
from .normalize import dice, tokenize
from .query import Need, QueryPlan

K1, B = 1.5, 0.75
ORIGIN_WEIGHT, EXPANDED_WEIGHT = 1.0, 0.6
FUZZY_THRESHOLD, FUZZY_MIN_LEN = 0.8, 5


@dataclass(frozen=True)
class Hit:
    fiche: Fiche
    score: float
    coverage: float
    matched: tuple[str, ...]
    unmatched: tuple[str, ...]


@dataclass
class _Doc:
    fiche: Fiche
    tf: Counter
    tokens: frozenset[str]
    padded: str
    length: int


class Index:
    def __init__(self, fiches: list[Fiche]):
        self.docs: list[_Doc] = []
        df: Counter = Counter()
        for f in fiches:
            title, kw = tokenize(f.title), [t for k in f.keywords for t in tokenize(k)]
            plain = title + kw + tokenize(f.type) + tokenize(f.description)
            weighted = title * 3 + kw * 2 + plain
            doc = _Doc(f, Counter(weighted), frozenset(plain), " " + " ".join(plain) + " ", len(weighted))
            self.docs.append(doc)
            df.update(doc.tf.keys())
        self.df = df
        self.n = len(self.docs)
        self.avgdl = sum(d.length for d in self.docs) / self.n if self.n else 0.0
        self.vocab = {t for t in df if t not in STOPWORDS}

    def _idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        return math.log(1 + (self.n - n + 0.5) / (n + 0.5))

    def _with_fuzzy(self, need: Need) -> Need:
        """Residual words unknown to the catalog may be spelling variants of indexed words."""
        if not need.residual or any(f in self.vocab for f in need.forms):
            return need
        word = need.origin[0]
        if len(word) < FUZZY_MIN_LEN:
            return need
        near = tuple(sorted(t for t in self.vocab if dice(word, t) >= FUZZY_THRESHOLD))
        return replace(need, expanded=near)

    def search(self, plan: QueryPlan, top_k: int = 5, validated_only: bool = True) -> list[Hit]:
        needs = [self._with_fuzzy(n) for n in plan.needs]
        if not needs or not self.n:
            return []
        weights: dict[str, float] = {}
        for need in needs:
            for forms, w in ((need.origin, ORIGIN_WEIGHT), (need.expanded, EXPANDED_WEIGHT)):
                for form in forms:
                    for term in form.split():
                        weights[term] = max(weights.get(term, 0.0), w)

        hits: list[Hit] = []
        for d in self.docs:
            if validated_only and not d.fiche.validated:
                continue
            ok = [n for n in needs if n.satisfied_by(d.tokens, d.padded)]
            if not ok:
                continue
            score = 0.0
            for term, w in weights.items():
                tf = d.tf.get(term, 0)
                if tf:
                    norm = tf + K1 * (1 - B + B * d.length / self.avgdl)
                    score += w * self._idf(term) * tf * (K1 + 1) / norm
            hits.append(
                Hit(
                    d.fiche,
                    round(score, 4),
                    len(ok) / len(needs),
                    tuple(n.label for n in ok),
                    tuple(n.label for n in needs if n not in ok),
                )
            )
        hits.sort(key=lambda h: (-h.coverage, -h.score, h.fiche.id))
        return hits[:top_k]
