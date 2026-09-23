from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from app.semantic import measures as M
from app.semantic.anomalies import detect_anomalies, score_risk
from app.semantic.filters import slice_lines, slice_opps
from app.semantic.loader import Store
from app.semantic.rls import Principal

CHART_Q = (
    ("takeaway", "Main takeaway"),
    ("off", "What looks off"),
    ("next", "What should I do next"),
)


def _m(v: float) -> str:
    n = float(v or 0)
    sign = "−" if n < 0 else ""
    a = abs(n)
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{sign}${a / 1_000:.0f}k"
    return f"{sign}${a:.0f}"


def _norm(q: str) -> str:
    q = q.lower().strip()
    q = re.sub(r"^using only the chart [“\"][^”\"]+[”\"]: ", "", q)
    q = re.sub(r"[?!.,]", "", q)
    q = re.sub(r"\s+", " ", q)
    return q


def _tldr(s: str) -> str:
    s = (s or "").strip()
    if len(s) <= 140:
        return s
    return s[:137].rstrip() + "…"


def _item(answer: str, tldr: str, chart: dict | None, key: str) -> dict[str, Any]:
    return {
        "key": key,
        "answer": answer,
        "tldr": tldr,
        "chart": chart,
        "provider": "precomputed",
        "suggestions": [],
    }


def _funnel_chart(data: list) -> dict:
    return {"type": "funnel", "title": "Stage mix", "data": data}


def _bar_chart(data: list, title: str) -> dict:
    return {"type": "bar", "title": title, "data": data}


