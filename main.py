from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import os
from datetime import datetime

app = FastAPI()

# Static & Templates setup
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

DB_FILE = "app.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            level TEXT,
            message TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS components(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            position TEXT,
            config TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------- Utility ----------
def log_event(level, message):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO logs (ts, level, message) VALUES (?,?,?)",
            (datetime.now().isoformat(), level, message)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Logging failed:", e)

# ---------- Routes ----------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/ui", response_class=HTMLResponse)
async def ui(request: Request):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM components")
    comps = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("ui.html", {"request": request, "components": comps})

@app.post("/add_component")
async def add_component(
    name: str = Form(...),
    type: str = Form(...),
    position: str = Form(...),
    config: str = Form("")
):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO components (name, type, position, config) VALUES (?,?,?,?)",
            (name, type, position, config)
        )
        conn.commit()
        conn.close()
        log_event("INFO", f"Component added: {name}")
        return RedirectResponse("/ui", status_code=303)
    except Exception as e:
        log_event("ERROR", str(e))
        return JSONResponse({"error": str(e)})
      @app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM components")
    comps = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("admin.html", {"request": request, "components": comps})

@app.post("/delete_component")
async def delete_component(id: int = Form(...)):
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("DELETE FROM components WHERE id=?", (id,))
        conn.commit()
        conn.close()
        log_event("INFO", f"Component deleted: {id}")
        return RedirectResponse("/admin", status_code=303)
    except Exception as e:
        log_event("ERROR", str(e))
        return JSONResponse({"error": str(e)})

@app.get("/logs", response_class=HTMLResponse)
async def logs(request: Request):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 100")
    logs = cur.fetchall()
    conn.close()
    return templates.TemplateResponse("logs.html", {"request": request, "logs": logs})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_event("ERROR", str(exc))
    return JSONResponse(
        status_code=500,
        content={"message": f"Internal server error: {str(exc)}"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
