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


def _opportunities(fs: FilterState, principal: Principal) -> tuple[dict, list[dict], dict]:
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
    overview = {
        "recommendations": int(summary["recommendations"]),
        "accounts": int(summary["accounts"]),
        "strongRecommendations": int(summary["strong"]),
        "veryHighRecommendations": int(summary["veryHigh"]),
        "repeatablePlays": int(summary["themes"]),
        "topPlay": str(summary.get("topTheme") or ""),
        "topPlayAccounts": int(summary.get("topThemeAccounts") or 0),
        "peerWonRevenueMedian": summary["peerWonRevenueMedian"],
        "formattedPeerWonRevenueMedian": (
            money(summary["peerWonRevenueMedian"])
            if summary["peerWonRevenueMedian"] is not None else "—"
        ),
    }
    return message, plays, overview


def _anomalies(fs: FilterState, principal: Principal) -> tuple[dict, list[dict], dict, list[dict]]:
    frame = ANOM.scoped(ANOM.for_persona("executive"), fs, principal)
    if not frame.empty:
        # Keep account risks here; account whitespace and portfolio-mix ideas
        # belong on What's the solution? and would duplicate its worklist.
        # Individual text fields are scrubbed below so profit wording from the
        # source finding never reaches the Executive payload.
        frame = frame.loc[
            frame["entity_type"].eq("Account") & frame["framing"].eq("risk")
        ].copy()
        # Mirror the workbook's strong-example rule: source-curated demo
        # priorities first, then severity. Triage remains the final tie-break.
        frame = frame.sort_values(
            ["demo_priority", "severity", "triage"], ascending=[False, False, False]
        )
    critical = int((frame["priority"] == "Critical").sum()) if not frame.empty else 0
    entities = int(frame["entity_id"].nunique()) if not frame.empty else 0
    risk = P.risk_table()
    codes = set(slice_frame(fs, principal)["opportunity_code"])
    stalled = risk[risk["opportunity_code"].isin(codes) & risk["is_stalled"]].copy()
    stalled = stalled.sort_values(["quiet_days", "risk_score"], ascending=[False, False])
    source_stalls = ANOM.enriched()
    source_stalls = source_stalls.loc[
        source_stalls["entity_type"].eq("Opportunity")
        & source_stalls["anomaly_type"].eq("stalled_pipeline")
    ].drop_duplicates("entity_id").set_index("entity_id")
    stalled_accounts = int(stalled["account_name"].nunique()) if len(stalled) else 0
    stalled_past_due = int(stalled["is_past_due"].sum()) if len(stalled) else 0
    longest_silence = int(stalled["quiet_days"].max()) if len(stalled) else 0
    stalled_revenue = float(stalled["acv_revenue"].sum()) if len(stalled) else 0.0
    stagnation_bands = []
    for label, minimum, maximum in (
        ("60–90 days", 60, 90),
        ("91–180 days", 91, 180),
        ("181+ days", 181, None),
    ):
        band = stalled[stalled["quiet_days"] >= minimum]
        if maximum is not None:
            band = band[band["quiet_days"] <= maximum]
        band_revenue = float(band["acv_revenue"].sum()) if len(band) else 0.0
        stagnation_bands.append({
            "label": label,
            "deals": int(len(band)),
            "revenue": band_revenue,
            "formattedRevenue": money(band_revenue),
            "share": float(len(band) / len(stalled)) if len(stalled) else 0.0,
        })
    forecast_calls = []
    for call in ("Commit", "Best Case", "Pipeline", "Omitted"):
        group = stalled[stalled["forecast_category"] == call]
        forecast_calls.append({
            "call": call,
            "deals": int(len(group)),
            "revenue": float(group["acv_revenue"].sum()) if len(group) else 0.0,
            "formattedRevenue": money(float(group["acv_revenue"].sum())) if len(group) else money(0),
        })
    message = {
        "key": "anomalies", "title": "Anomalies",
        "headline": f"{count(len(stalled))} stagnant deals and {count(len(frame))} account anomalies need review",
        "summary": (f"The two worklists separate pipeline inactivity from account-level patterns."
                    if len(frame) or len(stalled) else "No stagnant deal or account anomaly is visible in this scope."),
        "signals": [
            {"label": "Stagnant deals", "value": count(len(stalled))},
            {"label": "Account anomalies", "value": count(len(frame))},
            {"label": "Accounts affected", "value": count(entities)},
        ],
        "page": "anomalies",
    }
    findings = []
    for row in frame.head(20).itertuples(index=False):
        findings.append({
            "key": str(row.anomaly_id), "severity": str(row.priority),
            "entityType": str(row.entity_type), "entity": str(row.entity_label),
            "category": ("Pipeline health" if str(row.category) == "Pipeline Coverage"
                         else str(row.category)),
            "evidence": _safe_text(row.evidence, "The observed pattern is outside its peer range."),
            "owner": _safe_text(row.owner, "Executive sponsor") or "Executive sponsor",
            "question": _safe_text(row.category_question, "What changed, and does it require intervention?"),
            "nextStep": _safe_text(row.recommended_action, "Assign an owner to validate the finding."),
        })
    stalled_rows = []
    for row in stalled.head(5).itertuples(index=False):
        source = (source_stalls.loc[row.opportunity_code]
                  if row.opportunity_code in source_stalls.index else None)
        source_key = str(source["anomaly_id"]) if source is not None else None
        source_evidence = (_safe_text(source["evidence"], "") if source is not None else "")
        source_action = (_safe_text(source["recommended_action"], "")
                         if source is not None else "")
        deal_value = float(pd.to_numeric(getattr(row, "acv_revenue", 0), errors="coerce") or 0)
        days_in_stage = int(pd.to_numeric(
            getattr(row, "days_in_stage", getattr(row, "days_in_current_stage", 0)),
            errors="coerce",
        ) or 0)
        stalled_rows.append({
            "key": str(row.opportunity_code),
            "deal": str(row.opportunity_name),
            "account": str(row.account_name),
            "owner": str(row.owner),
            "stage": str(row.stage),
            "silenceDays": row.quiet_days if not pd.isna(row.quiet_days) else 0,
            "daysInStage": days_in_stage,
            "pastDueDays": int(pd.to_numeric(getattr(row, "days_past_due", 0), errors="coerce") or 0),
            "dealValue": deal_value,
            "dealValueLabel": money(deal_value),
            "call": str(row.forecast_category),
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
            "evidence": source_evidence or None,
            "nextStep": source_action or None,
            "priority": str(source["priority"]) if source is not None else None,
            "actionKey": f"stalled:{source_key}" if source_key and source_action else None,
        })
    overview = {
        "stalledDeals": int(len(stalled)),
        "stalledAccounts": stalled_accounts,
        "stalledRevenue": stalled_revenue,
        "formattedStalledRevenue": money(stalled_revenue),
        "stalledPastDue": stalled_past_due,
        "longestSilenceDays": longest_silence,
        "stagnationBands": stagnation_bands,
        "forecastCalls": forecast_calls,
        "accountFindings": int(len(frame)),
        "accountsAffected": entities,
        "criticalAccountFindings": critical,
    }
    return message, findings, overview, stalled_rows


