"""Language detection agent logic (kab / fr / en).

Deliberately small and transparent: script check + stopword/marker voting. It is a baseline to
be replaced by a trained identifier; the rest of the pipeline only needs a hint, and falls back
to ``und`` (undetermined) instead of guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .normalize import normalize, tokenize

_FR = ("un une des du de la le les l d et ou en dans sur pour par avec au aux ce cette ces "
       "est sont je tu il elle nous vous ils elles qui que quoi quel quelle quels quelles me "
       "moi mon ma mes cherche chercher cherchez trouve trouver veux voudrais existe donne "
       "donnez besoin svp plait ressource ressources fiche fiches propos").split()
_EN = ("a an the of for in on to from and or with is are there any i me my need looking find "
       "want show give about do you have some your please resource resources").split()
_KAB_STOP = "n d s i ar di deg ghef akked ad ur ma wi ta wa ula yella ulac".split()
_KAB_MARKERS = ("amawal adlis taqbaylit tamazight tasuqilt tasekla tamedyazt isefra ddwa").split()

_FR_SET = {normalize(w) for w in _FR}
_EN_SET = {normalize(w) for w in _EN}
_KAB_SET = {normalize(w) for w in _KAB_STOP}
_MARKERS = {normalize(w) for w in _KAB_MARKERS}

# Words shared by several languages carry no signal for detection.
_SHARED = (_FR_SET & _EN_SET) | (_FR_SET & _KAB_SET) | (_EN_SET & _KAB_SET)
STOPWORDS = frozenset(_FR_SET | _EN_SET | _KAB_SET)

_KAB_LETTERS = set("ɣɛḥṭẓṛṣḍčǧ")


@dataclass(frozen=True)
class Detection:
    lang: str  # "kab" | "fr" | "en" | "und"
    confidence: float
    script: str  # "latin" | "tifinagh"


def detect_language(text: str) -> Detection:
    if any("\u2d30" <= ch <= "\u2d7f" for ch in text):
        return Detection("kab", 1.0, "tifinagh")
    tokens = tokenize(text)
    scores = {
        "fr": sum(1.0 for t in tokens if t in _FR_SET - _SHARED),
        "en": sum(1.0 for t in tokens if t in _EN_SET - _SHARED),
        "kab": sum(2.0 for t in tokens if t in _MARKERS)
        + sum(0.5 for t in tokens if t in _KAB_SET - _SHARED)
        + (2.0 if _KAB_LETTERS & set(text.casefold()) else 0.0),
    }
    total = sum(scores.values())
    if total == 0:
        return Detection("und", 0.0, "latin")
    best = max(scores, key=lambda k: scores[k])
    return Detection(best, round(scores[best] / total, 2), "latin")