def _chart_pack(k: dict, charts: dict, anomalies, scored, principal: Principal) -> dict[str, dict[str, dict]]:
    funnel = charts.get("funnel") or []
    open_stages = [r for r in funnel if r.get("label") not in {"Deal Won", "Deal Lost"}]
    top_stage = max(open_stages, key=lambda r: r.get("acv") or 0) if open_stages else None
    won = next((r for r in funnel if r.get("label") == "Deal Won"), None)
    idn = next((r for r in funnel if r.get("label") == "Identification"), None)

    past_n = int(k.get("pastDueOpportunities") or 0)
    past_acv = float(k.get("pastDueAcv") or 0)
    cover = float(k.get("coverage") or 0)
    gm = float(k.get("servicesGmPct") or 0)

    bubble = charts.get("bubble") or []
    stale = [b for b in bubble if (b.get("x") or 0) >= 90]
    low_conf = [b for b in bubble if (b.get("y") or 0) < 40 and (b.get("z") or 0) > 20000]

    by_owner = charts.get("byOwner") or []
    top_owner = by_owner[0] if by_owner else None

    treemap = charts.get("treemap") or []
    top_ind = treemap[0] if treemap else None

    waterfall = charts.get("waterfall") or []
    uncovered = next((r for r in waterfall if r.get("label") == "Uncovered"), None)

    anom_n = int(len(anomalies)) if anomalies is not None and not getattr(anomalies, "empty", True) else 0
    anom_types = {}
    if anom_n:
        anom_types = anomalies.groupby("type").size().sort_values(ascending=False).to_dict()
    top_anom_type = next(iter(anom_types), None)

    high_n = int((scored["risk_band"] == "high_risk").sum()) if scored is not None and not scored.empty else 0

    stage_take = (
        f"Open book is {_m(k['pipelineAcv'])} across {k['openOpportunities']} opportunities. "
        + (
            f"{top_stage['label']} holds the most open ACV ({_m(top_stage['acv'])}, {top_stage['count']} deals)."
            if top_stage
            else "Stage mix is empty in this slice."
        )
    )
    stage_off = (
        f"{past_n} open opportunities ({_m(past_acv)}) are past close date. "
        + (
            f"Identification still holds {_m(idn['acv'])}."
            if idn and idn.get("acv")
            else "Early-stage ACV is thin."
        )
    )
    stage_next = (
        f"Work the {high_n} high-risk open deals first, then reset close dates on the {past_n} past-due records."
        if principal.key == "sales"
        else f"{anom_n} client-report flags sit in this slice. Start with {top_anom_type or 'the highest-severity rows'}."
    )

    bubble_take = (
        f"{len(bubble)} open deals are plotted. {len(stale)} are 90+ days old; {len(low_conf)} combine low confidence with material value."
    )
    bubble_off = (
        f"Age and confidence are misaligned on {len(low_conf)} deals. Past-due bubbles should not still sit in Commit."
        if low_conf
        else "No large low-confidence outliers in the plotted set."
    )
    bubble_next = "Open the oldest low-confidence deals and demand a dated next step or a forecast walk-back."

    cover_take = (
        f"Coverage is {cover:.1f}× against a {_m(k['budgetAcv'])} cell budget. Won ACV is {_m(k['wonAcv'])}."
        + (f" Uncovered remainder is {_m(uncovered['value'])}." if uncovered else "")
    )
    cover_off = (
        f"Coverage is below the 3× rule of thumb."
        if cover < 3
        else "Coverage clears the 3× rule of thumb in this slice."
    )
    cover_next = "Push Commit quality, not just more pipeline — past-due Commit is the first leak."

    combo = charts.get("combo") or []
    last = combo[-1] if combo else None
    combo_take = (
        f"Latest month {last['label']}: won {_m(last['won'])}, still open {_m(last['pipeline'])}, plan {_m(last['budget'])}."
        if last
        else "No monthly series in this slice."
    )
    combo_off = "Watch months where open pipeline sits under the monthly plan line."
    combo_next = "Use the thin months as the pipeline-generation conversation, not a year-end surprise."

    ind_take = (
        f"{top_ind['name']} is the largest industry block at {_m(top_ind['value'])}."
        if top_ind
        else "No industry mix in this slice."
    )
    ind_off = "Concentration in one industry is a diversification topic for entity stakeholders."
    ind_next = "Keep the industry mix next to the concentration flags in the client anomaly report."

    heat = charts.get("heatmap") or {}
    heat_take = "Open ACV by LOB × portfolio is the coverage map for this slice."
    heat_off = "Empty or near-empty cells with budget behind them are coverage holes — see coverage_hole in the client report."
    heat_next = "Regional leads should generate pipeline only in the empty budgeted cells, not everywhere."

    mekko_take = "LOB × order type shows where New Business vs Renewal dollars sit."
    mekko_off = "A LOB that is almost all Renewal is a new-business mix risk."
    mekko_next = "Coach the renewal-heavy owners using the Rep Behavior rows, not a generic pep talk."

    owner_take = (
        f"{top_owner['label']} holds the largest open ACV ({_m(top_owner.get('openAcv') or top_owner.get('acv') or 0)})."
        if top_owner
        else "No owner ranking in this slice."
    )
    owner_off = "Owner concentration is a coverage-planning issue if that person is out."
    owner_next = "Benchmark stalled and shrink flags by owner from the client report."

    sankey_take = "Order type flowing into stage shows where New / Renewal / Expansion actually sits in the funnel."
    sankey_off = "Renewal stuck in early stages is process, not demand."
    sankey_next = "Pull a sample of early-stage renewals and confirm they belong in the book."

    lob_take = "LOB mix is the dollar ranking for this slice."
    lob_off = "Do not average GM% across LOBs — Product vs Services mix moves the number."
    lob_next = f"Services GM is {gm}% versus the 30% planning target."

    flags_take = f"{anom_n} rows from Client_Anomaly_Report.csv are in scope. {high_n} open deals sit in the high-risk band."
    flags_off = (
        f"Most common type is {top_anom_type} ({anom_types.get(top_anom_type, 0)} rows)."
        if top_anom_type
        else "No client-report flags in this slice."
    )
    flags_next = "Treat Cross-Sell rows as upside. Sequence and Value Integrity rows need a human check, not an auto-close."

    pack = {
        "Stage mix": {
            "Main takeaway": _item(stage_take, _tldr(stage_take), _funnel_chart(funnel), "stage-takeaway"),
            "What looks off": _item(stage_off, f"{past_n} past close date", _funnel_chart(funnel), "stage-off"),
            "What should I do next": _item(stage_next, "Start with high-risk and past-due", _bar_chart(by_owner[:8], "Open book by owner"), "stage-next"),
        },
        "Age vs confidence": {
            "Main takeaway": _item(bubble_take, f"{len(stale)} aged 90+ days", {"type": "bubble", "title": "Age vs confidence", "data": bubble}, "bubble-takeaway"),
            "What looks off": _item(bubble_off, f"{len(low_conf)} low-confidence outliers", {"type": "bubble", "title": "Age vs confidence", "data": bubble}, "bubble-off"),
            "What should I do next": _item(bubble_next, "Dated next step or walk-back", {"type": "bubble", "title": "Age vs confidence", "data": bubble}, "bubble-next"),
        },
        "Coverage bridge": {
            "Main takeaway": _item(cover_take, f"{cover:.1f}× coverage", {"type": "waterfall", "title": "Coverage bridge", "data": waterfall}, "cover-takeaway"),
            "What looks off": _item(cover_off, cover_off, {"type": "waterfall", "title": "Coverage bridge", "data": waterfall}, "cover-off"),
            "What should I do next": _item(cover_next, "Commit quality first", {"type": "waterfall", "title": "Coverage bridge", "data": waterfall}, "cover-next"),
        },
        "Won vs open vs plan": {
            "Main takeaway": _item(combo_take, combo_take[:80], {"type": "combo", "title": "Won vs open vs plan", "data": combo}, "combo-takeaway"),
            "What looks off": _item(combo_off, combo_off, {"type": "combo", "title": "Won vs open vs plan", "data": combo}, "combo-off"),
            "What should I do next": _item(combo_next, combo_next, {"type": "combo", "title": "Won vs open vs plan", "data": combo}, "combo-next"),
        },
        "Won vs plan": {
            "Main takeaway": _item(combo_take, combo_take[:80], {"type": "combo", "title": "Won vs plan", "data": combo}, "combo2-takeaway"),
            "What looks off": _item(combo_off, combo_off, {"type": "combo", "title": "Won vs plan", "data": combo}, "combo2-off"),
            "What should I do next": _item(combo_next, combo_next, {"type": "combo", "title": "Won vs plan", "data": combo}, "combo2-next"),
        },
        "Industry mix": {
            "Main takeaway": _item(ind_take, ind_take, {"type": "treemap", "title": "Industry mix", "data": treemap}, "ind-takeaway"),
            "What looks off": _item(ind_off, ind_off, {"type": "treemap", "title": "Industry mix", "data": treemap}, "ind-off"),
            "What should I do next": _item(ind_next, ind_next, {"type": "heatmap", "title": "LOB × portfolio", **heat} if heat else {"type": "treemap", "data": treemap}, "ind-next"),
        },
        "Order type to stage": {
            "Main takeaway": _item(sankey_take, sankey_take, {"type": "sankey", "title": "Order type to stage", **(charts.get("sankey") or {})}, "sankey-takeaway"),
            "What looks off": _item(sankey_off, sankey_off, {"type": "sankey", "title": "Order type to stage", **(charts.get("sankey") or {})}, "sankey-off"),
            "What should I do next": _item(sankey_next, sankey_next, _funnel_chart(funnel), "sankey-next"),
        },
        "LOB × portfolio": {
            "Main takeaway": _item(heat_take, heat_take, {"type": "heatmap", "title": "LOB × portfolio", **heat} if heat else _bar_chart(charts.get("byLob") or [], "LOB mix"), "heat-takeaway"),
            "What looks off": _item(heat_off, heat_off, {"type": "heatmap", "title": "LOB × portfolio", **heat} if heat else _bar_chart(charts.get("byLob") or [], "LOB mix"), "heat-off"),
            "What should I do next": _item(heat_next, heat_next, {"type": "heatmap", "title": "LOB × portfolio", **heat} if heat else _bar_chart(charts.get("byLob") or [], "LOB mix"), "heat-next"),
        },
        "LOB mix": {
            "Main takeaway": _item(lob_take, lob_take, _bar_chart(charts.get("byLob") or [], "LOB mix"), "lob-takeaway"),
            "What looks off": _item(lob_off, lob_off, _bar_chart(charts.get("byLob") or [], "LOB mix"), "lob-off"),
            "What should I do next": _item(lob_next, lob_next, _bar_chart(charts.get("byPortfolio") or [], "Portfolio mix"), "lob-next"),
        },
        "Open book by owner": {
            "Main takeaway": _item(owner_take, owner_take, _bar_chart(by_owner[:12], "Open book by owner"), "owner-takeaway"),
            "What looks off": _item(owner_off, owner_off, _bar_chart(by_owner[:12], "Open book by owner"), "owner-off"),
            "What should I do next": _item(owner_next, owner_next, _bar_chart(by_owner[:12], "Open book by owner"), "owner-next"),
        },
        "LOB × order type": {
            "Main takeaway": _item(mekko_take, mekko_take, {"type": "mekko", "title": "LOB × order type", "data": charts.get("mekko") or []}, "mekko-takeaway"),
            "What looks off": _item(mekko_off, mekko_off, {"type": "mekko", "title": "LOB × order type", "data": charts.get("mekko") or []}, "mekko-off"),
            "What should I do next": _item(mekko_next, mekko_next, _bar_chart(by_owner[:12], "Open book by owner"), "mekko-next"),
        },
        "Flagged rows": {
            "Main takeaway": _item(flags_take, flags_take, _bar_chart(charts.get("byLob") or [], "LOB mix"), "flags-takeaway"),
            "What looks off": _item(flags_off, flags_off, _funnel_chart(funnel), "flags-off"),
            "What should I do next": _item(flags_next, flags_next, _bar_chart(by_owner[:8], "Open book by owner"), "flags-next"),
        },
        "Rep Behavior from client report": {
            "Main takeaway": _item(flags_take, flags_take, _bar_chart(by_owner[:12], "Open book by owner"), "rep-takeaway"),
            "What looks off": _item(flags_off, flags_off, _bar_chart(by_owner[:12], "Open book by owner"), "rep-off"),
            "What should I do next": _item(owner_next, owner_next, _bar_chart(by_owner[:12], "Open book by owner"), "rep-next"),
        },
        "Deals": {
            "Main takeaway": _item(stage_take, _tldr(stage_take), _funnel_chart(funnel), "deals-takeaway"),
            "What looks off": _item(stage_off, f"{past_n} past close date", _funnel_chart(funnel), "deals-off"),
            "What should I do next": _item(stage_next, "High-risk first", _bar_chart(by_owner[:8], "Open book by owner"), "deals-next"),
        },
    }
    return pack


