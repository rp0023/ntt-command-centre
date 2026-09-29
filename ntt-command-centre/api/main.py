"""Authenticated API boundary. Account identity comes only from the bearer token."""

from __future__ import annotations

import json
from typing import cast

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

import auth
from config import ALLOWED_ORIGINS, AS_OF
from llm import service as AI
from semantic import accounts as ACC
from semantic import actions as ACT
from semantic import anomalies as ANOM
from semantic import budget as B
from semantic import catalog as CAT
from semantic import crosssell as XS
from semantic import ds_model as DS
from semantic import executive as EXEC
from semantic import measures as M
from semantic import personas as PR
from semantic import predict as P
from semantic import query as Q
from semantic import views as V
from semantic.loader import CUR_QUARTER, fy_label, report
from semantic.measures import FilterState
from semantic.personas import Principal

app = FastAPI(
    title="NTT Deal Intelligence — semantic API",
    version="2.0.0",
    description=(
        "The API boundary. Authentication and row-level security attach here; "
        "every figure is computed in api/semantic/ from the client's three "
        "datasets at request time, pinned to AS_OF."
    ),
)

# Order matters and is the reverse of how it reads: Starlette makes the LAST
# middleware added the OUTERMOST. The gate goes on first so that CORS wraps
# it — a 401 from the gate then still carries the CORS headers, and the
# browser hands the page a readable status instead of an opaque network error.
app.add_middleware(auth.AccessGate)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.on_event("startup")
def _warm() -> None:
    """
    Build the expensive caches before the first person arrives.

    The first view of a process loads the four files, derives the movement
    features, scores every open deal and fits the independent closure model —
    about twenty seconds on a fresh Cloud Run instance. Left to the first
    request, that is twenty seconds of a stakeholder looking at a skeleton.
    Done here, in a thread so the health probe answers immediately, the same
    work happens while the instance is still being routed to.
    """
    import threading

    def run() -> None:
        try:
            for persona in PR.PERSONAS:
                p = PR.resolve(persona)
                V.view(p.persona.home, FilterState(), p)
        except Exception as e:  # noqa: BLE001 — warming must never take the process down
            print(f"warm-up skipped: {type(e).__name__}: {e}")

    threading.Thread(target=run, name="warm-up", daemon=True).start()


# --------------------------------------------------------------------------- #
# Identity — the one place a principal is created
# --------------------------------------------------------------------------- #


def _principal(request: Request) -> Principal:
    return auth.principal(request)


def _filters(request: Request) -> FilterState:
    fs = FilterState.from_query(dict(request.query_params))
    if _principal(request).key == "executive":
        return FilterState(country=fs.country, quarter=fs.quarter, measure="revenue")
    return fs


def _charts_say(request: Request) -> list[str]:
    """
    What the client says is on screen — union'd server-side, never trusted alone.

    A stale or edited client list must not be able to unlock a redundant answer,
    so the caller's list is combined with the set the server recomputes for the
    same page.
    """
    raw = request.query_params.get("chartsSay")
    if not raw:
        return []
    try:
        return [str(s) for s in json.loads(raw)][:40]
    except (ValueError, TypeError):
        return [s.strip() for s in raw.split(",") if s.strip()][:40]


# --------------------------------------------------------------------------- #
# Health and provenance
# --------------------------------------------------------------------------- #


# Both paths serve the same probe. `/healthz` is what run.sh and the local
# proxy use; on Cloud Run that path is answered by Google's front end before
# the container sees it, so production monitoring reads `/api/health`.
@app.get("/healthz")
@app.get("/api/health")
def healthz() -> dict:
    return {"ok": True}


@app.get("/api/health/details")
def health_details(request: Request) -> dict:
    if _principal(request).key != "executive":
        raise HTTPException(403, "Executive access required")
    r = report()
    return {
        "ok": True,
        "asOf": AS_OF.isoformat(),
        "quarter": CUR_QUARTER,
        "fy": fy_label(2026),
        "data": {
            "lines": r.lines, "opportunities": r.opportunities,
            "accounts": r.accounts, "reps": r.reps,
            "movementRows": r.movement_rows, "anomalies": r.anomalies,
            "orphanMovement": r.orphan_movement_opps,
            "orphanAnomalies": r.orphan_anomaly_opps,
            "closeBeforeCreate": r.close_before_create,
        },
        "dsModel": DS.available(),
        "llm": AI.health(),
        "catalog": CAT.size_report(),
    }


