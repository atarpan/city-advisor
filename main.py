from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import requests
import os
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 CLEAN THE KEY
RAW_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_KEY = RAW_KEY.strip()

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def home():
    return {"status": "online", "version": "V7-FINAL", "message": "Ready to go!"}

@app.get("/advisor")
def get_advice(
    query: str = Query(..., description="The user's question"),
    x_api_key: str = Query(..., alias="x-api-key", description="Security key")
):
    """
    Accepts 'x-api-key' with a dash to match the Frontend and common standards.
    """
    # Security check
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Invalid App Key!")

    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Gemini API Key is missing!"}

    # Fallback system for models
    model_names = ["gemini-1.5-flash", "gemini-pro", "models/gemini-1.5-flash"]
    selected_model = None
    
    for name in model_names:
        try:
            m = genai.GenerativeModel(name)
            m.generate_content("test")
            selected_model = m
            break
        except:
            continue

    if not selected_model:
        return {"status": "error", "message": "No working AI models found in this region."}

    try:
        # 1. AI extracts city
        city_res = selected_model.generate_content(f"Extract city from: {query}. Return ONLY name.").text.strip()
        
        # 2. Get Weather
        temp = "20"
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_res}&count=1").json()
            if geo.get("results"):
                res = geo["results"][0]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true").json()
                temp = w["current_weather"]["temperature"]
        except:
            pass

        # 3. Final Recommendation
        advice = selected_model.generate_content(f"I am in {city_res}, {temp}C. Plan for: {query} (in Romanian language).").text
        
        return {
            "status": "success",
            "city": city_res,
            "weather": {"temp": temp},
            "recommendation": advice
        }
    except Exception as e:
        return {"status": "error", "message": f"Processing error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
