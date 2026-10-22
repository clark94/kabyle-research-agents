#!/usr/bin/env python3
"""Aides OpenAI pour préparer l'évaluation du projet (questions, comparaison de modèles, pré-jugement).

La clé n'est JAMAIS écrite dans ce fichier : elle est lue dans la variable d'environnement OPENAI_API_KEY.
    PowerShell : $env:OPENAI_API_KEY = "sk-..."

Trois sous-commandes (depuis la racine du dépôt) :
  draft-questions  propose des questions fr/en/kab à relire à partir d'un corpus
  compare-models   mesure citations valides, repli, latence, jetons et coût par modèle
  prejudge         suggère si chaque affirmation découle de sa source (à CONFIRMER par un humain)

Limites : ce sont des brouillons. Les questions générées à partir d'une fiche sont biaisées et le kabyle
produit par un LLM est peu fiable : relecture humaine obligatoire. Les suggestions du juge LLM ne
remplacent pas l'annotation humaine ; elles laissent `supported` à null pour forcer cette étape.
Les fiches sont envoyées à un service tiers : n'utiliser que des données partageables.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def chat_json(model, system, user, max_tokens=1200):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        sys.exit('OPENAI_API_KEY non défini. PowerShell : $env:OPENAI_API_KEY = "sk-..."')
    base = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    payload = {'model': model, 'response_format': {'type': 'json_object'},
               'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}
    if model.lower().startswith(('gpt-5', 'o1', 'o3', 'o4')):  # modèles récents : autre paramètre, budget plus large
        payload['max_completion_tokens'] = max(max_tokens * 5, 4000)
    else:
        payload['max_tokens'] = max_tokens
    body = json.dumps(payload).encode()
    req = urllib.request.Request(base + '/chat/completions', data=body,
                                 headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit('Erreur API %s : %s' % (e.code, e.read().decode('utf-8', 'replace')[:300]))
    return json.loads(raw['choices'][0]['message']['content']), raw.get('usage') or {}


def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')


# ---------------------------------------------------------------- draft-questions
DRAFT_SYSTEM = ('You write realistic search questions for a catalog of Kabyle-language resources. '
                'Given one catalog record, write ONE question per requested language, as a real user would type it, '
                'WITHOUT copying the record title. Return JSON {"questions": {"<lang>": "<question>"}}. '
                'Language codes: fr=French, en=English, kab=Kabyle (Latin script).')


def draft_questions(a):
    fiches = read_jsonl(a.corpus)[:a.limit]
    langs = [x.strip() for x in a.langs.split(',')]
    rows = []
    for f in fiches:
        user = json.dumps({'languages': langs, 'title': f['title'], 'type': f.get('type'),
                           'description': f['description'], 'keywords': f.get('keywords', [])}, ensure_ascii=False)
        out, _ = chat_json(a.model, DRAFT_SYSTEM, user)
        for lang in langs:
            q = (out.get('questions') or {}).get(lang)
            if isinstance(q, str) and q.strip():
                rows.append({'id': '%s-%s' % (f['id'], lang), 'question': q.strip(), 'lang': lang,
                             'status': 'answered', 'expected_ids': [f['id']], 'review': 'TO_REVIEW'})
    write_jsonl(a.out, rows)
    print('%d questions écrites dans %s. À relire une par une (surtout le kabyle) avant usage ; '
          'retirez le champ "review" une fois validées.' % (len(rows), a.out))


# ---------------------------------------------------------------- compare-models
def parse_rates(items):
    rates = {}
    for it in items or []:
        name, _, val = it.partition('=')
        i, _, o = val.partition(':')
        rates[name] = (float(i), float(o))
    return rates


def compare_models(a):
    os.environ.update({'KABYLE_LLM_ENABLED': '1', 'KABYLE_LLM_PROVIDER': 'openai'})
    from kabyle_agents.service import ResearchService
    questions = [q for q in read_jsonl(a.questions) if q.get('status', 'answered') == 'answered']
    rates = parse_rates(a.rate)
    summary = {}
    out_dir = Path(a.out)
    for model in [m.strip() for m in a.models.split(',')]:
        os.environ['OPENAI_MODEL'] = model
        service = ResearchService(catalog=a.catalog)
        counts, lat, tin, tout, claims_rows = {}, [], 0, 0, []
        for i, q in enumerate(questions):
            qid = q.get('id', str(i))
            t0 = time.perf_counter()
            ans = service.ask(q['question'], use_llm=True)
            lat.append((time.perf_counter() - t0) * 1000)
            status = ans['llm_status']
            counts[status] = counts.get(status, 0) + 1
            syn = ans.get('synthesis')
            if syn:
                tin += syn['usage'].get('input_tokens') or 0
                tout += syn['usage'].get('output_tokens') or 0
                for j, c in enumerate(syn['claims']):
                    src = service.get_fiche(c['fiche_id'])
                    claims_rows.append({'question_id': qid, 'response_receipt': ans['response_receipt'], 'claim_index': j,
                                        'text': c['text'], 'quote': c['quote'], 'fiche_id': c['fiche_id'],
                                        'source_description': src['description'] if src else None})
        n = len(questions)
        r = rates.get(model)
        summary[model] = {'questions': n, 'llm_status': counts,
                          'generated_rate': round(counts.get('generated_unreviewed', 0) / n, 3) if n else None,
                          'latency_ms_mean': round(sum(lat) / n, 1) if n else None,
                          'input_tokens': tin, 'output_tokens': tout, 'claims': len(claims_rows),
                          'cost_usd_estimate': round((tin * r[0] + tout * r[1]) / 1e6, 4) if r else None}
        write_jsonl(out_dir / ('responses.%s.jsonl' % model.replace('/', '_')), claims_rows)
    (out_dir / 'comparison.json').parent.mkdir(parents=True, exist_ok=True)
    (out_dir / 'comparison.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Coût = null si aucun tarif fourni (--rate MODELE=entree:sortie, USD par million de jetons).')


# ---------------------------------------------------------------- prejudge
JUDGE_SYSTEM = ('You check whether a statement follows from a source description ALONE. '
                'Return JSON {"supported": true|false, "reason": "one short sentence"}. '
                'Be strict: extra details not in the source mean false.')


def prejudge(a):
    rows = read_jsonl(a.responses)
    out = []
    for r in rows:
        if not r.get('source_description'):
            continue
        verdict, _ = chat_json(a.model, JUDGE_SYSTEM, json.dumps(
            {'source': r['source_description'], 'statement': r['text']}, ensure_ascii=False), 200)
        out.append({'question_id': r['question_id'], 'response_receipt': r['response_receipt'],
                    'claim_index': r['claim_index'], 'supported': None,
                    'llm_suggestion': bool(verdict.get('supported')), 'llm_reason': verdict.get('reason', ''),
                    'text': r['text']})
    write_jsonl(a.out, out)
    print('%d suggestions écrites dans %s. Remplacez "supported": null par true/false après relecture '
          'humaine, puis passez le fichier à la commande benchmark (--annotations).' % (len(out), a.out))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('draft-questions')
    d.add_argument('--corpus', default='data/catalog.demo.jsonl')
    d.add_argument('--out', default='reports/openai/questions.draft.jsonl')
    d.add_argument('--model', default='gpt-4o-mini')
    d.add_argument('--langs', default='fr,en,kab')
    d.add_argument('--limit', type=int, default=50)
    d.set_defaults(fn=draft_questions)
    c = sub.add_parser('compare-models')
    c.add_argument('--models', default='gpt-4o-mini', help='liste séparée par des virgules')
    c.add_argument('--catalog', default='data/catalog.demo.jsonl')
    c.add_argument('--questions', default='eval/questions.jsonl')
    c.add_argument('--out', default='reports/openai')
    c.add_argument('--rate', action='append', help='MODELE=entree:sortie (USD / million de jetons), répétable')
    c.set_defaults(fn=compare_models)
    j = sub.add_parser('prejudge')
    j.add_argument('--responses', required=True, help='fichier responses.<modele>.jsonl de compare-models')
    j.add_argument('--out', default='reports/openai/annotations.to_review.jsonl')
    j.add_argument('--model', default='gpt-4o-mini')
    j.set_defaults(fn=prejudge)
    a = p.parse_args()
    a.fn(a)


if __name__ == '__main__':
    main()