"""Focused, profit-free view model for the Executive experience."""

from __future__ import annotations

from datetime import timedelta
import re

import pandas as pd

from . import anomalies as ANOM
from . import crosssell as XS
from . import ds_model as DS
from . import predict as P
from .loader import AS_OF, CUR_QUARTER, fy_label
from .measures import FilterState, count, money, slice_frame
from .personas import Principal

THEMES = ("opportunities", "anomalies", "closure")
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
FORBIDDEN_FINDING = re.compile(
    r"\b(?:gp|gross profit|margin|budget|coverage|plan gap|profit plan)\b", re.I
)


def _safe_text(value: object, fallback: str = "") -> str:
    if not isinstance(value, str) or FORBIDDEN_FINDING.search(value):
        return fallback
    return value


def _date(days: int) -> str:
    return (AS_OF + timedelta(days=days)).isoformat()


def _options(kind: str) -> list[dict]:
    labels = {
        "opportunities": ("Approve pilot", "Assign owner", "Hold for review"),
        "anomalies": ("Start investigation", "Assign review", "Monitor"),
        "closure": ("Request recovery plan", "Review commitment", "Monitor"),
    }[kind]
    return [
        {"key": "act", "label": labels[0], "status": "Actioned", "needsReason": False},
        {"key": "review", "label": labels[1], "status": "In Review", "needsReason": False},
        {"key": "monitor", "label": labels[2], "status": "Monitoring", "needsReason": True},
        {"key": "dismiss", "label": "Dismiss", "status": "Dismissed", "needsReason": True},
    ]


def _opportunities(fs: FilterState, principal: Principal) -> tuple[dict, list[dict]]:
    summary = XS.summary(fs, principal)
    themes = XS.themes(fs, principal)[:5]
    message = {
        "key": "opportunities",
        "title": "Opportunities",
        "headline": f"{count(summary['themes'])} repeatable plays are ready to run",
        "summary": (f"The leading play, {summary['topTheme']}, reaches "
                    f"{count(summary['topThemeAccounts'])} customers."
                    if summary.get("topTheme") else "No repeatable play is visible in this scope."),
        "signals": [
            {"label": "Repeatable plays", "value": count(summary["themes"])},
            {"label": "Customers reached", "value": count(summary["accounts"])},
            {"label": "High-confidence ideas", "value": count(summary["strong"])},
        ],
        "page": "opportunities",
    }
    plays = [{
        "key": f"play:{t['offering']}", "offering": t["offering"],
        "customerCount": int(t["accounts"]), "ownerCount": int(t["ownerCount"]),
        "confidence": t["strongest"]["confidence"],
        "pilotAccount": t["strongest"]["accountName"],
        "pilotOwner": t["strongest"]["owner"],
        "nextStep": f"Ask {t['strongest']['owner']} to validate {t['strongest']['accountName']} as the pilot.",
        "reason": t["strongest"]["reason"],
    } for t in themes]
    return message, plays


def _anomalies(fs: FilterState, principal: Principal) -> tuple[dict, list[dict]]:
    frame = ANOM.scoped(ANOM.for_persona("executive"), fs, principal)
    if not frame.empty:
        text = frame[["evidence", "meaning", "recommended_action"]].fillna("").agg(" ".join, axis=1)
        frame = frame.loc[~text.str.contains(FORBIDDEN_FINDING)].copy()
        frame = frame.loc[~frame["entity_type"].isin(("Industry", "Segment"))]
        # Mirror the workbook's strong-example rule: source-curated demo
        # priorities first, then severity. Triage remains the final tie-break.
        frame = frame.sort_values(
            ["demo_priority", "severity", "triage"], ascending=[False, False, False]
        )
    critical = int((frame["priority"] == "Critical").sum()) if not frame.empty else 0
    corroborated = int(frame["corroborated"].sum()) if not frame.empty else 0
    entities = int(frame["entity_id"].nunique()) if not frame.empty else 0
    message = {
        "key": "anomalies", "title": "Anomalies",
        "headline": f"{count(len(frame))} findings merit investigation",
        "summary": (f"{count(critical)} are critical and {count(corroborated)} were found by both detectors."
                    if len(frame) else "No operational anomaly is visible in this scope."),
        "signals": [
            {"label": "Critical", "value": count(critical)},
            {"label": "Detector agreement", "value": count(corroborated)},
            {"label": "Entities affected", "value": count(entities)},
        ],
        "page": "anomalies",
    }
    findings = []
    for row in frame.head(20).itertuples(index=False):
        agreement = "Both detectors" if bool(row.corroborated) else (
            "Data-science detector" if row.provenance == "ds-model" else "Live rules")
        findings.append({
            "key": str(row.anomaly_id), "severity": str(row.priority),
            "entityType": str(row.entity_type), "entity": str(row.entity_label),
            "category": ("Pipeline health" if str(row.category) == "Pipeline Coverage"
                         else str(row.category)), "agreement": agreement,
            "evidence": _safe_text(row.evidence, "The observed pattern is outside its peer range."),
            "owner": _safe_text(row.owner, "Executive sponsor") or "Executive sponsor",
            "question": _safe_text(row.category_question, "What changed, and does it require intervention?"),
            "nextStep": _safe_text(row.recommended_action, "Assign an owner to validate the finding."),
        })
    return message, findings


