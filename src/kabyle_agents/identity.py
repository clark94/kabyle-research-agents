"""did:key Ed25519 + signed VC-JWT subset. Trust must be provided by the caller."""
from __future__ import annotations
import base64
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def b58encode(data):
    num = int.from_bytes(data, 'big')
    out = ''
    while num:
        num, r = divmod(num, 58)
        out = ALPHABET[r] + out
    return '1'*(len(data)-len(data.lstrip(b'\x00'))) + out


def b58decode(text):
    num = 0
    for char in text:
        num = num*58 + ALPHABET.index(char)
    return b'\x00'*(len(text)-len(text.lstrip('1'))) + num.to_bytes((num.bit_length()+7)//8, 'big')


def did_from_public(public):
    return 'did:key:z' + b58encode(b'\xed\x01' + public.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))


def resolve(did):
    if not did.startswith('did:key:z'):
        raise ValueError('Only did:key Ed25519 is supported')
    raw = b58decode(did[len('did:key:z'):])
    if len(raw) != 34 or raw[:2] != b'\xed\x01':
        raise ValueError('Unsupported multicodec')
    public = Ed25519PublicKey.from_public_bytes(raw[2:])
    fragment = did.split(':')[-1]
    jwk = {'kty':'OKP','crv':'Ed25519','x':base64.urlsafe_b64encode(raw[2:]).rstrip(b'=').decode()}
    document = {'@context':['https://www.w3.org/ns/did/v1','https://w3id.org/security/jwk/v1'],
        'id':did,'verificationMethod':[{'id':did+'#'+fragment,'type':'JsonWebKey2020','controller':did,'publicKeyJwk':jwk}],
        'authentication':[did+'#'+fragment], 'assertionMethod':[did+'#'+fragment]}
    return public, document


def create_key(path):
    key = Ed25519PrivateKey.generate()
    data = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # No overwrite, restrictive permissions; on Windows also protect the folder with ACLs.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
    return did_from_public(key.public_key())


def load_key(path):
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Ed25519 key required')
    return key


def issue_credential(key, subject_id, content_hash, days=30):
    if not subject_id or not isinstance(content_hash, str) or not content_hash.startswith('sha256:'):
        raise ValueError('Subject and sha256 content hash required')
    if not 1 <= days <= 365:
        raise ValueError('Validity must be 1..365 days')
    did = did_from_public(key.public_key())
    now = datetime.now(timezone.utc)
    vc = {'@context':['https://www.w3.org/ns/credentials/v2'], 'type':['VerifiableCredential'],
          'issuer':did, 'validFrom':now.isoformat(), 'validUntil':(now+timedelta(days=days)).isoformat(),
          'credentialSubject':{'id':subject_id, 'https://schema.org/sha256':content_hash}}
    return jwt.encode(vc, key, algorithm='EdDSA', headers={'typ':'vc+jwt','kid':did+'#'+did.split(':')[-1]})


def verify_credential(token, trusted_issuer, expected_hash=None):
    public, _ = resolve(trusted_issuer)
    vc = jwt.decode(token, public, algorithms=['EdDSA'], options={'verify_aud':False})
    header = jwt.get_unverified_header(token)
    if header.get('typ') != 'vc+jwt' or header.get('kid') != trusted_issuer+'#'+trusted_issuer.split(':')[-1]:
        raise ValueError('Invalid VC header')
    if vc.get('issuer') != trusted_issuer or vc.get('@context') != ['https://www.w3.org/ns/credentials/v2']:
        raise ValueError('Wrong issuer or context')
    if 'VerifiableCredential' not in vc.get('type', []):
        raise ValueError('Wrong credential type')
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(vc['validFrom'].replace('Z','+00:00'))
    end = datetime.fromisoformat(vc['validUntil'].replace('Z','+00:00'))
    if not start <= now < end:
        raise ValueError('Expired or not yet valid credential')
    content_hash = vc['credentialSubject']['https://schema.org/sha256']
    if expected_hash is not None and content_hash != expected_hash:
        raise ValueError('Wrong content hash')
    return vc
