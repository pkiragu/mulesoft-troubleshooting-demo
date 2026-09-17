#!/usr/bin/env python3
"""Generate real HTTP traffic through all four Mule apps; record synthetic business activity."""
import argparse,json,random,time,uuid,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8084');p.add_argument('--count',type=int,default=1000);p.add_argument('--phase',choices=['baseline','incident','fixed'],required=True);p.add_argument('--out',type=Path,default=Path('evidence/requests.jsonl'));args=p.parse_args()
stores=['BRISTOL-02' if i%25 in (0,1) else 'LONDON-01' for i in range(args.count)]
random.Random(42).shuffle(stores);args.out.parent.mkdir(parents=True,exist_ok=True);counts={}
with args.out.open('a') as f:
 for i,store in enumerate(stores):
    cid=str(uuid.uuid4());body={'sku':'HEADSET-02' if i%3==0 else 'LAPTOP-01','storeId':store,'quantity':1}
    req=urllib.request.Request(args.base_url.rstrip('/')+'/checkout',json.dumps(body).encode(),{'Content-Type':'application/json','x-correlation-id':cid})
    start=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=45) as r: status=r.status;response=json.load(r)
    except urllib.error.HTTPError as e:status=e.code;response=json.load(e)
    record={'timestamp':datetime.now(timezone.utc).isoformat(),'synthetic':True,'phase':args.phase,'correlationId':cid,'request':body,'status':status,'durationMs':round((time.monotonic()-start)*1000,2),'response':response}
    f.write(json.dumps(record)+'\n');counts[status]=counts.get(status,0)+1
    if (i+1)%100==0:print(i+1,counts,flush=True)
print(json.dumps({'phase':args.phase,'requests':len(stores),'statuses':counts}))
expected=0 if args.phase!='incident' else stores.count('BRISTOL-02')
assert counts.get(502,0)==expected and counts.get(201,0)==len(stores)-expected,counts
