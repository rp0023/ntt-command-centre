"""Focused, profit-free view model for the Executive experience."""

from __future__ import annotations

from datetime import timedelta
import re

import pandas as pd

from . import anomalies as ANOM
from . import crosssell as XS
from . import ds_model as DS
from . import predict as P
from .loader import AS_OF, CUR_QUARTER, fy_label, opportunities
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
    themes = XS.themes(fs, principal)
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
        "peerRevenueBenchmark": float(t["peerRevenueBenchmark"]),
        "formattedPeerRevenueBenchmark": money(float(t["peerRevenueBenchmark"])),
        "nextStep": f"Ask {t['strongest']['owner']} to validate {t['strongest']['accountName']} as the pilot.",
        "reason": t["strongest"]["reason"],
    } for t in themes]
    overview = {
        "recommendations": int(summary["recommendations"]),
        "repeatableRecommendations": int(summary["repeatableRecommendations"]),
        "singleAccountRecommendations": int(summary["singleAccountRecommendations"]),
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
        "peerRevenueBenchmark": float(summary["peerRevenueBenchmark"]),
        "formattedPeerRevenueBenchmark": money(float(summary["peerRevenueBenchmark"])),
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
    account_codes = set(frame["entity_id"].astype(str)) if not frame.empty else set()
    account_revenue = float(risk[risk["account_code"].astype(str).isin(account_codes)]["acv_revenue"].sum()) if account_codes else 0.0
    account_revenue_by_code = risk.groupby(risk["account_code"].astype(str))["acv_revenue"].sum()
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
    for row in frame.itertuples(index=False):
        finding_revenue = float(account_revenue_by_code.get(str(row.entity_id), 0.0))
        findings.append({
            "key": str(row.anomaly_id), "severity": str(row.priority),
            "entityId": str(row.entity_id),
            "entityType": str(row.entity_type), "entity": str(row.entity_label),
            "category": ("Pipeline health" if str(row.category) == "Pipeline Coverage"
                         else str(row.category)),
            "evidence": _safe_text(row.evidence, "The observed pattern is outside its peer range."),
            "owner": _safe_text(row.owner, "Executive sponsor") or "Executive sponsor",
            "question": _safe_text(row.category_question, "What changed, and does it require intervention?"),
            "nextStep": _safe_text(row.recommended_action, "Assign an owner to validate the finding."),
            "revenue": finding_revenue, "formattedRevenue": money(finding_revenue),
        })
    stalled_rows = []
    for row in stalled.itertuples(index=False):
        source = (source_stalls.loc[row.opportunity_code]
                  if row.opportunity_code in source_stalls.index else None)
        source_evidence = (_safe_text(source["evidence"], "") if source is not None else "")
        source_action = (_safe_text(source["recommended_action"], "")
                         if source is not None else "")
        deal_value = float(pd.to_numeric(getattr(row, "acv_revenue", 0), errors="coerce") or 0)
        days_in_stage = int(pd.to_numeric(
            getattr(row, "days_in_stage", getattr(row, "days_in_current_stage", 0)),
            errors="coerce",
        ) or 0)
        fallback_evidence = (
            f"No field changed in {int(row.quiet_days)} days; the deal remains open at {row.stage}."
        )
        fallback_action = "Confirm the real status, update the deal, or close it out."
        fallback_priority = ("High" if str(row.risk_band) in ("Critical", "High")
                             else "Medium")
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
            "evidence": source_evidence or fallback_evidence,
            "nextStep": source_action or fallback_action,
            "priority": str(source["priority"]) if source is not None else fallback_priority,
            "actionKey": f"stalled:{row.opportunity_code}",
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
        "accountRevenue": account_revenue,
        "formattedAccountRevenue": money(account_revenue),
    }
    return message, findings, overview, stalled_rows


