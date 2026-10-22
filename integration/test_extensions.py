import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient
from kabyle_agents.service import ResearchService
from kabyle_agents.web import create_app
from kabyle_agents.llm import OllamaComposer, validate_claims
from kabyle_agents.identity import create_key, load_key, resolve, issue_credential, verify_credential
from kabyle_agents.web3 import raw_cid, IPFSClient, prepare_registration
from kabyle_agents.importer import import_catalog
from kabyle_agents.benchmark import benchmark

ROOT = Path(__file__).resolve().parents[1]


def service():
    return ResearchService(ROOT/'data/catalog.demo.jsonl',ROOT/'data/glossary.json',mode='lexical')


def test_web_search_and_validation():
    client = TestClient(create_app(service()))
    assert client.get('/').status_code == 200
    assert client.get('/static/app.js').status_code == 200
    assert client.get('/api/status').json()['source_records'] == 12
    assert client.get('/api/status').json()['demo_records'] == 10
    answer = client.post('/api/ask',json={'question':'amawal n ddwa'}).json()
    assert answer['results'][0]['citation']['fiche_id'] == 'demo-001'
    assert answer['response_receipt'].startswith('sha256:')
    assert client.post('/api/ask',json={'question':''}).status_code == 422
    assert client.get('/api/fiches/does-not-exist').status_code == 404
    with patch.dict(os.environ,{'KABYLE_LLM_ENABLED':'0'}):
        assert client.post('/api/ask',json={'question':'amawal n ddwa','use_llm':True}).status_code == 400


def test_llm_http_and_forged_quote():
    sources = [{'id':'s1','description':'Une ressource consacrée à la médecine.'}]
    claim = {'text':'Ressource médicale.','fiche_id':'s1','quote':'consacrée à la médecine'}
    def respond(request):
        body = json.loads(request.content)
        assert body['stream'] is False
        return httpx.Response(200,json={'message':{'content':json.dumps({'claims':[claim]})},'prompt_eval_count':30,'eval_count':10})
    composer = OllamaComposer(client=httpx.Client(transport=httpx.MockTransport(respond)))
    result = composer.compose('médecine',sources)
    assert result['usage']['input_tokens'] == 30
    assert result['semantic_fidelity'] == 'requires_human_review'
    with pytest.raises(ValueError):
        validate_claims({'claims':[dict(claim,quote='texte inventé')]},sources)
    with pytest.raises(ValueError):
        validate_claims({'claims':[dict(claim,fiche_id='unknown')]},sources)


def test_service_llm_fallback():
    with patch.dict(os.environ,{'KABYLE_LLM_ENABLED':'1'}),patch('kabyle_agents.llm.OllamaComposer.compose',side_effect=ValueError('bad JSON')):
        answer = service().ask('amawal n ddwa',True)
        assert answer['llm_status'] == 'failed_using_extractive_fallback'
        assert answer['results']
        assert answer['synthesis'] is None


def test_did_vc_signature_tamper_and_trust(tmp_path):
    keyfile = tmp_path/'issuer.pem'
    did = create_key(keyfile)
    assert did.startswith('did:key:z6Mk')
    assert resolve(did)[1]['id'] == did
    token = issue_credential(load_key(keyfile),'urn:fiche:001','sha256:abc')
    assert verify_credential(token,did,'sha256:abc')['credentialSubject']['id'] == 'urn:fiche:001'
    with pytest.raises(ValueError):
        verify_credential(token,did,'sha256:wrong')
    other = create_key(tmp_path/'other.pem')
    with pytest.raises(Exception):
        verify_credential(token,other)
    with pytest.raises(FileExistsError):
        create_key(keyfile)
    pieces = token.split('.')
    pieces[1] = pieces[1][:-2]+'xx'
    with pytest.raises(Exception):
        verify_credential('.'.join(pieces),did)


def test_ipfs_exact_cid_roundtrip_mock():
    from kabyle_agents.provenance import canonical_json
    data = canonical_json({'id':'r1','title':'test'})
    cid = raw_cid(data)
    assert cid.startswith('bafkrei')
    def respond(request):
        if request.url.path.endswith('/add'):
            return httpx.Response(200,json={'Hash':cid})
        return httpx.Response(200,content=data)
    client = IPFSClient(client=httpx.Client(transport=httpx.MockTransport(respond)))
    assert client.publish({'id':'r1','title':'test'})['cid'] == cid
    assert client.fetch(cid) == data
    with pytest.raises(ValueError):
        client.fetch(raw_cid(b'other'))


def test_erc8004_abi_transaction_no_broadcast():
    tx = prepare_registration('0x'+'11'*20,'0x'+'22'*20,'ipfs://bafkrei-example')
    assert tx['chainId'] == 11155111 and tx['data'].startswith('0x')
    assert tx['status'] == 'unsigned_not_broadcast'
    with pytest.raises(ValueError):
        prepare_registration(tx['from'],tx['to'],'https://example.org',chain_id=1)


def test_import_requires_review_and_rejects_duplicate(tmp_path):
    source = tmp_path/'clean.jsonl'
    source.write_text(''.join(json.dumps(f.to_record())+'\n' for f in service().orch.catalog),encoding='utf-8')
    target = tmp_path/'imported.jsonl'
    result = import_catalog(source,target)
    assert result['records'] == 10
    assert all(not json.loads(line)['validated'] for line in target.read_text().splitlines())
    with pytest.raises(ValueError):
        import_catalog(source,target)
    dup = tmp_path/'duplicate.jsonl'
    row = source.read_text().splitlines()[0]
    dup.write_text(row+'\n'+row+'\n')
    with pytest.raises(ValueError):
        import_catalog(dup,tmp_path/'bad.jsonl')


