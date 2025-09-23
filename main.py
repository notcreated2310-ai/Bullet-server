import sqlite3, os, time, logging, uuid, json
from typing import Optional
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

# ---------------------------
# Config
# ---------------------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "./data.db")
LOG_FILE = os.environ.get("LOG_FILE", "./server.log")
MAX_CODE_BYTES = int(os.environ.get("MAX_CODE_BYTES", "200000"))

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------
# App
# ---------------------------
app = FastAPI(title="Bullet Server")

# ---------------------------
# DB
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS ui_blocks (id TEXT PRIMARY KEY, title TEXT, category TEXT, code TEXT, created_at INTEGER, approved INTEGER DEFAULT 1)")
    cur.execute("CREATE TABLE IF NOT EXISTS deploy_history (id TEXT PRIMARY KEY, block_id TEXT, action TEXT, detail TEXT, ts INTEGER)")
    cur.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, level TEXT, message TEXT)")
    conn.commit(); conn.close()

init_db()

def now_ts(): return int(time.time())
def db_conn(): return sqlite3.connect(DB_PATH)
def save_log(level, msg):
    try:
        conn = db_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO logs (ts, level, message) VALUES (?,?,?)", (now_ts(), level, msg))
        conn.commit(); conn.close()
    except: pass

def require_admin(token: Optional[str]):
    if not ADMIN_TOKEN: return True
    if not token: raise HTTPException(403, "Admin token required")
    if token != ADMIN_TOKEN: raise HTTPException(403, "Invalid admin token")
    return True

# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def root():
    return {"status": "ok", "msg": "Server is live"}

@app.get("/admin/autologin")
def autologin():
    return {"status": "success", "message": "Login successful", "admin_token": ADMIN_TOKEN}

@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return """
    <html><body>
    <h2>Admin Control</h2>
    <form action='/code/deploy' method='post'>
    <input name='title' placeholder='Title'><br>
    <input name='category' placeholder='Category'><br>
    <textarea name='code' rows='10' cols='70'></textarea><br>
    <button type='submit'>Deploy</button>
    </form>
    </body></html>"""

@app.post("/code/deploy")
async def code_deploy(request: Request):
    form = await request.form()
    token = form.get('token') or request.query_params.get('token')
    require_admin(token)
    title = form.get('title','Untitled')
    category = form.get('category','misc')
    code = form.get('code','')
    if not code: raise HTTPException(400,"code required")
    if len(code.encode()) > MAX_CODE_BYTES: raise HTTPException(400,"code too large")
    block_id = str(uuid.uuid4()); ts = now_ts()
    conn = db_conn(); cur = conn.cursor()
    cur.execute("INSERT INTO ui_blocks (id,title,category,code,created_at,approved) VALUES (?,?,?,?,?,1)",(block_id,title,category,code,ts))
    conn.commit()
    cur.execute("INSERT INTO deploy_history (id,block_id,action,detail,ts) VALUES (?,?,?,?,?)",(str(uuid.uuid4()),block_id,'deploy',json.dumps({'title':title}),ts))
    conn.commit(); conn.close()
    return {"status":"ok","block_id":block_id}

@app.get("/code/active")
def active():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT code FROM ui_blocks WHERE approved=1 ORDER BY created_at")
    rows = cur.fetchall(); conn.close()
    if not rows: return {"status":"empty"}
    return HTMLResponse("\n".join(r[0] for r in rows))

@app.get("/ui", response_class=HTMLResponse)
def ui():
    conn = db_conn(); cur = conn.cursor()
    cur.execute("SELECT code FROM ui_blocks WHERE approved=1 ORDER BY created_at")
    rows = cur.fetchall(); conn.close()
    if not rows: return HTMLResponse("<h3>No UI</h3>")
    return HTMLResponse("<html><body>%s</body></html>"%"\n".join(r[0] for r in rows))

@app.get("/status")
def status():
    conn = db_conn(); cur = conn.cursor(); cur.execute("SELECT COUNT(*) FROM ui_blocks"); c=cur.fetchone()[0]; conn.close()
    return {"status":"ok","blocks":c,"time":now_ts()}

@app.exception_handler(Exception)
async def handler(req,exc):
    save_log('ERR',str(exc)); return JSONResponse(status_code=500,content={"detail":"Internal error"})
    
