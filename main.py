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
# Auto-Login (No Credentials Needed)
# -----------------------
@app.get("/admin/login")
def auto_login():
    return {"status": "success", "msg": "Auto-login successful"}

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
            <label>Paste HTML / UI Code below:</label><br>
            <textarea name="code" rows="12" cols="80"></textarea><br><br>
            <button type="submit">Deploy & Refresh</button>
        </form>
    </body>
    </html>
    """

# -----------------------
# Dynamic Code Deploy (Auto-Approve)
# -----------------------
approved_code = "<h2>🚀 Default UI Ready</h2>"

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    """
    Code submit karega, auto-approve hote hi /ui par update ho jayega
    """
    global approved_code
    approved_code = code
    return {"status": "success", "msg": "Code deployed & approved successfully"}

# -----------------------
# Active UI Endpoint
# -----------------------
@app.get("/ui", response_class=HTMLResponse)
def get_active_ui():
    """
    Approved code ko directly render karega as UI
    """
    global approved_code
    return approved_code
    
