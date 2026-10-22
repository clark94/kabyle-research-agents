"""Kubo RPC connector, real raw CIDv1, and unsigned ERC-8004 transaction preparation."""
from __future__ import annotations
import base64
import hashlib
import httpx
from .provenance import canonical_json


def raw_cid(data: bytes):
    """CIDv1/raw/sha2-256 for a SINGLE raw block, not an arbitrary UnixFS file CID."""
    return 'b' + base64.b32encode(b'\x01\x55\x12\x20'+hashlib.sha256(data).digest()).decode().lower().rstrip('=')


class IPFSClient:
    def __init__(self, url='http://127.0.0.1:5001', client=None):
        self.url = url.rstrip('/')
        self.client = client or httpx.Client(timeout=30, trust_env=False)

    def publish(self, record):
        data = canonical_json(record)
        if len(data) > 262144:
            raise ValueError('Single raw-block export limited to 256 KiB')
        response = self.client.post(self.url+'/api/v0/add',
            params={'cid-version':1, 'raw-leaves':'true', 'pin':'true', 'chunker':'size-262144'},
            files={'file':('fiche.json',data,'application/json')})
        response.raise_for_status()
        result = response.json()
        if result['Hash'] != raw_cid(data):
            raise ValueError('Kubo CID does not match the exact exported bytes')
        return {'cid': result['Hash'], 'uri':'ipfs://'+result['Hash'], 'bytes':len(data)}

    def fetch(self, cid):
        response = self.client.post(self.url+'/api/v0/cat', params={'arg':cid})
        response.raise_for_status()
        if raw_cid(response.content) != cid:
            raise ValueError('IPFS content does not match requested raw CID')
        return response.content


REGISTER_ABI = [{'type':'function','name':'register','stateMutability':'nonpayable',
                 'inputs':[{'name':'agentURI','type':'string'}],
                 'outputs':[{'name':'agentId','type':'uint256'}]}]


def prepare_registration(sender, registry, agent_uri, chain_id=11155111):
    """No private key, no broadcast, no invented registry address. Sepolia only."""
    from web3 import Web3
    if chain_id != 11155111:
        raise ValueError('Only Sepolia testnet is enabled')
    if not agent_uri.startswith(('ipfs://','https://')):
        raise ValueError('agentURI must be ipfs:// or https://')
    sender = Web3.to_checksum_address(sender)
    registry = Web3.to_checksum_address(registry)
    contract = Web3().eth.contract(address=registry, abi=REGISTER_ABI)
    return {'chainId':chain_id, 'from':sender, 'to':registry, 'value':0,
            'data':contract.encode_abi('register',args=[agent_uri]),
            'status':'unsigned_not_broadcast', 'note':'Verify registry deployment, estimate gas, nonce and fees with your wallet.'}


def registration_document(name, a2a_url, mcp_url, mcp_version='2025-11-25'):
    return {'type':'https://eips.ethereum.org/EIPS/eip-8004#registration-v1', 'name':name,
            'description':'Kabyle catalog research coordinator',
            'services':[{'name':'A2A','endpoint':a2a_url,'version':'0.3.0'},
                        {'name':'MCP','endpoint':mcp_url,'version':mcp_version}],
            'active':True, 'x402Support':False, 'registrations':[]}
