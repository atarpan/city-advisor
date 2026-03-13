from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import requests
import os
import json
import logging
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# Configurare Log-uri (pentru a vedea erorile pe Render)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. Configurare Mediu & Bază de Date
load_dotenv()
DATABASE_URL = "sqlite:///./advisor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    query = Column(String)
    city = Column(String)
    temperature = Column(Float)
    recommendation = Column(Text)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 2. Configurare FastAPI
app = FastAPI(title="City Advisor Ultra Pro")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Securitate & AI
MY_APP_AUTH_KEY = "secret-vibe-123" # Am pus-o fixă pentru a fi siguri
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Inițializare Client nou SDK
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

async def verify_api_key(
    x_api_key_header: Optional[str] = Header(None, alias="x-api-key"),
    x_api_key_query: Optional[str] = Query(None, alias="x-api-key")
):
    """Verifică cheia de acces atât în Header cât și în URL."""
    auth_key = x_api_key_header or x_api_key_query
    
    # Adăugăm un print pentru debugging în log-urile Render
    print(f"DEBUG: Primit auth_key: {auth_key}")
    
    if auth_key != MY_APP_AUTH_KEY:
        logger.warning(f"Tentativă de acces neautorizat cu cheia: {auth_key}")
        raise HTTPException(status_code=403, detail=f"Acces refuzat: Cheia '{auth_key}' este invalidă.")
    return auth_key

# 4. Funcții Utilitare
def fetch_weather(city: str):
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        geo = requests.get(geo_url, timeout=10).json()
        if not geo.get("results"): return None
        res = geo["results"][0]
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true"
        w = requests.get(w_url, timeout=10).json()
        return {"city": res["name"], "temp": w["current_weather"]["temperature"]}
    except Exception as e:
        logger.error(f"Eroare la meteo pentru {city}: {str(e)}")
        return None

# --- ENDPOINT-URI ---

@app.get("/")
def home():
    return {"status": "online", "message": "City Advisor Pro este gata de aventură!"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "gemini_configured": bool(GEMINI_API_KEY),
        "database": "active"
    }

@app.get("/advisor", dependencies=[Depends(verify_api_key)])
def get_advice(
    query: str = Query(..., description="Întrebarea ta"),
    db: Session = Depends(get_db)
):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Configurație incorectă: Cheia Gemini lipsește.")

    try:
        # Pasul 1: Extragere oraș
        response_city = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=f"Extract only city name from: '{query}'. Return 'Unknown' if none."
        )
        city_name = response_city.text.strip().replace("City:", "").strip()

        if "Unknown" in city_name:
            return {"status": "error", "message": "Te rog să incluzi un oraș."}

        # Pasul 2: Vreme reală
        weather = fetch_weather(city_name)
        temp = weather["temp"] if weather else "necunoscută"

        # Pasul 3: Recomandare AI detaliată
        prompt_advice = f"Ghid turistic în {city_name}. Utilizator: {query}. Vreme: {temp}C. Recomandă activități în română."
        response_advice = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=prompt_advice
        )
        recommendation = response_advice.text

        # Pasul 4: Salvare în Baza de Date
        new_trip = Trip(
            query=query,
            city=city_name,
            temperature=float(temp) if isinstance(temp, (int, float)) else 0.0,
            recommendation=recommendation
        )
        db.add(new_trip)
        db.commit()

        return {
            "status": "success",
            "city": city_name,
            "weather": weather,
            "recommendation": recommendation
        }
    except Exception as e:
        logger.error(f"EROARE ADVISOR: {str(e)}")
        return {"status": "error", "message": f"Eroare la procesarea AI: {str(e)}"}

@app.get("/saved-trips", dependencies=[Depends(verify_api_key)])
def list_trips(db: Session = Depends(get_db)):
    return db.query(Trip).order_by(Trip.timestamp.desc()).all()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
