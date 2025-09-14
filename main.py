from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"message": "✅ FastAPI app is running on Render!"}

@app.get("/dashboard")
def dashboard():
    return {
        "status": "ok",
        "users": 125,
        "active_models": ["AI-Trade", "AI-Chat", "AI-Helper"]
    }
  
