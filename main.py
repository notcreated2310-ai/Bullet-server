from flask import Flask, request, jsonify, render_template
import os, json

app = Flask(__name__)

# ---- Existing Settings (Don't Change) ----
ADMIN_USER = "admin"
ADMIN_PASS = "password"
DEPLOY_FOLDER = "deployed"
os.makedirs(DEPLOY_FOLDER, exist_ok=True)


# ---------- Home / Login UI ----------
@app.route("/")
def home():
    return render_template("index.html")


# ---------- API: Handle Login ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if data.get("username") == ADMIN_USER and data.get("password") == ADMIN_PASS:
        return jsonify({"status": "success", "msg": "Login successful"})
    return jsonify({"status": "error", "msg": "Invalid credentials"})
    


# ---------- API: Deploy Strategy Code ----------
@app.route("/deploy", methods=["POST"])
def deploy_code():
    try:
        code = request.json.get("code", "")
        filepath = os.path.join(DEPLOY_FOLDER, "strategy.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)

        # Default response
        response = {
            "status": "success",
            "msg": "Strategy saved",
            "file": filepath,
            "new_blocks": []
        }

        # -------- Dynamic UI Parsing --------
        # If code contains JSON like {"new_blocks":[{...}]}, parse it
        try:
            parsed = json.loads(code)
            if "new_blocks" in parsed:
                response["new_blocks"] = parsed["new_blocks"]
                response["msg"] = "Dynamic UI deployed with new blocks"
        except Exception:
            pass  # ignore if code is normal Python

        return jsonify(response)

    except Exception as e:
        return jsonify({"status": "error", "msg": str(e)})


# ---------- API: Upgrade UI via Action ----------
@app.route("/action", methods=["POST"])
def action():
    payload = request.json
    response = {"ui_update": False, "new_blocks": []}

    if payload.get("action") == "upgrade":
        response["ui_update"] = True
        response["msg"] = "UI upgraded with Preview + Approve/Reject blocks"
        response["new_blocks"].extend([
            {"name": "PreviewBlock", "type": "button"},
            {"name": "ApproveBlock", "type": "button"},
            {"name": "RejectBlock", "type": "button"}
        ])
    else:
        response["msg"] = "No valid action provided!"

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# -----------------------
# ✅ New Dynamic Deploy System
# -----------------------

pending_code = None
approved_code = None

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    global pending_code
    pending_code = code
    return {"status": "pending", "msg": "Code received, waiting for approval"}

@app.post("/code/approve")
def code_approve():
    global pending_code, approved_code
    if not pending_code:
        return {"status": "fail", "msg": "No pending code to approve"}
    approved_code = pending_code
    pending_code = None
    return {"status": "success", "msg": "Code approved & deployed", "approved_code": approved_code}

@app.get("/code/status")
def code_status():
    return {
        "pending": pending_code if pending_code else None,
        "approved": approved_code if approved_code else None
    }
    
