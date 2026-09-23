from __future__ import annotations

from typing import Any

import pandas as pd

from app.config import AS_OF, COVERAGE_TARGET, SERVICES_GM_TARGET
from app.semantic.loader import STAGE_ORDER


def _money(v: float) -> float:
    return float(round(v, 2))


def kpis(lines: pd.DataFrame, opps: pd.DataFrame) -> dict[str, Any]:
    open_lines = lines[lines["is_open"]]
    won_lines = lines[lines["is_won"]]
    open_opps = opps[opps["is_open"]]
    won_opps = opps[opps["is_won"]]
    past = opps[opps["past_due"]]
    services = lines[lines["is_services"]]

    pipeline = float(open_lines["acv_revenue"].sum())
    won_rev = float(won_lines["acv_revenue"].sum())
    gp = float(lines["acv_gp"].sum())
    rev = float(lines["acv_revenue"].sum())
    gm = (gp / rev) if rev else 0.0
    svc_rev = float(services["acv_revenue"].sum())
    svc_gp = float(services["acv_gp"].sum())
    svc_gm = (svc_gp / svc_rev) if svc_rev else 0.0

    # Budget is denormalized at line grain — take unique (quarter, lob, portfolio) cells.
    budget_cells = (
        lines.drop_duplicates(["quarter", "lob", "portfolio"])[["cell_budget_rev", "cell_budget_gp"]]
        if not lines.empty
        else pd.DataFrame(columns=["cell_budget_rev", "cell_budget_gp"])
    )
    budget_rev = float(budget_cells["cell_budget_rev"].fillna(0).sum()) if not budget_cells.empty else 0.0
    if budget_rev <= 0 and not lines.empty:
        budget_rev = float(lines.drop_duplicates(["quarter"])["q_budget_rev"].fillna(0).sum())
    coverage = (pipeline / budget_rev) if budget_rev else 0.0

    closed_commit = lines[lines["forecast_category"].isin(["Closed", "Commit"])]
    # Distinct opportunity ACV for commit+closed would double-count lines; use lines for $ mix.

    return {
        "asOf": AS_OF.isoformat(),
        "fy": "FY26",
        "lines": int(len(lines)),
        "opportunities": int(opps["opportunity_code"].nunique()) if not opps.empty else 0,
        "accounts": int(opps["account_code"].nunique()) if not opps.empty else 0,
        "openOpportunities": int(len(open_opps)),
        "wonOpportunities": int(len(won_opps)),
        "lostOpportunities": int(int(opps["is_lost"].sum()) if not opps.empty else 0),
        "openLines": int(len(open_lines)),
        "pipelineAcv": _money(pipeline),
        "wonAcv": _money(won_rev),
        "totalAcv": _money(rev),
        "totalGp": _money(gp),
        "gmPct": round(gm * 100, 2),
        "servicesGmPct": round(svc_gm * 100, 2),
        "servicesGmTarget": round(SERVICES_GM_TARGET * 100, 1),
        "budgetAcv": _money(budget_rev),
        "coverage": round(coverage, 2),
        "coverageTarget": COVERAGE_TARGET,
        "pastDueOpportunities": int(len(past)),
        "pastDueAcv": _money(float(past["acv_revenue"].sum()) if not past.empty else 0),
        "qualifiedAcv": _money(float(lines[lines["is_qualified"]]["acv_revenue"].sum())),
        "commitAcv": _money(float(lines[lines["forecast_category"].eq("Commit")]["acv_revenue"].sum())),
        "bestCaseAcv": _money(float(lines[lines["forecast_category"].eq("Best Case")]["acv_revenue"].sum())),
        "avgOpenConfidence": round(float(open_opps["confidence"].mean() * 100), 1) if not open_opps.empty else 0,
    }


def group_measure(df: pd.DataFrame, col: str, grain: str = "lines") -> list[dict]:
    if df.empty:
        return []
    g = df.groupby(col, dropna=False)
    rows = []
    for key, part in g:
        rows.append(
            {
                "label": str(key) if key is not None else "(blank)",
                "acv": _money(float(part["acv_revenue"].sum())),
                "gp": _money(float(part["acv_gp"].sum())),
                "count": int(part["opportunity_code"].nunique() if grain == "opps" or col in ("stage", "forecast_category", "owner") else len(part)),
                "openAcv": _money(float(part.loc[part["is_open"], "acv_revenue"].sum())),
                "wonAcv": _money(float(part.loc[part["is_won"], "acv_revenue"].sum())),
            }
        )
    rows.sort(key=lambda r: r["acv"], reverse=True)
    return rows


def stage_funnel(opps: pd.DataFrame) -> list[dict]:
    rows = []
    for stage in STAGE_ORDER:
        part = opps[opps["stage"] == stage]
        rows.append(
            {
                "label": stage,
                "count": int(len(part)),
                "acv": _money(float(part["acv_revenue"].sum()) if not part.empty else 0),
            }
        )
    return rows