def _closure(fs: FilterState, principal: Principal) -> tuple[dict, list[dict], dict]:
    risk = P.risk_table()
    codes = set(slice_frame(fs, principal)["opportunity_code"])
    risk = risk[risk["opportunity_code"].isin(codes)].copy()
    risk = risk.sort_values(["risk_score", "close_date"], ascending=[False, True])
    hot = risk[risk["risk_band"].isin(("High", "Critical"))]
    ds = DS.predictions().set_index("opportunity_code") if DS.available() else pd.DataFrame()
    message = {
        "key": "closure", "title": "Closure Risk",
        "headline": f"{count(len(hot))} commitments need a closure review",
        "summary": ("Observable deal movement identifies the exceptions below; model probability is directional."
                    if len(risk) else "No open commitment is visible in this scope."),
        "signals": [
            {"label": "Open deals scored", "value": count(len(risk))},
            {"label": "High or critical", "value": count(len(hot))},
            {"label": "Past due", "value": count(int(risk["is_past_due"].sum()))},
        ],
        "page": "closure-risk",
    }
    rows = []
    for row in risk.head(10).itertuples(index=False):
        pwin = None
        ds_driver = None
        if not ds.empty and row.opportunity_code in ds.index:
            pred = ds.loc[row.opportunity_code]
            if isinstance(pred, pd.DataFrame):
                pred = pred.iloc[0]
            raw = pred.get("p_win")
            pwin = float(raw) if raw is not None and not pd.isna(raw) else None
            driver = pred.get("driving_force")
            ds_driver = _safe_text(driver) if isinstance(driver, str) else None
        factors = [f for f in row.risk_factors if f.get("key") != "thin_margin"]
        driver = ds_driver or (factors[0]["detail"] if factors else "No single observable driver dominates.")
        rows.append({
            "key": str(row.opportunity_code), "deal": str(row.opportunity_name),
            "account": str(row.account_name), "owner": str(row.owner), "stage": str(row.stage),
            "riskBand": str(row.risk_band), "riskScore": int(row.risk_score),
            "closureProbability": pwin, "mainDriver": driver,
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
            "silenceDays": int(row.quiet_days) if not pd.isna(row.quiet_days) else None,
            "revenue": float(row.acv_revenue), "formattedRevenue": money(float(row.acv_revenue)),
        })
    model = DS.model_card() if DS.available() else DS.unavailable_card()
    disclosure = {
        "available": bool(model.get("available")), "testAuc": model.get("testAuc"),
        "text": ("Closure probability is directional. The model test AUC is "
                 f"{model.get('testAuc'):.3f} against 0.50 for chance; prioritize observable deal movement."
                 if isinstance(model.get("testAuc"), (int, float)) else
                 "Closure probability is unavailable; prioritize observable deal movement."),
    }
    return message, rows, disclosure


