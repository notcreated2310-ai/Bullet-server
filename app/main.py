from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"message": "✅ Your app is running successfully on Render 🚀"}

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "pong"}
    