def monthly_combo(lines: pd.DataFrame) -> list[dict]:
    if lines.empty:
        return []
    g = lines.groupby("month")
    rows = []
    for month, part in g:
        cells = part.drop_duplicates(["month", "lob", "portfolio"])
        rows.append(
            {
                "label": str(month)[:7],
                "won": _money(float(part.loc[part["is_won"], "acv_revenue"].sum())),
                "pipeline": _money(float(part.loc[part["is_open"], "acv_revenue"].sum())),
                "budget": _money(float(cells["m_cell_budget_rev"].sum())),
            }
        )
    rows.sort(key=lambda r: r["label"])
    return rows


def budget_waterfall(lines: pd.DataFrame) -> list[dict]:
    cells = lines.drop_duplicates(["quarter", "lob", "portfolio"]) if not lines.empty else lines
    budget = float(cells["cell_budget_rev"].sum()) if not cells.empty else 0.0
    won = float(lines.loc[lines["is_won"], "acv_revenue"].sum()) if not lines.empty else 0.0
    commit = float(lines.loc[lines["forecast_category"].eq("Commit") & lines["is_open"], "acv_revenue"].sum()) if not lines.empty else 0.0
    best = float(lines.loc[lines["forecast_category"].eq("Best Case") & lines["is_open"], "acv_revenue"].sum()) if not lines.empty else 0.0
    rest = float(lines.loc[lines["is_open"] & ~lines["forecast_category"].isin(["Commit", "Best Case"]), "acv_revenue"].sum()) if not lines.empty else 0.0
    covered = won + commit + best + rest
    gap = budget - covered
    return [
        {"label": "FY26 plan", "value": _money(budget), "kind": "start"},
        {"label": "Closed won", "value": _money(-won), "kind": "delta"},
        {"label": "Commit", "value": _money(-commit), "kind": "delta"},
        {"label": "Best case", "value": _money(-best), "kind": "delta"},
        {"label": "Other open", "value": _money(-rest), "kind": "delta"},
        {"label": "Uncovered", "value": _money(gap), "kind": "end"},
    ]


def heat_lob_portfolio(lines: pd.DataFrame, field: str = "openAcv") -> dict:
    lobs = sorted(lines["lob"].dropna().unique().tolist()) if not lines.empty else []
    ports = sorted(lines["portfolio"].dropna().unique().tolist()) if not lines.empty else []
    values: list[list[float]] = []
    for lob in lobs:
        row = []
        for port in ports:
            part = lines[(lines["lob"] == lob) & (lines["portfolio"] == port)]
            if field == "coverage":
                cell_b = part.drop_duplicates(["quarter", "lob", "portfolio"])["cell_budget_rev"].sum() if not part.empty else 0
                pipe = part.loc[part["is_open"], "acv_revenue"].sum() if not part.empty else 0
                row.append(round(float(pipe / cell_b), 2) if cell_b else 0)
            else:
                row.append(_money(float(part.loc[part["is_open"], "acv_revenue"].sum()) if not part.empty else 0))
        values.append(row)
    return {"rows": lobs, "cols": ports, "values": values}


def treemap_industry(opps: pd.DataFrame) -> list[dict]:
    if opps.empty:
        return []
    g = opps.groupby("industry")["acv_revenue"].sum().sort_values(ascending=False)
    return [{"name": str(i), "value": _money(float(v))} for i, v in g.head(16).items()]


def sankey_order_stage(opps: pd.DataFrame) -> dict:
    if opps.empty:
        return {"nodes": [], "links": []}
    nodes: list[str] = []

    def nid(label: str) -> int:
        if label not in nodes:
            nodes.append(label)
        return nodes.index(label)

    links = []
    g = opps.groupby(["order_type", "stage"])["acv_revenue"].sum()
    for (order, stage), val in g.items():
        links.append({"source": nid(str(order)), "target": nid(str(stage)), "value": _money(float(val))})
    return {"nodes": [{"name": n} for n in nodes], "links": links}


def mekko_lob_order(lines: pd.DataFrame) -> list[dict]:
    if lines.empty:
        return []
    orders = sorted(lines["order_type"].dropna().unique().tolist())
    rows = []
    for lob, part in lines.groupby("lob"):
        series = {o: _money(float(part.loc[part["order_type"] == o, "acv_revenue"].sum())) for o in orders}
        rows.append({"label": str(lob), "total": _money(sum(series.values())), "series": series})
    rows.sort(key=lambda r: r["total"], reverse=True)
    return rows


def bubble_opps(opps: pd.DataFrame, limit: int = 80) -> list[dict]:
    if opps.empty:
        return []
    open_ = opps[opps["is_open"]].copy()
    if open_.empty:
        open_ = opps.copy()
    open_ = open_.sort_values("acv_revenue", ascending=False).head(limit)
    as_of = pd.Timestamp(AS_OF)
    rows = []
    for _, r in open_.iterrows():
        age = (as_of - pd.Timestamp(r["create_date"])).days if pd.notna(r["create_date"]) else 0
        rows.append(
            {
                "id": r["opportunity_code"],
                "name": r["opportunity_name"],
                "owner": r["owner"],
                "x": int(age),
                "y": round(float(r["confidence"]) * 100, 1) if pd.notna(r["confidence"]) else 0,
                "z": _money(float(r["acv_revenue"])),
                "stage": r["stage"],
                "pastDue": bool(r["past_due"]),
            }
        )
    return rows
