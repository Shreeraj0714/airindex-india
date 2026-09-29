# AirIndex India

Smart India Hackathon prototype for SIH26056: a transparent, development/replay-data-backed airfare price intelligence platform. It calculates a Laspeyres-style prototype airfare index—it does not claim live prices, official CPI statistics, or Government of India weights.

## What is included

- FastAPI + Pydantic + SQLAlchemy API with SQLite local storage
- Configurable 10-route prototype basket and T+1, T+7, T+15, T+30, T+45 windows
- Deterministic 45-day development/replay collector (6,750 seeded observations)
- Core-fare normalization, validation, duplicate-ready payload hashes, IQR/MAD flags, quality scoring
- National/route indices, route contribution, dispersion, market-shock assessment, evidence-only explanations and a transparent baseline forecast
- Book / Monitor / Wait decision support and a prototype-weight scenario simulator
- React + TypeScript + Vite + Tailwind + Recharts dashboard; all numerical UI data comes from API responses

## Run on Windows PowerShell

Open two PowerShell terminals from `D:\Coding\airindex-india`.

### Terminal 1 — backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API documentation is at `http://127.0.0.1:8000/docs`.

### Terminal 2 — frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, then click **Initialize Dataset**. The dashboard will populate with clearly marked development/replay calculations.

## Dataset commands

With the backend running:

```powershell
# Seed only if the database is empty
Invoke-RestMethod -Method Post http://127.0.0.1:8000/seed

# Reset and regenerate deterministic development/replay data
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/seed?reset=true"

# Empty the local database
Invoke-RestMethod -Method Post http://127.0.0.1:8000/reset
```

## Verify

```powershell
cd backend
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

cd ..\frontend
npm run build
```

## Important limitations

This prototype uses no scraping circumvention: no CAPTCHA/access-control/robots/rate-limit/terms bypasses are implemented. Future collectors must use authorized airline or OTA APIs, permitted public sources, or user-provided CSV data.

**This prototype is not an official CPI calculation and does not represent official Government of India weights or statistics.**
