from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, TOGETHER_API_KEY
from app.semantic import measures as M
from app.semantic.anomalies import detect_anomalies, score_risk
from app.semantic.filters import slice_lines, slice_opps
from app.semantic.loader import Store
from app.semantic.rls import Principal

SYSTEM = """You are the NTT Deal Intelligence assistant for North America Salesforce pipeline.
You answer from the JSON facts you are given. Never invent numbers or anomaly types that are not in the facts.
Anomaly rows come only from Client_Anomaly_Report.csv. DealValue in that file is GP, not revenue.
If the facts are insufficient, say so. Prefer short executive prose.
Return ONLY valid JSON with this shape:
{
  "answer": "2-5 sentence answer with the key numbers in plain language",
  "tldr": "one line",
  "chartType": "funnel|waterfall|combo|heatmap|bubble|mekko|treemap|sankey|bar|table",
  "chartTitle": "short title",
  "focus": "stage|lob|portfolio|owner|industry|order_type|month|budget"
}
chartType must be the visualisation that best fits the question:
- stage conversion / how deals progress → funnel
- plan vs won vs commit vs gap → waterfall
- trend vs budget over months → combo
- LOB × portfolio or owner × anomaly → heatmap
- open deals by age vs confidence vs value → bubble
- mix of two dimensions → mekko
- composition of a total → treemap
- flow from order type to stage → sankey
- simple ranking → bar
- lists of deals → table
"""


def _facts(store: Store, principal: Principal, filters: dict | None, question: str) -> dict[str, Any]:
    lines = slice_lines(store, principal, filters)
    opps = slice_opps(store, principal, filters)
    anomalies = detect_anomalies(store, opps, principal)
    scored = score_risk(opps, anomalies)
    k = M.kpis(lines, opps)
    high = scored[scored["risk_band"] == "high_risk"].sort_values("acv_revenue", ascending=False).head(8)
    top_anom = anomalies.head(8) if not anomalies.empty else anomalies
    return {
        "question": question,
        "persona": principal.key,
        "scope": principal.scope_label,
        "kpis": k,
        "byStage": M.stage_funnel(opps),
        "byLob": M.group_measure(lines, "lob"),
        "byPortfolio": M.group_measure(lines, "portfolio"),
        "byOwnerOpen": M.group_measure(opps[opps["is_open"]] if not opps.empty else opps, "owner")[:12],
        "anomaliesByType": (
            anomalies.groupby("type").agg(n=("id", "count"), gp=("value", "sum")).reset_index().to_dict("records")
            if not anomalies.empty
            else []
        ),
        "highRiskDeals": _records(high),
        "topAnomalies": _records(top_anom),
        "anomalySource": "Client_Anomaly_Report.csv",
    }


def _records(df) -> list[dict]:
    if df is None or getattr(df, "empty", True):
        return []
    keep = [
        c
        for c in [
            "opportunity_code",
            "opportunity_name",
            "account_name",
            "owner",
            "stage",
            "acv_revenue",
            "close_probability",
            "risk_band",
            "risk_drivers",
            "type",
            "category",
            "severity",
            "title",
            "evidence",
            "reason",
            "action",
            "value",
            "entity_type",
            "entity_id",
            "label",
            "id",
        ]
        if c in df.columns
    ]
    out = df[keep].head(10).copy()
    for c in out.columns:
        if str(out[c].dtype).startswith("datetime"):
            out[c] = out[c].astype(str)
    return json.loads(out.to_json(orient="records"))


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if match:
        text = match.group(0)
    return json.loads(text)


async def _try_openrouter(messages: list[dict]) -> str | None:
    if not OPENROUTER_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemini-2.0-flash-001",
                "messages": messages,
                "temperature": 0.2,
            },
        )
        if r.status_code >= 400:
            return None
        return r.json()["choices"][0]["message"]["content"]


async def _try_gemini(prompt: str) -> str | None:
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        if r.status_code >= 400:
            return None
        parts = r.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts) or None


async def _try_together(messages: list[dict]) -> str | None:
    if not TOGETHER_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.together.xyz/v1/chat/completions",
            headers={"Authorization": f"Bearer {TOGETHER_API_KEY}"},
            json={"model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "messages": messages, "temperature": 0.2},
        )
        if r.status_code >= 400:
            return None
        return r.json()["choices"][0]["message"]["content"]


async def _try_groq(messages: list[dict]) -> str | None:
    if not GROQ_API_KEY:
        return None
    async with httpx.AsyncClient(timeout=40) as client:
        r = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.2},
        )
        if r.status_code >= 400:
            return None
        return r.json()["choices"][0]["message"]["content"]


