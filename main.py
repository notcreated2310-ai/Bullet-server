from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import JSONResponse, HTMLResponse
import os

app = FastAPI()

# Simple in-memory storage
CODE_STORAGE = {
    "pending": None,
    "active": None
}


# --- Auto Login (no credentials needed) ---
@app.get("/admin/autologin")
async def auto_login():
    return {"status": "success", "message": "Auto login successful"}
    
# --- Code Deploy ---
@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    CODE_STORAGE["pending"] = code
    return {"status": "success", "message": "Code deployed. Waiting for approval."}


# --- Code Approve ---
@app.post("/code/approve")
async def code_approve():
    if CODE_STORAGE["pending"]:
        CODE_STORAGE["active"] = CODE_STORAGE["pending"]
        CODE_STORAGE["pending"] = None
        return {"status": "success", "message": "Code approved & active."}
    return {"status": "error", "message": "No pending code found."}


# --- Active Code (returns HTML directly) ---
@app.get("/code/active")
async def code_active():
    if CODE_STORAGE["active"]:
        return HTMLResponse(content=CODE_STORAGE["active"])
    return HTMLResponse("<h3>No active code found.</h3>")


# --- UI Preview (helper route) ---
@app.get("/ui")
async def ui_preview():
    if CODE_STORAGE["active"]:
        return HTMLResponse(content=CODE_STORAGE["active"])
    return HTMLResponse("<h3>No UI deployed yet.</h3>")


# --- Root ---
@app.get("/")
async def root():
    return {"message": "✅ Server is live. Use /admin/login, /code/deploy, /code/approve, /code/active, /ui"}
        
