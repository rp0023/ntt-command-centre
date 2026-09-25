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
    hot = risk[risk["risk_band"].isin(("High", "Critical"))]
    ds = pd.DataFrame()
    if DS.available():
        ds = DS.predictions().drop_duplicates("opportunity_code").set_index("opportunity_code")
        risk["closure_probability"] = pd.to_numeric(
            risk["opportunity_code"].map(ds["p_win"]), errors="coerce"
        )
        risk["model_driver"] = risk["opportunity_code"].map(ds["driving_force"])
    else:
        risk["closure_probability"] = float("nan")
        risk["model_driver"] = None

    # Curate the exception list around the decisions introduced on the Brief:
    # low-probability Commit first, then Best Case, followed by a distinct
    # stalled deal and a distinct slipped deal. Fill the remaining places by
    # observable risk so the page stays useful when one category is absent.
    selected_codes: list[str] = []

    def select_one(frame: pd.DataFrame, by: list[str], ascending: list[bool]) -> None:
        for code in frame.sort_values(by, ascending=ascending)["opportunity_code"].astype(str):
            if code not in selected_codes:
                selected_codes.append(code)
                return

    for forecast in ("Commit", "Best Case"):
        candidates = risk[risk["forecast_category"] == forecast]
        low = candidates[candidates["closure_probability"] < .5]
        select_one(low if len(low) else candidates,
                   ["closure_probability", "risk_score"], [True, False])
    select_one(risk[risk["is_stalled"]], ["risk_score", "quiet_days"], [False, False])
    select_one(risk[risk["close_date_slips"] > 0], ["risk_score", "slip_days"], [False, False])
    for code in risk.sort_values(["risk_score", "close_date"], ascending=[False, True])[
        "opportunity_code"
    ].astype(str):
        if code not in selected_codes:
            selected_codes.append(code)
        if len(selected_codes) == 10:
            break
    order = {code: i for i, code in enumerate(selected_codes)}
    risk["brief_order"] = risk["opportunity_code"].astype(str).map(order)
    curated = risk[risk["brief_order"].notna()].sort_values("brief_order")
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
    for row in curated.itertuples(index=False):
        pwin = (float(row.closure_probability)
                if not pd.isna(row.closure_probability) else None)
        ds_driver = _safe_text(row.model_driver) if isinstance(row.model_driver, str) else None
        factors = [f for f in row.risk_factors if f.get("key") != "thin_margin"]
        driver = ds_driver or (factors[0]["detail"] if factors else "No single observable driver dominates.")
        deterioration = []
        if int(row.close_date_slips or 0) > 0:
            deterioration.append(
                f"close date moved {int(row.close_date_slips)}x ({int(row.slip_days or 0)} days later)"
            )
        if bool(row.went_backwards):
            deterioration.append("stage moved backwards")
        if bool(row.shrank):
            deterioration.append(f"deal value fell {abs(float(row.value_drift)):.0%}")
        if bool(row.is_past_due):
            deterioration.append(f"{int(row.days_past_due)} days past due")
        if not deterioration and bool(row.is_stalled):
            deterioration.append(f"no material movement for {int(row.quiet_days)} days")
        rows.append({
            "key": str(row.opportunity_code), "deal": str(row.opportunity_name),
            "account": str(row.account_name), "owner": str(row.owner), "stage": str(row.stage),
            "forecastCategory": str(row.forecast_category),
            "riskBand": str(row.risk_band), "riskScore": int(row.risk_score),
            "closureProbability": pwin, "mainDriver": driver,
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
            "silenceDays": int(row.quiet_days) if not pd.isna(row.quiet_days) else None,
            "isStalled": bool(row.is_stalled),
            "closeDateSlips": int(row.close_date_slips or 0),
            "slipDays": int(row.slip_days or 0),
            "deterioration": "; ".join(deterioration) if deterioration else "No deterioration signal detected",
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
    slipped = risk[risk["close_date_slips"] > 0]

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
    commit_low = scored[(scored["forecast_at_cutoff"] == "Commit") & (scored["p_win"] < .5)]
    best_case_low = scored[(scored["forecast_at_cutoff"] == "Best Case") & (scored["p_win"] < .5)]
    hot_revenue = float(hot["acv_revenue"].sum()) if len(hot) else 0.0
    open_revenue = float(risk["acv_revenue"].sum()) if len(risk) else 0.0
    banner = {
        "tone": "danger" if len(hot) else "accent",
        "headline": (f"{count(len(commit_low))} Commit and {count(len(best_case_low))} Best Case "
                     "deals sit below 50% closure probability"
                     if len(scored) else "Closure probability is unavailable for this week's commitments"),
        "subline": ("Review Commit first, then Best Case. Require customer and stage evidence before "
                    f"keeping the category; only {count(clears_half)} of {count(len(scored))} open deals clear 50%."
                    if len(scored) else
                    f"{count(len(past_due))} open deals are past due and {count(len(stalled))} are stalled."),
        "stats": [
            {"label": "Stuck", "value": count(len(stalled)), "tone": "danger"},
            {"label": "Slipped", "value": count(len(slipped)), "tone": "warn"},
            {"label": "Deal anomalies", "value": count(len(findings)), "tone": "warn"},
        ],
        "supporting": [
            {
                "key": "pipeline-health", "tone": "danger",
                "headline": f"{count(len(stalled))} deals are stuck in the pipeline",
                "subline": (f"They represent {money(float(stalled['acv_revenue'].sum()))} ACV Revenue; "
                            "owners must record a customer event, reset the date, or close the deal."),
            },
            {
                "key": "conversion-quality", "tone": "warn",
                "headline": f"{count(len(slipped))} deals carry close-date slippage risk",
                "subline": (f"Close dates moved {int(slipped['close_date_slips'].sum()) if len(slipped) else 0:,} times; "
                            "the current date needs customer-backed evidence."),
            },
        ],
    }

    insights: list[dict] = []

    def closure_insight(deal: dict | None, key: str, rank: int, title: str,
                        conclusion: str, next_step: str) -> None:
        if not deal:
            return
        insights.append({
            "key": key, "rank": rank, "theme": "closure", "title": title,
            "conclusion": conclusion,
            "evidence": [deal["deterioration"],
                         f"{deal['owner']} owns {deal['formattedRevenue']} ACV Revenue in {deal['forecastCategory']}."],
            "nextStep": next_step, "page": "closure-risk", "entity": deal["deal"],
            "actionKey": f"closure:{deal['key']}",
        })

    stalled_deal = next((d for d in closures if d["isStalled"]), None)
    slipped_deal = next((d for d in closures if d["closeDateSlips"] > 0), None)
    commit_deal = next((d for d in closures if d["forecastCategory"] == "Commit"), None)
    best_case_deal = next((d for d in closures if d["forecastCategory"] == "Best Case"), None)
    closure_insight(
        stalled_deal, "weekly:stuck", 1, "A stuck deal needs an owner decision",
        (f"{stalled_deal['deal']} has been silent for {stalled_deal['silenceDays'] or 0} days."
         if stalled_deal else ""),
        (f"Ask {stalled_deal['owner']} to log the next customer event within 48 hours, "
         "or reset the close date." if stalled_deal else ""),
    )
    if findings:
        finding = findings[0]
        insights.append({
            "key": "weekly:anomaly", "rank": 2, "theme": "anomalies",
            "title": "A deal anomaly needs investigation",
            "conclusion": f"{finding['entity']} carries a {finding['severity'].lower()}-priority {finding['category'].lower()} finding.",
            "evidence": [finding["evidence"], f"Detector view: {finding['agreement']}."],
            "nextStep": finding["nextStep"], "page": "anomalies", "entity": finding["entity"],
            "actionKey": f"anomaly:{finding['key']}",
        })
    closure_insight(
        slipped_deal, "weekly:slippage", 3, "Close-date slippage needs correction",
        (f"{slipped_deal['deal']} moved its close date {slipped_deal['closeDateSlips']} times, "
         f"{slipped_deal['slipDays']} days later in total." if slipped_deal else ""),
        (f"Ask {slipped_deal['owner']} to confirm the current date with customer evidence this week; "
         "otherwise re-date the deal." if slipped_deal else ""),
    )
    closure_insight(
        commit_deal, "weekly:commit-probability", 4, "A low-probability Commit needs evidence first",
        (f"{commit_deal['deal']} is marked Commit at "
         f"{commit_deal['closureProbability']:.0%} closure probability."
         if commit_deal and commit_deal["closureProbability"] is not None else
         f"{commit_deal['deal']} is marked Commit without a usable probability." if commit_deal else ""),
        (f"Ask {commit_deal['owner']} for the buying event, decision date, and next meeting; "
         "move it out of Commit if that evidence is absent." if commit_deal else ""),
    )
    closure_insight(
        best_case_deal, "weekly:best-case-probability", 5,
        "A low-probability Best Case needs qualification",
        (f"{best_case_deal['deal']} is marked Best Case at "
         f"{best_case_deal['closureProbability']:.0%} closure probability."
         if best_case_deal and best_case_deal["closureProbability"] is not None else
         f"{best_case_deal['deal']} is marked Best Case without a usable probability."
         if best_case_deal else ""),
        (f"Ask {best_case_deal['owner']} to validate the next customer step and close-date basis; "
         "downgrade it if neither is confirmed." if best_case_deal else ""),
    )
    insights = sorted(insights, key=lambda item: item["rank"])
    for rank, insight in enumerate(insights[:5], start=1):
        insight["rank"] = rank
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