def _prompt_pack(k: dict, charts: dict, anomalies, scored, tldr_lines: list[str], principal: Principal) -> list[dict]:
    funnel = {"type": "funnel", "title": "Stage mix", "data": charts.get("funnel") or []}
    waterfall = {"type": "waterfall", "title": "Coverage bridge", "data": charts.get("waterfall") or []}
    treemap = {"type": "treemap", "title": "Industry mix", "data": charts.get("treemap") or []}
    owners = {"type": "bar", "title": "Open book by owner", "data": (charts.get("byOwner") or [])[:12]}
    bubble = {"type": "bubble", "title": "Age vs confidence", "data": charts.get("bubble") or []}
    past = f"{k['pastDueOpportunities']} open deals ({_m(k['pastDueAcv'])}) are past close date."
    high_n = int((scored["risk_band"] == "high_risk").sum()) if scored is not None and not scored.empty else 0
    brief = " ".join(tldr_lines[:3])
    if principal.key == "executive":
        rows = [
            ("Give me this week’s three-line brief", brief, waterfall),
            ("Where is the gap to the FY26 plan?", f"Coverage is {k['coverage']:.1f}× vs a {_m(k['budgetAcv'])} cell budget. Won ACV is {_m(k['wonAcv'])}.", waterfall),
            ("Which industries hold closed-won ACV?", "Industry mix below is ACV for this slice — the treemap is the ranking, not a forecast.", treemap),
            ("Show the stage funnel", f"Open {_m(k['pipelineAcv'])} / won {_m(k['wonAcv'])}.", funnel),
        ]
    elif principal.key == "manager":
        rows = [
            ("Which owners concentrate stalled deals?", "Open book by owner is the ranking. Pair it with stalled_pipeline rows in the client report.", owners),
            ("Who is walking forecast backwards?", "Use forecast_regression and rep_forecast_reliability from Client_Anomaly_Report.csv — do not invent extra names.", owners),
            ("Compare open book by owner", "Bar chart is open ACV by owner in this slice.", owners),
            ("Where should I coach this week?", "Rep Behavior flags first, then Value Shrink / Sandbagging pairs. Cross-sell is upside, not a reprimand.", owners),
        ]
    else:
        rows = [
            ("Which deals are most likely to slip?", f"{high_n} open deals are in the high-risk band. {past}", bubble),
            ("What is still open past close date?", past, funnel),
            ("Show my funnel by stage", f"Your open book is {_m(k['pipelineAcv'])} across {k['openOpportunities']} opportunities.", funnel),
            ("What should I do this week?", brief, bubble),
        ]
    out = []
    for text, answer, chart in rows:
        out.append(
            {
                "text": text,
                "answer": answer,
                "tldr": _tldr(answer),
                "chart": chart,
                "provider": "precomputed",
                "suggestions": [],
            }
        )
    return out


