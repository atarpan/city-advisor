from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import os
import requests
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔑 API Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def home():
    return {"status": "online", "message": "City Advisor Magic Mode is LIVE!"}

@app.get("/advisor")
def get_advice(
    query: str = Query(...),
    x_api_key: str = Query(..., alias="x-api-key")
):
    # Security Check
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Invalid API Key")

    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Gemini Key missing on server"}

    try:
        # 🤖 AUTOMATIC MODEL DISCOVERY (The Magic Fix)
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Select best available model
        model_name = "gemini-1.5-flash" 
        if "models/gemini-2.5-flash" in available_models:
            model_name = "models/gemini-2.5-flash"
        elif "models/gemini-1.5-flash" in available_models:
            model_name = "models/gemini-1.5-flash"
        elif available_models:
            model_name = available_models[0]

        model = genai.GenerativeModel(model_name)
        
        # 1. Extract City
        city_res = model.generate_content(f"Extract city name from: {query}. Return ONLY name.").text.strip()
        
        # 2. Get Weather
        temp = "20"
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_res}&count=1").json()
            if geo.get("results"):
                res = geo["results"][0]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true").json()
                temp = w["current_weather"]["temperature"]
        except: pass

        # 3. Generate Recommendation
        response = model.generate_content(f"Sunt în {city_res}, sunt {temp} grade. Recomandă ce să fac pentru: {query} în limba română.")
        
        return {
            "status": "success",
            "city": city_res,
            "weather": {"temp": temp},
            "recommendation": response.text,
            "model_used": model_name
        }
    except Exception as e:
        return {"status": "error", "message": f"AI Logic Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
