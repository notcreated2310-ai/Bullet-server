# final_main.py (replace your existing main.py with this)
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
# App + logging
# ---------------------------
import logging
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Bullet Live Trading Server")

# ---------------------------
# DB init (keep schema compatible)
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
    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, level TEXT, message TEXT
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ui_nav_buttons (
        id TEXT PRIMARY KEY, position TEXT, label TEXT, route TEXT, ord INTEGER, code TEXT
    )""")
    conn.commit(); conn.close()

init_db()

def now_ts(): return int(time.time())
def db_conn(): return sqlite3.connect(DB_PATH)

def require_admin(token: Optional[str]):
    if not ADMIN_TOKEN:
        return True
    if not token:
        raise HTTPException(403, "Admin token required")
    if token != ADMIN_TOKEN:
        raise HTTPException(403, "Invalid admin token")
    return True

# ---------------------------
# BrokerManager (Binance testnet ready)
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
        resp = requests.post(endpoint, headers=headers, params=payload, timeout=10)
        return resp.json()

    def account_balance(self):
        ts = int(time.time()*1000)
        endpoint = f'{self.base}/v3/account'
        payload = {'timestamp':ts}
        payload = self._sign_payload(payload)
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = requests.get(endpoint, headers=headers, params=payload, timeout=10)
        return resp.json()

broker = BrokerManager(BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET)

# ---------------------------
# Routes - basic
# ---------------------------
@app.get('/')
def root():
    return {'status':'ok','msg':'server live'}

@app.get('/admin/autologin')
def auto_login():
    return {'status':'success','message':'Login successful','admin_token': ADMIN_TOKEN}

# ---------------------------
# Admin panel (browser) - manage nav buttons, deploy blocks, cleanup
# ---------------------------
@app.get('/admin/panel', response_class=HTMLResponse)
def admin_panel():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT id, position, label, route, ord FROM ui_nav_buttons ORDER BY ord ASC")
    navs = cur.fetchall(); conn.close()
    rows_html = ''
    for n in navs:
        rows_html += f"<tr><td>{n[2]}</td><td>{n[1]}</td><td>{n[3]}</td><td><form action='/admin/nav/delete' method='post' style='display:inline'><input type='hidden' name='id' value='{n[0]}'/><button>Delete</button></form></td></tr>"

    return f"""
    <html><body style='font-family:Arial;padding:20px;'>
      <h2>Admin Panel</h2>
      <h3>Add Navigation Button (Header/Footer)</h3>
      <form action='/admin/nav/add' method='post'>
        <label>Position:</label>
        <select name='position'>
          <option value='header'>Header</option>
          <option value='footer'>Footer</option>
        </select><br>
        <label>Label:</label><input name='label'/><br>
        <label>Route (e.g. /reports):</label><input name='route' placeholder='/reports'/><br>
        <label>Optional code (HTML) for route content (paste):</label><br>
        <textarea name='code' rows='8' cols='80'></textarea><br>
        <button type='submit'>Add Button</button>
      </form>

      <h3>Existing Nav Buttons</h3>
      <table border='1' cellpadding='6'>
        <tr><th>Label</th><th>Position</th><th>Route</th><th>Action</th></tr>
        {rows_html}
      </table>

      <h3>Deploy UI Block (category + code)</h3>
      <form action='/code/deploy' method='post'>
        <label>Category:</label><input name='category' placeholder='misc'/><br>
        <label>Code:</label><br>
        <textarea name='code' rows='10' cols='80'></textarea><br>
        <button type='submit'>Deploy & Append</button>
      </form>

      <h3>Cleanup</h3>
      <form action='/admin/cleanup' method='post'>
        <label>Category (optional):</label><input name='category' placeholder='leave empty to remove all'/><br>
        <button type='submit'>Cleanup</button>
      </form>

      <p><a href='/ui' target='_blank'>Open UI Preview</a></p>
    </body></html>
    """

@app.post('/admin/nav/add')
async def admin_nav_add(request: Request):
    form = await request.form()
    token = form.get('token') or request.query_params.get('token')
    require_admin(token)
    position = form.get('position','footer')
    label = form.get('label','Button')
    route = form.get('route','/')
    code = form.get('code','')
    conn = db_conn(); cur = conn.cursor()
    ordv = int(time.time())
    nid = str(uuid.uuid4())
    cur.execute('INSERT INTO ui_nav_buttons (id, position, label, route, ord, code) VALUES (?,?,?,?,?,?)', (nid, position, label, route, ordv, code))
    conn.commit(); conn.close()
    return JSONResponse({'status':'ok','id':nid})

@app.post('/admin/nav/delete')
async def admin_nav_delete(id: str = Form(...), token: Optional[str] = Form(None)):
    require_admin(token)
    conn = db_conn(); cur = conn.cursor()
    cur.execute('DELETE FROM ui_nav_buttons WHERE id=?', (id,))
    conn.commit(); conn.close()
    return HTMLResponse('<html><body>Deleted. <a href="/admin/panel">Back</a></body></html>')

# ---------------------------
# Deploy / active / cleanup
# ---------------------------
@app.post('/code/deploy')
async def code_deploy(request: Request):
    form = await request.form()
    token = form.get('token') or request.query_params.get('token')
    require_admin(token)
    category = form.get('category','misc')
    code = form.get('code','')
    if not code:
        raise HTTPException(400,'code required')
    if len(code.encode())>MAX_CODE_BYTES:
        raise HTTPException(400,'code too large')
    block_id = str(uuid.uuid4()); ts = now_ts()
    conn = db_conn(); cur = conn.cursor()
    cur.execute('INSERT INTO ui_blocks (id,category,code,created_at,approved) VALUES (?,?,?,?,1)', (block_id, category, code, ts))
    cur.execute('INSERT INTO deploy_history (id,block_id,action,detail,ts) VALUES (?,?,?,?,?)', (str(uuid.uuid4()), block_id, 'deploy', json.dumps({'category':category}), ts))
    conn.commit(); conn.close()
    return JSONResponse({'status':'ok','block_id':block_id})

@app.get('/code/active')
def code_active():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT category, code FROM ui_blocks WHERE approved=1 ORDER BY created_at")
    rows = cur.fetchall(); conn.close()
    if not rows:
        return HTMLResponse('<h3>No UI Deployed</h3>')
    html = ''
    cats = {}
    for cat, code in rows:
        cats.setdefault(cat, []).append(code)
    for cat, blocks in cats.items():
        html += f"<section style='padding:12px 0;'><h2 style='margin-bottom:8px'>{cat.upper()}</h2>"
        for b in blocks:
            # wrap each block in a container so CSS can make it full width
            html += f"<div class='deployed-block' style='width:100%;min-height:220px;margin-bottom:12px'>{b}</div>"
        html += '</section>'
    return HTMLResponse(f"<div style='padding:6px'>{html}</div>")

@app.post('/admin/cleanup')
async def admin_cleanup(category: Optional[str] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    conn = db_conn(); cur = conn.cursor()
    if category:
        cur.execute('DELETE FROM ui_blocks WHERE category=?', (category,))
        cur.execute('DELETE FROM deploy_history WHERE detail LIKE ?', (f'%{category}%',))
    else:
        cur.execute('DELETE FROM ui_blocks')
        cur.execute('DELETE FROM deploy_history')
    conn.commit(); conn.close()
    return JSONResponse({'status':'ok','category': category or 'ALL'})

# ---------------------------
# Provide nav route content (used by /ui to load code for a nav route)
# ---------------------------
@app.get('/nav/content')
def nav_content(route: str):
    conn = db_conn(); cur = conn.cursor()
    cur.execute('SELECT code FROM ui_nav_buttons WHERE route=? LIMIT 1', (route,))
    row = cur.fetchone(); conn.close()
    if not row:
        raise HTTPException(404, "No content")
    return HTMLResponse(row[0])

# ---------------------------
# UI preview - improved: dynamic area loads code active (full width) or nav-specific code
# ---------------------------
@app.get('/ui', response_class=HTMLResponse)
def ui_preview():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT position, label, route FROM ui_nav_buttons ORDER BY ord ASC")
    navs = cur.fetchall()
    header_buttons = [n for n in navs if n[0]=='header']
    footer_buttons = [n for n in navs if n[0]=='footer']
    conn.close()

    # header html
    if not header_buttons:
        header_html = "<div class='nav-item' onclick=\"loadDefault()\">Index</div><div class='nav-item' onclick=\"loadDefault()\">Market</div><div class='nav-item' onclick=\"loadDefault()\">Status</div>"
    else:
        header_html = ''.join([f"<div class='nav-item' onclick=\"navigate('{n[2]}')\">{n[1]}</div>" for n in header_buttons])
    # footer html
    if not footer_buttons:
        footer_html = "<div class='nav-item' onclick=\"navigate('/home')\">Home</div><div class='nav-item' onclick=\"navigate('/watchlist')\">Watchlist</div><div class='nav-item' onclick=\"navigate('/orders')\">Orders</div><div class='nav-item' onclick=\"navigate('/account')\">Account</div><div class='nav-item' onclick=\"navigate('/admin/panel')\">Admin</div>"
    else:
        footer_html = ''.join([f"<div class='nav-item' onclick=\"navigate('{n[2]}')\">{n[1]}</div>" for n in footer_buttons])

    # return full shell: header / dynamic middle / footer
    return HTMLResponse(f"""