@app.get("/api/meta")
def api_meta(request: Request) -> dict:
    return V.meta(_principal(request))


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #


@app.get("/api/view")
def api_view(request: Request, page: str = Query(default="")) -> dict:
    p = _principal(request)
    return V.view(page or p.persona.home, _filters(request), p)


@app.get("/api/actions")
def api_actions(request: Request, limit: int = Query(default=12, le=40)) -> dict:
    p = _principal(request)
    if p.key == "executive":
        actions = EXEC.payload(_filters(request), p)["actions"][:limit]
        return {"actions": actions, "persona": p.key, "scope": p.identity_label}
    return {"actions": ACT.build(_filters(request), p, limit=limit),
            "persona": p.key, "scope": p.identity_label}


# --------------------------------------------------------------------------- #
# Intelligence
# --------------------------------------------------------------------------- #


@app.get("/api/risk")
def api_risk(request: Request, limit: int = Query(default=50, le=300)) -> dict:
    p = _principal(request)
    fs = _filters(request)
    r = P.risk_table()
    codes = set(M.slice_frame(fs, p)["opportunity_code"])
    r = r[r["opportunity_code"].isin(codes)].head(limit)
    if p.key == "executive":
        focused = EXEC.payload(fs, p)
        return {"asOf": AS_OF.isoformat(), "model": focused["closureModel"],
                "deals": focused["closureExceptions"][:limit]}
    return {
        "asOf": AS_OF.isoformat(),
        "model": P.model_card(),
        "deals": [
            {"opportunityCode": row.opportunity_code, "name": row.opportunity_name,
             "account": row.account_name, "owner": row.owner, "stage": row.stage,
             "lob": row.lob, "portfolio": row.portfolio,
             "gp": float(cast(float, row.acv_gp)),
             "revenue": float(cast(float, row.acv_revenue)),
             "riskScore": int(cast(int, row.risk_score)), "riskBand": row.risk_band,
             "topDriver": row.top_driver, "factors": row.risk_factors,
             "valueAtRisk": float(cast(float, row.value_at_risk))}
            for row in r.itertuples(index=False)
        ],
    }


@app.get("/api/deal/{opportunity_code}")
def api_deal(opportunity_code: str, request: Request) -> dict:
    p = _principal(request)
    # RLS on a single record too: a deal outside the principal's scope is a 404,
    # not a redacted 200 — the existence of the record is itself information.
    scoped = set(M.slice_frame(FilterState(), p)["opportunity_code"])
    if opportunity_code not in scoped:
        raise HTTPException(status_code=404, detail="no such opportunity in your scope")
    detail = P.explain(opportunity_code)
    if not detail:
        raise HTTPException(status_code=404, detail="opportunity is not open")
    if p.key == "executive":
        safe_factors = [f for f in detail.get("riskFactors", []) if f.get("key") != "thin_margin"]
        return {
            "opportunityCode": detail["opportunityCode"], "name": detail["name"],
            "account": detail["account"], "owner": detail["owner"], "stage": detail["stage"],
            "acvRevenue": detail["acvRevenue"], "closeDate": detail["closeDate"],
            "riskScore": detail["riskScore"], "riskBand": detail["riskBand"],
            "riskFactors": safe_factors, "quietDays": detail["quietDays"],
            "closureProbability": detail.get("pWin"),
            "modelDisclosure": "Closure probability is directional; use observable deal movement to decide.",
        }
    return {
        **detail,
        "timeline": ANOM.evidence_rows(opportunity_code, 60),
        "benchmarks": DS.benchmark_card(opportunity_code) if DS.available() else [],
        "findings": ANOM.unified().query(
            "entity_id == @opportunity_code").to_dict("records"),
    }


