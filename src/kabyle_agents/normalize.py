"""Orthographic normalization for Kabyle, French and English search keys.

Kabyle is written in several ways (Latin with special letters, ASCII approximations such as
``3`` for ``ɛ`` or ``gh`` for ``ɣ``, and Tifinagh). Everything is folded into one lossy,
ASCII-like key used *only for matching*. Displayed text is never altered.
"""

from __future__ import annotations

import re
import unicodedata

# Neo-Tifinagh -> Latin key. Emphatic/pharyngeal letters are folded onto their plain
# counterparts, exactly like the diacritics stripped below, so both scripts meet in one key.
_TIFINAGH = {
    "ⴰ": "a", "ⴱ": "b", "ⴳ": "g", "ⴷ": "d", "ⴹ": "d", "ⴻ": "e", "ⴼ": "f", "ⴽ": "k",
    "ⵀ": "h", "ⵃ": "h", "ⵄ": "3", "ⵅ": "x", "ⵇ": "q", "ⵉ": "i", "ⵊ": "j", "ⵍ": "l",
    "ⵎ": "m", "ⵏ": "n", "ⵓ": "u", "ⵔ": "r", "ⵕ": "r", "ⵖ": "gh", "ⵙ": "s", "ⵚ": "s",
    "ⵛ": "c", "ⵜ": "t", "ⵟ": "t", "ⵡ": "w", "ⵢ": "y", "ⵣ": "z", "ⵥ": "z", "ⵯ": "",
}
_SPECIAL = {
    "ɣ": "gh", "γ": "gh", "ɛ": "3", "ε": "3", "ʕ": "3", "œ": "oe", "æ": "ae",
    "’": " ", "'": " ", "ʼ": " ", "-": " ", "‑": " ", "_": " ",
}
_TABLE = str.maketrans({**_TIFINAGH, **_SPECIAL})
_TOKEN = re.compile(r"\w+", re.UNICODE)


def normalize(text: str) -> str:
    """Lowercase, fold scripts and variants, strip diacritics."""
    text = unicodedata.normalize("NFKC", text).casefold().translate(_TABLE)
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", text)


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(normalize(text))


def trigrams(word: str) -> set[str]:
    w = f"^{word}$"
    return {w[i : i + 3] for i in range(len(w) - 2)}


def dice(a: str, b: str) -> float:
    """Character-trigram Dice similarity, used to tolerate non-standard spellings."""
    ta, tb = trigrams(a), trigrams(b)
    if not ta or not tb:
        return 0.0
    return 2 * len(ta & tb) / (len(ta) + len(tb))
