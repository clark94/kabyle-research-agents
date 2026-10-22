"""Shared application layer used by the web UI, MCP, A2A and evaluation."""
from __future__ import annotations

import os
import json
import time
from dataclasses import asdict
from pathlib import Path
from threading import RLock
from .orchestrator import Orchestrator
from .provenance import digest


class ResearchService:
    def __init__(self, catalog=None, glossary=None, mode=None, encoder=None):
        self.catalog_path = Path(catalog or os.getenv('KABYLE_CATALOG', 'data/catalog.demo.jsonl'))
        self.mode = mode or os.getenv('KABYLE_RETRIEVAL', 'lexical')
        if self.mode not in ('lexical', 'semantic', 'hybrid'):
            raise ValueError('KABYLE_RETRIEVAL must be lexical, semantic or hybrid')
        self.orch = Orchestrator.from_files(self.catalog_path, glossary or os.getenv('KABYLE_GLOSSARY', 'data/glossary.json'))
        self.attestations_checked = 0
        if os.getenv('KABYLE_REQUIRE_ATTESTATIONS', '0') == '1':
            from .identity import verify_credential
            from .catalog import Catalog
            from .retrieval import Index
            tokens = json.loads(Path(os.environ['KABYLE_ATTESTATIONS_FILE']).read_text(encoding='utf-8'))
            trusted = [x.strip() for x in os.environ['KABYLE_TRUSTED_ISSUERS'].split(',') if x.strip()]
            kept = []
            for fiche in self.orch.catalog:
                token = tokens.get(fiche.id)
                if not token:
                    continue
                for issuer in trusted:
                    try:
                        vc = verify_credential(token, issuer, fiche.content_hash)
                        if vc['credentialSubject']['id'] != 'urn:fiche:'+fiche.id:
                            continue
                    except Exception:
                        continue
                    kept.append(fiche)
                    break
            self.orch.catalog = Catalog(kept)
            self.orch.index = Index(kept)
            self.attestations_checked = len(kept)
        self.lock = RLock()
        if self.mode != 'lexical':
            from .semantic import HybridIndex
            self.orch.index = HybridIndex(list(self.orch.catalog),
                os.getenv('KABYLE_EMBED_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
                self.mode, float(os.getenv('KABYLE_SEMANTIC_THRESHOLD', '0.60')), encoder)

    def info(self):
        fiches = list(self.orch.catalog)
        return {'source_records': self.orch.report.total, 'catalog_size': len(fiches), 'validated': sum(f.validated for f in fiches),
                'demo_records': sum(f.id.startswith('demo-') or f.title.startswith('[DEMO]') for f in fiches),
                'attestations_accepted': self.attestations_checked,
                'attestations_required': os.getenv('KABYLE_REQUIRE_ATTESTATIONS', '0') == '1',
                'retrieval': self.mode, 'llm_available': os.getenv('KABYLE_LLM_ENABLED', '0') == '1',
                'protocols': {'mcp': 'SDK 1.x, separate process', 'a2a': 'SDK 0.3.22, separate process'},
                'quarantined': len(self.orch.report.quarantined), 'tampered': len(self.orch.report.tampered)}

    def get_fiche(self, fiche_id):
        fiche = self.orch.catalog.get(fiche_id)
        return dict(fiche.to_record(), content_hash=fiche.content_hash) if fiche and fiche.validated else None

    def ask(self, question, use_llm=False):
        if not isinstance(question, str) or not question.strip() or len(question) > 2000:
            raise ValueError('Question required, at most 2000 characters')
        started = time.perf_counter()
        with self.lock:
            answer = asdict(self.orch.ask(question))
        answer['retrieval'] = self.mode
        answer['synthesis'] = None
        answer['llm_status'] = 'not_requested'
        if use_llm:
            if os.getenv('KABYLE_LLM_ENABLED', '0') != '1':
                raise ValueError('LLM disabled: set KABYLE_LLM_ENABLED=1 and configure Ollama or OpenAI')
            if answer['results']:
                from .llm import make_composer
                sources = [self.get_fiche(r['citation']['fiche_id']) for r in answer['results']]
                composer = None
                try:
                    composer = make_composer()
                    answer['synthesis'] = composer.compose(question, sources)
                    answer['llm_status'] = 'generated_unreviewed'
                except Exception:
                    answer['llm_status'] = 'failed_using_extractive_fallback'
                finally:
                    if composer is not None:
                        composer.close()
            else:
                answer['llm_status'] = 'skipped_no_sources'
        answer['metrics'] = {'latency_ms': round((time.perf_counter()-started)*1000, 3)}
        answer['response_receipt'] = digest({'extractive_receipt': answer['receipt'],
                                            'synthesis': answer['synthesis'], 'retrieval': self.mode})
        return answer
