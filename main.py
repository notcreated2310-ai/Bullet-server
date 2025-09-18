from fastapi import FastAPI, Request
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
# Admin Login (Raw Text Format)
# -----------------------
@app.post("/admin/login")
async def admin_login(request: Request):
    try:
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
        ADMIN_USER = os.getenv("ADMIN_USER", "admin")
        ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

        if admin_id == ADMIN_USER and admin_pass == ADMIN_PASS:
            return {"status": "success", "msg": "Login successful"}
        else:
            return {"status": "fail", "msg": "Invalid credentials"}

    except Exception as e:
        return JSONResponse(content={"status": "error", "msg": str(e)}, status_code=500)

# -----------------------
# Admin Panel UI (HTML)
# -----------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    try:
        with open("admin.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h2>Admin Panel Not Found</h2>"

# -----------------------
# Admin Deploy Endpoint
# -----------------------
@app.post("/admin/deploy")
async def deploy_code(request: Request):
    try:
        data = await request.json()
        code = data.get("code", "")

        if not code.strip():
            return {"status": "error", "msg": "No code provided"}

        # Code को server पर save करो
        with open("strategy.py", "w", encoding="utf-8") as f:
            f.write(code)

        # Future: यहां auto-reload / run logic add कर सकते हो
        return {"status": "success", "msg": "Code saved successfully"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# -----------------------
# Broker Balance Example
# -----------------------
@app.get("/balance")
def get_balance():
    # Dummy response — future में real broker API से connect करना है
    return {"balance": 100000, "currency": "INR"}
            
