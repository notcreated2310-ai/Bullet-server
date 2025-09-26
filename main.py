from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, os, sqlite3, json, datetime, traceback

# ------------------------------
# App Initialization
# ------------------------------
app = FastAPI(title="Bullet Server - V3")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates & Static
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# ------------------------------
# Database Setup
# ------------------------------
DB_PATH = os.path.join(BASE_DIR, "appdata.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Users
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    # Logs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event TEXT,
            details TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Dynamic UI blocks
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ui_blocks(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            block_name TEXT,
            block_type TEXT,
            config TEXT,
            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------------------
# Utility Helpers
# ------------------------------
def log_event(event, details=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (event, details) VALUES (?, ?)", (event, details))
    conn.commit()
    conn.close()

def get_logs(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT event, details, created FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_ui_blocks():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, block_name, block_type, config, created FROM ui_blocks ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

# ------------------------------
# Routes - Public
# ------------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "Bullet Server Home"})

@app.get("/ui", response_class=HTMLResponse)
async def ui_page(request: Request):
    blocks = get_ui_blocks()
    return templates.TemplateResponse("ui.html", {"request": request, "blocks": blocks})

# ------------------------------
# Routes - Authentication
# ------------------------------
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        log_event("login", f"{username} logged in")
        return RedirectResponse(url="/admin", status_code=303)
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)

@app.post("/register")
async def register(username: str = Form(...), password: str = Form(...)):
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        log_event("register", f"new user {username}")
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# ------------------------------
# Routes - Admin
# ------------------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    blocks = get_ui_blocks()
    logs = get_logs(30)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "blocks": blocks,
        "logs": logs
    })

@app.post("/admin/add-block")
async def add_block(
    block_name: str = Form(...),
    block_type: str = Form(...),
    config: str = Form(...)
):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT INTO ui_blocks (block_name, block_type, config) VALUES (?, ?, ?)",
                (block_name, block_type, config))
    conn.commit()
    conn.close()
    log_event("add_block", f"{block_name} ({block_type})")
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/delete-block")
async def delete_block(block_id: int = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM ui_blocks WHERE id=?", (block_id,))
    conn.commit()
    conn.close()
    log_event("delete_block", f"id={block_id}")
    return RedirectResponse(url="/admin", status_code=303)

# ------------------------------
# Routes - Advanced Features
# ------------------------------
@app.get("/api/logs")
async def api_logs(limit: int = 20):
    return {"logs": get_logs(limit)}

@app.get("/api/blocks")
async def api_blocks():
    blocks = get_ui_blocks()
    data = [
        {"id": b[0], "name": b[1], "type": b[2], "config": b[3], "created": b[4]}
        for b in blocks
    ]
    return {"blocks": data}

@app.post("/admin/run-code")
async def run_code(code: str = Form(...)):
    try:
        safe_globals = {"__builtins__": {"print": print, "len": len, "range": range}}
        safe_locals = {}
        exec(code, safe_globals, safe_locals)
        log_event("run_code", code[:100])
        return {"result": "Executed successfully", "output": str(safe_locals)}
    except Exception as e:
        log_event("run_code_error", str(e))
        return {"error": str(e), "trace": traceback.format_exc()}

import sqlite3

@app.get("/init-admin")
async def init_admin():
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    # अगर पहले से admin है तो create नहीं होगा
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin123", "superadmin"))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Default admin created → username: admin / password: admin123"}

from fastapi.responses import RedirectResponse

# -----------------------
# Login Form (UI)
# -----------------------
@app.get("/login", response_class=HTMLResponse)
async def login_form():
    return """
    <html>
    <head>
        <title>Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(to right, #2c3e50, #3498db);
                height: 100vh;
                margin: 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .card {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                width: 350px;
                text-align: center;
            }
            h2 {
                margin-bottom: 20px;
                color: #333;
            }
            input[type="text"], input[type="password"] {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            button {
                width: 100%;
                padding: 12px;
                background: #3498db;
                color: white;
                font-size: 16px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }
            button:hover {
                background: #2980b9;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🔑 Secure Login</h2>
            <form method="post" action="/login">
                <input type="text" name="username" placeholder="Username" required><br>
                <input type="password" name="password" placeholder="Password" required><br>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """

# -----------------------
# Login Action (POST)
# -----------------------
@app.post("/login")
async def login_action(username: str = Form(...), password: str = Form(...)):
    import sqlite3
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    row = cur.fetchone()
    conn.close()

    if row:
        role = row[0]
        # ✅ Redirect to Admin Panel after success
        return RedirectResponse(url="/admin", status_code=303)
    else:
        return JSONResponse({"status": "error", "message": "Invalid credentials"})
    
# ------------------------------
# Server Runner
# ------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