def _closure(fs: FilterState, principal: Principal) -> tuple[dict, list[dict], dict, dict, list[dict]]:
    risk = P.risk_table()
    codes = set(slice_frame(fs, principal)["opportunity_code"])
    risk = risk[risk["opportunity_code"].isin(codes)].copy()
    history_codes = set(slice_frame(FilterState(measure="revenue"), principal)["opportunity_code"])
    history = opportunities()
    history = history.loc[
        history["opportunity_code"].isin(history_codes)
        & history["is_closed"]
        & history["cycle_days"].gt(0)
        & history["close_date"].le(pd.Timestamp(AS_OF))
    ]
    account_cycles = history.groupby("account_code")["cycle_days"].agg(
        account_cycle_sample_size="count", account_cycle_days="median",
    )
    risk = risk.merge(account_cycles, left_on="account_code", right_index=True, how="left")
    risk["account_cycle_sample_size"] = risk["account_cycle_sample_size"].fillna(0).astype(int)
    risk["planned_cycle_days"] = (
        risk["age_days"] + risk["days_to_close"].clip(lower=0)
    ).astype(int)
    risk["account_cycle_gap_days"] = (
        risk["account_cycle_days"] - risk["planned_cycle_days"]
    )
    target_quarter = fs.quarter or CUR_QUARTER
    risk["account_cycle_mismatch"] = (
        risk["fiscal_quarter"].eq(target_quarter)
        & risk["account_cycle_sample_size"].ge(3)
        & risk["account_cycle_gap_days"].ge(30)
        & risk["account_cycle_gap_days"].ge(risk["account_cycle_days"] * .25)
    )
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
    select_one(risk[risk["account_cycle_mismatch"]],
               ["account_cycle_gap_days", "acv_revenue"], [False, False])
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
        if (row.close_date_slips or 0) > 0:
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
        account_cycle_days = (
            int(round(row.account_cycle_days))
            if row.account_cycle_sample_size >= 3 and row.fiscal_quarter == target_quarter
            else None
        )
        account_cycle_gap_days = (
            int(round(row.account_cycle_gap_days))
            if row.account_cycle_mismatch else 0
        )
        account_cycle_context = None
        if account_cycle_days is not None:
            account_cycle_context = (
                f"{row.account_cycle_sample_size} prior closed deals at this account had a "
                f"median {account_cycle_days}-day cycle. This deal's planned close implies "
                f"{int(row.planned_cycle_days)} total days"
                + (f", {account_cycle_gap_days} days shorter than that median."
                   if row.account_cycle_mismatch else ".")
            )
        rows.append({
            "key": str(row.opportunity_code), "deal": str(row.opportunity_name),
            "account": str(row.account_name), "owner": str(row.owner), "stage": str(row.stage),
            "forecastCategory": str(row.forecast_category),
            "riskBand": str(row.risk_band), "riskScore": row.risk_score,
            "closureProbability": pwin, "mainDriver": driver,
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
            "silenceDays": row.quiet_days if not pd.isna(row.quiet_days) else None,
            "accountCycleDays": account_cycle_days,
            "accountCycleSampleSize": int(row.account_cycle_sample_size),
            "plannedCycleDays": int(row.planned_cycle_days) if account_cycle_days is not None else None,
            "accountCycleGapDays": account_cycle_gap_days,
            "accountCycleMismatch": bool(row.account_cycle_mismatch),
            "accountCycleContext": account_cycle_context,
            "isStalled": bool(row.is_stalled),
            "closeDateSlips": row.close_date_slips or 0,
            "slipDays": row.slip_days or 0,
            "deterioration": "; ".join(deterioration) if deterioration else "No deterioration signal detected",
            "revenue": float(row.acv_revenue), "formattedRevenue": money(float(row.acv_revenue)),
        })

    # Slippage is a movement-log use case, not a model-risk use case. Include
    # every open deal whose close date moved later, and order by the observable
    # movement first: number of re-dates, cumulative days moved, overdue days,
    # then ACV. This list intentionally does not inherit the curated Brief cap.
    slipped = risk[risk["close_date_slips"] > 0].copy()
    slipped = slipped.sort_values(
        ["close_date_slips", "slip_days", "days_past_due", "acv_revenue"],
        ascending=[False, False, False, False],
    )
    source_slips = ANOM.unified()
    source_slips = source_slips.loc[
        source_slips["entity_type"].eq("Opportunity")
        & source_slips["anomaly_type"].eq("close_date_slip")
    ].drop_duplicates("entity_id").set_index("entity_id")
    slippage_rows = []
    for row in slipped.itertuples(index=False):
        portfolio = str(row.portfolio) if isinstance(row.portfolio, str) else ""
        lob = str(row.lob) if isinstance(row.lob, str) else ""
        source = (source_slips.loc[row.opportunity_code]
                  if row.opportunity_code in source_slips.index else None)
        evidence = (_safe_text(source["evidence"], "") if source is not None else "")
        next_step = (_safe_text(source["recommended_action"], "")
                     if source is not None else "")
        slippage_rows.append({
            "key": str(row.opportunity_code),
            "account": str(row.account_name),
            "deal": str(row.opportunity_name),
            "line": portfolio or lob,
            "owner": str(row.owner),
            "accountOwner": str(row.account_owner),
            "revenue": float(row.acv_revenue),
            "formattedRevenue": money(float(row.acv_revenue)),
            "forecastCategory": str(row.forecast_category),
            "riskBand": str(row.risk_band),
            "evidence": evidence or None,
            "nextStep": next_step or None,
            "priority": str(source["priority"]) if source is not None else None,
            "closeDateSlips": int(row.close_date_slips),
            "slipDays": int(row.slip_days),
            "pastDueDays": int(row.days_past_due),
            "closeDate": row.close_date.date().isoformat() if not pd.isna(row.close_date) else None,
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
    # Forecast defensibility is category-specific: Commit carries a higher
    # evidence bar than Best Case. The page worklist still uses the separate
    # business definition of low probability (below 50%).
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
        "lowProbabilityRevenue": float(risk[risk["closure_probability"] < .5]["acv_revenue"].sum()) if "closure_probability" in risk else 0.0,
        "formattedLowProbabilityRevenue": money(float(risk[risk["closure_probability"] < .5]["acv_revenue"].sum())) if "closure_probability" in risk else money(0),
        "lowProbabilityDeals": int((risk["closure_probability"] < .5).sum()) if "closure_probability" in risk else 0,
        "slippageRevenue": float(risk[risk["close_date_slips"] > 0]["acv_revenue"].sum()),
        "formattedSlippageRevenue": money(float(risk[risk["close_date_slips"] > 0]["acv_revenue"].sum())),
        "slipEvents": int(slipped["close_date_slips"].sum()),
        "totalSlipDays": int(slipped["slip_days"].sum()),
        "slippedPastDueDeals": int(slipped["is_past_due"].sum()),
    }
    return message, rows, disclosure, overview, slippage_rows


def _actions(plays: list[dict], findings: list[dict], stalled_deals: list[dict],
             closures: list[dict], slippage_deals: list[dict]) -> list[dict]:
    actions: list[dict] = []
    for i, play in enumerate(plays):
        actions.append({
            "key": f"opportunity:{play['key']}", "theme": "opportunities",
            "priority": ("High" if play["confidence"] in ("High", "Very High")
                         else "Medium"), "owner": play["pilotOwner"],
            "dueDate": _date(7 + i * 2), "headline": f"Pilot {play['offering']}",
            "description": play["reason"],
            "nextStep": play["nextStep"],
            "sourcePage": "opportunities",
            "revenueImpact": play["peerRevenueBenchmark"],
            "formattedRevenueImpact": play["formattedPeerRevenueBenchmark"],
            "revenueLabel": "Peer-based revenue benchmark",
            "revenueBasis": "peer_benchmark",
            "revenueEntityKey": play["key"],
            "options": _options("opportunities"),
        })
    seen: set[str] = set()
    for finding in findings:
        if finding["entity"] in seen:
            continue
        seen.add(finding["entity"])
        actions.append({
            "key": f"anomaly:{finding['key']}", "theme": "anomalies",
            "priority": finding["severity"], "owner": finding["owner"],
            "dueDate": _date(2 if finding["severity"] == "Critical" else 5),
            "headline": f"Investigate {finding['entity']}", "nextStep": finding["nextStep"],
            "description": finding["evidence"],
            "sourcePage": "account-anomalies",
            "revenueImpact": finding["revenue"],
            "formattedRevenueImpact": finding["formattedRevenue"],
            "revenueLabel": "Open ACV Revenue at this account",
            "revenueBasis": "account_book_acv",
            "revenueEntityKey": finding["entityId"],
            "options": _options("anomalies"),
        })
    for deal in stalled_deals:
        actions.append({
            "key": deal["actionKey"], "theme": "anomalies",
            "priority": deal.get("priority") or "High", "owner": deal["owner"],
            # The supplied DS recommendation explicitly asks for confirmation this week.
            "dueDate": _date(7), "headline": f"Confirm status of {deal['deal']}",
            "description": deal["evidence"], "nextStep": deal["nextStep"],
            "sourcePage": "stagnated-deals",
            "revenueImpact": deal["dealValue"],
            "formattedRevenueImpact": deal["dealValueLabel"],
            "revenueLabel": "Associated ACV Revenue",
            "revenueBasis": "deal_acv",
            "revenueEntityKey": deal["key"],
            "options": _options("anomalies"),
        })
    for i, deal in enumerate(closures):
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
            "sourcePage": "low-probability",
            "revenueImpact": deal["revenue"], "formattedRevenueImpact": deal["formattedRevenue"],
            "revenueLabel": "Associated ACV Revenue",
            "revenueBasis": "deal_acv", "revenueEntityKey": deal["key"],
            "options": _options("closure"),
        })
    for deal in slippage_deals:
        priority = (deal.get("priority") or
                    ("Critical" if deal["riskBand"] == "Critical" else
                     "High" if deal["riskBand"] == "High" else "Medium"))
        actions.append({
            "key": f"slippage:{deal['key']}", "theme": "closure",
            "priority": priority, "owner": deal["owner"],
            "dueDate": _date(2 if priority == "Critical" else 4 if priority == "High" else 7),
            "headline": f"Validate close date for {deal['deal']}",
            "description": (deal.get("evidence") or
                            f"The close date moved later {deal['closeDateSlips']} time(s), "
                            f"adding {deal['slipDays']} days."),
            "nextStep": (deal.get("nextStep") or
                         "Confirm the new date is committed rather than the deal drifting."),
            "sourcePage": "slippage-risk",
            "revenueImpact": deal["revenue"],
            "formattedRevenueImpact": deal["formattedRevenue"],
            "revenueLabel": "Associated ACV Revenue",
            "revenueBasis": "deal_acv", "revenueEntityKey": deal["key"],
            "options": _options("closure"),
        })
    return sorted(actions, key=lambda a: (PRIORITY_ORDER.get(a["priority"], 9), a["dueDate"]))


