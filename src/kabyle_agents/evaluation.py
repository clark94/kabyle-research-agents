"""Evaluation harness: retrieval quality, honesty and citation validity on a labelled set."""

from __future__ import annotations

import json
from pathlib import Path

from .orchestrator import Orchestrator


def run_eval(orch: Orchestrator, questions_path: str | Path) -> dict:
    rows = [json.loads(line) for line in Path(questions_path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    lang_ok = lang_n = status_ok = recall_n = unans = unans_ok = hallucinated = 0
    recall_sum = 0.0
    cited = cited_valid = 0
    failures = []
    for row in rows:
        ans = orch.ask(row["question"])
        got_ids = [r.citation.fiche_id for r in ans.results]
        if "lang" in row:
            lang_n += 1
            lang_ok += ans.query_language == row["lang"]
        status_ok += ans.status == row["status"]
        if ans.status != row["status"]:
            failures.append((row["question"], row["status"], ans.status))
        if row["status"] == "no_answer":
            unans += 1
            unans_ok += ans.status == "no_answer"
            hallucinated += len(got_ids)
        elif row.get("expected_ids"):
            recall_n += 1
            recall_sum += len(set(row["expected_ids"]) & set(got_ids)) / len(row["expected_ids"])
        cited += ans.verification.get("checked", 0)
        cited_valid += ans.verification.get("valid", 0)
    n = len(rows)
    return {
        "questions": n,
        "language_accuracy": lang_ok / lang_n if lang_n else None,
        "status_accuracy": status_ok / n if n else None,
        "recall": recall_sum / recall_n if recall_n else None,
        "abstention_rate_on_unanswerable": unans_ok / unans if unans else None,
        "results_on_unanswerable": hallucinated,
        "citation_validity": cited_valid / cited if cited else None,
        "failures": failures,
    }
