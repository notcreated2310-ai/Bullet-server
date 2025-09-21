from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# Fake in-memory storage
deployed_code = ""
approved = False

# ------------------------
# Admin Login
# ------------------------
@app.post("/admin/login")
async def admin_login(
    username: str = Form(...),
    password: str = Form(...)
):
    if username == "admin" and password == "40394039":
        return {"status": "success", "msg": "Login successful"}
    else:
        return {"status": "error", "msg": "Invalid credentials"}


# ------------------------
# Deploy Code
# ------------------------
@app.post("/code/deploy")
async def deploy_code(code: str = Form(...)):
    global deployed_code, approved
    deployed_code = code
    approved = False
    return {"status": "success", "msg": "Code deployed", "code": deployed_code}


# ------------------------
# Approve Code
# ------------------------
@app.post("/code/approve")
async def approve_code():
    global approved
    if not deployed_code:
        return {"status": "error", "msg": "No code deployed"}
    approved = True
    return {"status": "success", "msg": "Code approved"}


# ------------------------
# Active Code (UI refresh)
# ------------------------
@app.get("/code/active", response_class=HTMLResponse)
async def get_active_code():
    if not deployed_code:
        return "<h3>No code deployed yet.</h3>"
    if not approved:
        return f"<h3>Pending Approval</h3><pre>{deployed_code}</pre>"
    return f"<h3>Approved Code</h3><pre>{deployed_code}</pre>"


# ------------------------
# Admin Panel (open in WebViewer)
# ------------------------
@app.get("/admin/panel", response_class=HTMLResponse)
async def admin_panel():
    return """
    <html>
    <body>
        <h2>Admin Panel</h2>
        <p>Use the mobile app to deploy and approve code.</p>
    </body>
    </html>
    """
        
