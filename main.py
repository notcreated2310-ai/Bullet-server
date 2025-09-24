from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse, HTMLResponse

app = FastAPI()

# -----------------------
# Root Route (Test)
# -----------------------
@app.get("/")
def home():
    return {"status": "ok", "msg": "Server is live"}

# -----------------------
# Direct Auto Login (No credentials)
# -----------------------
@app.get("/admin/autologin")
def auto_login():
    return {"status": "success", "message": "Login successful"}

# -----------------------
# Admin Panel (HTML page with code box)
# -----------------------
@app.get("/admin/panel", response_class=HTMLResponse)
def admin_panel():
    return """
    <html>
    <head><title>Admin Control Center</title></head>
    <body style="font-family: Arial; margin:40px;">
        <h2>Admin Control Center</h2>
        <p>Status: Ready</p>

        <form action="/code/deploy" method="post">
            <label>Paste Python/HTML code for UI below:</label><br>
            <textarea name="code" rows="12" cols="80"></textarea><br><br>
            <button type="submit">Deploy Code</button>
        </form>
    </body>
    </html>
    """

# -----------------------
# Dynamic Code Deploy System
# -----------------------
approved_code = None  # final active code

@app.post("/code/deploy")
async def code_deploy(code: str = Form(...)):
    """
    Code submit karega → auto approve → UI refresh ke liye ready
    """
    global approved_code
    approved_code = code
    return {"status": "approved", "msg": "Code deployed & approved successfully"}

@app.get("/code/active")
def get_active_code():
    """
    Currently active (approved) code dikhayega
    """
    global approved_code
    if approved_code:
        return HTMLResponse(content=approved_code)
    else:
        return {"status": "empty", "msg": "No active code"}

# -----------------------
# Final UI with Fixed Header/Footer
# -----------------------
@app.get("/ui", response_class=HTMLResponse)
def preview_ui():
    global approved_code
    dynamic_content = approved_code if approved_code else "<p>No UI Deployed</p>"

    return f"""
    <html>
    <head>
        <title>Trading App</title>
        <style>
            body {{
                margin: 0;
                font-family: Arial, sans-serif;
                background: #f9f9f9;
            }}
            /* Header */
            .header {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 60px;
                background: #111827;
                color: white;
                display: flex;
                justify-content: space-around;
                align-items: center;
                font-size: 14px;
                z-index: 1000;
            }}
            /* Footer Menu */
            .footer {{
                position: fixed;
                bottom: 0;
                left: 0;
                right: 0;
                height: 60px;
                background: #111827;
                color: white;
                display: flex;
                justify-content: space-around;
                align-items: center;
                font-size: 14px;
                z-index: 1000;
            }}
            .footer div {{
                text-align: center;
            }}
            /* Scrollable Middle Section */
            .content {{
                margin-top: 70px;
                margin-bottom: 70px;
                padding: 15px;
            }}
            .card {{
                background: white;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 15px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <!-- Fixed Header -->
        <div class="header">
            <div>Balance: $10,000</div>
            <div>Index: NIFTY 50</div>
            <div>Status: LIVE</div>
        </div>

        <!-- Scrollable Middle Section -->
        <div class="content">
            <div class="card">
                <h3>Dynamic Section</h3>
                {dynamic_content}
            </div>
            <div class="card">
                <h3>Market News</h3>
                <p>Latest forex & crypto updates will appear here...</p>
            </div>
            <div class="card">
                <h3>Signals</h3>
                <p>Buy/Sell suggestions...</p>
            </div>
        </div>

        <!-- Fixed Footer Menu -->
        <div class="footer">
            <div>🏠<br>Home</div>
            <div>📈<br>Watchlist</div>
            <div>📊<br>Orders</div>
            <div>👤<br>Account</div>
            <div>⚙️<br>Admin</div>
        </div>
    </body>
    </html>
    """
    
