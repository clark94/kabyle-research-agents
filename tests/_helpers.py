from pathlib import Path

from kabyle_agents.orchestrator import Orchestrator

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "catalog.demo.jsonl"
GLOSSARY = ROOT / "data" / "glossary.json"
QUESTIONS = ROOT / "eval" / "questions.jsonl"


def make_orchestrator() -> Orchestrator:
    return Orchestrator.from_files(CATALOG, GLOSSARY)
