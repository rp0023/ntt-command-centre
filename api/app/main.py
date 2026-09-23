from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel, Field

from app.config import CORS_ORIGINS
from app.semantic.ask import ask, suggestions
from app.semantic.filters import slice_lines, slice_opps
from app.semantic.loader import load_store
from app.semantic.precompute import cached_ask_pack, warm_ask_packs
from app.semantic.rls import resolve
from app.semantic.views import alerts, default_sales_owner, meta, opportunity_detail, view


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_store()
    warm_ask_packs()
    yield


app = FastAPI(title="NTT Deal Intelligence", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS + ["http://localhost:5173", "https://localhost:5174"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskBody(BaseModel):
    question: str
    persona: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)


def _principal(persona: str | None, x_persona: str | None = None):
    store = load_store()
    key = persona or x_persona or "sales"
    owner = default_sales_owner(store) if key == "sales" else None
    return resolve(key, owner)


@app.get("/healthz")
def healthz():
    store = load_store()
    return {
        "ok": True,
        "lines": int(len(store.lines)),
        "opportunities": int(store.opportunities["opportunity_code"].nunique()),
        "movement": int(len(store.movement)),
        "anomalies": int(len(store.anomalies)),
        "anomaliesMatchedToExcel": int(store.anomalies["in_excel"].sum()) if not store.anomalies.empty else 0,
    }


@app.get("/api/meta")
def api_meta(persona: str | None = Query(default=None), x_persona: str | None = Header(default=None)):
    store = load_store()
    return meta(store, _principal(persona, x_persona))


@app.get("/api/view")
def api_view(
    lens: str = Query(default="command"),
    persona: str | None = Query(default=None),
    country: list[str] | None = Query(default=None),
    lob: list[str] | None = Query(default=None),
    portfolio: list[str] | None = Query(default=None),
    stage: list[str] | None = Query(default=None),
    forecast: list[str] | None = Query(default=None),
    orderType: list[str] | None = Query(default=None),
    owner: list[str] | None = Query(default=None),
    quarter: list[str] | None = Query(default=None),
    industry: list[str] | None = Query(default=None),
    search: str | None = Query(default=None),
):
    store = load_store()
    principal = _principal(persona)
    filters = {
        "countries": country or [],
        "lobs": lob or [],
        "portfolios": portfolio or [],
        "stages": stage or [],
        "forecasts": forecast or [],
        "orderTypes": orderType or [],
        "owners": owner or [],
        "quarters": quarter or [],
        "industries": industry or [],
        "search": search or "",
    }
    return view(store, principal, filters, lens)


@app.get("/api/opportunity/{code}")
def api_opportunity(code: str, persona: str | None = Query(default=None)):
    store = load_store()
    try:
        return opportunity_detail(store, _principal(persona), code)
    except KeyError as e:
        raise HTTPException(404, f"Opportunity {e} is outside this persona's scope") from e


@app.get("/api/alerts")
def api_alerts(persona: str | None = Query(default=None)):
    return {"items": alerts(load_store(), _principal(persona))}


@app.get("/api/suggestions")
def api_suggestions(persona: str | None = Query(default=None)):
    return {"items": suggestions((persona or "sales"))}


@app.get("/api/ask-pack")
def api_ask_pack(persona: str | None = Query(default=None)):
    principal = _principal(persona)
    return cached_ask_pack(principal.key, principal.owner or "-", "{}")


@app.post("/api/ask")
async def api_ask(body: AskBody):
    store = load_store()
    principal = _principal(body.persona)
    return await ask(store, principal, body.question, body.filters)


@app.get("/api/v1/measures")
def api_measures(persona: str | None = Query(default=None)):
    """Raw KPI dictionary — proof the semantic layer is not welded to the UI."""
    from app.semantic.measures import kpis

    store = load_store()
    p = _principal(persona)
    return kpis(slice_lines(store, p, None), slice_opps(store, p, None))
