from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os, datetime

app = FastAPI()

# ----------------------------
# Database setup
# ----------------------------
DB_FILE = "database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Active deployed UI
    cur.execute("""
    CREATE TABLE IF NOT EXISTS deployed_ui (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        code TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Logs (errors + actions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        level TEXT,
        message TEXT
    )
    """)

    # Broker API settings
    cur.execute("""
    CREATE TABLE IF NOT EXISTS broker_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        broker_name TEXT,
        api_key TEXT,
        api_secret TEXT,
        mode TEXT DEFAULT 'testnet'
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ----------------------------
# Templates & Static
# ----------------------------
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----------------------------
# Root Test Route
# ----------------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "Server is live"}

# ----------------------------
# Auto Login
# ----------------------------
@app.get("/admin/autologin")
def auto_login():
    return {"status": "success", "message": "Auto login successful"}

# ----------------------------
# Admin Panel UI
# ----------------------------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

# ----------------------------
# Deploy New UI
# ----------------------------
@app.post("/code/deploy")
async def code_deploy(category: str = Form(...), code: str = Form(...)):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO deployed_ui (category, code) VALUES (?, ?)", (category, code))
        conn.commit()
        conn.close()
        return {"status": "approved", "msg": "UI deployed successfully"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# ----------------------------
# View Active UI
# ----------------------------
@app.get("/code/active/{category}", response_class=HTMLResponse)
def get_active_code(category: str):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT code FROM deployed_ui WHERE category=? ORDER BY id DESC LIMIT 1", (category,))
    row = cur.fetchone()
    conn.close()
    if row:
        return HTMLResponse(content=row[0])
    else:
        return HTMLResponse("<h3>No UI Deployed for this category</h3>")
  # ----------------------------
# Rollback (delete all UI of a category)
# ----------------------------
@app.post("/admin/rollback")
async def rollback(category: str = Form(...)):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM deployed_ui WHERE category=?", (category,))
        conn.commit()
        conn.close()
        return {"status": "ok", "msg": f"Rolled back all UI for category {category}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# ----------------------------
# List Deployment History
# ----------------------------
@app.get("/admin/history")
def get_history():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, category, created_at FROM deployed_ui ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.close()
    return {"status": "ok", "history": rows}

# ----------------------------
# Logs view
# ----------------------------
@app.get("/admin/logs")
def get_logs():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT ts, level, message FROM logs ORDER BY id DESC LIMIT 100")
    rows = cur.fetchall()
    conn.close()
    return {"status": "ok", "logs": rows}

# ----------------------------
# Broker Settings Save
# ----------------------------
@app.post("/broker/save")
async def save_broker(
    broker_name: str = Form(...),
    api_key: str = Form(...),
    api_secret: str = Form(...),
    mode: str = Form("testnet")
):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO broker_settings (broker_name, api_key, api_secret, mode) VALUES (?, ?, ?, ?)",
                    (broker_name, api_key, api_secret, mode))
        conn.commit()
        conn.close()
        return {"status": "ok", "msg": "Broker settings saved"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# ----------------------------
# Broker Settings View
# ----------------------------
@app.get("/broker/settings")
def view_broker():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT broker_name, mode, created_at FROM broker_settings ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return {"status": "ok", "broker": row}
    else:
        return {"status": "empty"}

# ----------------------------
# Global Exception Handler
# ----------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("INSERT INTO logs (level, message) VALUES (?, ?)", ("ERROR", str(exc)))
        conn.commit()
        conn.close()
    except:
        pass
    return JSONResponse(status_code=500, content={"status": "error", "msg": str(exc)})
  
