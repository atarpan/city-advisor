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

# 🔑 CONFIGURARE GEMINI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Folosim cea mai stabilă metodă de inițializare
    model = genai.GenerativeModel('gemini-1.5-flash')

@app.get("/")
def home():
    # Mesaj de verificare: Dacă vezi asta, înseamnă că ai versiunea NOUĂ!
    return {
        "status": "online", 
        "version": "V3-ULTRA-STABLE",
        "message": "Dacă vezi acest mesaj, Render a terminat deploy-ul corect!"
    }

@app.get("/advisor")
def get_advice(query: str = Query(...), x_api_key: str = Query(...)):
    # Securitate simplă
    if x_api_key != "secret-vibe-123":
        raise HTTPException(status_code=403, detail="Cheie API invalidă!")

    if not GEMINI_API_KEY:
        return {"status": "error", "message": "Cheia Gemini lipsește de pe Render!"}

    try:
        # Pasul 1: AI află orașul
        city_prompt = f"Extract city name from: '{query}'. Return only the name. If none, return 'Bucuresti'."
        city_res = model.generate_content(city_prompt).text.strip()
        
        # Pasul 2: Vremea (simplificată)
        temp = "20" # Valoare de siguranță
        try:
            geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city_res}&count=1").json()
            if geo.get("results"):
                res = geo["results"][0]
                w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true").json()
                temp = w["current_weather"]["temperature"]
        except:
            pass

        # Pasul 3: Recomandarea finală
        advice_prompt = f"Sunt în {city_res}, e vreme de {temp} grade. Recomandă activități pentru: {query} (în română)."
        recommendation = model.generate_content(advice_prompt).text

        return {
            "status": "success",
            "city": city_res,
            "weather": {"temp": temp},
            "recommendation": recommendation,
            "backend_version": "V3"
        }
    except Exception as e:
        return {"status": "error", "message": f"Eroare AI: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
