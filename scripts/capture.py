#!/usr/bin/env python3
"""Capture only this demonstration's real runtime output, excluding setup attempts."""
import argparse,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('action',choices=['begin','end']);a=p.parse_args();state=R/'.run/capture-offsets.json'
if a.action=='begin':
 files=list((R/'.runtime/mule/logs').glob('*.jsonl'))+[R/'.run/mule-console.log']
 state.write_text(json.dumps({str(f.relative_to(R)):f.stat().st_size for f in files}))
else:
 for name,offset in json.loads(state.read_text()).items():
  src=R/name;dest=R/'evidence'/('api' if src.suffix=='.jsonl' else 'runtime')/src.name.replace('${sys:domainId}-','')
  dest.parent.mkdir(parents=True,exist_ok=True)
  with src.open('rb') as f:f.seek(offset);dest.write_bytes(f.read())
 print('Captured original application events and runtime output into evidence/.')
