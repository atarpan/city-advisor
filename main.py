from fastapi import FastAPI, Query, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import requests
import os
from datetime import datetime
from google import genai
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# 1. Configurare Mediu & Bază de Date
load_dotenv()
DATABASE_URL = "sqlite:///./advisor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Model Bază de Date
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
app = FastAPI(title="City Advisor Pro (GET Mode)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Securitate & AI
MY_APP_AUTH_KEY = os.getenv("APP_AUTH_KEY", "secret-vibe-123")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-1.5-flash"

async def verify_api_key(x_api_key: str = Header(None)):
    """Verifică Header-ul 'x-api-key'."""
    if x_api_key != MY_APP_AUTH_KEY:
        raise HTTPException(status_code=403, detail="Acces refuzat: Cheie API invalidă.")
    return x_api_key

# 4. Funcții Utilitare
def fetch_weather(city: str):
    try:
        geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1").json()
        if not geo.get("results"): return None
        res = geo["results"][0]
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={res['latitude']}&longitude={res['longitude']}&current_weather=true").json()
        return {"city": res["name"], "temp": w["current_weather"]["temperature"]}
    except:
        return None

# --- ENDPOINT-URI (Transformate în GET) ---

@app.get("/")
def home():
    return {
        "message": "Bun venit la City Advisor Pro API!",
        "endpoints": {
            "health": "/health",
            "docs": "/docs (Interfață de testare)",
            "advisor": "/advisor (Cere recomandări)",
            "saved-trips": "/saved-trips (Vezi istoricul)"
        }
    }

@app.get("/health")
def health():
    return {"status": "ok", "mode": "GET", "database": "active"}

@app.get("/advisor", dependencies=[Depends(verify_api_key)])
def get_advice(
    query: str = Query(..., description="Întrebarea ta (ex: Vreau să joc biliard în Chișinău)"),
    days: int = Query(1, description="Număr de zile"),
    interests: str = Query("mâncare, cultură", description="Interese separate prin virgulă"),
    db: Session = Depends(get_db)
):
    """
    Acum funcționează cu GET! 
    Exemplu URL: /advisor?query=Bucuresti&days=1
    IMPORTANT: Trebuie să trimiți Header-ul 'x-api-key'.
    """
    try:
        # AI extrage orașul
        city_res = client.models.generate_content(
            model=MODEL_NAME, 
            contents=f"Extract only city name from: '{query}'. If none, return 'Unknown'."
        )
        city_name = city_res.text.strip()
        
        weather = fetch_weather(city_name)
        temp = weather["temp"] if weather else 0
        
        # AI generează recomandarea detaliată
        ai_prompt = f"""
        Utilizatorul vrea: {query}. 
        Vreme actuală în {city_name}: {temp}°C. 
        Plan pentru {days} zile. Interese: {interests}.
        Oferă un plan detaliat în română.
        """
        recommendation = client.models.generate_content(model=MODEL_NAME, contents=ai_prompt).text
        
        # SALVARE ÎN BAZA DE DATE
        new_trip = Trip(
            query=query,
            city=city_name,
            temperature=temp,
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/saved-trips", dependencies=[Depends(verify_api_key)])
def list_trips(db: Session = Depends(get_db)):
    """Afișează istoricul din baza de date."""
    return db.query(Trip).order_by(Trip.timestamp.desc()).all()

if __name__ == "__main__":
    import uvicorn
    # Portul este citit din mediu pentru Deploy (Render)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