@app.get("/api/anomalies")
def api_anomalies(request: Request, limit: int = Query(default=80, le=500)) -> dict:
    p = _principal(request)
    fs = _filters(request)
    if p.key == "executive":
        focused = EXEC.payload(fs, p)
        return {"summary": focused["messages"][1],
                "findings": focused["anomalyFindings"][:limit],
                "total": len(focused["anomalyFindings"])}
    a = ANOM.for_persona(p.key)
    if fs.anomaly_category:
        a = a[a["category"] == fs.anomaly_category]
    # Routing decides which findings a role can act on; row-level security
    # decides which of those this caller may see. Every grain is narrowed —
    # an account finding to the caller's own accounts, a rep finding to the
    # reps in their predicate — not only the opportunity ones. The rule lives
    # with the findings so the risks page applies the same one.
    a = ANOM.scoped(a, fs, p)
    return {
        "summary": ANOM.summary(a),
        "taxonomy": {"categories": [{"name": c, "question": ANOM.CATEGORY_BLURB[c]}
                                    for c in ANOM.CATEGORY_ORDER]},
        "findings": a.head(limit).replace({float("nan"): None}).to_dict("records"),
        "total": int(len(a)),
    }


@app.get("/api/accounts")
def api_accounts(request: Request) -> dict:
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Account analysis is not part of the focused Executive experience")
    fs = _filters(request)
    return {
        "whitespace": ACC.whitespace(fs, p, limit=40),
        "concentration": ACC.concentration(fs, p),
        "lobValue": ACC.lob_count_value(fs, p).to_dict("records"),
        "attach": ACC.attach_matrix(fs, p).to_dict("records"),
    }


@app.get("/api/account/{account_code}")
def api_account(account_code: str, request: Request) -> dict:
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Account analysis is not part of the focused Executive experience")
    d = ACC.account_detail(account_code, FilterState(), p)
    if not d:
        raise HTTPException(status_code=404, detail="no such account")
    # The cross-sell recommendations for this account travel with it, so the
    # drawer never has to make a second call to answer "what should we sell
    # them next".
    d["crossSell"] = [r for r in XS.unified(FilterState(), p, limit=10000)
                      if r.get("accountCode") == account_code]
    return d


@app.get("/api/crosssell")
def api_crosssell(request: Request) -> dict:
    """
    The growth surface: recommendations, the plays they group into, and counts.

    Row-level security applies before anything is grouped, so a rep's themes
    are themes across their own accounts rather than the entity's themes with
    other people's accounts hidden — a filtered aggregate is a different
    number, not a smaller view of the same one.
    """
    p = _principal(request)
    if p.key == "executive":
        focused = EXEC.payload(_filters(request), p)
        return {"plays": focused["opportunityPlays"],
                "message": focused["messages"][0]}
    fs = _filters(request)
    return {
        "recommendations": XS.unified(fs, p, limit=100),
        "themes": XS.themes(fs, p),
        "summary": XS.summary(fs, p),
        "confidenceMeaning": XS.CONFIDENCE_MEANING,
        "methodMeaning": XS.METHOD_MEANING,
        "caveat": XS.CAVEAT,
    }


@app.get("/api/budget")
def api_budget(request: Request) -> dict:
    p = _principal(request)
    if not p.may_see("budget"):
        raise HTTPException(403, "Budget is not available for this role")
    fs = _filters(request)
    return {
        "totals": B.totals(fs, p),
        "quarters": B.by_quarter(fs, p),
        "months": B.by_month(fs, p),
        "grid": B.coverage_grid(fs, p),
        "byLob": B.coverage_by(fs, p, "lob"),
        "byPortfolio": B.coverage_by(fs, p, "portfolio"),
        "bridge": B.bridge(fs, p),
    }


# --------------------------------------------------------------------------- #
# The AI surfaces
# --------------------------------------------------------------------------- #


