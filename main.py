from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os

app = FastAPI()

# -----------------------
# Root Route (Test)
# -----------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Admin Login (auto fallback)
# -----------------------
@app.post("/admin/login")
async def admin_login(
    username: str = Form("admin"),
    password: str = Form("1234")
):
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

    if username == ADMIN_USER and password == ADMIN_PASS:
        return {"status": "success", "message": "Login successful"}
    else:
        return JSONResponse(
            status_code=401,
            content={"status": "error", "message": "Invalid credentials"}
        )

# -----------------------
# Example Broker API (Dummy)
# -----------------------
@app.get("/balance")
def get_balance():
    return {"balance": 100000, "currency": "INR"}

# -----------------------
# Admin Panel (HTML page with code box)
# -----------------------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return """
    <html>
    <head><title>Admin Control Center</title></head>
    <body style="font-family: Arial; margin:40px;">
        <h2>Admin Control Center</h2>
        <p>Status: Ready</p>

        <form action="/code/deploy" method="post">
            <label>Paste Python code / strategy below:</label><br>
            <textarea name="code" rows="12" cols="80"></textarea><br><br>
            <button type="submit">Deploy Code</button>
        </form>
    </body>
    </html>
    """

# -----------------------
# Dynamic Code Deploy System
# -----------------------
pending_code = None
approved_code = None

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    global pending_code
    pending_code = code
    return {"status": "pending", "msg": "Code received, waiting for approval"}

@app.get("/code/pending")
def get_pending_code():
    global pending_code
    if pending_code:
        return {"status": "pending", "code": pending_code}
    else:
        return {"status": "empty", "msg": "No pending code"}

@app.post("/code/approve")
async def approve_code():
    global pending_code, approved_code
    if pending_code:
        approved_code = pending_code
        pending_code = None
        return {"status": "approved", "msg": "Code approved successfully"}
    else:
        return {"status": "fail", "msg": "No pending code to approve"}

# -----------------------
# Active Code (Direct HTML)
# -----------------------
@app.get("/code/active", response_class=HTMLResponse)
def get_active_code():
    global approved_code
    if approved_code:
        return f"""<html><body>
        <h3>🚀 Active Strategy</h3>
        <pre style="background:#f4f4f4;padding:10px;border-radius:8px;">{approved_code}</pre>
        </body></html>"""
    else:
        return """<html><body><p>No active code available</p></body></html>"""

# -----------------------
# UI Endpoint (for AppInventor WebViewer)
# -----------------------
@app.get("/ui", response_class=HTMLResponse)
def ui_page():
    return """
    <html>
    <head><title>Bullet App UI</title></head>
    <body style="font-family: Arial; margin:20px;">
        <h2>📲 Bullet App Live UI</h2>
        <iframe src="/code/active" width="100%" height="400" style="border:1px solid #ccc;"></iframe>
        <p style="margin-top:20px;color:gray;">Auto-refresh by clicking Refresh in app</p>
    </body>
    </html>
    """
    
