#!/usr/bin/env python3
import json, urllib.request, urllib.error, argparse,uuid
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['baseline','incident','fixed'],default='incident');a=p.parse_args()
def call(port,path,body=None):
 cid=str(uuid.uuid4());req=urllib.request.Request(f'http://127.0.0.1:{port}{path}',json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json','x-correlation-id':cid})
 try:r=urllib.request.urlopen(req,timeout=20)
 except urllib.error.HTTPError as e:r=e
 with r:return r.status,json.load(r),r.headers.get('x-correlation-id'),cid
for port in [8081,8082,8083,8084,8095]:assert call(port,'/health')[0]==200
for store in ['LONDON-01','BRISTOL-02']:
 status,order,trace,cid=call(8084,'/checkout',{'sku':'LAPTOP-01','storeId':store,'quantity':1})
 expected=502 if a.mode=='incident' and store=='BRISTOL-02' else 201
 assert status==expected,(store,status,order)
 assert trace==cid and order['correlationId']==cid,(trace,cid,order)
 if status==201:
  s,saved,_,_=call(8082,'/orders/'+order['orderId']);assert s==200 and saved['storeId']==store
 print(store,status)
# Out-of-stock must create neither a reservation nor an order.
import sqlite3
from pathlib import Path
def counts():
 with sqlite3.connect(Path(__file__).resolve().parents[1]/'.run/backend.sqlite') as db:return tuple(db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ['orders','reservations'])
before=counts();assert call(8084,'/checkout',{'sku':'MONITOR-03','storeId':'LONDON-01','quantity':1})[0]==409;assert counts()==before
for body in [{},{'sku':'LAPTOP-01','storeId':'LONDON-01','quantity':0},{'sku':'LAPTOP-01','storeId':'LONDON-01','quantity':1.5}]:assert call(8084,'/checkout',body)[0]==400
print('PASS: health, happy path, incident behaviour, correlation, persisted order, out-of-stock and invalid requests')