def test_benchmark_measured_no_fake_fidelity(tmp_path):
    report = benchmark(service(),ROOT/'eval/questions.jsonl',tmp_path/'run')
    assert report['questions'] == 17
    assert report['recall'] == 1
    assert report['latency_ms']['p95'] >= 0
    assert report['estimated_token_cost'] is None
    assert report['fidelity']['human_supported_rate'] is None


def test_dense_retrieval_uses_real_encoder_interface():
    from kabyle_agents.models import Fiche
    from kabyle_agents.semantic import HybridIndex
    from kabyle_agents.query import QueryPlan,Need
    class Encoder:
        def encode(self,texts,**kwargs):
            return [[1.,0.] if 'health' in text or 'médecine' in text else [0.,1.] for text in texts]
    fiche = Fiche('dense','Santé','corpus','health research','https://example.org',validated=True)
    index = HybridIndex([fiche],'fake-for-unit-test',mode='semantic',encoder=Encoder())
    plan = QueryPlan(question='médecine',tokens=['médecine'],needs=[Need('medicine',('médecine',))])
    hits = index.search(plan)
    assert hits[0].fiche.id == 'dense'
    assert hits[0].coverage == 1


def test_a2a_actual_jsonrpc_message():
    from kabyle_agents.a2a_server import create_app as a2a_app
    with TestClient(a2a_app(service())) as client:
        card = client.get('/.well-known/agent-card.json')
        assert card.status_code == 200
        assert card.json()['protocolVersion'] == '0.3.0'
        body = {'jsonrpc':'2.0','id':'test1','method':'message/send','params':{'message':{
            'role':'user','messageId':'q1','parts':[{'kind':'text','text':'amawal n ddwa'}]}}}
        response = client.post('/',json=body)
        data = response.json()
        assert 'error' not in data, data
        text = data['result']['parts'][0]['text']
        assert json.loads(text)['results'][0]['citation']['fiche_id'] == 'demo-001'


def test_mcp_sdk_stdio_roundtrip():
    from mcp import ClientSession,StdioServerParameters
    from mcp.client.stdio import stdio_client
    async def run():
        params = StdioServerParameters(command=sys.executable,args=['-m','kabyle_agents.mcp_server'],cwd=str(ROOT))
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {'search_catalog','get_fiche'} <= {t.name for t in tools.tools}
                result = await session.call_tool('search_catalog',{'query':'amawal n ddwa'})
                assert not result.isError
                assert 'demo-001' in str(result)
                missing = await session.call_tool('get_fiche',{'fiche_id':'missing'})
                assert missing.isError
    asyncio.run(run())


def test_trust_gate_requires_signed_fiche(tmp_path):
    s = service()
    fiche = s.orch.catalog.get('demo-001')
    did = create_key(tmp_path/'key.pem')
    token = issue_credential(load_key(tmp_path/'key.pem'),'urn:fiche:demo-001',fiche.content_hash)
    tokens = tmp_path/'tokens.json'
    tokens.write_text(json.dumps({'demo-001':token}))
    with patch.dict(os.environ,{'KABYLE_REQUIRE_ATTESTATIONS':'1','KABYLE_ATTESTATIONS_FILE':str(tokens),'KABYLE_TRUSTED_ISSUERS':did}):
        trusted = service()
        assert len(trusted.orch.catalog) == 1
        assert trusted.ask('amawal n ddwa')['results']


def test_fidelity_saved_run_and_receipt_binding(tmp_path):
    from kabyle_agents.benchmark import score_saved_fidelity
    responses = tmp_path/'responses.jsonl'
    responses.write_text(json.dumps({'question_id':'q1','answer':{'response_receipt':'sha256:a','synthesis':{'claims':[{'text':'test'}]}}})+'\n')
    labels = tmp_path/'labels.jsonl'
    labels.write_text(json.dumps({'question_id':'q1','response_receipt':'sha256:a','claim_index':0,'supported':False})+'\n')
    report = score_saved_fidelity(responses,labels)
    assert report['human_supported_rate'] == 0
    labels.write_text(labels.read_text().replace('sha256:a','sha256:wrong'))
    with pytest.raises(ValueError):
        score_saved_fidelity(responses,labels)


def test_openai_composer_validates_citations():
    import httpx, json as _j
    from kabyle_agents.llm import OpenAIComposer
    src = [{'id': 'F1', 'description': 'Dictionnaire kabyle de médecine avec glossaire'}]
    def respond(request):
        assert request.headers['authorization'] == 'Bearer test-key'
        body = {'claims': [{'text': 'Un dictionnaire médical existe.', 'fiche_id': 'F1', 'quote': 'Dictionnaire kabyle de médecine'}]}
        return httpx.Response(200, json={'choices': [{'message': {'content': _j.dumps(body)}}],
                                         'usage': {'prompt_tokens': 10, 'completion_tokens': 5}})
    c = OpenAIComposer(api_key='test-key', client=httpx.Client(transport=httpx.MockTransport(respond)))
    out = c.compose('dictionnaire médecine', src)
    assert out['citation_check'] == 'passed' and out['usage'] == {'input_tokens': 10, 'output_tokens': 5}
