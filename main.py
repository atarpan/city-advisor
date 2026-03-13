from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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

# 🔑 Auth Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

@app.get("/")
def home():
    return {"status": "online", "method": "BULLETPROOF-V11", "key_loaded": bool(GEMINI_API_KEY)}

@app.get("/advisor")
def get_advice(
    query: str = Query(...),
    x_api_key: str = Query(..., alias="x-api-key")
):
    # 1. Security Check
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Invalid App Key")

    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Gemini Key missing on Render settings"}

    try:
        # 2. Get Weather (Chisinau default if not found)
        temp = "15"
        city_name = "Chișinău"
        try:
            # Simple prompt to extract city
            extract_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
            extract_payload = {"contents": [{"parts": [{"text": f"Extract only city name from: '{query}'. Return only the name."}]}]}
            city_res = requests.post(extract_url, json=extract_payload).json()
            city_name = city_res['candidates'][0]['content']['parts'][0]['text'].strip()
            
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_name}&count=1").json()
            if geo.get("results"):
                res = geo["results"][0]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true").json()
                temp = w["current_weather"]["temperature"]
        except: pass

        # 3. Get AI Recommendation (DIRECT HTTP CALL)
        ai_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        ai_payload = {
            "contents": [{
                "parts": [{"text": f"Ești un ghid în {city_name}. Vremea e de {temp} grade. Recomandă ce să fac pentru: {query}. Răspunde prietenos în română."}]
            }]
        }
        
        ai_res = requests.post(ai_url, json=ai_payload, timeout=15).json()
        
        # Check for Google Errors
        if "error" in ai_res:
            return {"status": "error", "message": ai_res["error"]["message"]}

        recommendation = ai_res['candidates'][0]['content']['parts'][0]['text']
        
        return {
            "status": "success",
            "city": city_name,
            "weather": {"temp": temp},
            "recommendation": recommendation
        }
    except Exception as e:
        return {"status": "error", "message": f"Server Error: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