def _closure(fs: FilterState, principal: Principal) -> tuple[dict, list[dict], dict, dict]:
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
        pwin = (row.closure_probability
                if not pd.isna(row.closure_probability) else None)
        ds_driver = _safe_text(row.model_driver) if isinstance(row.model_driver, str) else None
        factors = [f for f in row.risk_factors if f.get("key") != "thin_margin"]
        driver = ds_driver or (factors[0]["detail"] if factors else "No single observable driver dominates.")
        deterioration = []
        if row.close_date_slips or 0 > 0:
            deterioration.append(
                f"close date moved {row.close_date_slips}x ({row.slip_days or 0} days later)"
            )
        if bool(row.went_backwards):
            deterioration.append("stage moved backwards")
        if bool(row.shrank):
            deterioration.append(f"deal value fell {abs(float(row.value_drift)):.0%}")
        if bool(row.is_past_due):
            deterioration.append(f"{row.days_past_due} days past due")
        if not deterioration and bool(row.is_stalled):
            deterioration.append(f"no material movement for {row.quiet_days} days")
        rows.append({
            "key": str(row.opportunity_code), "deal": str(row.opportunity_name),
            "account": str(row.account_name), "owner": str(row.owner), "stage": str(row.stage),
            "forecastCategory": str(row.forecast_category),
            "riskBand": str(row.risk_band), "riskScore": row.risk_score,
            "closureProbability": pwin, "mainDriver": driver,
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
            "silenceDays": row.quiet_days if not pd.isna(row.quiet_days) else None,
            "isStalled": bool(row.is_stalled),
            "closeDateSlips": row.close_date_slips or 0,
            "slipDays": row.slip_days or 0,
            "deterioration": "; ".join(deterioration) if deterioration else "No deterioration signal detected",
            "revenue": row.acv_revenue, "formattedRevenue": row.acv_revenue,
        })
    model = DS.model_card() if DS.available() else DS.unavailable_card()
    disclosure = {
        "available": bool(model.get("available")), "testAuc": model.get("testAuc"),
        "text": ("Closure probability is directional. The model test AUC is "
                 f"{model.get('testAuc'):.3f} against 0.50 for chance; prioritize observable deal movement."
                 if isinstance(model.get("testAuc"), (int, float)) else
                 "Closure probability is unavailable; prioritize observable deal movement."),
    }
    revenue_series = []
    for forecast, threshold in (("Commit", .35), ("Best Case", .25)):
        declared = risk[risk["forecast_category"] == forecast]
        scored = declared[declared["closure_probability"].notna()]
        defensible = scored[scored["closure_probability"] >= threshold]
        declared_revenue = float(declared["acv_revenue"].sum())
        defensible_revenue = (float(defensible["acv_revenue"].sum())
                              if len(scored) else None)
        screened_out = (declared_revenue - defensible_revenue
                        if defensible_revenue is not None else None)
        revenue_series.append({
            "forecast": forecast,
            "threshold": threshold,
            "declaredRevenue": declared_revenue,
            "formattedDeclaredRevenue": money(declared_revenue),
            "declaredDeals": int(len(declared)),
            "defensibleRevenue": defensible_revenue,
            "formattedDefensibleRevenue": (money(defensible_revenue)
                                             if defensible_revenue is not None else "—"),
            "defensibleDeals": int(len(defensible)) if len(scored) else None,
            "screenedOutRevenue": screened_out,
            "formattedScreenedOutRevenue": (money(screened_out)
                                              if screened_out is not None else "—"),
            "retainedShare": (defensible_revenue / declared_revenue
                              if defensible_revenue is not None and declared_revenue else None),
        })
    overview = {
        "series": revenue_series,
        "stats": {
            "openDeals": int(len(risk)),
            "highRiskDeals": int(len(hot)),
            "pastDueDeals": int(risk["is_past_due"].sum()),
            "stalledDeals": int(risk["is_stalled"].sum()),
            "slippedDeals": int((risk["close_date_slips"] > 0).sum()),
        },
    }
    return message, rows, disclosure, overview