<html>
<head>
  <meta name='viewport' content='width=device-width,initial-scale=1' />
  <style>
    :root{{--header-h:72px;--footer-h:72px;}}
    body{{margin:0;font-family:Arial;background:#f4f6f8;-webkit-font-smoothing:antialiased}}
    .header{{position:fixed;top:0;left:0;right:0;height:var(--header-h);background:#0f172a;color:white;display:flex;align-items:center;justify-content:space-around;z-index:1000;gap:8px;padding:0 8px}}
    .header .nav-item{{padding:10px 14px;cursor:pointer;font-size:16px;border-radius:8px}}
    .header .nav-item:hover{{background:rgba(255,255,255,0.04)}}
    .footer{{position:fixed;bottom:0;left:0;right:0;height:var(--footer-h);background:#0f172a;color:white;display:flex;align-items:center;justify-content:space-around;z-index:1000;padding:0 6px;gap:6px}}
    .footer .nav-item{{flex:1;text-align:center;padding:10px 6px;cursor:pointer;font-size:13px}}
    .footer .nav-item:hover{{background:rgba(255,255,255,0.03);border-radius:8px}}
    .middle{{padding:calc(var(--header-h) + 12px) 12px calc(var(--footer-h) + 12px) 12px;height:calc(100vh - (var(--header-h) + var(--footer-h)) - 24px);overflow:auto}}
    .card{{background:white;border-radius:12px;padding:18px;margin-bottom:14px;box-shadow:0 6px 18px rgba(2,6,23,0.06)}}
    .deployed-block{width:100%;min-height:260px;padding:0;margin:0}
    .big-btn{display:inline-block;padding:10px 14px;border-radius:8px;border:none;background:#0b84ff;color:white;cursor:pointer;margin-right:8px}
    /* ensure any embedded content (from user) takes width */
    .deployed-block > *{max-width:100% !important;box-sizing:border-box}
  </style>
</head>
<body>
  <div class='header'>
    {header_html}
  </div>

  <div class='middle' id='middle'>
    <div class='card' id='dynamic-card'>
      <h3 style='margin-top:0'>Live UI Blocks</h3>
      <div id='dynamic-area' style='width:100%'></div>
    </div>

    <div class='card'>
      <h3 style='margin-top:0'>Market News</h3>
      <div id='news-area'>Live news & signals will appear here.</div>
    </div>

    <div class='card'>
      <h3 style='margin-top:0'>Quick Actions</h3>
      <button class='big-btn' onclick="fetch('/broker/balance').then(r=>r.json()).then(d=>alert(JSON.stringify(d)))">Check Balance</button>
      <button class='big-btn' onclick="navigate('/admin/panel')">Open Admin</button>
    </div>
  </div>

  <div class='footer'>
    {footer_html}
  </div>

<script>
// load active deployed blocks into dynamic-area (full-width)
async function loadActive(){
  try{
    const res = await fetch('/code/active');
    const text = await res.text();
    const area = document.getElementById('dynamic-area');
    area.innerHTML = text;
    // optional: make deployed blocks clickable or interactive
    // scroll to top
    document.getElementById('middle').scrollTop = 0;
  }catch(e){
    console.error(e);
  }
}

// load nav route content (if admin saved custom code for route)
async function navigate(path){
  if(!path) return;
  // if admin route -> open admin panel in same tab (full admin control)
  if(path.startsWith('/admin')){
    window.location.href = path;
    return;
  }
  // try to fetch nav content from /nav/content?route=...
  try{
    const url = '/nav/content?route=' + encodeURIComponent(path);
    const res = await fetch(url);
    if(res.status===200){
      const html = await res.text();
      document.getElementById('dynamic-area').innerHTML = html;
      // ensure scroll to top of middle
      document.getElementById('middle').scrollTop = 0;
      return;
    }
  }catch(e){/* continue to fallback */}
  // fallback: navigate to path (may be external or other route)
  window.location.href = path;
}

// initial load
loadActive();

// optionally refresh active blocks every 30s (you can remove/change)
setInterval(loadActive, 30000);
</script>
</body>
</html>
""")

# ---------------------------
# Broker endpoints
# ---------------------------
@app.post('/broker/buy')
async def broker_buy(symbol: str = Form(...), qty: float = Form(...), price: Optional[float] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    return broker.place_order(symbol=symbol, side='BUY', type_='MARKET' if not price else 'LIMIT', quantity=qty, price=price)

@app.post('/broker/sell')
async def broker_sell(symbol: str = Form(...), qty: float = Form(...), price: Optional[float] = Form(None), token: Optional[str] = Form(None)):
    require_admin(token)
    return broker.place_order(symbol=symbol, side='SELL', type_='MARKET' if not price else 'LIMIT', quantity=qty, price=price)

@app.get('/broker/balance')
def broker_balance(token: Optional[str] = None):
    require_admin(token)
    try:
        return broker.account_balance()
    except Exception as e:
        return JSONResponse({'error': str(e)}, status_code=400)

# ---------------------------
# Status / simple logs
# ---------------------------
@app.get('/status')
def status():
    conn = db_conn(); cur = conn.cursor(); cur.execute('SELECT COUNT(*) FROM ui_blocks'); c = cur.fetchone()[0]; conn.close()
    return {'status':'ok','blocks':c,'time': now_ts()}

# ---------------------------
# Exception handler (basic)
# ---------------------------
from fastapi import Request
@app.exception_handler(Exception)
async def global_exc(request: Request, exc: Exception):
    try:
        conn = db_conn(); cur = conn.cursor(); cur.execute('INSERT INTO logs (ts, level, message) VALUES (?,?,?)', (now_ts(), 'ERROR', str(exc))); conn.commit(); conn.close()
    except: pass
    return JSONResponse({'detail':'internal error'}, status_code=500)

# ---------------------------
# End of file
# ---------------------------
