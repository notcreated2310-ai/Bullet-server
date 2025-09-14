# main.py
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import os, requests, json, uuid

app = FastAPI(title="Control Center - Trading Backend")

# Simple in-memory for demo. Replace with persistent DB in prod.
USERS = {"admin": {"password": "adminpass", "role": "admin"}}
BROKER_SESSIONS: Dict[str, Dict] = {}   # user -> {token, meta}
UI_CONFIG = {"cards": ["balance","positions","quickbuy"]}

# ----- models -----
class BrokerInit(BaseModel):
    app_user: str
    finvasia_user: str
    finvasia_password: str
    api_key: Optional[str] = None

class BrokerOTP(BaseModel):
    app_user: str
    otp: str

class AdminLoginIn(BaseModel):
    username: str
    password: str

class ApproveIn(BaseModel):
    cmd: str
    payload: dict = {}

# ----- util -----
def verify_token(header_token: Optional[str] = Header(None)):
    # naive token verification for demo - replace with JWT
    if header_token and header_token in USERS:
        return header_token
    raise HTTPException(status_code=401, detail="Invalid token")

# ----- root & health -----
@app.get("/")
def root():
    return {"status":"ok","service":"control-center"}

@app.get("/dashboard")
def dashboard():
    return {"status":"ok","users":len(USERS),"ui_config": UI_CONFIG}

# ----- app user auth (basic demo) -----
@app.post("/auth/login")
def auth_login(data: AdminLoginIn):
    u = USERS.get(data.username)
    if not u or u["password"] != data.password:
        raise HTTPException(401, "invalid credentials")
    # return a simple token (in prod use JWT)
    token = data.username  # using username as token for simplicity
    return {"token": token, "role": u.get("role","user")}

# ----- broker login start: call Finvasia auth endpoint (placeholder) -----
@app.post("/broker/initiate_login")
def broker_initiate(data: BrokerInit, token: Optional[str] = Header(None)):
    # ensure app user exists / authorized
    app_user = data.app_user
    # --- CALL FINVASIA AUTH API HERE ---
    # Example placeholder: Finvasia often expects API-key + username+password and returns a response requiring OTP
    # We'll simulate: return {"otp_required": True, "session_id": "..."}
    session_id = str(uuid.uuid4())
    # store temporary session
    BROKER_SESSIONS[app_user] = {"stage":"OTP_PENDING", "session_id": session_id, "meta": {"fin_user": data.finvasia_user}}
    return {"otp_required": True, "message": "OTP sent to registered mobile (simulated)", "session_id": session_id}

# ----- broker submit otp -----
@app.post("/broker/submit_otp")
def broker_submit_otp(body: BrokerOTP):
    app_user = body.app_user
    rec = BROKER_SESSIONS.get(app_user)
    if not rec or rec.get("stage") != "OTP_PENDING":
        raise HTTPException(400, "no pending login")
    otp = body.otp
    # --- CALL FINVASIA VERIFY OTP HERE, exchange for token ---
    # Simulate success if otp length >= 4
    if len(otp) < 3:
        raise HTTPException(400, "invalid otp")
    # simulate token
    broker_token = "broker-token-" + str(uuid.uuid4())
    rec.update({"stage":"LOGGED_IN","token":broker_token})
    return {"ok": True, "token": broker_token, "message":"broker login successful"}

# ----- portfolio endpoint -----
@app.get("/portfolio")
def portfolio(app_user: Optional[str] = None, auth: str = Header(None)):
    # require token: for demo we accept header token equals username
    if not auth or auth not in BROKER_SESSIONS and auth not in USERS:
        # allow app_user param for demo
        pass
    # sample portfolio
    return {
        "balance": 125000.0,
        "holdings":[{"symbol":"NIFTY","qty":2,"ltp":23800,"value":47600},{"symbol":"RELIANCE","qty":3,"ltp":2400,"value":7200}],
        "pnl": 4200.0
    }

# ----- admin endpoints -----
@app.post("/admin/login")
def admin_login(creds: AdminLoginIn):
    u = USERS.get(creds.username)
    if not u or u["password"] != creds.password or u.get("role") != "admin":
        raise HTTPException(401, "invalid admin credentials")
    return {"token": creds.username, "role":"admin"}

@app.post("/admin/ui-config")
def admin_ui_config(payload: dict, auth: Optional[str] = Header(None)):
    # require admin token; in demo token == 'admin'
    if auth != "admin":
        raise HTTPException(403, "admin only")
    UI_CONFIG.clear()
    UI_CONFIG.update(payload)
    return {"ok": True, "ui_config": UI_CONFIG}

@app.post("/admin/approve")
def admin_approve(data: ApproveIn, auth: Optional[str] = Header(None)):
    if auth != "admin":
        raise HTTPException(403, "admin only")
    # Example: if cmd == 'deploy' -> trigger GitHub workflow / Render redeploy
    cmd = data.cmd
    if cmd == "deploy":
        # call GitHub Actions / Render API here (use env vars)
        # For demo just return ok
        return {"ok": True, "action": "deploy_triggered", "payload": data.payload}
    elif cmd == "upgrade_ui":
        UI_CONFIG.update(data.payload or {})
        return {"ok": True, "action":"ui_updated","ui_config": UI_CONFIG}
    else:
        return {"ok": False, "message":"unknown command"}

# ----- run local (for dev only) -----
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=10000, reload=True)
    
