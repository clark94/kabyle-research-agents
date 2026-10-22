"""Local JSONL/CSV import, validation, duplicate checks and explicit editorial approval."""
import csv
import json
from pathlib import Path
from urllib.parse import urlparse
from .catalog import load_catalog
from .provenance import fiche_hash


def import_catalog(source, target, approve_reviewed=False):
    source, target = Path(source), Path(target)
    if target.exists():
        raise ValueError('Target already exists: choose a new output file')
    if source.suffix.lower() == '.csv':
        with source.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            for key in ('languages','keywords'):
                row[key] = [v.strip() for v in row.get(key,'').split('|') if v.strip()]
    else:
        rows = [json.loads(line) for line in source.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    ids = set()
    for row in rows:
        for field in ('id','title','type','description','url'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f'Missing/invalid {field}')
        if row['id'] in ids:
            raise ValueError('Duplicate id: '+row['id'])
        ids.add(row['id'])
        url = urlparse(row['url'])
        if url.scheme not in ('https','http') or not url.hostname:
            raise ValueError('A public source URL is required')
        for field in ('languages','keywords'):
            if not isinstance(row.get(field,[]), list) or any(not isinstance(x,str) for x in row.get(field,[])):
                raise ValueError(field+' must be a list of strings')
        row['validated'] = bool(approve_reviewed)
        row['content_hash'] = fiche_hash(row)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Validate all records through the same integrity/security gate before committing output.
    temp = target.with_suffix(target.suffix+'.tmp')
    if temp.exists():
        raise ValueError('Temporary output already exists')
    try:
        with temp.open('x',encoding='utf-8') as stream:
            for row in rows:
                stream.write(json.dumps(row,ensure_ascii=False)+'\n')
        catalog, report = load_catalog(temp)
        if not report.clean or len(catalog) != len(rows):
            raise ValueError('Import rejected by catalog security checks')
        temp.rename(target)
    finally:
        temp.unlink(missing_ok=True)
    return {'records':len(rows), 'approved':bool(approve_reviewed), 'output':str(target)}
