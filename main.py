import sqlite3
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Static + Templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ---------------- Database Init ----------------
def init_db():
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    # Users Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    # Components Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            position TEXT,
            config TEXT
        )
    """)
    # Create default admin
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin123", "superadmin"))
    conn.commit()
    conn.close()

# Initialize DB
init_db()

# ---------------- Home / UI ----------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT name, type, position, config FROM components")
    components = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("ui.html", {"request": request, "components": components})
# ---------------- Admin Panel ----------------
@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, type, position, config FROM components")
    components = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "components": components})

# Add Component (from Admin Form)
@app.post("/add-component")
async def add_component(
    name: str = Form(...),
    type: str = Form(...),
    position: str = Form(...),
    config: str = Form(...)
):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("INSERT INTO components (name, type, position, config) VALUES (?, ?, ?, ?)",
                (name, type, position, config))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

# Delete Component
@app.get("/delete-component/{comp_id}")
async def delete_component(comp_id: int):
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM components WHERE id=?", (comp_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/admin", status_code=303)

# ---------------- Extra Routes ----------------
@app.get("/init-admin")
async def init_admin():
    conn = sqlite3.connect("app.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                ("admin", "admin123", "superadmin"))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Default admin created → username: admin / password: admin123"}

# Test Route
@app.get("/ping")
async def ping():
    return {"message": "pong"}
    
@app.get("/admin/autologin")
def auto_login():
    return {"status": "success", "message": "Login successful"}
    
# Auto-login always ON → /admin direct open
# (No login form required)
