"""Measured latency/retrieval/cost plus receipt-bound HUMAN fidelity annotations."""
from __future__ import annotations
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from .provenance import digest


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q*len(values))-1)]


def benchmark(service, questions, output_dir, use_llm=False, input_rate=None, output_rate=None,
              annotations=None, hourly_infra_cost=None):
    rows = [json.loads(line) for line in Path(questions).read_text(encoding='utf-8').splitlines() if line.strip()]
    ids = [r.get('id',str(i)) for i,r in enumerate(rows)]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate question IDs')
    if annotations and not Path(annotations).is_file():
        raise ValueError('Annotations file not found')
    labels = {}
    if annotations:
        for line in Path(annotations).read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            a = json.loads(line)
            if not isinstance(a.get('supported'), bool):
                raise ValueError('Human supported label must be boolean')
            key = (a['question_id'], a['response_receipt'], a['claim_index'])
            if key in labels:
                raise ValueError('Duplicate human annotation')
            labels[key] = a['supported']
    outputs, recalls, precisions, reciprocal_ranks, latencies = [], [], [], [], []
    lang = defaultdict(lambda: {'questions':0,'status_correct':0})
    checked = valid = abstentions = unanswerable = true_abstentions = 0
    inputs = outputs_tokens = 0
    token_usage_complete = True
    claims_count = annotated = supported = 0
    matched_labels = set()
    started = time.perf_counter()
    for qid,row in zip(ids,rows):
        result = service.ask(row['question'], use_llm)
        got = [r['citation']['fiche_id'] for r in result['results']]
        expected = set(row.get('expected_ids',[]))
        if expected:
            recalls.append(len(expected & set(got))/len(expected))
            precisions.append(len(expected & set(got))/len(got) if got else 0)
            reciprocal_ranks.append(next((1/i for i,f in enumerate(got,1) if f in expected),0))
        group = lang[row.get('lang','und')]
        group['questions'] += 1
        group['status_correct'] += result['status'] == row.get('status')
        checked += result['verification'].get('checked',0)
        valid += result['verification'].get('valid',0)
        abstentions += result['status'] == 'no_answer'
        if row.get('status') == 'no_answer':
            unanswerable += 1
            true_abstentions += result['status'] == 'no_answer'
        latencies.append(result['metrics']['latency_ms'])
        synthesis = result.get('synthesis')
        if use_llm and result['llm_status'] == 'failed_using_extractive_fallback':
            token_usage_complete = False
        if synthesis:
            usage = synthesis['usage']
            if usage['input_tokens'] is None or usage['output_tokens'] is None:
                token_usage_complete = False
            else:
                inputs += usage['input_tokens']
                outputs_tokens += usage['output_tokens']
            for i,claim in enumerate(synthesis['claims']):
                claims_count += 1
                key = (qid,result['response_receipt'],i)
                if key in labels:
                    annotated += 1
                    supported += labels[key]
                    matched_labels.add(key)
        outputs.append({'question_id':qid,'expected_ids':sorted(expected),'answer':result})
    duration = time.perf_counter()-started
    if set(labels)-matched_labels:
        raise ValueError('Stale or unmatched annotations: question, receipt or claim index differs')
    money = None
    if input_rate is not None and output_rate is not None and token_usage_complete:
        money = (inputs*input_rate + outputs_tokens*output_rate)/1_000_000
    report = {'questions':len(rows), 'catalog_fingerprint':digest([f.to_record() for f in service.orch.catalog]),
        'retrieval':service.mode, 'llm_requested':use_llm,
        'recall':statistics.mean(recalls) if recalls else None,
        'precision':statistics.mean(precisions) if precisions else None,
        'mrr':statistics.mean(reciprocal_ranks) if reciprocal_ranks else None,
        'citation_validity':valid/checked if checked else None,
        'abstention_rate':abstentions/len(rows) if rows else None,
        'abstention_on_unanswerable':true_abstentions/unanswerable if unanswerable else None,
        'latency_ms':{'mean':statistics.mean(latencies) if latencies else None,'p50':percentile(latencies,.5),'p95':percentile(latencies,.95)},
        'by_language':dict(lang), 'tokens':{'input':inputs,'output':outputs_tokens,'complete':token_usage_complete},
        'estimated_token_cost':money, 'estimated_infrastructure_cost':duration*hourly_infra_cost/3600 if hourly_infra_cost is not None else None,
        'cost_note':'Currency follows supplied rates. Infrastructure estimate excludes startup/model download. Null means not priced.',
        'fidelity':{'generated_claims':claims_count,'human_annotated':annotated,
                    'annotation_coverage':annotated/claims_count if claims_count else None,
                    'human_supported_rate':supported/annotated if annotated else None},
        'notice':'Scores concern this dataset only; technical citation validity is not semantic fidelity.'}
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty report directory')
    output.mkdir(parents=True,exist_ok=True)
    (output/'responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in outputs),encoding='utf-8')
    (output/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def score_saved_fidelity(responses_file, annotations_file):
    """Annotate a saved run without rerunning an LLM or incurring another inference cost."""
    valid_claims = set()
    for line in Path(responses_file).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        answer = row['answer']
        for i,_ in enumerate((answer.get('synthesis') or {}).get('claims',[])):
            valid_claims.add((row['question_id'],answer['response_receipt'],i))
    scored = {}
    for line in Path(annotations_file).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        key = (row['question_id'],row['response_receipt'],row['claim_index'])
        if key not in valid_claims or key in scored or not isinstance(row.get('supported'),bool):
            raise ValueError('Invalid, duplicate or stale annotation')
        scored[key] = row['supported']
    return {'generated_claims':len(valid_claims),'human_annotated':len(scored),
            'annotation_coverage':len(scored)/len(valid_claims) if valid_claims else None,
            'human_supported_rate':sum(scored.values())/len(scored) if scored else None}
