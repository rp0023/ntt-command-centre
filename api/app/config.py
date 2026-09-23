from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data")).resolve()
OPP_PATH = DATA_DIR / "opportunities.xlsx"
MOV_PATH = DATA_DIR / "opportunity_movement.csv"
ANOM_PATH = DATA_DIR / "client_anomaly_report.csv"

AS_OF = date.fromisoformat(os.environ.get("AS_OF", "2026-09-18"))

CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5174,http://127.0.0.1:5174,http://localhost:4173",
    ).split(",")
    if o.strip()
]

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

SERVICES_GM_TARGET = 0.30
COVERAGE_TARGET = 3.0
STALL_DAYS = 60
