# City Activity Advisor — Project Rules

## What This Project Is
An AI agent that helps users plan outings. It checks real weather data, finds real places, and gives personalized recommendations combining both.

## Tech Stack
- Python 3.12
- FastAPI (backend framework)
- Google Gemini API (AI brain)
- Open-Meteo API (weather, free, no key)
- Requests library (HTTP calls)
- python-dotenv (environment variables)
- Single file: main.py

## Code Style
- Type hints on all functions
- Docstring on every endpoint
- Consistent JSON response: {"status": "ok/error", "data": ...}
- Environment variables for ALL secrets
- try/except on every endpoint

## When Unsure
- Ask me before creating new files
- Don't modify .env
- If an external API fails, return a graceful error