def _actions(plays: list[dict], findings: list[dict], closures: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for i, play in enumerate(plays[:4]):
        actions.append({
            "key": f"opportunity:{play['key']}", "theme": "opportunities",
            "priority": "High" if i == 0 else "Medium", "owner": play["pilotOwner"],
            "dueDate": _date(7 + i * 2), "headline": f"Pilot {play['offering']}",
            "nextStep": play["nextStep"], "options": _options("opportunities"),
        })
    seen: set[str] = set()
    for finding in findings:
        if finding["entity"] in seen or len([a for a in actions if a["theme"] == "anomalies"]) >= 4:
            continue
        seen.add(finding["entity"])
        actions.append({
            "key": f"anomaly:{finding['key']}", "theme": "anomalies",
            "priority": finding["severity"], "owner": finding["owner"],
            "dueDate": _date(2 if finding["severity"] == "Critical" else 5),
            "headline": f"Investigate {finding['entity']}", "nextStep": finding["nextStep"],
            "options": _options("anomalies"),
        })
    for i, deal in enumerate(closures[:4]):
        actions.append({
            "key": f"closure:{deal['key']}", "theme": "closure",
            "priority": "Critical" if deal["riskBand"] == "Critical" else "High",
            "owner": deal["owner"], "dueDate": _date(1 + i),
            "headline": f"Review {deal['deal']}",
            "nextStep": f"Ask {deal['owner']} for evidence supporting the current close date.",
            "revenueImpact": deal["revenue"], "formattedRevenueImpact": deal["formattedRevenue"],
            "options": _options("closure"),
        })
    return sorted(actions, key=lambda a: (PRIORITY_ORDER.get(a["priority"], 9), a["dueDate"]))


def _weekly_focus(fs: FilterState, principal: Principal, findings: list[dict],
                  closures: list[dict]) -> tuple[dict, list[dict]]:
    """The five decisions worth leadership time this week.

    Selection follows the accompanying Top10 workbook: absolute probability
    for closure (never the misleading relative bucket), multi-method confidence
    for expansion, and source demo-priority plus severity for anomalies.
    """
    risk = P.risk_table()
    codes = set(slice_frame(fs, principal)["opportunity_code"])
    risk = risk[risk["opportunity_code"].isin(codes)].copy()
    hot = risk[risk["risk_band"].isin(("High", "Critical"))]
    past_due = risk[risk["is_past_due"]]
    stalled = risk[risk["is_stalled"]]

    scored = pd.DataFrame()
    if DS.available():
        scored = DS.predictions()
        scored = scored[scored["opportunity_code"].isin(codes)].copy()
        if "is_open_in_model" in scored.columns:
            scored = scored[scored["is_open_in_model"]]
        scored = scored.drop_duplicates("opportunity_code")
        scored["p_win"] = pd.to_numeric(scored["p_win"], errors="coerce")
        scored = scored.dropna(subset=["p_win"]).sort_values("p_win", ascending=False)

    ceiling = float(scored.iloc[0]["p_win"]) if len(scored) else None
    clears_half = int((scored["p_win"] >= .5).sum()) if len(scored) else 0
    hot_revenue = float(hot["acv_revenue"].sum()) if len(hot) else 0.0
    banner = {
        "tone": "danger" if len(hot) else "accent",
        "headline": (f"{money(hot_revenue)} ACV Revenue across {count(len(hot))} "
                     "high-risk commitments needs review this week"
                     if len(hot) else "No high-risk commitment is visible this week"),
        "subline": (f"Only {count(clears_half)} of {count(len(scored))} model-scored open deals "
                    f"clear 50% closure probability; {count(len(past_due))} are already past due."
                    if len(scored) else
                    f"{count(len(past_due))} open deals are past due and {count(len(stalled))} are stalled."),
        "stats": [
            {"label": "High / critical", "value": count(len(hot)), "tone": "danger"},
            {"label": "Model ceiling", "value": f"{ceiling:.0%}" if ceiling is not None else "—",
             "tone": "warn"},
            {"label": "Past due", "value": count(len(past_due)), "tone": "warn"},
        ],
    }

    insights: list[dict] = []
    if len(scored):
        top = scored.iloc[0]
        code = str(top["opportunity_code"])
        rr = risk[risk["opportunity_code"] == code]
        revenue = float(rr.iloc[0]["acv_revenue"]) if len(rr) else float(top.get("revenue_at_cutoff") or 0)
        deal = str(top.get("opportunity_name") or (rr.iloc[0]["opportunity_name"] if len(rr) else code))
        stage = str(top.get("stage_at_cutoff") or (rr.iloc[0]["stage"] if len(rr) else "Unknown"))
        insights.append({
            "key": "weekly:conversion-ceiling", "rank": 1, "theme": "closure",
            "title": "Conversion confidence has a low ceiling",
            "conclusion": (f"The strongest open model signal is only {float(top['p_win']):.0%}; "
                           f"just {count(clears_half)} deals clear 50%."),
            "evidence": [f"{deal} is the highest-ranked open commitment.",
                         f"It is at {stage} with {money(revenue)} ACV Revenue."],
            "nextStep": "Treat probability as directional and require stage evidence before strengthening the forecast.",
            "page": "closure-risk", "entity": deal,
        })
    if closures:
        deal = closures[0]
        insights.append({
            "key": "weekly:deal-rescue", "rank": 2, "theme": "closure",
            "title": "The highest-risk commitment needs a rescue decision",
            "conclusion": f"{deal['deal']} scores {deal['riskScore']} ({deal['riskBand']}) for closure risk.",
            "evidence": [deal["mainDriver"],
                         f"{deal['formattedRevenue']} ACV Revenue; {deal['silenceDays'] or 0} days since movement."],
            "nextStep": f"Ask {deal['owner']} for evidence supporting the close date before the next review.",
            "page": "closure-risk", "entity": deal["deal"],
        })
    insights.append({
        "key": "weekly:pipeline-hygiene", "rank": 3, "theme": "closure",
        "title": "Pipeline hygiene is suppressing conversion quality",
        "conclusion": f"{count(len(past_due))} open deals are past due and {count(len(stalled))} have stopped moving.",
        "evidence": [f"{count(len(hot))} commitments now sit in High or Critical risk.",
                     "Silence and expired close dates are observable signals, independent of the weak model."],
        "nextStep": "Require owners to validate, re-date, or close the oldest exceptions this week.",
        "page": "closure-risk", "entity": "Open pipeline",
    })

    recommendations = XS.unified(fs, principal, limit=10_000)
    if recommendations:
        rec = recommendations[0]
        reason = rec["reasons"][0]["text"] if rec.get("reasons") else "Peer evidence supports the fit."
        insights.append({
            "key": "weekly:expansion", "rank": 4, "theme": "opportunities",
            "title": "One expansion signal is ready for customer validation",
            "conclusion": f"{rec['accountName']} is a {rec['confidence']} confidence fit for {rec['offering']}.",
            "evidence": [f"{rec['methodCount']} independent method{'s' if rec['methodCount'] != 1 else ''} support the recommendation.",
                         reason],
            "nextStep": f"Ask {rec['owner']} to test the need with {rec['accountName']} this week.",
            "page": "opportunities", "entity": rec["accountName"],
        })
    if findings:
        finding = findings[0]
        insights.append({
            "key": "weekly:anomaly", "rank": 5, "theme": "anomalies",
            "title": "The strongest client anomaly needs validation",
            "conclusion": f"{finding['entity']} carries a {finding['severity'].lower()}-priority {finding['category'].lower()} finding.",
            "evidence": [finding["evidence"], f"Detector view: {finding['agreement']}."],
            "nextStep": finding["nextStep"], "page": "anomalies", "entity": finding["entity"],
        })
    return banner, insights[:5]


def payload(fs: FilterState, principal: Principal) -> dict:
    opportunity_message, plays = _opportunities(fs, principal)
    anomaly_message, findings = _anomalies(fs, principal)
    closure_message, closures, disclosure = _closure(fs, principal)
    actions = _actions(plays, findings, closures)
    weekly_banner, weekly_insights = _weekly_focus(fs, principal, findings, closures)
    return {
        "messages": [opportunity_message, anomaly_message, closure_message],
        "opportunityPlays": plays, "anomalyFindings": findings,
        "closureExceptions": closures, "closureModel": disclosure,
        "actions": actions, "weeklyBanner": weekly_banner,
        "weeklyInsights": weekly_insights,
    }


def view(page: str, fs: FilterState, principal: Principal, label: str, question: str) -> dict:
    focused = payload(fs, principal)
    if page == "tldr":
        focused["actions"] = [next(a for a in focused["actions"] if a["theme"] == theme)
                              for theme in THEMES
                              if any(a["theme"] == theme for a in focused["actions"])]
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["closureExceptions"] = []
    elif page == "opportunities":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "opportunities"]
        focused["anomalyFindings"] = []
        focused["closureExceptions"] = []
    elif page == "anomalies":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "anomalies"]
        focused["opportunityPlays"] = []
        focused["closureExceptions"] = []
    elif page == "closure-risk":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "closure"]
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
    elif page == "action-center":
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["closureExceptions"] = []
    if page != "tldr":
        focused["weeklyBanner"] = None
        focused["weeklyInsights"] = []
    return {
        "page": page, "label": label, "question": question, "persona": "executive",
        "asOf": AS_OF.isoformat(), "fy": fy_label(2026), "quarter": CUR_QUARTER,
        "scope": {"label": principal.identity_label, "predicate": principal.predicate_sql,
                  "persona": principal.key, "identity": principal.identity},
        "filters": fs.active(), "measure": "revenue", "kpis": [], "metricBanners": [],
        "narrative": {"headline": "", "sentences": [], "provider": "computed"},
        "actions": [], "charts": [], "chartsSay": [], "extras": {}, "measures": {},
        "executive": focused,
    }
