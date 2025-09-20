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
# Admin Login (Raw Text Format admin_id|admin_pass)
# -----------------------
@app.post("/admin/login")
async def admin_login(request: Request):
    try:
        # Raw text body (App Inventor से आएगा)
        body = await request.body()
        text_data = body.decode("utf-8").strip()

        # Format: admin_id|admin_pass
        if "|" not in text_data:
            return JSONResponse(
                content={"status": "error", "msg": "Invalid format, use admin|password"},
                status_code=400
            )

        admin_id, admin_pass = text_data.split("|", 1)

        # ✅ Credentials check (Env variables से)
        ADMIN_USER = os.getenv("ADMIN_USER", "admin")     # default = admin
        ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")      # default = 1234

        if admin_id == ADMIN_USER and admin_pass == ADMIN_PASS:
            return {"status": "success", "msg": "Login successful"}
        else:
            return {"status": "fail", "msg": "Invalid credentials"}

    except Exception as e:
        return JSONResponse(content={"status": "error", "msg": str(e)}, status_code=500)

# -----------------------
# Example Broker API (Dummy)
# -----------------------
@app.get("/balance")
def get_balance():
    # Dummy response, यहाँ broker API call करना है
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
            <label>Paste Python/HTML code below:</label><br>
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
    Currently active (approved) code JSON ke format me dikhayega
    """
    global approved_code
    if approved_code:
        return {"status": "active", "code": approved_code}
    else:
        return {"status": "empty", "msg": "No active code"}

# -----------------------
# New Extra Route: /ui (Direct HTML render for App)
# -----------------------
@app.get("/ui", response_class=HTMLResponse)
def ui_page():
    """
    Approved code ko directly HTML me render karega
    """
    global approved_code
    if approved_code:
        return approved_code
    else:
        return "<h3>No active UI found</h3>"
        
