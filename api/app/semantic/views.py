from __future__ import annotations

from typing import Any

import pandas as pd

from app.config import AS_OF
from app.semantic import measures as M
from app.semantic.anomalies import catalog_with_counts, detect_anomalies, score_risk
from app.semantic.precompute import build_ask_pack
from app.semantic.filters import filter_options, slice_lines, slice_opps
from app.semantic.loader import Store
from app.semantic.rls import Principal, PERSONAS


def default_sales_owner(store: Store) -> str:
    open_ = store.opportunities[store.opportunities["is_open"]]
    if open_.empty:
        return str(store.opportunities["owner"].mode().iloc[0])
    return str(open_.groupby("owner")["acv_revenue"].sum().sort_values(ascending=False).index[0])


def _json_records(df, limit: int = 40) -> list[dict]:
    if df is None or df.empty:
        return []
    out = df.head(limit).copy()
    for c in out.columns:
        if str(out[c].dtype).startswith("datetime"):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif str(out[c].dtype) == "bool":
            out[c] = out[c].astype(bool)
    out = out.replace([float("inf"), float("-inf")], pd.NA)
    records = out.where(out.notna(), None).to_dict(orient="records")
    clean = []
    for rec in records:
        row = {}
        for k, v in rec.items():
            if v is None:
                row[k] = None
            elif isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
                row[k] = None
            elif hasattr(v, "item"):
                row[k] = v.item()
            else:
                row[k] = v
        clean.append(row)
    return clean


def meta(store: Store, principal: Principal) -> dict[str, Any]:
    lines = slice_lines(store, principal, None)
    return {
        "asOf": AS_OF.isoformat(),
        "fy": "FY26",
        "fyWindow": "Apr 2026 – Mar 2027",
        "personas": [
            {"id": p.key, "name": p.name, "role": p.role, "lens": p.lens, "scopeLabel": p.scope_label}
            for p in PERSONAS.values()
        ],
        "principal": {
            "id": principal.key,
            "name": principal.name,
            "role": principal.role,
            "lens": principal.lens,
            "scopeLabel": principal.scope_label,
            "owner": principal.owner,
        },
        "dataset": {
            "lines": int(len(store.lines)),
            "opportunities": int(store.opportunities["opportunity_code"].nunique()),
            "movementRows": int(len(store.movement)),
            "path": "opportunities.xlsx + opportunity_movement.csv + client_anomaly_report.csv",
        },
        "filters": filter_options(lines if not lines.empty else store.lines),
        "notes": [
            "Grain is opportunity line. Stage and forecast count distinct opportunities; LOB and portfolio count lines.",
            "GM% is ACV GP divided by ACV, never an average of row GM%.",
            "Only SDIS carries a contract term; other portfolios are one-time (TCV = ACV).",
            "Budget is a Country → LOB → Portfolio hierarchy, illustrative and scaled to this NA extract.",
            "Anomaly rows are the Client_Anomaly_Report.csv export, joined to Opportunities.xlsx. No extra flags are generated.",
        ],
    }


def tldr(k: dict, anomalies_n: int, high_n: int, persona: str) -> list[str]:
    cover = k["coverage"]
    cover_line = (
        f"Coverage is {cover:.1f}× against the cell budget — thin versus a 3× rule of thumb."
        if cover < 3
        else f"Coverage is {cover:.1f}× against the cell budget."
    )
    past = (
        f"{k['pastDueOpportunities']} open opportunities (${k['pastDueAcv']/1e6:.1f}M) are already past close date."
    )
    gm = f"Services GM is {k['servicesGmPct']}% versus the 30% planning target."
    if persona == "executive":
        return [
            f"North America has ${k['wonAcv']/1e6:.1f}M closed/won ACV and ${k['pipelineAcv']/1e6:.1f}M still open.",
            cover_line,
            past + " That is the first conversation with entity stakeholders.",
            f"{high_n} open deals sit in the high-risk band; {anomalies_n} rows from the client anomaly report are in scope.",
        ]
    if persona == "manager":
        return [
            f"{anomalies_n} client-report flags are in scope — use Rep Behavior rows for coaching, not for naming and shaming.",
            past,
            gm,
            "Look for owners who both shrink value and walk forecast backwards; that pattern is trainable.",
        ]
    return [
        f"Your open book is ${k['pipelineAcv']/1e6:.1f}M across {k['openOpportunities']} opportunities.",
        past,
        f"{high_n} of those deals are scored high-risk. Work those first this week.",
        gm,
    ]


def actions(scored, anomalies) -> list[dict]:
    items = []
    high = scored[scored["risk_band"] == "high_risk"].sort_values("acv_revenue", ascending=False).head(5)
    for _, r in high.iterrows():
        items.append(
            {
                "id": f"risk-{r['opportunity_code']}",
                "urgency": "now",
                "title": f"Unblock {r['account_name']}",
                "why": r["risk_drivers"],
                "owner": r["owner"],
                "value": float(r["acv_revenue"]),
                "opportunityCode": r["opportunity_code"],
                "cta": "Open the deal and reset the next step",
            }
        )
    if not anomalies.empty:
        top = anomalies.iloc[0]
        val = top["value"]
        items.append(
            {
                "id": top["id"],
                "urgency": "this_week",
                "title": str(top.get("title") or top.get("type_label") or top.get("type")),
                "why": str(top.get("evidence") or top.get("reason") or ""),
                "owner": str(top.get("owner") or ""),
                "value": float(val) if pd.notna(val) else 0.0,
                "opportunityCode": str(top.get("opportunity_code") or ""),
                "cta": str(top.get("action") or ""),
            }
        )
    return items[:6]


