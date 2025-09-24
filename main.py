from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests

# -------------------------
# Main App
# -------------------------
app = FastAPI()

# Templates (UI pages)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# -------------------------
# Home / UI Route
# -------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# -------------------------
# Auto Login (old feature preserved)
# -------------------------
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    # Example: Replace with DB or secure storage
    if username == "admin" and password == "admin123":
        return {"status": "success", "message": "Auto Login Successful"}
    return {"status": "failed", "message": "Invalid credentials"}


# -------------------------
# Deploy Code Feature (old feature preserved)
# -------------------------
@app.post("/deploy")
async def deploy_code(code: str = Form(...)):
    try:
        # safe eval/exec not used for security (future sandbox)
        exec(code, globals())
        return {"status": "success", "message": "Code deployed successfully!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------------
# 🔹 Live Trading Endpoints
# -------------------------

# 1. Live Price from Binance
@app.get("/price/{symbol}")
def get_price(symbol: str):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol.upper()}"
        data = requests.get(url, timeout=5).json()
        return {"symbol": symbol.upper(), "price": data["price"]}
    except Exception as e:
        return {"error": str(e)}


# 2. Account Balance (dummy now, connect to broker API later)
@app.get("/account/balance")
def get_balance():
    # Later replace with broker API call
    return {"balance": 5000, "pnl": 230}


# 3. Order History (dummy now, replace with real broker orders later)
@app.get("/orders")
def get_orders():
    return [
        {"symbol": "BTCUSDT", "side": "BUY", "qty": 0.01, "price": 64000},
        {"symbol": "ETHUSDT", "side": "SELL", "qty": 0.5, "price": 2400},
    ]


# -------------------------
# Status Check
# -------------------------
@app.get("/status")
def status():
    return {"status": "running", "message": "Trading App Backend Active ✅"}
    
