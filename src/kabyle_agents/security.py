"""Defence against prompt injection hidden in indexed documents.

Catalog text is *data*. Before indexing, every field is scanned for (a) invisible characters
that can smuggle instructions past a human reviewer and (b) instruction-like phrases. Matches
are quarantined for human review, never indexed. Heuristics reduce risk; they do not replace
the architectural rule that retrieved text is never executed as instructions.
"""

from __future__ import annotations

import re
import unicodedata

_INVISIBLE = re.compile(
    "[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff\U000e0000-\U000e007f]"
)
_PATTERNS = {
    "override-instructions": re.compile(
        r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all)\b"
        r".{0,30}\b(instructions?|prompts?|rules)\b",
        re.I,
    ),
    "override-instructions-fr": re.compile(
        r"\b(ignore[zr]?|oublie[zr]?|neglige[zr]?)\b.{0,30}\b(instructions?|consignes?|regles?)\b",
        re.I,
    ),
    "role-hijack": re.compile(r"\byou\s+are\s+now\b|\btu\s+es\s+maintenant\b", re.I),
    "system-prompt": re.compile(r"\bsystem\s+prompt\b|\bprompt\s+systeme\b", re.I),
    "markup-injection": re.compile(r"<\s*/?\s*(system|assistant|script|instructions?)\b", re.I),
    "exfiltration": re.compile(
        r"\b(reveal|print|show|revele)\b.{0,20}\b(secret|api\s*key|password|mot\s+de\s+passe)\b",
        re.I,
    ),
}


def is_invisible(ch: str) -> bool:
    return bool(_INVISIBLE.fullmatch(ch))


def scan_text(text: str) -> list[str]:
    reasons = []
    if _INVISIBLE.search(text):
        reasons.append("hidden-characters")
    clean = _INVISIBLE.sub("", unicodedata.normalize("NFKC", text))
    clean = "".join(c for c in unicodedata.normalize("NFD", clean) if unicodedata.category(c) != "Mn")
    reasons += [name for name, rx in _PATTERNS.items() if rx.search(clean)]
    return reasons


def scan_record(record: dict) -> list[str]:
    reasons = []
    for key, value in record.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, str):
                reasons += [f"{key}: {r}" for r in scan_text(item)]
    return reasons
