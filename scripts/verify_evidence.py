#!/usr/bin/env python3
"""Check ledger outcomes and real cross-API trace coverage."""
import json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1]
rows=[json.loads(s) for s in (R/'evidence/requests.jsonl').read_text().splitlines()]
events=[]
for f in (R/'evidence/api').glob('*.jsonl'):
 events += [json.loads(s) for s in f.read_text().splitlines() if s.strip()]
traces=collections.defaultdict(set)
for e in events:traces[e['correlationId']].add(e['api'])
for phase,count,failures in [('baseline',500,0),('incident',1000,80)]:
 subset=[r for r in rows if r['phase']==phase]
 assert len(subset)==count
 assert sum(r['status']==502 for r in subset)==failures
 assert sum(r['status']==201 for r in subset)==count-failures
 for r in subset:
  expected={'shopping-experience-api','order-process-api','inventory-system-api'}
  if r['status']==201:expected.add('order-system-api')
  assert expected <= traces[r['correlationId']],r['correlationId']
  if r['status']==502:
   assert r['request']['storeId']=='BRISTOL-02'
   assert 'order-system-api' not in traces[r['correlationId']]
 print(phase,count,'requests;',failures,'failures; complete cross-API traces')
print(len(events),'original structured Mule events verified')