def build_ask_pack(k: dict, charts: dict, anomalies, scored, tldr_lines: list[str], principal: Principal) -> dict[str, Any]:
    return {
        "charts": _chart_pack(k, charts, anomalies, scored, principal),
        "prompts": _prompt_pack(k, charts, anomalies, scored, tldr_lines, principal),
        "persona": principal.key,
    }


def lookup_ask(pack: dict[str, Any], question: str, chart_title: str | None = None) -> dict[str, Any] | None:
    q = _norm(question)
    if chart_title:
        block = pack.get("charts", {}).get(chart_title) or pack.get("charts", {}).get(chart_title.lower())
        if block:
            for label, item in block.items():
                if _norm(label) in q or _norm(label.split(" ")[0]) in q:
                    return {**item, "suggestions": [p["text"] for p in pack.get("prompts", [])]}
            if "takeaway" in q or "main" in q:
                return {**block["Main takeaway"], "suggestions": [p["text"] for p in pack.get("prompts", [])]}
            if "off" in q or "wrong" in q or "risk" in q:
                return {**block["What looks off"], "suggestions": [p["text"] for p in pack.get("prompts", [])]}
            if "next" in q or "do" in q:
                return {**block["What should I do next"], "suggestions": [p["text"] for p in pack.get("prompts", [])]}
    for p in pack.get("prompts", []):
        if _norm(p["text"]) == q or _norm(p["text"]) in q or q in _norm(p["text"]):
            return {**p, "suggestions": [x["text"] for x in pack.get("prompts", [])]}
    for title, block in pack.get("charts", {}).items():
        if title.lower() in q:
            for label, item in block.items():
                if _norm(label.split(" ")[0]) in q or _norm(label) in q:
                    return {**item, "suggestions": [x["text"] for x in pack.get("prompts", [])]}
    return None