def _fallback_plan(question: str) -> dict:
    q = question.lower()
    if any(w in q for w in ("funnel", "stage", "conversion", "progress")):
        return {"chartType": "funnel", "focus": "stage", "chartTitle": "Open and closed book by stage"}
    if any(w in q for w in ("budget", "plan", "gap", "coverage", "waterfall")):
        return {"chartType": "waterfall", "focus": "budget", "chartTitle": "Plan coverage bridge"}
    if any(w in q for w in ("month", "trend", "over time", "combo")):
        return {"chartType": "combo", "focus": "month", "chartTitle": "Won vs pipeline vs monthly plan"}
    if any(w in q for w in ("heatmap", "lob", "portfolio", "coverage matrix")):
        return {"chartType": "heatmap", "focus": "lob", "chartTitle": "Open ACV · LOB × portfolio"}
    if any(w in q for w in ("rep", "owner", "coach", "benchmark", "pattern")):
        return {"chartType": "bar", "focus": "owner", "chartTitle": "Open book by owner"}
    if any(w in q for w in ("industry", "treemap", "mix")):
        return {"chartType": "treemap", "focus": "industry", "chartTitle": "ACV by industry"}
    if any(w in q for w in ("sankey", "flow", "new business", "renewal")):
        return {"chartType": "sankey", "focus": "order_type", "chartTitle": "Order type into stage"}
    if any(w in q for w in ("bubble", "confidence", "age", "risk")):
        return {"chartType": "bubble", "focus": "owner", "chartTitle": "Open deals · age vs confidence"}
    if any(w in q for w in ("mekko", "marimekko")):
        return {"chartType": "mekko", "focus": "lob", "chartTitle": "LOB × order type"}
    return {"chartType": "bar", "focus": "lob", "chartTitle": "ACV by line of business"}


def _chart_payload(store: Store, principal: Principal, filters: dict | None, plan: dict) -> dict:
    lines = slice_lines(store, principal, filters)
    opps = slice_opps(store, principal, filters)
    ctype = plan.get("chartType") or "bar"
    title = plan.get("chartTitle") or "Pipeline view"
    if ctype == "funnel":
        return {"type": "funnel", "title": title, "data": M.stage_funnel(opps)}
    if ctype == "waterfall":
        return {"type": "waterfall", "title": title, "data": M.budget_waterfall(lines)}
    if ctype == "combo":
        return {"type": "combo", "title": title, "data": M.monthly_combo(lines)}
    if ctype == "heatmap":
        return {"type": "heatmap", "title": title, **M.heat_lob_portfolio(lines)}
    if ctype == "bubble":
        return {"type": "bubble", "title": title, "data": M.bubble_opps(opps)}
    if ctype == "mekko":
        return {"type": "mekko", "title": title, "data": M.mekko_lob_order(lines)}
    if ctype == "treemap":
        return {"type": "treemap", "title": title, "data": M.treemap_industry(opps)}
    if ctype == "sankey":
        return {"type": "sankey", "title": title, **M.sankey_order_stage(opps)}
    if ctype == "table":
        scored = score_risk(opps, detect_anomalies(store, opps, principal))
        top = scored.sort_values("acv_revenue", ascending=False).head(12)
        return {"type": "table", "title": title, "data": _records(top)}
    focus = plan.get("focus") or "lob"
    col = {"stage": "stage", "portfolio": "portfolio", "owner": "owner", "industry": "industry", "order_type": "order_type"}.get(
        focus, "lob"
    )
    src = opps if col in ("owner", "stage", "industry", "order_type") else lines
    return {"type": "bar", "title": title, "data": M.group_measure(src, col)}


def _deterministic_answer(facts: dict, plan: dict) -> dict:
    k = facts["kpis"]
    tldr = (
        f"Open pipeline is ${k['pipelineAcv']/1e6:.1f}M across {k['openOpportunities']} opportunities "
        f"({k['coverage']:.1f}× coverage vs a ${k['budgetAcv']/1e6:.1f}M cell budget)."
    )
    answer = (
        f"{tldr} Closed/won ACV is ${k['wonAcv']/1e6:.1f}M. {k['pastDueOpportunities']} open deals "
        f"(${k['pastDueAcv']/1e6:.1f}M) are past their close date. Services GM is {k['servicesGmPct']}% "
        f"against a 30% target. {len(facts['highRiskDeals'])} high-risk deals are in the current slice."
    )
    return {"answer": answer, "tldr": tldr, **plan, "provider": "deterministic"}


async def ask(store: Store, principal: Principal, question: str, filters: dict | None) -> dict:
    from app.semantic.precompute import cached_ask_pack, lookup_ask, _filter_key

    pack = cached_ask_pack(principal.key, principal.owner or "-", _filter_key(filters))
    title = None
    m = re.search(r"chart [“\"](.+?)[”\"]:", question)
    if m:
        title = m.group(1)
    hit = lookup_ask(pack, question, title)
    if hit:
        return {
            "answer": hit.get("answer") or "",
            "tldr": hit.get("tldr") or "",
            "chart": hit.get("chart") or _chart_payload(store, principal, filters, _fallback_plan(question)),
            "provider": "precomputed",
            "suggestions": hit.get("suggestions") or suggestions(principal.key),
        }
    facts = _facts(store, principal, filters, question)
    plan = _fallback_plan(question)
    parsed = _deterministic_answer(facts, plan)
    chart = _chart_payload(store, principal, filters, plan)
    return {
        "answer": parsed["answer"],
        "tldr": parsed["tldr"],
        "chart": chart,
        "provider": "precomputed",
        "suggestions": suggestions(principal.key),
    }


def suggestions(persona: str) -> list[str]:
    if persona == "executive":
        return [
            "Give me the three-line story for entity stakeholders this week",
            "Are we covering the FY26 plan, and where is the gap?",
            "Which industries concentrate closed-won ACV?",
            "Show pipeline as a stage funnel",
        ]
    if persona == "manager":
        return [
            "Which owners concentrate stalled or shrinking deals?",
            "Who is systematically walking forecast backwards?",
            "Compare open book by owner",
            "Where should I coach upsell versus clean-up?",
        ]
    return [
        "Which of my deals are at highest risk of slipping?",
        "What is still open past its close date?",
        "Show my funnel by stage",
        "What should I do this week?",
    ]
