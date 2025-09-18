# main.py  (final - merged)
import os
import time
import json
import hashlib
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Control Center")

# ---------- Config from env ----------
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")
# ADMIN_TOKEN: if provided in env use it, otherwise deterministic from user:pass
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN") or hashlib.sha256(f"{ADMIN_USER}:{ADMIN_PASS}".encode()).hexdigest()

# GitHub / Render config (optional)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GITHUB_COMMIT_PATH = os.getenv("GITHUB_COMMIT_PATH", "update_code.py")
RENDER_API_KEY = os.getenv("RENDER_API_KEY")
RENDER_SERVICE_ID = os.getenv("RENDER_SERVICE_ID")

LOCAL_UPDATE_FILENAME = os.getenv("LOCAL_UPDATE_FILENAME", "update_code.py")

# in-memory applied code
APPLIED = {"text": None, "namespace": None, "last_update": None}

# serve static files from ./static
if not os.path.isdir("static"):
    os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# helpers
def parse_login_text(text: str):
    text = (text or "").strip()
    if "|" in text:
        a, b = text.split("|", 1)
        return a.strip(), b.strip()
    # try json
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj.get("admin_id"), obj.get("admin_pass")
    except:
        pass
    return None, None

def parse_update_text(text: str):
    text = (text or "").strip()
    # json {"token":"..","code":".."} ?
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "token" in obj and "code" in obj:
            return obj["token"], obj["code"]
    except:
        pass
    # pipe format: token|code...
    if "|" in text:
        tok, code = text.split("|", 1)
        return tok.strip(), code
    return None, text  # no token, entire text as code

def save_code(filename: str, code_text: str):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code_text)

def apply_code_runtime(code_text: str):
    ns = {}
    try:
        exec(compile(code_text, "<admin_code>", "exec"), ns)
        APPLIED["text"] = code_text
        APPLIED["namespace"] = ns
        APPLIED["last_update"] = time.time()
        return True, "Applied in-memory"
    except Exception as e:
        return False, str(e)

# (Optional) GitHub commit helper — simple approach
def commit_to_github(path_in_repo: str, content_str: str):
    if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
        return False, "GitHub config missing"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    api = "https://api.github.com"
    # 1) get latest commit sha for branch
    ref_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}"
    r = requests.get(ref_url, headers=headers)
    if r.status_code != 200:
        return False, f"Get ref failed: {r.status_code} {r.text}"
    commit_sha = r.json()["object"]["sha"]
    # 2) get commit tree
    commit_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits/{commit_sha}"
    r = requests.get(commit_url, headers=headers)
    if r.status_code != 200:
        return False, f"Get commit failed: {r.status_code} {r.text}"
    base_tree = r.json()["tree"]["sha"]
    # 3) create blob
    blob_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/blobs"
    r = requests.post(blob_url, headers=headers, json={"content": content_str, "encoding": "utf-8"})
    if r.status_code not in (200,201):
        return False, f"Create blob failed: {r.status_code} {r.text}"
    blob_sha = r.json()["sha"]
    # 4) create tree
    tree_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/trees"
    tree_item = {"path": path_in_repo, "mode": "100644", "type": "blob", "sha": blob_sha}
    r = requests.post(tree_url, headers=headers, json={"base_tree": base_tree, "tree": [tree_item]})
    if r.status_code not in (200,201):
        return False, f"Create tree failed: {r.status_code} {r.text}"
    new_tree = r.json()["sha"]
    # 5) commit
    commit_msg = f"Admin update: {path_in_repo} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    commit_payload = {"message": commit_msg, "tree": new_tree, "parents": [commit_sha]}
    commit_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/commits"
    r = requests.post(commit_url, headers=headers, json=commit_payload)
    if r.status_code not in (200,201):
        return False, f"Create commit failed: {r.status_code} {r.text}"
    new_commit = r.json()["sha"]
    # 6) update ref
    update_ref_url = f"{api}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/git/refs/heads/{GITHUB_BRANCH}"
    r = requests.patch(update_ref_url, headers=headers, json={"sha": new_commit})
    if r.status_code not in (200,201):
        return False, f"Update ref failed: {r.status_code} {r.text}"
    return True, f"Committed {path_in_repo}"

def trigger_render_deploy():
    if not (RENDER_API_KEY and RENDER_SERVICE_ID):
        return False, "Render config missing"
    url = f"https://api.render.com/v1/services/srv-{RENDER_SERVICE_ID}/deploys"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {RENDER_API_KEY}"}
    r = requests.post(url, headers=headers, json={})
    if r.status_code not in (200,201):
        return False, f"Render deploy failed: {r.status_code} {r.text}"
    return True, "Render deploy triggered"

# ---------- routes ----------
@app.get("/")
def root():
    return {"status": "ok", "msg": "Service live"}

@app.post("/admin/login")
async def admin_login(request: Request):
    body = await request.body()
    text = body.decode("utf-8")
    user, pwd = parse_login_text(text)
    if not user or not pwd:
        return JSONResponse(status_code=400, content={"detail": [{"type":"missing","loc":["body","admin_id/admin_pass"],"msg":"Field required"}]})
    if user == ADMIN_USER and pwd == ADMIN_PASS:
        # return token to be stored by app
        return {"status": "ok", "token": ADMIN_TOKEN}
    return JSONResponse(status_code=401, content={"status":"fail","msg":"Invalid credentials"})

@app.post("/admin/update")
async def admin_update(request: Request):
    """
    Accepts:
      - raw token|code (plain text)
      - OR JSON {"token":"..","code":".."}
    """
    body = await request.body()
    text = body.decode("utf-8")
    token, code = parse_update_text(text)
    if not token:
        return JSONResponse(status_code=400, content={"status":"error","msg":"Missing token in body; use token|code or JSON"})
    if token != ADMIN_TOKEN:
        return JSONResponse(status_code=403, content={"status":"error","msg":"Invalid admin token"})

    # save file locally
    try:
        save_code(LOCAL_UPDATE_FILENAME, code)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status":"error","msg":f"Save failed: {e}"})

    # try to apply runtime
    ok, info = apply_code_runtime(code)
    res = {"status":"ok","saved":True,"applied_runtime": ok, "apply_info": info}

    # optionally commit to github and trigger render
    if GITHUB_TOKEN and GITHUB_OWNER and GITHUB_REPO:
        c_ok, c_msg = commit_to_github(GITHUB_COMMIT_PATH, code)
        res["github_commit"] = {"ok": c_ok, "msg": c_msg}
        if RENDER_API_KEY and RENDER_SERVICE_ID:
            d_ok, d_msg = trigger_render_deploy()
            res["render_deploy"] = {"ok": d_ok, "msg": d_msg}

    return res

@app.post("/run_strategy")
async def run_strategy(request: Request):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    ns = APPLIED.get("namespace")
    if not ns:
        return JSONResponse(status_code=400, content={"status":"error","msg":"No applied code"})
    if "run_strategy" not in ns or not callable(ns["run_strategy"]):
        return JSONResponse(status_code=400, content={"status":"error","msg":"run_strategy not found"})
    try:
        out = ns["run_strategy"](payload)
        return {"status":"ok","result": out}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status":"error","msg": str(e)})
        
