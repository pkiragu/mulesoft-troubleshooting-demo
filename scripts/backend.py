#!/usr/bin/env python3
"""Fictional warehouse and order database. Local only, no external services."""
import json, sqlite3, threading, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
ROOT=Path(__file__).resolve().parents[1]
ROOT.joinpath('.run').mkdir(exist_ok=True)
DB=ROOT/'.run/backend.sqlite'
lock=threading.Lock()
with sqlite3.connect(DB) as db:
    db.executescript('CREATE TABLE IF NOT EXISTS stock (store TEXT, sku TEXT, qty INTEGER, PRIMARY KEY(store,sku)); CREATE TABLE IF NOT EXISTS reservations (id TEXT PRIMARY KEY, store TEXT, sku TEXT, qty INTEGER, active INTEGER); CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, reservation TEXT UNIQUE, body TEXT);')
    for row in json.loads((ROOT/'fixtures/stock.json').read_text()):
        db.execute('INSERT OR IGNORE INTO stock VALUES (?,?,?)',(row['storeId'],row['sku'],int(row['availableQuantity'])))
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def respond(self,status,body):
        raw=json.dumps(body).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self): self.dispatch()
    def do_POST(self): self.dispatch()
    def do_DELETE(self): self.dispatch()
    def dispatch(self):
        try:
            parsed=urlparse(self.path); q=parse_qs(parsed.query)
            size=int(self.headers.get('Content-Length','0'))
            if size>65536: return self.respond(413,{'error':'BODY_TOO_LARGE'})
            if self.headers.get('Transfer-Encoding','').lower()=='chunked':
                chunks=[];total=0
                while True:
                    n=int(self.rfile.readline().split(b';')[0].strip(),16)
                    if not n:
                        while self.rfile.readline().strip():pass
                        break
                    total+=n
                    if total>65536:return self.respond(413,{'error':'BODY_TOO_LARGE'})
                    chunks.append(self.rfile.read(n));self.rfile.read(2)
                raw=b''.join(chunks)
            else:raw=self.rfile.read(size)
            body=json.loads(raw) if raw else {}
            with lock, sqlite3.connect(DB) as db:
                path=parsed.path
                if self.command=='GET' and path=='/health': return self.respond(200,{'status':'UP'})
                if self.command=='GET' and path=='/stock':
                    store=q.get('storeId',[''])[0]; sku=q.get('sku',[''])[0]
                    row=db.execute('SELECT qty FROM stock WHERE store=? AND sku=?',(store,sku)).fetchone()
                    if row is None:return self.respond(404,{'error':'STOCK_NOT_FOUND'})
                    return self.respond(200,{'storeId':store,'sku':sku,'availableQuantity':str(row[0]) if store=='BRISTOL-02' else row[0]})
                if self.command=='POST' and path=='/reservations':
                    store,sku,qty=body['storeId'],body['sku'],body['quantity']
                    if type(qty)!=int or qty<=0:return self.respond(400,{'error':'INVALID_QUANTITY'})
                    changed=db.execute('UPDATE stock SET qty=qty-? WHERE store=? AND sku=? AND qty>=?',(qty,store,sku,qty)).rowcount
                    if not changed:return self.respond(409,{'error':'OUT_OF_STOCK'})
                    rid='res-'+str(uuid.uuid4());db.execute('INSERT INTO reservations VALUES (?,?,?,?,1)',(rid,store,sku,qty));db.commit()
                    return self.respond(201,{'reservationId':rid})
                if self.command=='DELETE' and path.startswith('/reservations/'):
                    rid=path.split('/')[-1]
                    if db.execute('SELECT 1 FROM orders WHERE reservation=?',(rid,)).fetchone():return self.respond(409,{'error':'ORDER_ALREADY_CREATED'})
                    row=db.execute('SELECT store,sku,qty FROM reservations WHERE id=? AND active=1',(rid,)).fetchone()
                    if row:
                        db.execute('UPDATE stock SET qty=qty+? WHERE store=? AND sku=?',(row[2],row[0],row[1]));db.execute('UPDATE reservations SET active=0 WHERE id=?',(rid,));db.commit()
                    return self.respond(200,{'released':True})
                if self.command=='POST' and path=='/orders':
                    rid=body['reservationId']
                    existing=db.execute('SELECT body FROM orders WHERE reservation=?',(rid,)).fetchone()
                    if existing:return self.respond(200,json.loads(existing[0]))
                    row=db.execute('SELECT store,sku,qty FROM reservations WHERE id=? AND active=1',(rid,)).fetchone()
                    if not row or (body['storeId'],body['sku'],body['quantity'])!=row:return self.respond(409,{'error':'INVALID_RESERVATION'})
                    result={'orderId':'ord-'+str(uuid.uuid4()),'status':'READY_FOR_COLLECTION',**body}
                    db.execute('INSERT INTO orders VALUES (?,?,?)',(result['orderId'],rid,json.dumps(result)));db.commit()
                    return self.respond(201,result)
                if self.command=='GET' and path.startswith('/orders/'):
                    row=db.execute('SELECT body FROM orders WHERE id=?',(path.split('/')[-1],)).fetchone()
                    return self.respond(200,json.loads(row[0])) if row else self.respond(404,{'error':'ORDER_NOT_FOUND'})
                self.respond(404,{'error':'NOT_FOUND'})
        except (KeyError,ValueError,TypeError):self.respond(400,{'error':'BAD_REQUEST'})
        except Exception as e:
            print(type(e).__name__,str(e),flush=True);self.respond(500,{'error':'BACKEND_FAILURE'})
if __name__=='__main__':
    print('Mock backend listening at http://127.0.0.1:8095',flush=True)
    ThreadingHTTPServer(('127.0.0.1',8095),Handler).serve_forever()