def view(store: Store, principal: Principal, filters: dict | None, lens: str) -> dict[str, Any]:
    lines = slice_lines(store, principal, filters)
    opps = slice_opps(store, principal, filters)
    anomalies = detect_anomalies(store, opps, principal)
    scored = score_risk(opps, anomalies)
    k = M.kpis(lines, opps)
    high_n = int((scored["risk_band"] == "high_risk").sum()) if not scored.empty else 0

    payload: dict[str, Any] = {
        "lens": lens,
        "principal": {
            "id": principal.key,
            "name": principal.name,
            "scopeLabel": principal.scope_label,
            "owner": principal.owner,
        },
        "kpis": k,
        "tldr": tldr(k, int(len(anomalies)), high_n, principal.key),
        "actions": actions(scored, anomalies),
        "charts": {
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
            "byAnomalyCategory": (
                anomalies.groupby("category")
                .agg(value=("id", "count"))
                .reset_index()
                .rename(columns={"category": "name"})
                .to_dict("records")
                if not anomalies.empty
                else []
            ),
            "byAnomalyType": (
                anomalies.groupby("type")
                .agg(value=("id", "count"))
                .reset_index()
                .rename(columns={"type": "name"})
                .to_dict("records")
                if not anomalies.empty
                else []
            ),
        },
        "anomalyCatalog": catalog_with_counts(anomalies),
        "anomalySource": {
            "file": "Client_Anomaly_Report.csv",
            "rowsInFile": int(len(store.anomalies)),
            "rowsInScope": int(len(anomalies)),
            "matchedToExcel": int(store.anomalies["in_excel"].sum()) if not store.anomalies.empty else 0,
            "unmatchedToExcel": int((~store.anomalies["in_excel"]).sum()) if not store.anomalies.empty else 0,
        },
        "anomalySummary": _json_records(
            anomalies.groupby(["category", "type"]).agg(n=("id", "count"), gp=("value", "sum")).reset_index(),
            80,
        ) if not anomalies.empty else [],
    }
    payload["askPack"] = build_ask_pack(k, payload["charts"], anomalies, scored, payload["tldr"], principal)
    if lens in {"command", "book", "anomalies", "patterns"}:
        show = scored if lens != "anomalies" else scored
        if lens == "book":
            show = scored[scored["is_open"]] if "is_open" in scored else scored
        cols = [
            "opportunity_code",
            "opportunity_name",
            "account_name",
            "owner",
            "stage",
            "forecast_category",
            "confidence",
            "acv_revenue",
            "close_date",
            "past_due",
            "risk_band",
            "close_probability",
            "risk_drivers",
            "industry",
            "order_type",
            "lobs",
            "portfolios",
        ]
        anom = anomalies
        payload["opportunities"] = _json_records(show[cols] if not show.empty else show, 80)
        payload["anomalies"] = _json_records(anom, 500 if lens in {"anomalies", "patterns"} else 40)
    if lens == "opportunity":
        pass
    return payload


def opportunity_detail(store: Store, principal: Principal, code: str) -> dict[str, Any]:
    opps = slice_opps(store, principal, None)
    row = opps[opps["opportunity_code"] == code]
    if row.empty:
        raise KeyError(code)
    lines = slice_lines(store, principal, None)
    lines = lines[lines["opportunity_code"] == code]
    mov = store.movement[store.movement["opportunity_code"] == code].sort_values("change_date")
    anomalies = detect_anomalies(store, opps, principal)
    scored = score_risk(row, anomalies[anomalies["opportunity_code"] == code] if not anomalies.empty else anomalies)
    gantt = []
    stage_m = mov[mov["field"] == "Stage"]
    prev = None
    for _, r in stage_m.iterrows():
        if prev is not None:
            gantt.append(
                {
                    "label": str(prev["new_value"]),
                    "start": str(prev["change_date"].date()) if hasattr(prev["change_date"], "date") else str(prev["change_date"])[:10],
                    "end": str(r["change_date"].date()) if hasattr(r["change_date"], "date") else str(r["change_date"])[:10],
                }
            )
        prev = r
    return {
        "opportunity": _json_records(scored, 1)[0] if not scored.empty else {},
        "lines": _json_records(lines, 40),
        "movement": _json_records(mov, 80),
        "anomalies": _json_records(
            anomalies[anomalies["entity_id"] == code] if not anomalies.empty else anomalies,
            40,
        ),
        "gantt": gantt,
    }


def alerts(store: Store, principal: Principal) -> list[dict]:
    opps = slice_opps(store, principal, None)
    anomalies = detect_anomalies(store, opps, principal)
    if anomalies.empty:
        return []
    out = []
    for _, r in anomalies.head(12).iterrows():
        val = r["value"]
        out.append(
            {
                "id": r["id"],
                "severity": r["severity"],
                "title": r["title"],
                "subtitle": f"{r.get('label') or r.get('account_name')} · {r.get('owner') or r.get('entity_type')}",
                "opportunityCode": r.get("opportunity_code") or "",
                "value": float(val) if pd.notna(val) else 0.0,
            }
        )
    return out
