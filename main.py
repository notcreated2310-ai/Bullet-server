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
    """
    Code submit karega (pending state me)
    """
    global pending_code
    pending_code = code
    return {"status": "pending", "msg": "Code received, waiting for approval"}

@app.get("/code/pending")
def get_pending_code():
    """
    Admin ko dikhane ke liye pending code
    """
    global pending_code
    if pending_code:
        return {"status": "pending", "code": pending_code}
    else:
        return {"status": "empty", "msg": "No pending code"}

@app.post("/code/approve")
async def approve_code():
    """
    Pending code ko approve karke active bana dega
    """
    global pending_code, approved_code
    if pending_code:
        approved_code = pending_code
        pending_code = None
        return {"status": "approved", "msg": "Code approved successfully"}
    else:
        return {"status": "fail", "msg": "No pending code to approve"}

@app.get("/code/active")
def get_active_code():
    """
    Currently active (approved) code dikhayega
    """
    global approved_code
    if approved_code:
        return HTMLResponse(content=approved_code)  # direct HTML return karega
    else:
        return {"status": "empty", "msg": "No active code"}

# -----------------------
# Simple UI Preview (GET)
# -----------------------
@app.get("/ui", response_class=HTMLResponse)
def preview_ui():
    global approved_code
    if approved_code:
        return HTMLResponse(content=approved_code)
    else:
        return HTMLResponse("<h3>No UI Deployed</h3>")
        
