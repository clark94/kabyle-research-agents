"""Command line interface: ask, audit, stamp, eval, agents."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .catalog import load_catalog, stamp_file
from .evaluation import run_eval
from .models import Answer
from .orchestrator import Orchestrator
from .protocols import agent_cards

DEFAULT_CATALOG = "data/catalog.demo.jsonl"
DEFAULT_GLOSSARY = "data/glossary.json"
DEFAULT_QUESTIONS = "eval/questions.jsonl"


def _render(ans: Answer, show_trace: bool) -> str:
    lines = [f"Question : {ans.question}",
             f"Langue   : {ans.query_language}  |  Statut : {ans.status}", "", ans.message]
    for i, r in enumerate(ans.results, 1):
        c = r.citation
        lines += ["", f"{i}. {r.title}  [{r.type}]",
                  f"   Source   : {c.url}",
                  f"   Empreinte: {c.content_hash}",
                  f"   Licence  : {c.license}",
                  f"   Extrait  : « {c.quote}{'…' if c.truncated else ''} »"]
        if r.missing:
            lines.append(f"   Manque   : {', '.join(r.missing)}")
    v = ans.verification
    lines += ["", f"Vérification : {v.get('valid', 0)}/{v.get('checked', 0)} citations valides"
                  f"  |  reçu {ans.receipt[:19]}…"]
    if show_trace:
        lines += ["", "Trace :"] + [f"  - {s['agent']:<9} {s['summary']}  ({s['ms']} ms)" for s in ans.trace]
    return "\n".join(lines)


def _orchestrator(args: argparse.Namespace) -> Orchestrator:
    return Orchestrator.from_files(args.catalog, args.glossary)


def cmd_ask(args: argparse.Namespace) -> int:
    ans = _orchestrator(args).ask(args.question)
    print(json.dumps(asdict(ans), ensure_ascii=False, indent=2) if args.json
          else _render(ans, args.trace))
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    _, rep = load_catalog(args.catalog)
    print(f"{rep.accepted}/{rep.total} fiches acceptées")
    for fid, reasons in rep.quarantined.items():
        print(f"  QUARANTAINE {fid}: {'; '.join(reasons)}")
    for fid in rep.tampered:
        print(f"  ALTÉRÉE     {fid}: l'empreinte ne correspond pas au contenu")
    for fid in rep.unstamped:
        print(f"  SANS EMPREINTE {fid}: lancez `stamp`")
    return 0 if rep.clean else 1


def cmd_stamp(args: argparse.Namespace) -> int:
    n = stamp_file(args.catalog, force=args.force)
    print(f"{n} empreinte(s) écrite(s) dans {args.catalog}")
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    m = run_eval(_orchestrator(args), args.questions)
    failures = m.pop("failures")
    for k, v in m.items():
        print(f"{k:<34} {v:.3f}" if isinstance(v, float) else f"{k:<34} {v}")
    for q, exp, got in failures:
        print(f"ÉCHEC : {q!r} attendu={exp} obtenu={got}")
    return 1 if failures or m["citation_validity"] not in (None, 1.0) else 0


def cmd_agents(args: argparse.Namespace) -> int:
    print(json.dumps(agent_cards(_orchestrator(args).agents), ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="kabyle-agents", description=__doc__)
    p.add_argument("--catalog", default=DEFAULT_CATALOG)
    p.add_argument("--glossary", default=DEFAULT_GLOSSARY)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ask", help="poser une question")
    a.add_argument("question")
    a.add_argument("--json", action="store_true")
    a.add_argument("--trace", action="store_true", help="afficher le travail de chaque agent")
    a.set_defaults(fn=cmd_ask)
    sub.add_parser("audit", help="intégrité + sécurité du catalogue").set_defaults(fn=cmd_audit)
    s = sub.add_parser("stamp", help="écrire les empreintes content_hash")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_stamp)
    e = sub.add_parser("eval", help="évaluer sur un jeu de questions")
    e.add_argument("--questions", default=DEFAULT_QUESTIONS)
    e.set_defaults(fn=cmd_eval)
    sub.add_parser("agents", help="cartes descriptives des agents").set_defaults(fn=cmd_agents)
    args = p.parse_args(argv)
    if not Path(args.catalog).exists():
        print(f"Catalogue introuvable : {args.catalog}", file=sys.stderr)
        return 2
    return args.fn(args)
