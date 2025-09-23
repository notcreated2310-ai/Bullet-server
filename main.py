from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import sqlite3, os, time, uuid, json, hmac, hashlib, requests
from typing import Optional

# ---------------------------
# Config
# ---------------------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "./data.db")
LOG_FILE = os.environ.get("LOG_FILE", "./server.log")
MAX_CODE_BYTES = int(os.environ.get("MAX_CODE_BYTES", "200000"))
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.environ.get("BINANCE_TESTNET", "True").lower() == "true"

# ---------------------------
# App
# ---------------------------
app = FastAPI(title="Bullet Live Trading Server")

# ---------------------------
# Database Init
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ui_blocks (
        id TEXT PRIMARY KEY, category TEXT, code TEXT, created_at INTEGER, approved INTEGER DEFAULT 1
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS deploy_history (
        id TEXT PRIMARY KEY, block_id TEXT, action TEXT, detail TEXT, ts INTEGER
    )""")
    conn.commit(); conn.close()

init_db()

def now_ts(): return int(time.time())
def db_conn(): return sqlite3.connect(DB_PATH)

def require_admin(token: Optional[str]):
    if not ADMIN_TOKEN: return True
    if not token: raise HTTPException(403, "Admin token required")
    if token != ADMIN_TOKEN: raise HTTPException(403, "Invalid admin token")
    return True

# ---------------------------
# Broker Manager (Binance)
# ---------------------------
class BrokerManager:
    def __init__(self, api_key, api_secret, testnet=True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base = 'https://testnet.binance.vision/api' if testnet else 'https://api.binance.com/api'

    def _sign_payload(self, payload):
        query_string = '&'.join([f'{k}={v}' for k,v in payload.items()])
        signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        payload['signature'] = signature
        return payload

    def place_order(self, symbol, side, type_, quantity, price=None):
        ts = int(time.time()*1000)
        endpoint = f'{self.base}/v3/order'
        payload = {'symbol':symbol,'side':side,'type':type_,'quantity':quantity,'timestamp':ts}
        if price: payload['price']=price
        payload = self._sign_payload(payload)
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = requests.post(endpoint, headers=headers, params=payload)
        return resp.json()

    def account_balance(self):
        ts = int(time.time()*1000)
        endpoint = f'{self.base}/v3/account'
        payload = {'timestamp':ts}
        payload = self._sign_payload(payload)
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = requests.get(endpoint, headers=headers, params=payload)
        return resp.json()

broker = BrokerManager(BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET)

# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def root():
    return {"status":"ok","msg":"Server is live"}

@app.get("/admin/autologin")
def autologin():
    return {"status":"success","message":"Login successful","admin_token":ADMIN_TOKEN}

# ---------------------------
# Admin Panel
# ---------------------------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return """
    <html><body>
    <h2>Admin Control</h2>
    <form action='/code/deploy' method='post'>
      <input name='category' placeholder='Category'><br><br>
      <textarea name='code' rows='10' cols='70' placeholder='Paste HTML/Python code here'></textarea><br><br>
      <button type='submit'>Deploy</button>
    </form>
    <br>
    <form action='/admin/cleanup' method='post'>
      <input name='category' placeholder='(optional) Category to cleanup'><br><br>
      <button type='submit'>Cleanup History</button>
    </form>
    </body></html>"""

# ---------------------------
# Code Deploy
# ---------------------------
@app.post("/code/deploy")
async def code_deploy(request: Request):
    form = await request.form()
    token = form.get('token') or request.query_params.get('token')
    require_admin(token)
    category = form.get('category','misc')
    code = form.get('code','')
    if not code: raise HTTPException(400,'code required')
    if len(code.encode())>MAX_CODE_BYTES: raise HTTPException(400,'code too large')
    block_id = str(uuid.uuid4()); ts=now_ts()
    conn = db_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO ui_blocks (id,category,code,created_at,approved) VALUES (?,?,?,?,1)",
                (block_id,category,code,ts))
    conn.commit()
    cur.execute("INSERT INTO deploy_history (id,block_id,action,detail,ts) VALUES (?,?,?,?,?)",
                (str(uuid.uuid4()),block_id,'deploy',json.dumps({'category':category}),ts))
    conn.commit(); conn.close()
    return {'status':'ok','block_id':block_id}

@app.get("/code/active")
def active():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT category, code FROM ui_blocks WHERE approved=1 ORDER BY created_at")
    rows = cur.fetchall(); conn.close()
    if not rows: return {'status':'empty'}
    # Group by category
    html = ""
    cats = {}
    for cat, code in rows:
        cats.setdefault(cat, []).append(code)
    for cat, blocks in cats.items():
        html += f"<h2>{cat.upper()}</h2>" + "\n".join(blocks)
    return HTMLResponse(html)

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return HTMLResponse("""
<html><head><title>Trading App</title></head>
<body>
<header style='background:#1e1e2d;color:white;padding:10px;text-align:center;'>
  <h2>📊 Trading App Dashboard</h2>
</header>
<nav style='background:#2e2e3e;padding:10px;'>
  <a href='/admin/panel' style='color:white;'>Admin Panel</a> | 
  <a href='/status' style='color:white;'>Server Status</a>
</nav>
<div style='padding:20px;'>
  <h3>Deployed UI Blocks (Category-wise)</h3>
  <iframe src='/code/active' width='100%' height='500px'></iframe>
</div>
</body></html>
""")

# ---------------------------
# Cleanup History
# ---------------------------
@app.post("/admin/cleanup")
async def cleanup(category: Optional[str] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    conn = db_conn(); cur = conn.cursor()
    if category:
        cur.execute("DELETE FROM ui_blocks WHERE category=?", (category,))
        cur.execute("DELETE FROM deploy_history WHERE detail LIKE ?", (f'%{category}%',))
    else:
        cur.execute("DELETE FROM ui_blocks")
        cur.execute("DELETE FROM deploy_history")
    conn.commit(); conn.close()
    return {"status":"ok","msg":"Cleanup done","category":category or "ALL"}

# ---------------------------
# Broker Endpoints
# ---------------------------
@app.post('/broker/buy')
async def broker_buy(symbol: str = Form(...), qty: float = Form(...), price: Optional[float] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    res = broker.place_order(symbol=symbol, side='BUY', type_='MARKET' if not price else 'LIMIT', quantity=qty, price=price)
    return res

@app.post('/broker/sell')
async def broker_sell(symbol: str = Form(...), qty: float = Form(...), price: Optional[float] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    res = broker.place_order(symbol=symbol, side='SELL', type_='MARKET' if not price else 'LIMIT', quantity=qty, price=price)
    return res

@app.get('/broker/balance')
def broker_balance(token: Optional[str] = None):
    require_admin(token)
    return broker.account_balance()

# ---------------------------
# Status
# ---------------------------
@app.get('/status')
def status():
    conn = db_conn(); cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM ui_blocks"); c=cur.fetchone()[0]; conn.close()
    return {'status':'ok','blocks':c,'time':now_ts()}
    