def _action_overview(actions: list[dict]) -> dict:
    """Revenue attached to actions, kept separate by non-additive basis."""
    totals: dict[str, dict[str, float]] = {
        "deal_acv": {}, "account_book_acv": {}, "peer_benchmark": {},
    }
    for action in actions:
        basis = action.get("revenueBasis")
        entity = action.get("revenueEntityKey")
        value = float(action.get("revenueImpact", 0) or 0)
        if basis in totals and entity:
            # A deal can require both probability and slippage actions. Count
            # its ACV once in the headline while retaining both action cards.
            totals[basis][str(entity)] = value
    deal_acv = float(sum(totals["deal_acv"].values()))
    account_book = float(sum(totals["account_book_acv"].values()))
    peer_benchmark = float(sum(totals["peer_benchmark"].values()))
    return {
        "totalActions": int(len(actions)),
        "uniqueDealActions": int(len(totals["deal_acv"])),
        "dealAcvRevenue": deal_acv, "formattedDealAcvRevenue": money(deal_acv),
        "accountActions": int(len(totals["account_book_acv"])),
        "accountBookRevenue": account_book, "formattedAccountBookRevenue": money(account_book),
        "growthActions": int(len(totals["peer_benchmark"])),
        "growthBenchmark": peer_benchmark, "formattedGrowthBenchmark": money(peer_benchmark),
    }


