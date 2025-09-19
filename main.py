# main.py
# FastAPI server - robust deploy + admin login endpoints
import os
import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import JSONResponse, HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

LOG = logging.getLogger("uvicorn.error")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Bullet Control Server")

# Allow CORS from anywhere (use tighter policy in production if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your app origin if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount static folder (for admin.html and assets)
STATIC_DIR = Path("static")
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# where we save deployed code
DEPLOY_DIR = Path("deployed")
DEPLOY_DIR.mkdir(exist_ok=True)

# Helper: read admin.html if present
ADMIN_HTML_PATH = STATIC_DIR / "admin.html"

# -----------------------
# Root route
# -----------------------
@app.get("/")
def root():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Admin login (RAW text: admin_id|admin_pass)  <-- keep this logic unchanged as requested
# -----------------------
@app.post("/admin/login")
async def admin_login(request: Request):
    """
    Accepts raw body like: "admin|password" (plain text).
    Returns JSON {"status":"success"/"fail"/"error", "msg": ...}
    """
    try:
        body_bytes = await request.body()
        text = body_bytes.decode("utf-8", errors="ignore").strip()
        if "|" not in text:
            return JSONResponse({"status": "error", "msg": "Invalid format. Expected admin_id|admin_pass"}, status_code=400)

        admin_id, admin_pass = text.split("|", 1)

        ADMIN_USER = os.getenv("ADMIN_USER", "admin")
        ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

        if admin_id == ADMIN_USER and admin_pass == ADMIN_PASS:
            return {"status": "success", "msg": "Login successful"}
        else:
            return JSONResponse({"status": "fail", "msg": "Invalid credentials"}, status_code=401)
    except Exception as e:
        LOG.exception("admin_login error")
        return JSONResponse({"status": "error", "msg": str(e)}, status_code=500)

# -----------------------
# Admin page (serve admin.html from /static/admin.html)
# -----------------------
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    if ADMIN_HTML_PATH.exists():
        return HTMLResponse(ADMIN_HTML_PATH.read_text(encoding="utf-8"))
    else:
        return HTMLResponse("<h2>Admin UI not found (upload static/admin.html)</h2>", status_code=404)

# -----------------------
# Deploy endpoint - flexible parsing
# -----------------------
@app.post("/admin/deploy")
async def admin_deploy(request: Request):
    """
    Accepts:
      - JSON body: {"code": "...", "kind": "strategy"|"ui"} (Content-Type: application/json)
      - form-encoded or multipart: code field
      - raw text (PostText from App Inventor): either "{"..."}" (JSON) or raw code string or "code=..."
    Saves:
      - strategy -> deployed/strategy.py
      - ui -> deployed/ui_update.json
    Returns JSON with status.
    """
    try:
        # detect content type
        content_type = request.headers.get("content-type", "").lower()
        LOG.info("Deploy request content-type: %s", content_type)

        code_text: Optional[str] = None
        kind: Optional[str] = None

        # 1) If application/json, try parse json
        if "application/json" in content_type:
            payload = await request.json()
            LOG.info("JSON payload received: keys=%s", list(payload.keys()))
            # accept either raw code or wrapper
            code_text = payload.get("code") or payload.get("payload") or payload.get("body") or None
            kind = payload.get("kind") or payload.get("type") or None

            # if top-level is string (some clients may send raw string as json string), handle it:
            if code_text is None and isinstance(payload, str):
                code_text = payload

        # 2) If form data (application/x-www-form-urlencoded or multipart)
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            form = await request.form()
            LOG.info("Form keys: %s", list(form.keys()))
            code_text = form.get("code") or form.get("payload") or form.get("body") or None
            kind = form.get("kind") or form.get("type") or None

        # 3) Otherwise: raw text (e.g., App Inventor PostText) - try decode and heuristics
        else:
            raw = await request.body()
            text = raw.decode("utf-8", errors="ignore").strip()
            LOG.info("Raw text received (len=%d)", len(text))
            if not text:
                return JSONResponse({"status": "error", "msg": "Empty body"}, status_code=400)

            # sometimes App Inventor sends "code=...." or a JSON string
            if text.startswith("{") and text.endswith("}"):
                # maybe it's JSON string - try parse
                try:
                    parsed = json.loads(text)
                    code_text = parsed.get("code") or json.dumps(parsed)
                    kind = parsed.get("kind") or parsed.get("type")
                except Exception:
                    # treat as raw JSON-like string -> might be UI config
                    code_text = text
            elif text.startswith("code="):
                # form-like single string
                code_text = text.split("code=", 1)[1]
            else:
                code_text = text

        # final check
        if not code_text:
            return JSONResponse({"status": "error", "msg": "No code found in request"}, status_code=400)

        # Decide kind automatically if not provided
        guessed_kind = kind
        if not guessed_kind:
            trimmed = code_text.strip()
            # simple heuristics:
            if (trimmed.startswith("{") and ("buttons" in trimmed or "layout" in trimmed or "theme" in trimmed)):
                guessed_kind = "ui"
            elif trimmed.startswith("def ") or "def " in trimmed or "import " in trimmed:
                guessed_kind = "strategy"
            else:
                # fallback: if valid JSON -> treat as ui
                try:
                    json.loads(trimmed)
                    guessed_kind = "ui"
                except Exception:
                    guessed_kind = "strategy"

        # Save file accordingly
        if guessed_kind == "ui":
            # ensure valid JSON
            try:
                ui_obj = json.loads(code_text) if isinstance(code_text, str) else code_text
            except Exception:
                # try to sanitize common issues: replace single quotes -> double quotes (best-effort)
                try:
                    ui_obj = json.loads(code_text.replace("'", '"'))
                except Exception as e:
                    LOG.exception("Invalid UI JSON")
                    return JSONResponse({"status": "error", "msg": "UI JSON parse error: " + str(e)}, status_code=400)

            out_path = DEPLOY_DIR / "ui_update.json"
            out_path.write_text(json.dumps(ui_obj, indent=2, ensure_ascii=False), encoding="utf-8")
            LOG.info("Saved UI config -> %s", out_path)
            return {"status": "success", "msg": "UI saved", "file": str(out_path)}

        else:
            # save python strategy code as file
            out_path = DEPLOY_DIR / "strategy.py"
            # ensure we keep it exactly as sent
            out_path.write_text(code_text, encoding="utf-8")
            LOG.info("Saved strategy -> %s", out_path)
            return {"status": "success", "msg": "Strategy saved", "file": str(out_path)}

    except Exception as e:
        LOG.exception("deploy error")
        return JSONResponse({"status": "error", "msg": str(e)}, status_code=500)

# -----------------------
# Example broker endpoint (dummy)
# -----------------------
@app.get("/balance")
async def get_balance():
    return {"balance": 100000, "currency": "INR"}

# -----------------------
# health route
# -----------------------
@app.get("/health")
def health():
    return PlainTextResponse("ok")
        
