from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 CLEAN THE KEY (Remove any hidden spaces from Render)
RAW_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEY = RAW_KEY.strip()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def home():
    return {
        "status": "online", 
        "version": "DIAGNOSTIC-V6", 
        "key_status": "Loaded" if GEMINI_API_KEY else "Missing"
    }

@app.get("/advisor")
def get_advice(query: str = Query(...), x_api_key: str = Query(...)):
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Wrong App Key!")

    try:
        # We try 'gemini-1.5-flash' first, then 'gemini-pro'
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(f"Recommend one place in: {query} (Romanian)")
            recommendation = res.text
        except:
            # Fallback to the most basic model
            model = genai.GenerativeModel('gemini-pro')
            res = model.generate_content(f"Recommend one place in: {query} (Romanian)")
            recommendation = res.text

        return {
            "status": "success",
            "recommendation": recommendation,
            "engine": "V6-Stable"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# New endpoint to see what models your Render server actually sees
@app.get("/debug-models")
def list_models():
    try:
        models = [m.name for m in genai.list_models()]
        return {"available_models": models}
    except Exception as e:
        return {"error": str(e)}
