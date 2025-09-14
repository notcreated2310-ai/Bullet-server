# app/main.py
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import os, requests, json, subprocess
from uuid import uuid4
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(title="Trading Automation Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory DB for demo (replace with Postgres)
DB = {
    "users": {},
    "ui_config": {},      # admin editable UI config JSON
    "broker_tokens": {},  # user_id -> token details (encrypted in prod)
    "audit": []
}

# ------------ Auth stubs ------------
class LoginIn(BaseModel):
    username: str
    password: str

@app.post("/auth/register")
def register(u: LoginIn):
    if u.username in DB["users"]:
        raise HTTPException(400, "user exists")
    DB["users"][u.username] = {"password": u.password}
    return {"ok": True, "user": u.username}

@app.post("/auth/login")
def login(u: LoginIn):
    user = DB["users"].get(u.username)
    if not user or user["password"] != u.password:
        raise HTTPException(401, "invalid credentials")
    # return a naive token
    token = str(uuid4())
    user["token"] = token
    return {"token": token, "user": u.username}

def get_current_user(token: str = ""):
    # quick check: token passed as query or header in real app use OAuth2
    for username, info in DB["users"].items():
        if info.get("token") == token:
            return username
    raise HTTPException(401, "invalid token")

# ------------ Broker connect (placeholder for Finvasia) ------------
class BrokerConnectIn(BaseModel):
    user: str
    api_key: str
    username: str
    password: str

@app.post("/broker/connect")
def broker_connect(payload: BrokerConnectIn, user=Depends(get_current_user)):
    # --- Replace with real Finvasia login flow; this is a placeholder ---
    # You must implement Finvasia authentication here: form post, OTP handling, etc.
    token = f"demo-token-{uuid4()}"
    DB["broker_tokens"][user] = {"token": token, "meta": {"api_key": payload.api_key}}
    DB["audit"].append({"action": "broker_connect", "user": user})
    return {"ok": True, "token": token}

@app.get("/portfolio")
def portfolio(user=Depends(get_current_user)):
    # placeholder: return demo portfolio
    t = DB["broker_tokens"].get(user)
    if not t:
        raise HTTPException(404, "no broker connected")
    return {
        "balance": 100000.0,
        "holdings": [
            {"symbol": "NIFTY", "qty": 5, "ltp": 21400, "value": 107000},
            {"symbol": "RELIANCE", "qty": 2, "ltp": 2500, "value": 5000}
        ],
    }

# ------------ Place order (manual) ------------
class OrderIn(BaseModel):
    symbol: str
    qty: int
    side: str
    order_type: str
    price: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None

@app.post("/order/place")
def place_order(o: OrderIn, user=Depends(get_current_user)):
    # map to broker API here
    DB["audit"].append({"action": "place_order", "user": user, "order": o.dict()})
    return {"ok": True, "order_id": str(uuid4()), "status": "queued"}

# ------------ Admin endpoints ------------
class UIConfigIn(BaseModel):
    config: dict

@app.post("/admin/ui-config")
def set_ui_config(payload: UIConfigIn, user=Depends(get_current_user)):
    # check admin flag (simple)
    if user != "admin":
        raise HTTPException(403, "admin only")
    DB["ui_config"] = payload.config
    DB["audit"].append({"action": "set_ui", "user": user})
    return {"ok": True}

# Trigger GitHub workflow_dispatch to deploy (requires GITHUB_TOKEN env & repo info)
class DeployRequest(BaseModel):
    ref: str = "main"
    message: Optional[str] = "Admin triggered deploy"

@app.post("/admin/trigger-deploy")
def trigger_deploy(req: DeployRequest, user=Depends(get_current_user), background: BackgroundTasks = None):
    if user != "admin":
        raise HTTPException(403, "admin only")
    # call GitHub API workflow dispatch
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    GITHUB_OWNER = os.environ.get("GITHUB_OWNER")
    GITHUB_REPO = os.environ.get("GITHUB_REPO")
    WORKFLOW_ID = os.environ.get("GITHUB_WORKFLOW_ID", "deploy.yml")
    if not (GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO):
        raise HTTPException(500, "github env not configured")
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    body = {"ref": req.ref, "inputs": {"message": req.message}}
    r = requests.post(url, headers=headers, json=body)
    if r.status_code not in (204, 201):
        raise HTTPException(500, f"github dispatch failed: {r.status_code} {r.text}")
    DB["audit"].append({"action": "trigger_deploy", "user": user, "ref": req.ref})
    return {"ok": True, "detail": "workflow dispatched"}

@app.get("/admin/audit")
def get_audit(user=Depends(get_current_user)):
    if user != "admin":
        raise HTTPException(403, "admin only")
    return DB["audit"]
  