def _weekly_focus(fs: FilterState, principal: Principal, findings: list[dict],
                  closures: list[dict], stalled_deals: list[dict],
                  slippage_deals: list[dict], plays: list[dict],
                  opportunity_overview: dict, anomaly_overview: dict,
                  closure_overview: dict) -> tuple[dict, list[dict]]:
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
                "page": "low-probability",
            },
            {
                "key": "anomalies", "tone": "warn", "label": "Anomaly detection",
                "headline": (f"{anomaly_overview['formattedStalledRevenue']} ACV Revenue "
                             "on stagnant deals"),
                "subline": (f"{count(anomaly_overview['stalledDeals'])} stagnant deals across "
                            f"{count(anomaly_overview['stalledAccounts'])} accounts; "
                            f"{count(anomaly_overview['stalledPastDue'])} are past due."),
                "page": "stagnated-deals",
            },
            {
                "key": "opportunities", "tone": "good", "label": "Cross-sell and upsell",
                "headline": (f"{opportunity_overview['formattedPeerRevenueBenchmark']} "
                             "peer-based revenue benchmark"),
                "subline": (f"{count(opportunity_overview['recommendations'])} source recommendations "
                            f"across {count(opportunity_overview['accounts'])} accounts; "
                            f"{count(opportunity_overview['repeatablePlays'])} repeatable plays."),
                "page": "opportunities",
            },
        ],
    }

    insights: list[dict] = []

    def closure_insight(deal: dict | None, key: str, rank: int, title: str,
                        conclusion: str, evidence: list[str], next_step: str,
                        page: str, action_key: str) -> None:
        if not deal:
            return
        insights.append({
            "key": key, "rank": rank, "theme": "closure", "title": title,
            "conclusion": conclusion, "evidence": evidence,
            "nextStep": next_step, "page": page, "entity": deal["deal"],
            "actionKey": action_key,
        })

    low_probability_deal = next((d for d in closures
                                 if d["forecastCategory"] == "Commit"
                                 and d["closureProbability"] is not None
                                 and d["closureProbability"] < .5), None)
    if not low_probability_deal:
        low_probability_deal = next((d for d in closures
                                     if d["closureProbability"] is not None
                                     and d["closureProbability"] < .5), None)
    stalled_deal = stalled_deals[0] if stalled_deals else None
    slipped_deal = slippage_deals[0] if slippage_deals else None
    closure_insight(
        low_probability_deal, "weekly:forecast-probability", 1,
        "Low-probability forecast calls need reclassification",
        (f"{closure_overview['formattedLowProbabilityRevenue']} across "
         f"{count(closure_overview['lowProbabilityDeals'])} open deals sits below 50% closure probability."),
        ([f"{low_probability_deal['deal']} has a {low_probability_deal['closureProbability']:.0%} model probability "
          f"and {low_probability_deal['formattedRevenue']} ACV Revenue.",
          f"It is currently forecast as {low_probability_deal['forecastCategory']} and rated {low_probability_deal['riskBand']} risk."]
         if low_probability_deal else []),
        (f"Ask {low_probability_deal['owner']} for the buying event, decision date, and next meeting; "
         "move it out of the current forecast call if that evidence is absent." if low_probability_deal else ""),
        "low-probability", f"closure:{low_probability_deal['key']}" if low_probability_deal else "",
    )
    closure_insight(
        slipped_deal, "weekly:slippage", 2, "Close-date slippage needs correction",
        f"{closure_overview['formattedSlippageRevenue']} sits on {count(closure_overview['stats']['slippedDeals'])} deals whose close date moved later.",
        ([f"{slipped_deal['deal']} moved {slipped_deal['closeDateSlips']} times, "
          f"{slipped_deal['slipDays']} days later in total.",
          slipped_deal.get("evidence") or f"Current close date: {slipped_deal['closeDate'] or 'unavailable'}."]
         if slipped_deal else []),
        (f"Ask {slipped_deal['owner']} to confirm the date with customer evidence this week; "
         "otherwise re-date the deal." if slipped_deal else ""),
        "slippage-risk", f"slippage:{slipped_deal['key']}" if slipped_deal else "",
    )
    if stalled_deal:
        insights.append({
            "key": "weekly:stuck", "rank": 3, "theme": "anomalies",
            "title": "Stuck pipeline needs an owner decision",
            "conclusion": (f"{anomaly_overview['formattedStalledRevenue']} across "
                           f"{count(anomaly_overview['stalledDeals'])} deals has no material movement for 60+ days."),
            "evidence": [f"{stalled_deal['deal']} has been silent for {stalled_deal['silenceDays']} days.",
                         f"{stalled_deal['owner']} owns {stalled_deal['dealValueLabel']} ACV Revenue."],
            "nextStep": stalled_deal["nextStep"], "page": "stagnated-deals",
            "entity": stalled_deal["deal"], "actionKey": stalled_deal["actionKey"],
        })
    if findings:
        finding = findings[0]
        insights.append({
            "key": "weekly:anomaly", "rank": 4, "theme": "anomalies",
            "title": "A deal anomaly needs investigation",
            "conclusion": f"{finding['entity']} carries a {finding['severity'].lower()}-priority {finding['category'].lower()} finding.",
            "evidence": [finding["evidence"], f"Account pattern: {finding['category']}."],
            "nextStep": finding["nextStep"], "page": "account-anomalies", "entity": finding["entity"],
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
    closure_message, closures, disclosure, closure_overview, slippage_deals = _closure(fs, principal)
    actions = _actions(plays, findings, stalled_deals, closures, slippage_deals)
    action_overview = _action_overview(actions)
    weekly_banner, weekly_insights = _weekly_focus(
        fs, principal, findings, closures, stalled_deals, slippage_deals, plays,
        opportunity_overview, anomaly_overview, closure_overview,
    )
    return {
        "messages": [opportunity_message, anomaly_message, closure_message],
        "opportunityPlays": plays, "opportunityOverview": opportunity_overview,
        "anomalyFindings": findings, "anomalyOverview": anomaly_overview,
        "stalledDeals": stalled_deals,
        "closureExceptions": closures, "closureModel": disclosure,
        "closureOverview": closure_overview,
        "slippageDeals": slippage_deals,
        "actions": actions, "actionOverview": action_overview, "weeklyBanner": weekly_banner,
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
        focused["slippageDeals"] = []
    elif page == "opportunities":
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "opportunities"]
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
        focused["closureExceptions"] = []
        focused["slippageDeals"] = []
    elif page in ("stagnated-deals", "account-anomalies"):
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "anomalies"]
        focused["opportunityPlays"] = []
        focused["closureExceptions"] = []
        focused["slippageDeals"] = []
        if page == "stagnated-deals":
            focused["anomalyFindings"] = []
        else:
            focused["stalledDeals"] = []
    elif page in ("low-probability", "slippage-risk"):
        focused["actions"] = [a for a in focused["actions"] if a["theme"] == "closure"]
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
        if page == "low-probability":
            focused["slippageDeals"] = []
        else:
            focused["closureExceptions"] = []
    elif page == "action-center":
        focused["opportunityPlays"] = []
        focused["anomalyFindings"] = []
        focused["stalledDeals"] = []
        focused["closureExceptions"] = []
        focused["slippageDeals"] = []
    page_revenue = {
        "low-probability": {"value": focused["closureOverview"]["lowProbabilityRevenue"], "formatted": focused["closureOverview"]["formattedLowProbabilityRevenue"], "label": "open revenue scores below 50% closure probability"},
        "slippage-risk": {"value": focused["closureOverview"]["slippageRevenue"], "formatted": focused["closureOverview"]["formattedSlippageRevenue"], "label": "open revenue has a moved close date"},
        "stagnated-deals": {"value": focused["anomalyOverview"]["stalledRevenue"], "formatted": focused["anomalyOverview"]["formattedStalledRevenue"], "label": "open revenue has no material movement for 60+ days"},
        "account-anomalies": {"value": focused["anomalyOverview"]["accountRevenue"], "formatted": focused["anomalyOverview"]["formattedAccountRevenue"], "label": "open revenue belongs to accounts with a risk anomaly"},
        "opportunities": {"value": focused["opportunityOverview"]["peerRevenueBenchmark"], "formatted": focused["opportunityOverview"]["formattedPeerRevenueBenchmark"], "label": "peer-based revenue benchmark across repeatable plays; not pipeline or forecast"},
        "action-center": {"value": focused["actionOverview"]["dealAcvRevenue"], "formatted": focused["actionOverview"]["formattedDealAcvRevenue"], "label": "unique deal ACV attached to action items; account-book ACV and growth benchmark are shown separately"},
    }.get(page)
    return {
        "page": page, "label": label, "question": question, "persona": "executive",
        "asOf": AS_OF.isoformat(), "fy": fy_label(2026), "quarter": CUR_QUARTER,
        "scope": {"label": principal.identity_label, "predicate": principal.predicate_sql,
                  "persona": principal.key, "identity": principal.identity},
        "filters": fs.active(), "measure": "revenue", "kpis": [], "metricBanners": [],
        "narrative": {"headline": "", "sentences": [], "provider": "computed"},
        "actions": [], "charts": [], "chartsSay": [], "extras": {}, "measures": {},
        "executive": focused,
        "pageRevenueSummary": page_revenue,
    }