def _actions(plays: list[dict], findings: list[dict], stalled_deals: list[dict],
             closures: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for i, play in enumerate(plays[:4]):
        actions.append({
            "key": f"opportunity:{play['key']}", "theme": "opportunities",
            "priority": "High" if i == 0 else "Medium", "owner": play["pilotOwner"],
            "dueDate": _date(7 + i * 2), "headline": f"Pilot {play['offering']}",
            "description": play["reason"],
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
            "description": finding["evidence"],
            "options": _options("anomalies"),
        })
    for deal in stalled_deals:
        if not deal.get("actionKey") or not deal.get("evidence") or not deal.get("nextStep"):
            continue
        actions.append({
            "key": deal["actionKey"], "theme": "anomalies",
            "priority": deal.get("priority") or "High", "owner": deal["owner"],
            # The supplied DS recommendation explicitly asks for confirmation this week.
            "dueDate": _date(7), "headline": f"Confirm status of {deal['deal']}",
            "description": deal["evidence"], "nextStep": deal["nextStep"],
            "options": _options("anomalies"),
        })
    for i, deal in enumerate(closures[:10]):
        if deal["forecastCategory"] == "Commit":
            next_step = (f"Ask {deal['owner']} for the buying event, decision date, and next meeting; "
                         "move the deal out of Commit if that evidence is absent.")
        elif deal["forecastCategory"] == "Best Case":
            next_step = (f"Ask {deal['owner']} to validate the next customer step and close-date basis; "
                         "downgrade the deal if neither is confirmed.")
        elif deal["closeDateSlips"] > 0:
            next_step = (f"Ask {deal['owner']} to confirm the current date with customer evidence; "
                         "otherwise re-date the deal.")
        else:
            next_step = (f"Ask {deal['owner']} to log the next customer event within 48 hours, "
                         "or reset the close date.")
        actions.append({
            "key": f"closure:{deal['key']}", "theme": "closure",
            "priority": "Critical" if deal["riskBand"] == "Critical" else "High",
            "owner": deal["owner"], "dueDate": _date(1 + i),
            "headline": f"Review {deal['deal']}",
            "description": f"{deal['mainDriver']} {deal['deterioration']}.",
            "nextStep": next_step,
            "revenueImpact": deal["revenue"], "formattedRevenueImpact": deal["formattedRevenue"],
            "options": _options("closure"),
        })
    return sorted(actions, key=lambda a: (PRIORITY_ORDER.get(a["priority"], 9), a["dueDate"]))


def _weekly_focus(fs: FilterState, principal: Principal, findings: list[dict],
                  closures: list[dict], plays: list[dict], opportunity_overview: dict,
                  anomaly_overview: dict) -> tuple[dict, list[dict]]:
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

    clears_half = int((scored["p_win"] >= .5).sum()) if len(scored) else 0
    commit_low = scored[(scored["forecast_at_cutoff"] == "Commit") & (scored["p_win"] < .5)]
    best_case_low = scored[(scored["forecast_at_cutoff"] == "Best Case") & (scored["p_win"] < .5)]
    hot_revenue = float(hot["acv_revenue"].sum()) if len(hot) else 0.0
    open_revenue = float(risk["acv_revenue"].sum()) if len(risk) else 0.0
    stalled_revenue = float(stalled["acv_revenue"].sum()) if len(stalled) else 0.0
    slipped_revenue = float(slipped["acv_revenue"].sum()) if len(slipped) else 0.0
    commit_low_revenue = float(risk[risk["opportunity_code"].isin(
        set(commit_low["opportunity_code"]))]["acv_revenue"].sum())
    best_case_low_revenue = float(risk[risk["opportunity_code"].isin(
        set(best_case_low["opportunity_code"]))]["acv_revenue"].sum())
    region_label = "NA region" if "north america" in principal.identity_label.lower() else principal.identity_label
    stalled_days = int(stalled["quiet_days"].max()) if len(stalled) else 60
    banner = {
        "tone": "danger" if len(hot) else "accent",
        "headline": f"{money(hot_revenue)} ACV Revenue is at risk for {region_label}",
        "subline": (
            f"{count(len(stalled))} deals ({money(stalled_revenue)}) stuck in pipeline for >{stalled_days} days. "
            f"{count(len(slipped))} deals ({money(slipped_revenue)}) with major slippage risk"
        ),
        "stats": [
            {"label": "Open pipeline", "value": money(open_revenue), "tone": "accent"},
            {"label": "At risk", "value": money(hot_revenue), "tone": "danger"},
            {"label": "Past due", "value": count(len(past_due)), "tone": "warn"},
        ],
        "supporting": [
            {
                "key": "closure", "tone": "danger", "label": "Deal closure likelihood",
                "headline": f"{money(hot_revenue)} ACV Revenue at risk",
                "subline": (f"{count(len(commit_low))} Commit and {count(len(best_case_low))} Best Case "
                            "deals sit below 50% probability."),
                "page": "closure-risk",
            },
            {
                "key": "anomalies", "tone": "warn", "label": "Anomaly detection",
                "headline": (f"{anomaly_overview['formattedStalledRevenue']} ACV Revenue "
                             "on stagnant deals"),
                "subline": (f"{count(anomaly_overview['stalledDeals'])} stagnant deals across "
                            f"{count(anomaly_overview['stalledAccounts'])} accounts; "
                            f"{count(anomaly_overview['stalledPastDue'])} are past due."),
                "page": "anomalies",
            },
            {
                "key": "opportunities", "tone": "good", "label": "Cross-sell and upsell",
                "headline": (f"{opportunity_overview['formattedPeerWonRevenueMedian']} "
                             "median peer-won revenue"),
                "subline": (f"{count(opportunity_overview['recommendations'])} source recommendations "
                            f"across {count(opportunity_overview['accounts'])} accounts; "
                            f"{count(opportunity_overview['repeatablePlays'])} repeatable plays."),
                "page": "opportunities",
            },
        ],
    }

    insights: list[dict] = []

    def closure_insight(deal: dict | None, key: str, rank: int, title: str,
                        conclusion: str, evidence: list[str], next_step: str) -> None:
        if not deal:
            return
        insights.append({
            "key": key, "rank": rank, "theme": "closure", "title": title,
            "conclusion": conclusion, "evidence": evidence,
            "nextStep": next_step, "page": "closure-risk", "entity": deal["deal"],
            "actionKey": f"closure:{deal['key']}",
        })

    stalled_deal = next((d for d in closures if d["isStalled"]), None)
    slipped_deal = next((d for d in closures if d["closeDateSlips"] > 0), None)
    commit_deal = next((d for d in closures if d["forecastCategory"] == "Commit"), None)
    best_case_deal = next((d for d in closures if d["forecastCategory"] == "Best Case"), None)
    closure_insight(
        commit_deal, "weekly:forecast-probability", 1,
        "Low-probability forecast calls need reclassification",
        (f"{money(commit_low_revenue)} in Commit and {money(best_case_low_revenue)} in Best Case "
         "sit below 50% closure probability."),
        ([f"Commit: {count(len(commit_low))} deals; review this category first.",
          f"Best Case: {count(len(best_case_low))} deals; review it second."]),
        (f"Ask {commit_deal['owner']} for the buying event, decision date, and next meeting; "
         "move it out of Commit if that evidence is absent." if commit_deal else ""),
    )
    closure_insight(
        slipped_deal, "weekly:slippage", 2, "Close-date slippage needs correction",
        f"{money(slipped_revenue)} sits on {count(len(slipped))} deals whose close date has moved.",
        ([f"{slipped_deal['deal']} moved {slipped_deal['closeDateSlips']} times, "
          f"{slipped_deal['slipDays']} days later in total.", slipped_deal["deterioration"]]
         if slipped_deal else []),
        (f"Ask {slipped_deal['owner']} to confirm the date with customer evidence this week; "
         "otherwise re-date the deal." if slipped_deal else ""),
    )
    closure_insight(
        stalled_deal, "weekly:stuck", 3, "Stuck pipeline needs an owner decision",
        f"{money(stalled_revenue)} across {count(len(stalled))} deals has stopped moving.",
        ([f"{stalled_deal['deal']} has been silent for {stalled_deal['silenceDays'] or 0} days.",
          f"{stalled_deal['owner']} owns {stalled_deal['formattedRevenue']} ACV Revenue."]
         if stalled_deal else []),
        (f"Ask {stalled_deal['owner']} to log the next customer event within 48 hours, "
         "or reset the close date." if stalled_deal else ""),
    )
    if findings:
        finding = findings[0]
        insights.append({
            "key": "weekly:anomaly", "rank": 4, "theme": "anomalies",
            "title": "A deal anomaly needs investigation",
            "conclusion": f"{finding['entity']} carries a {finding['severity'].lower()}-priority {finding['category'].lower()} finding.",
            "evidence": [finding["evidence"], f"Account pattern: {finding['category']}."],
            "nextStep": finding["nextStep"], "page": "anomalies", "entity": finding["entity"],
            "actionKey": f"anomaly:{finding['key']}",
        })
    if plays:
        play = plays[0]
        insights.append({
            "key": "weekly:cross-sell", "rank": 5, "theme": "opportunities",
            "title": "A cross-sell play is ready for customer validation",
            "conclusion": (f"{play['offering']} reaches {count(play['customerCount'])} customers "
                           f"across {count(play['ownerCount'])} owners."),
            "evidence": [f"{play['pilotAccount']} is the strongest {play['confidence']} confidence pilot.",
                         play["reason"]],
            "nextStep": play["nextStep"], "page": "opportunities",
            "entity": play["pilotAccount"], "actionKey": f"opportunity:{play['key']}",
        })
    insights = sorted(insights, key=lambda item: item["rank"])
    for rank, insight in enumerate(insights[:5], start=1):
        insight["rank"] = rank
    return banner, insights[:5]


def payload(fs: FilterState, principal: Principal) -> dict:
    opportunity_message, plays, opportunity_overview = _opportunities(fs, principal)
    anomaly_message, findings, anomaly_overview, stalled_deals = _anomalies(fs, principal)
    closure_message, closures, disclosure, closure_overview = _closure(fs, principal)
    actions = _actions(plays, findings, stalled_deals, closures)
    weekly_banner, weekly_insights = _weekly_focus(
        fs, principal, findings, closures, plays, opportunity_overview, anomaly_overview,
    )
    return {
        "messages": [opportunity_message, anomaly_message, closure_message],
        "opportunityPlays": plays, "opportunityOverview": opportunity_overview,
        "anomalyFindings": findings, "anomalyOverview": anomaly_overview,
        "stalledDeals": stalled_deals,
        "closureExceptions": closures, "closureModel": disclosure,
        "closureOverview": closure_overview,
        "actions": actions, "weeklyBanner": weekly_banner,
        "weeklyInsights": weekly_insights,
    }


def view(page: str, fs: FilterState, principal: Principal, label: str, question: str) -> dict:
    focused = payload(fs, principal)
    if page == "tldr":
        weekly_action_keys = {
            insight["actionKey"] for insight in focused["weeklyInsights"]
            if insight.get("actionKey")
        }
        focused["actions"] = [a for a in focused["actions"] if a["key"] in weekly_action_keys]
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
        focused["closureExceptions"] = []
    elif page == "opportunities":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "opportunities"]
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
        focused["closureExceptions"] = []
    elif page == "anomalies":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "anomalies"]
        focused["opportunityPlays"] = []
        focused["closureExceptions"] = []
    elif page == "closure-risk":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "closure"]
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
    elif page == "action-center":
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
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
