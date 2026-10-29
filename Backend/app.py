"""Run from the project root: python -m Backend.app. Local single-profile demo."""
import json, os, sqlite3, sys
from datetime import datetime
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from functools import partial
from Backend.policy import recommend
ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('MEMORY_DB', ROOT / 'Backend' / 'memory.db'))
MODEL = None
MODEL_ERROR = None

def connect():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def initialize():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with connect() as con: con.executescript((ROOT/'Backend/schema.sql').read_text())

def load_model():
    global MODEL, MODEL_ERROR
    try:
        import joblib
        MODEL=joblib.load(ROOT/'ML/artifacts/model.joblib')
    except Exception as exc:
        MODEL_ERROR=type(exc).__name__
        print('ML unavailable; rule policy remains available:', MODEL_ERROR)

def bounded_int(data,key,lo,hi):
    v=data.get(key)
    if type(v) is not int or not lo <= v <= hi: raise ValueError(f'{key} must be an integer from {lo} to {hi}')
    return v

def clean_text(data,key,limit):
    v=data.get(key)
    if not isinstance(v,str) or not v.strip() or len(v)>limit: raise ValueError(f'{key} must contain 1-{limit} characters')
    return v.strip()

class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def reply(self,status,payload):
        body=json.dumps(payload).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/health': return self.reply(200,{'ok':True,'model_loaded':MODEL is not None,'model_error':MODEL_ERROR})
        if path=='/api/dashboard':
            with connect() as c:
                data={'profile':dict(c.execute('SELECT * FROM profile').fetchone())}
                for table in ['memories','reminders','sessions']:
                    order=' ORDER BY id DESC LIMIT 100' if table=='sessions' else ' ORDER BY id'
                    data[table]=[dict(r) for r in c.execute('SELECT * FROM '+table+order)]
            data['model_loaded']=MODEL is not None
            return self.reply(200,data)
        if path.startswith('/api/'): return self.reply(404,{'error':'Unknown endpoint'})
        if path not in ['/', '/index.html','/style.css','/app.js']: return self.reply(404,{'error':'Not found'})
        super().do_GET()
    def do_POST(self):
        # Browser cross-origin writes are rejected; no CORS is enabled.
        origin=self.headers.get('Origin')
        if origin and origin != 'http://'+self.headers.get('Host',''):
            return self.reply(403,{'error':'Cross-origin writes are disabled'})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n<0 or n>16384: raise ValueError('Request too large')
            data=json.loads(self.rfile.read(n) or b'{}')
            if not isinstance(data,dict): raise ValueError('Expected a JSON object')
            path=urlparse(self.path).path
            with connect() as c:
                if path=='/api/profile':
                    name=clean_text(data,'name',80)
                    if type(data.get('consent')) is not bool: raise ValueError('consent must be boolean')
                    c.execute('UPDATE profile SET name=?,consent=? WHERE id=1',(name,int(data['consent'])))
                    return self.reply(200,{'saved':True})
                if path=='/api/sessions':
                    if not c.execute('SELECT consent FROM profile').fetchone()[0]: return self.reply(403,{'error':'Caregiver consent is required to save activity measures'})
                    correct=bounded_int(data,'correct',0,10000); attempts=bounded_int(data,'attempts',0,10000)
                    hints=bounded_int(data,'hints',0,10000);level=bounded_int(data,'level',1,3)
                    if correct>attempts: raise ValueError('correct cannot exceed attempts')
                    paused=data.get('paused')
                    if type(paused) is not bool: raise ValueError('paused must be boolean')
                    action,next_level,reason=recommend(correct,attempts,hints,level,paused)
                    model_action=None
                    if MODEL is not None and attempts>=3:
                        import pandas as pd
                        row={'activity':'matching','level':level,'accuracy':correct/attempts,'hint_rate':min(hints/attempts,1),'paused':int(paused)}
                        model_action=str(MODEL.predict(pd.DataFrame([row]))[0])
                    c.execute('INSERT INTO sessions(correct,attempts,hints,paused,level,recommendation,next_level,model_action) VALUES(?,?,?,?,?,?,?,?)',(correct,attempts,hints,int(paused),level,action,next_level,model_action))
                    return self.reply(201,{'recommendation':action,'next_level':next_level,'reason':reason,'model_action':model_action,'review_required':True})
                if path=='/api/memories':
                    title=clean_text(data,'title',100); description=clean_text(data,'description',1000)
                    if type(data.get('approved')) is not bool: raise ValueError('approved must be boolean')
                    c.execute('INSERT INTO memories(title,description,approved) VALUES(?,?,?)',(title,description,int(data['approved'])))
                    return self.reply(201,{'saved':True})
                if path=='/api/reminders':
                    title=clean_text(data,'title',120); due=clean_text(data,'due_at',40)
                    datetime.fromisoformat(due)
                    c.execute('INSERT INTO reminders(title,due_at) VALUES(?,?)',(title,due))
                    return self.reply(201,{'saved':True})
                parts=path.strip('/').split('/')
                if len(parts)==4 and parts[:2]==['api','reminders'] and parts[3]=='acknowledge':
                    cur=c.execute('UPDATE reminders SET acknowledged=1 WHERE id=?',(int(parts[2]),))
                    return self.reply(200 if cur.rowcount else 404,{'saved':bool(cur.rowcount)})
                return self.reply(404,{'error':'Unknown endpoint'})
        except (ValueError,TypeError,KeyError) as exc: self.reply(400,{'error':str(exc)})
        except Exception as exc:
            print('Server error:',repr(exc),file=sys.stderr)
            self.reply(500,{'error':'Server could not complete the request'})

def main():
    initialize(); load_model()
    port=int(os.environ.get('PORT','8000'))
    server=ThreadingHTTPServer(('127.0.0.1',port),partial(Handler,directory=str(ROOT/'Frontend')))
    print(f'Memory Companion: http://127.0.0.1:{port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__=='__main__': main()
