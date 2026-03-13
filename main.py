from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
import requests
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

# 🔑 CONFIGURATION
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@app.get("/")
def home():
    return {"status": "online", "version": "ROBUST-V4", "message": "Backend is ready!"}

@app.get("/advisor")
def get_advice(query: str = Query(...), x_api_key: str = Query(...)):
    # Security check
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Invalid API Key!")

    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Gemini API Key is missing on Render!"}

    try:
        # Try different model names for maximum compatibility
        model_names = ["gemini-1.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]
        model = None
        
        for name in model_names:
            try:
                model = genai.GenerativeModel(name)
                # Test the model with a tiny request
                model.generate_content("test")
                break 
            except:
                continue
        
        if not model:
            return {"status": "error", "message": "Could not connect to any Gemini model."}

        # 1. Extract City
        city_res = model.generate_content(f"Extract city name from: '{query}'. Return ONLY the name. Default: London").text.strip()
        
        # 2. Get Weather
        temp = "20"
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_res}&count=1").json()
            if geo.get("results"):
                coords = geo["results"][0]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={coords['latitude']}&longitude={coords['longitude']}&current_weather=true").json()
                temp = w["current_weather"]["temperature"]
        except:
            pass

        # 3. Final Recommendation
        advice_prompt = f"I am in {city_res}, the weather is {temp} degrees. Recommend activities for: {query} (in Romanian language)."
        recommendation = model.generate_content(advice_prompt).text

        return {
            "status": "success",
            "city": city_res,
            "weather": {"temp": temp},
            "recommendation": recommendation
        }
    except Exception as e:
        return {"status": "error", "message": f"AI Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
