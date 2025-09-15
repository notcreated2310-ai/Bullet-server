from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

# Mount static for favicon
app.mount("/static", StaticFiles(directory="static"), name="static")

# Dummy in-memory session (for demo)
sessions = {"broker": False, "admin": False}

@app.get("/", response_class=HTMLResponse)
def screen1():
    return """
    <h2>📌 Screen 1</h2>
    <form action="/broker-login" method="post">
        <input type="text" name="api_key" placeholder="Broker API Key" required><br>
        <input type="text" name="otp" placeholder="Enter OTP" required><br>
        <button type="submit">Broker Login</button>
    </form>
    <br>
    <form action="/admin-login" method="post">
        <input type="text" name="admin_id" placeholder="Admin ID" required><br>
        <input type="password" name="admin_pass" placeholder="Admin Password" required><br>
        <button type="submit">Admin Login</button>
    </form>
    """

@app.post("/broker-login")
def broker_login(api_key: str = Form(...), otp: str = Form(...)):
    # TODO: integrate real Finvasia API login here
    if api_key == os.getenv("FINVASIA_API_KEY") and otp == "123456":  
        sessions["broker"] = True
        return RedirectResponse("/dashboard", status_code=302)
    return {"error": "Invalid Broker Login"}

@app.post("/admin-login")
def admin_login(admin_id: str = Form(...), admin_pass: str = Form(...)):
    if admin_id == "admin" and admin_pass == os.getenv("ADMIN_PASS", "admin123"):
        sessions["admin"] = True
        return RedirectResponse("/dashboard", status_code=302)
    return {"error": "Invalid Admin Login"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    if not (sessions["broker"] or sessions["admin"]):
        return RedirectResponse("/", status_code=302)

    broker_status = "✅ Connected" if sessions["broker"] else "❌ Not Connected"
    admin_status = "✅ Logged In" if sessions["admin"] else "❌ Not Logged In"

    return f"""
    <h2>📊 Dashboard</h2>
    <p>Broker Status: {broker_status}</p>
    <p>Admin Status: {admin_status}</p>
    <hr>
    <h3>🔧 Admin Control Centre</h3>
    <form action="/upgrade-ui" method="post">
        <button type="submit">Upgrade UI</button>
    </form>
    <form action="/upgrade-backend" method="post">
        <button type="submit">Upgrade Backend</button>
    </form>
    <form action="/upgrade-server" method="post">
        <button type="submit">Upgrade Server</button>
    </form>
    """

@app.post("/upgrade-ui")
def upgrade_ui():
    # TODO: Put your real UI upgrade logic here
    return {"message": "UI upgrade triggered ✅"}

@app.post("/upgrade-backend")
def upgrade_backend():
    # TODO: Put your real backend update logic here
    return {"message": "Backend upgrade triggered ✅"}

@app.post("/upgrade-server")
def upgrade_server():
    # TODO: Put your real server update logic here
    return {"message": "Server upgrade triggered ✅"}
    
