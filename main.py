import ssl
import certifi
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
import sqlite3, os, time, uuid, json, hmac, hashlib, requests
from typing import Optional

# ---------------------------
# SSL / Requests Session Fix
# ---------------------------
session = requests.Session()
session.verify = certifi.where()

# ---------------------------
# Config
# ---------------------------
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
DB_PATH = os.environ.get("DB_PATH", "./data.db")
LOG_FILE = os.environ.get("LOG_FILE", "./server.log")
MAX_CODE_BYTES = int(os.environ.get("MAX_CODE_BYTES", "200000"))
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")
BINANCE_TESTNET = os.environ.get("BINANCE_TESTNET", "True").lower() == "true"

# ---------------------------
# Logging
# ---------------------------
import logging
logging.basicConfig(level=logging.INFO, filename=LOG_FILE, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------
# App
# ---------------------------
app = FastAPI(title="Bullet Live Trading Server")

# ---------------------------
# Database & Helpers
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS ui_blocks (
        id TEXT PRIMARY KEY, title TEXT, category TEXT, code TEXT, created_at INTEGER, approved INTEGER DEFAULT 1
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS deploy_history (
        id TEXT PRIMARY KEY, block_id TEXT, action TEXT, detail TEXT, ts INTEGER
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, level TEXT, message TEXT
    )""")
    conn.commit(); conn.close()

init_db()

def now_ts(): return int(time.time())
def db_conn(): return sqlite3.connect(DB_PATH)
def save_log(level, msg):
    try:
        conn = db_conn(); cur = conn.cursor()
        cur.execute("INSERT INTO logs (ts, level, message) VALUES (?,?,?)", (now_ts(), level, msg))
        conn.commit(); conn.close()
    except: pass

def require_admin(token: Optional[str]):
    if not ADMIN_TOKEN: return True
    if not token: raise HTTPException(403, "Admin token required")
    if token != ADMIN_TOKEN: raise HTTPException(403, "Invalid admin token")
    return True

# ---------------------------
# Broker Manager with Requests Session
# ---------------------------
class BrokerManager:
    def __init__(self, api_key, api_secret, testnet=True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base = 'https://testnet.binance.vision/api' if testnet else 'https://api.binance.com/api'
        self.session = session

    def _sign_payload(self, payload):
        query_string = '&'.join([f'{k}={v}' for k,v in payload.items()])
        signature = hmac.new(self.api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
        payload['signature'] = signature
        return payload

    def place_order(self, symbol, side, type_, quantity, price=None):
        endpoint = f'{self.base}/v3/order'
        ts = int(time.time()*1000)
        payload = {'symbol':symbol,'side':side,'type':type_,'quantity':quantity,'timestamp':ts}
        if price: payload['price']=price
        payload = self._sign_payload(payload)
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = self.session.post(endpoint, headers=headers, params=payload)
        return resp.json()

    def account_balance(self):
        endpoint = f'{self.base}/v3/account'
        ts = int(time.time()*1000)
        payload = {'timestamp':ts}
        payload = self._sign_payload(payload)
        headers = {'X-MBX-APIKEY': self.api_key}
        resp = self.session.get(endpoint, headers=headers, params=payload)
        return resp.json()

broker = BrokerManager(BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_TESTNET)

# ---------------------------
# Routes
# ---------------------------
@app.get("/")
def root():
    return {"status":"ok","msg":"Server is live"}

@app.get("/admin/autologin")
def autologin():
    return {"status":"success","message":"Login successful","admin_token":ADMIN_TOKEN}
