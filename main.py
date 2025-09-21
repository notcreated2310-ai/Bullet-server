from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI()

# -----------------------
# Root Route (Test)
# -----------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Direct Auto Login (No credentials)
# -----------------------
@app.get("/admin/autologin")
def auto_login():
    return {"status": "success", "message": "Login successful"}

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
        <p>Status: Auto-Deploy Mode (No Manual Approval Needed)</p>

        <form action="/code/deploy" method="post">
            <label>Paste HTML / UI Code below:</label><br>
            <textarea name="code" rows="12" cols="80"></textarea><br><br>
            <button type="submit">Deploy & Refresh</button>
        </form>
    </body>
    </html>
    """

# -----------------------
# Dynamic Code Deploy System (Auto-Approve)
# -----------------------
approved_code = """
<h2>🚀 Default UI</h2>
<p>No code deployed yet.</p>
"""

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    """
    Deploy code → auto approve → refresh
    """
    global approved_code
    approved_code = code  # सीधे approve कर दिया
    return {
        "status": "approved",
        "msg": "Code deployed & approved successfully",
        "refresh_url": "/ui"
    }

@app.get("/ui", response_class=HTMLResponse)
def get_active_ui():
    """
    Always serve the approved (active) UI code
    """
    global approved_code
    return HTMLResponse(content=approved_code)
         
