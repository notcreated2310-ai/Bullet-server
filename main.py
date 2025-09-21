# main.py - Robust server for AppInventor integration
from fastapi import FastAPI, Request, Form
from fastapi.responses import JSONResponse, HTMLResponse
import os
from urllib.parse import parse_qs

app = FastAPI()

# In-memory storage
pending_code = None
approved_code = None

# -----------------------
# Root
# -----------------------
@app.get("/")
def root():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Admin login - accept GET and POST (flexible)
# -----------------------
@app.api_route("/admin/login", methods=["GET", "POST"])
async def admin_login(request: Request):
    """
    Accepts:
     - GET  -> returns success (useful for quick browser test)
     - POST -> accepts:
         * form fields username + password
         * raw body like "admin|1234"
         * urlencoded "username=admin&password=1234"
         * empty body -> fallback to environment defaults ADMIN_USER/ADMIN_PASS
    """
    # If GET -> return success (so browser GET doesn't 405)
    if request.method == "GET":
        return {"status": "success", "message": "Login successful (GET)"}

    # POST handling
    username = None
    password = None

    # Try to read form (application/x-www-form-urlencoded or multipart)
    try:
        form = await request.form()
        if form:
            username = form.get("username") or form.get("admin_id")
            password = form.get("password") or form.get("admin_pass")
    except Exception:
        # ignore form parse errors
        pass

    # If not found in form, try raw body inspect
    if not username and not password:
        raw = (await request.body()).decode("utf-8", errors="ignore").strip()
        if raw:
            # format: admin|1234
            if "|" in raw:
                parts = raw.split("|", 1)
                username = parts[0].strip()
                password = parts[1].strip() if len(parts) > 1 else None
            # urlencoded: username=admin&password=1234
            elif "=" in raw and "&" in raw:
                parsed = parse_qs(raw)
                username = parsed.get("username", [None])[0]
                password = parsed.get("password", [None])[0]
            else:
                # maybe a single username only - treat as username
                username = raw if raw else None

    # Fallback to env defaults if still missing
    if not username:
        username = os.getenv("ADMIN_USER", "admin")
    if not password:
        password = os.getenv("ADMIN_PASS", "1234")

    # Validate
    ADMIN_USER = os.getenv("ADMIN_USER", "admin")
    ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")

    if username == ADMIN_USER and password == ADMIN_PASS:
        return {"status": "success", "message": "Login successful"}
    else:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid credentials"})


# -----------------------
# Admin Panel (simple HTML form)
# -----------------------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return """
    <html>
    <head><title>Admin Panel</title></head>
    <body style="font-family: Arial; margin:20px;">
      <h2>Admin Control Panel</h2>
      <form action="/code/deploy" method="post">
        <label>Paste HTML / Python code:</label><br>
        <textarea name="code" rows="12" cols="80"></textarea><br><br>
        <button type="submit">Deploy Code</button>
      </form>
      <p>Use /code/approve to approve and /code/active to view active UI.</p>
    </body>
    </html>
    """

# -----------------------
# Deploy (accept form or raw)
# -----------------------
@app.post("/code/deploy")
async def code_deploy(request: Request):
    """
    Accepts form (code=<...>) or raw body.
    Saves into pending_code.
    """
    global pending_code
    code = None
    # try form
    try:
        form = await request.form()
        if form:
            code = form.get("code") or form.get("payload")
    except Exception:
        pass

    # if not form, raw body
    if not code:
        raw = (await request.body()).decode("utf-8", errors="ignore").strip()
        if raw:
            # if it's "code=..." urlencoded
            if raw.startswith("code="):
                parsed = parse_qs(raw)
                code = parsed.get("code", [None])[0]
            else:
                # treat raw body as code (html or python)
                code = raw

    if not code:
        return JSONResponse(status_code=400, content={"status": "error", "msg": "No code provided"})

    pending_code = code
    return {"status": "pending", "msg": "Code received and stored as pending"}

# -----------------------
# Check pending
# -----------------------
@app.get("/code/pending")
def code_pending():
    if pending_code:
        return {"status": "pending", "code_preview": (pending_code[:500] + "...") if len(pending_code) > 500 else pending_code}
    return {"status": "empty", "msg": "No pending code"}

# -----------------------
# Approve
# -----------------------
@app.post("/code/approve")
async def code_approve():
    global pending_code, approved_code
    if not pending_code:
        return JSONResponse(status_code=400, content={"status": "error", "msg": "No pending code to approve"})
    approved_code = pending_code
    pending_code = None
    return {"status": "approved", "msg": "Code approved and active"}

# -----------------------
# Active UI - return raw HTML for WebViewer
# -----------------------
@app.get("/code/active", response_class=HTMLResponse)
def code_active():
    if approved_code:
        # return approved HTML (if it's HTML) — if it's a python strategy, still show as preformatted text
        html = approved_code
        # if it looks like HTML (starts with <), return directly; else wrap in <pre>
        if html.strip().startswith("<"):
            return html
        else:
            safe = "<html><body><h3>Active Code (not HTML)</h3><pre style='white-space:pre-wrap;background:#f4f4f4;padding:10px;border-radius:6px;'>%s</pre></body></html>" % (html.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))
            return safe
    return "<html><body><h3>No active UI</h3></body></html>"
    
