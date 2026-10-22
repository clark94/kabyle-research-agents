"""Operational CLI for import, benchmark, identities and opt-in Web3 operations."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='command',required=True)
    i = sub.add_parser('import'); i.add_argument('source'); i.add_argument('target'); i.add_argument('--approve-reviewed',action='store_true')
    e = sub.add_parser('benchmark'); e.add_argument('--questions',default='eval/questions.jsonl'); e.add_argument('--out',required=True)
    e.add_argument('--llm',action='store_true'); e.add_argument('--annotations'); e.add_argument('--input-rate',type=float);e.add_argument('--output-rate',type=float);e.add_argument('--hourly-cost',type=float)
    f = sub.add_parser('fidelity');f.add_argument('responses');f.add_argument('annotations')
    k = sub.add_parser('keygen'); k.add_argument('--key',default='.secrets/issuer.pem')
    r = sub.add_parser('resolve');r.add_argument('did')
    c = sub.add_parser('issue');c.add_argument('--key',required=True);c.add_argument('--subject',required=True);c.add_argument('--hash',required=True);c.add_argument('--out',required=True)
    v = sub.add_parser('verify');v.add_argument('token_file');v.add_argument('--issuer',required=True);v.add_argument('--hash')
    ip = sub.add_parser('ipfs-publish');ip.add_argument('json_file');ip.add_argument('--url',default='http://127.0.0.1:5001')
    tx = sub.add_parser('erc8004-prepare');tx.add_argument('--sender',required=True);tx.add_argument('--registry',required=True);tx.add_argument('--uri',required=True)
    args = p.parse_args()
    try:
        if args.command == 'import':
            from .importer import import_catalog
            result = import_catalog(args.source,args.target,args.approve_reviewed)
        elif args.command == 'benchmark':
            from .benchmark import benchmark
            from .service import ResearchService
            result = benchmark(ResearchService(),args.questions,args.out,args.llm,args.input_rate,args.output_rate,args.annotations,args.hourly_cost)
        elif args.command == 'fidelity':
            from .benchmark import score_saved_fidelity
            result = score_saved_fidelity(args.responses,args.annotations)
        elif args.command == 'keygen':
            from .identity import create_key
            result = {'did':create_key(args.key),'private_key':args.key}
        elif args.command == 'resolve':
            from .identity import resolve
            _,result = resolve(args.did)
        elif args.command == 'issue':
            from .identity import issue_credential,load_key
            token = issue_credential(load_key(args.key),args.subject,args.hash)
            with Path(args.out).open('x',encoding='utf-8') as out:
                out.write(token)
            result = {'credential_file':args.out}
        elif args.command == 'verify':
            from .identity import verify_credential
            result = verify_credential(Path(args.token_file).read_text().strip(),args.issuer,args.hash)
        elif args.command == 'ipfs-publish':
            from .web3 import IPFSClient
            result = IPFSClient(args.url).publish(json.loads(Path(args.json_file).read_text(encoding='utf-8')))
        else:
            from .web3 import prepare_registration
            result = prepare_registration(args.sender,args.registry,args.uri)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError) as exc:
        p.exit(1,str(exc)+'\n')


if __name__ == '__main__':
    main()