@app.get("/api/ai/brief")
def api_brief(request: Request, page: str = Query(default="")) -> dict:
    p = _principal(request)
    fs = _filters(request)
    page = V.resolve_page(page or p.persona.home, p)
    # The server recomputes what is on screen and unions it with the client's
    # claim, so a stale client cannot unlock a redundant answer.
    server_says = [s for c in V.charts_for(page, fs, p) for s in c["says"]]
    say = list(dict.fromkeys(_charts_say(request) + server_says))
    return AI.brief(fs, p, say, page)


@app.get("/api/ai/ask")
def api_ask(request: Request, q: str = Query(..., min_length=2, max_length=400),
            chart: str | None = Query(default=None, max_length=80),
            page: str | None = Query(default=None, max_length=40)) -> dict:
    """
    `chart` and `page` name the chart a question was typed beside. The chart
    is rebuilt server-side from the id for THIS principal and slice — the
    client's copy of it is never trusted — and the answer is words only.
    """
    p = _principal(request)
    return AI.ask(q, _filters(request), p, _charts_say(request), chart_id=chart, page=page)


@app.post("/api/ai/explain")
def api_explain(request: Request, card: dict = Body(...)) -> dict:
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Use the focused Executive action details")
    fs = _filters(request)
    cards = ACT.build(fs, p, limit=10000)
    actual = next((c for c in cards if c["key"] == card.get("key")), None)
    if actual is None:
        raise HTTPException(404, "No such recommendation in your scope")
    return AI.explain(actual, fs, p, _charts_say(request))


@app.get("/api/ai/next-action/{opportunity_code}")
def api_next_action(opportunity_code: str, request: Request) -> dict:
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Deal next-step generation is not available for Executive")
    scoped = set(M.slice_frame(FilterState(), p)["opportunity_code"])
    if opportunity_code not in scoped:
        raise HTTPException(status_code=404, detail="no such opportunity in your scope")
    return AI.next_action(opportunity_code, _filters(request), p)


@app.get("/api/ai/digest")
def api_digest(request: Request, days: int = Query(default=7, ge=1, le=90)) -> dict:
    p = _principal(request)
    return AI.digest(_filters(request), p, days)


# --------------------------------------------------------------------------- #
# The proof the semantic layer is not welded to this UI
# --------------------------------------------------------------------------- #


@app.get("/api/v1/measures")
def api_measures(request: Request) -> dict:
    """
    The raw measure dictionary, unwrapped.

    No view model, no chart specs, no prose. If the semantic layer were welded
    to the front end, this endpoint could not exist.
    """
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Raw measures are not part of the focused Executive experience")
    fs = _filters(request)
    return {
        "asOf": AS_OF.isoformat(),
        "principal": {"persona": p.key, "identity": p.identity,
                      "predicate": p.predicate_sql},
        "filters": fs.values,
        "measure": fs.measure,
        "measures": M.measures(fs, p),
    }


@app.get("/api/v1/catalog")
def api_catalog(request: Request) -> dict:
    """
    The machine-readable semantic catalog — the context layer the LLM is given.

    Published deliberately: any other consumer that wants to reason over this
    business reads the same description of it that our own model does, and can
    check that the definitions match what the screen shows.
    """
    if _principal(request).key == "executive":
        raise HTTPException(403, "The raw catalog is not part of the focused Executive experience")
    if _principal(request).key != "executive":
        raise HTTPException(403, "Executive access required")
    return {**CAT.build(), "size": CAT.size_report()}


@app.post("/api/v1/query")
def api_query(request: Request, plan: dict = Body(...)) -> dict:
    """
    Execute a query plan directly, without a model in the loop.

    The same validator and the same dispatch the AI path uses. It exists so the
    plan contract can be tested — and demonstrated — independently of whether a
    language model is available or behaving.
    """
    p = _principal(request)
    if p.key == "executive":
        raise HTTPException(403, "Raw semantic queries are not part of the focused Executive experience")
    fs = _filters(request)
    try:
        r = Q.execute(plan, fs, p, _charts_say(request))
    except Q.PlanError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"rows": r.rows, "shape": r.shape, "chartKey": r.chart_key,
            "chartWhy": r.chart_why, "claim": r.claim, "note": r.note,
            "chart": Q.to_chart_spec(plan, r, fs)}
