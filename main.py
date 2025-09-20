from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

app = FastAPI()

# memory store
db = {"pending": None, "active": None}

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    db["pending"] = code
    return {"status": "pending", "message": "Code uploaded, waiting for approval"}

@app.post("/code/approve")
async def code_approve():
    if db["pending"]:
        db["active"] = db["pending"]
        db["pending"] = None
        return {"status": "approved", "message": "Code approved successfully"}
    return {"status": "error", "message": "No pending code"}

# अब यहां JSON नहीं, सीधे HTML return होगा
@app.get("/code/active", response_class=HTMLResponse)
async def code_active():
    if db["active"]:
        return db["active"]
    return "<html><body><h3>No active UI yet</h3></body></html>"
    