def _filter_key(filters: dict | None) -> str:
    f = filters or {}
    slim = {k: v for k, v in sorted(f.items()) if v}
    return json.dumps(slim, sort_keys=True, default=str)


@lru_cache(maxsize=48)
def cached_ask_pack(persona: str, owner: str, filter_key: str) -> dict[str, Any]:
    from app.semantic.loader import load_store
    from app.semantic.rls import resolve
    from app.semantic.views import default_sales_owner

    store = load_store()
    own = owner if owner != "-" else None
    if persona == "sales" and not own:
        own = default_sales_owner(store)
    principal = resolve(persona, own)
    filters = json.loads(filter_key) if filter_key else {}
    return compute_ask_pack(store, principal, filters)


def compute_ask_pack(store: Store, principal: Principal, filters: dict | None) -> dict[str, Any]:
    lines = slice_lines(store, principal, filters)
    opps = slice_opps(store, principal, filters)
    anomalies = detect_anomalies(store, opps, principal)
    scored = score_risk(opps, anomalies)
    k = M.kpis(lines, opps)
    high_n = int((scored["risk_band"] == "high_risk").sum()) if not scored.empty else 0
    from app.semantic.views import tldr

    charts = {
        "funnel": M.stage_funnel(opps),
        "waterfall": M.budget_waterfall(lines),
        "combo": M.monthly_combo(lines),
        "heatmap": M.heat_lob_portfolio(lines),
        "bubble": M.bubble_opps(opps),
        "mekko": M.mekko_lob_order(lines),
        "treemap": M.treemap_industry(opps),
        "sankey": M.sankey_order_stage(opps),
        "byLob": M.group_measure(lines, "lob"),
        "byPortfolio": M.group_measure(lines, "portfolio"),
        "byOwner": M.group_measure(opps, "owner")[:20],
        "byIndustry": M.group_measure(opps, "industry"),
        "byOrderType": M.group_measure(opps, "order_type"),
    }
    return build_ask_pack(k, charts, anomalies, scored, tldr(k, int(len(anomalies)), high_n, principal.key), principal)


def warm_ask_packs() -> None:
    cached_ask_pack.cache_clear()
    for persona in ("sales", "executive", "manager"):
        cached_ask_pack(persona, "-", "{}")
