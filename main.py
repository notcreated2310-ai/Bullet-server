from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os

app = FastAPI()

# -----------------------
# Root Route (Test)
# -----------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Admin Login (New)
# -----------------------
@app.post("/admin/login")
async def admin_login(request: Request):
    try:
        # Raw text body (App Inventor से आएगा)
        body = await request.body()
        text_data = body.decode("utf-8").strip()

        # Format: admin_id|admin_pass
        if "|" not in text_data:
            return JSONResponse(content={"status": "error", "msg": "Invalid format, use admin|password"}, status_code=400)

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
# (यहाँ आपके Broker APIs, trading routes आदि add रहेंगे)
# Example:
# -----------------------
@app.get("/balance")
def get_balance():
    # Dummy response, यहाँ broker API call करना है
    return {"balance": 100000, "currency": "INR"}
        
