"""Real dense embeddings + reciprocal rank fusion; no model loaded in lexical mode."""
from __future__ import annotations

import math
from .retrieval import Hit, Index


def cosine(a, b):
    norm = math.sqrt(sum(float(v)**2 for v in a) * sum(float(v)**2 for v in b))
    return sum(float(x)*float(y) for x, y in zip(a, b)) / norm if norm else 0.0


class HybridIndex(Index):
    def __init__(self, fiches, model_name, mode='hybrid', threshold=0.60, encoder=None):
        super().__init__(fiches)
        if encoder is None:
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(model_name)
        self.encoder, self.mode, self.threshold = encoder, mode, threshold
        self.vectors = self.encoder.encode(
            [f'{d.fiche.title}. {d.fiche.description}. {", ".join(d.fiche.keywords)}' for d in self.docs],
            normalize_embeddings=True,
        ) if self.docs else []

    def search(self, plan, top_k=5, validated_only=True):
        if not plan.needs or not self.docs:
            return []
        lexical = super().search(plan, top_k=len(self.docs), validated_only=validated_only)
        lexical_by_id = {h.fiche.id: h for h in lexical}
        # Each semantic need is evaluated separately so that dense retrieval cannot silently
        # erase a constraint. Threshold is experimental and must be calibrated on held-out data.
        vectors = self.encoder.encode([' / '.join(n.forms) for n in plan.needs], normalize_embeddings=True)
        dense = []
        for d, vec in zip(self.docs, self.vectors):
            if validated_only and not d.fiche.validated:
                continue
            scores = [cosine(v, vec) for v in vectors]
            matched = [n.label for n, score in zip(plan.needs, scores) if score >= self.threshold]
            lex = lexical_by_id.get(d.fiche.id)
            if self.mode == 'hybrid' and lex:
                matched = list(dict.fromkeys(matched + list(lex.matched)))
            if matched:
                dense.append(Hit(d.fiche, sum(scores)/len(scores), len(matched)/len(plan.needs),
                                 tuple(matched), tuple(n.label for n in plan.needs if n.label not in matched)))
        dense.sort(key=lambda h: (-h.score, h.fiche.id))
        if self.mode == 'semantic':
            return sorted(dense, key=lambda h: (-h.coverage, -h.score, h.fiche.id))[:top_k]
        ranks = {h.fiche.id: 1/(60+i) for i, h in enumerate(lexical, 1)}
        for i, h in enumerate(dense, 1):
            ranks[h.fiche.id] = ranks.get(h.fiche.id, 0) + 1/(60+i)
        pool = dict(lexical_by_id)
        for h in dense:
            pool[h.fiche.id] = h
        fused = [Hit(h.fiche, ranks[fid], h.coverage, h.matched, h.unmatched) for fid, h in pool.items()]
        return sorted(fused, key=lambda h: (-h.coverage, -h.score, h.fiche.id))[:top_k]
