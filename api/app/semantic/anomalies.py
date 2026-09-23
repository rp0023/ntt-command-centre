from __future__ import annotations

from typing import Any

import pandas as pd

from app.semantic.anomaly_catalog import TYPES, catalog_payload
from app.semantic.loader import Store
from app.semantic.rls import Principal

REQUIRED_COLS = [
    "AnomalyId",
    "EntityType",
    "DealId",
    "Deal",
    "RepName",
    "DealValue",
    "AnomalyCategory",
    "AnomalyType",
    "Evidence",
    "RecommendedAction",
    "Severity",
    "DemoPriority",
]


def load_client_report(path, opps: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Load Client_Anomaly_Report.csv and join to Excel. No extra flags are generated."""
    raw = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLS if c not in raw.columns]
    if missing:
        raise ValueError(f"Client_Anomaly_Report.csv is missing columns: {missing}")

    df = pd.DataFrame(
        {
            "id": raw["AnomalyId"].astype(str),
            "entity_type": raw["EntityType"].astype(str),
            "entity_id": raw["DealId"].astype(str),
            "label": raw["Deal"].astype(str),
            "owner": raw["RepName"].where(raw["RepName"].notna(), "").astype(str),
            "value": pd.to_numeric(raw["DealValue"], errors="coerce"),
            "category": raw["AnomalyCategory"].astype(str),
            "type": raw["AnomalyType"].astype(str),
            "evidence": raw["Evidence"].astype(str),
            "action": raw["RecommendedAction"].astype(str),
            "severity_score": pd.to_numeric(raw["Severity"], errors="coerce"),
            "demo_priority": raw["DemoPriority"].astype(str).str.lower().isin(["true", "1", "yes"]),
        }
    )
    meta = df["type"].map(lambda t: TYPES.get(str(t), {}))
    df["type_label"] = [m.get("label", t) for m, t in zip(meta, df["type"])]
    df["meaning"] = [m.get("meaning", "") for m in meta]
    df["title"] = df["type_label"]
    df["reason"] = df["evidence"]
    df["severity"] = df["severity_score"]

    opp_idx = opps.set_index("opportunity_code")
    acct_codes = set(opps["account_code"].astype(str))
    owners = set(opps["owner"].astype(str))
    industries = set(opps["industry"].astype(str))
    segments = set()
    if {"quarter", "lob", "portfolio"}.issubset(lines.columns):
        for q, lob, port in zip(lines["quarter"].astype(str), lines["lob"].astype(str), lines["portfolio"].astype(str)):
            segments.add(f"{q} / {lob} / {port}")

    excel_name: list[str] = []
    excel_owner: list[str] = []
    excel_gp: list[float | None] = []
    excel_revenue: list[float | None] = []
    stage: list[str] = []
    in_excel: list[bool] = []
    opportunity_code: list[str] = []
    account_name: list[str] = []

    for _, r in df.iterrows():
        et, eid = r["entity_type"], r["entity_id"]
        if et == "Opportunity" and eid in opp_idx.index:
            row = opp_idx.loc[eid]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            excel_name.append(str(row["opportunity_name"]))
            excel_owner.append(str(row["owner"]))
            excel_gp.append(float(row["acv_gp"]))
            excel_revenue.append(float(row["acv_revenue"]))
            stage.append(str(row["stage"]))
            in_excel.append(True)
            opportunity_code.append(eid)
            account_name.append(str(row["account_name"]))
        elif et == "Account":
            excel_name.append(r["label"])
            excel_owner.append("")
            excel_gp.append(None)
            excel_revenue.append(None)
            stage.append("")
            in_excel.append(eid in acct_codes)
            opportunity_code.append("")
            account_name.append(r["label"])
        elif et == "Rep":
            excel_name.append(r["label"])
            excel_owner.append(eid)
            excel_gp.append(None)
            excel_revenue.append(None)
            stage.append("")
            in_excel.append(eid in owners)
            opportunity_code.append("")
            account_name.append("")
        elif et == "Industry":
            excel_name.append(r["label"])
            excel_owner.append("")
            excel_gp.append(None)
            excel_revenue.append(None)
            stage.append("")
            in_excel.append(eid in industries)
            opportunity_code.append("")
            account_name.append("")
        elif et == "Segment":
            excel_name.append(r["label"])
            excel_owner.append("")
            excel_gp.append(None)
            excel_revenue.append(None)
            stage.append("")
            in_excel.append(eid in segments or r["label"] in segments)
            opportunity_code.append("")
            account_name.append("")
        else:
            excel_name.append(r["label"])
            excel_owner.append(r["owner"])
            excel_gp.append(None)
            excel_revenue.append(None)
            stage.append("")
            in_excel.append(False)
            opportunity_code.append("")
            account_name.append("")

    df["excel_name"] = excel_name
    df["excel_owner"] = excel_owner
    df["excel_gp"] = excel_gp
    df["excel_revenue"] = excel_revenue
    df["stage"] = stage
    df["in_excel"] = in_excel
    df["opportunity_code"] = opportunity_code
    df["account_name"] = account_name
    df["severity_rank"] = df["severity_score"].fillna(0)
    df = df.sort_values(["demo_priority", "severity_rank"], ascending=[False, False]).drop(columns=["severity_rank"])
    return df.reset_index(drop=True)


def detect_anomalies(store: Store, opps: pd.DataFrame | None = None, principal: Principal | None = None) -> pd.DataFrame:
    """Scope the client report to the current book. Does not invent additional anomalies."""
    flags = store.anomalies
    if flags is None or flags.empty:
        return pd.DataFrame()
    if opps is None:
        opps = store.opportunities
    codes = set(opps["opportunity_code"].astype(str))
    accounts = set(opps["account_code"].astype(str)) if "account_code" in opps.columns else set()
    owners = set(opps["owner"].astype(str))
    industries = set(opps["industry"].astype(str)) if "industry" in opps.columns else set()
    mask = (
        ((flags["entity_type"] == "Opportunity") & flags["entity_id"].isin(codes))
        | ((flags["entity_type"] == "Account") & flags["entity_id"].isin(accounts))
        | ((flags["entity_type"] == "Rep") & flags["entity_id"].isin(owners))
        | ((flags["entity_type"] == "Industry") & flags["entity_id"].isin(industries))
    )
    if principal is None or not principal.owner:
        mask = mask | (flags["entity_type"] == "Segment")
    out = flags[mask].copy()
    return out.reset_index(drop=True)


def catalog_with_counts(flags: pd.DataFrame) -> list[dict[str, Any]]:
    counts = flags.groupby("type").size().to_dict() if not flags.empty else {}
    return catalog_payload({str(k): int(v) for k, v in counts.items()})


def score_risk(opps: pd.DataFrame, anomalies: pd.DataFrame) -> pd.DataFrame:
    """Risk band uses client opportunity flags plus fact-table past-due. No extra anomaly types."""
    if opps.empty:
        return opps.assign(close_probability=pd.Series(dtype=float), risk_band=pd.Series(dtype=str), risk_drivers=pd.Series(dtype=str))
    opp_flags = anomalies
    if not anomalies.empty and "entity_type" in anomalies.columns:
        opp_flags = anomalies[anomalies["entity_type"] == "Opportunity"]
    types = (
        opp_flags.groupby("opportunity_code")["type"].apply(lambda s: ", ".join(sorted(set(s.astype(str)))))
        if not opp_flags.empty and "opportunity_code" in opp_flags.columns
        else pd.Series(dtype=str)
    )
    max_sev = (
        opp_flags.groupby("opportunity_code")["severity_score"].max()
        if not opp_flags.empty and "severity_score" in opp_flags.columns
        else pd.Series(dtype=float)
    )
    out = opps.copy()
    scores = []
    bands = []
    drivers = []
    for _, r in out.iterrows():
        if r["is_won"]:
            scores.append(92)
            bands.append("likely")
            drivers.append("Already closed won")
            continue
        if r["is_lost"]:
            scores.append(4)
            bands.append("closed_lost")
            drivers.append("Already lost")
            continue
        s = 70
        d: list[str] = []
        if r["past_due"]:
            s -= 20
            d.append("Past close date on the fact table")
        code = str(r["opportunity_code"])
        sev = float(max_sev.get(code, 0) or 0)
        if sev:
            s -= min(40, int(sev * 0.4))
            d.append(str(types.get(code, "Flagged in client report")))
        s = max(5, min(88, s))
        scores.append(s)
        if s >= 70:
            bands.append("likely")
        elif s >= 45:
            bands.append("watch")
        else:
            bands.append("high_risk")
        drivers.append("; ".join(d) if d else "No client-report flag on this opportunity")
    out["close_probability"] = scores
    out["risk_band"] = bands
    out["risk_drivers"] = drivers
    return out
