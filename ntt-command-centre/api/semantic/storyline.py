"""Executive use-case payloads sourced only from the supplied storyline workbook."""

from __future__ import annotations

import functools

import pandas as pd

from config import DATA_DIR
from .measures import money


CLOSURE_SOURCE = DATA_DIR / "Deal Closure Probability 29th Sept.xlsx"
ENRICHMENT_SOURCE = DATA_DIR / "Deal Enrichment 29th Sept.xlsx"
ANOMALY_SOURCE = DATA_DIR / "Anamoly  Detection 29th Sept.xlsx"
_RISK = {1: "Critical", 2: "High", 3: "Watch", 4: "Low", 5: "Low"}


def _text(value: object, fallback: str = "Not supplied") -> str:
    return fallback if pd.isna(value) or str(value).strip() == "" else str(value).strip()


def _number(value: object) -> float:
    number = pd.to_numeric(value, errors="coerce")
    return 0.0 if pd.isna(number) else float(number)


@functools.lru_cache(maxsize=1)
def tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the three dedicated 29 September source workbooks only."""
    closure = pd.read_excel(CLOSURE_SOURCE, sheet_name=0, header=1).dropna(how="all")
    growth = pd.read_excel(ENRICHMENT_SOURCE, sheet_name=0, header=1).dropna(how="all")
    anomaly = pd.read_excel(ANOMALY_SOURCE, sheet_name=0, header=0).dropna(how="all")
    return closure, growth, anomaly


def _options() -> list[dict]:
    return [
        {"key": "complete", "label": "Complete", "status": "Complete", "needsReason": False},
        {"key": "delegate", "label": "Delegate", "status": "Delegated", "needsReason": False},
        {"key": "dismiss", "label": "Dismiss", "status": "Dismissed", "needsReason": True},
    ]


def payload() -> dict:
    closure_raw, growth_raw, anomaly_raw = tables()

    closures: list[dict] = []
    for row in closure_raw.itertuples(index=False):
        revenue = _number(row.SFDC_ACV_Revenue)
        bucket = int(_number(row.Risk_Bucket)) or None
        probability = _number(row.Predicted_WinProbability)
        closures.append({
            "key": _text(row.OpportunityCode), "deal": _text(row.OpportunityName),
            "account": _text(row.AccountName), "owner": "Not supplied", "stage": _text(row.OpportunityStage),
            "forecastCategory": _text(row.forecast_at_cutoff), "riskBand": _RISK.get(bucket, "Low"),
            "riskScore": 0, "closureProbability": probability, "riskBucket": bucket,
            "riskBucketLabel": _RISK.get(bucket, "Low"), "mainDriver": _text(row.Main_Driving_Force),
            "closeDate": None, "silenceDays": None, "accountCycleDays": None,
            "accountCycleSampleSize": 0, "plannedCycleDays": None, "accountCycleGapDays": 0,
            "accountCycleMismatch": False, "accountCycleContext": None, "isStalled": False,
            "closeDateSlips": 0, "slipDays": 0,
            "deterioration": "Not supplied by the storyline workbook.",
            "revenue": revenue, "formattedRevenue": money(revenue),
        })

    plays: list[dict] = []
    for row in growth_raw.itertuples(index=False):
        benchmark = _number(row.AvgWonRevenue)
        plays.append({
            "key": _text(row.RecommendationId), "offering": _text(row.Recommendation),
            "customerCount": 1, "ownerCount": 0, "confidence": _text(row.Confidence),
            "pilotAccount": _text(row.AccountName), "pilotOwner": "Not supplied",
            "peerRevenueBenchmark": benchmark, "formattedPeerRevenueBenchmark": money(benchmark),
            "nextStep": f"Validate {_text(row.Recommendation)} with {_text(row.AccountName)}.",
            "reason": _text(row.Why),
        })

    findings: list[dict] = []
    for row in anomaly_raw.itertuples(index=False):
        priority = int(_number(row.Severity))
        severity = "Critical" if priority >= 95 else "High" if priority >= 85 else "Medium"
        revenue = _number(row.DealValue)
        findings.append({
            "key": _text(row.AnomalyId), "severity": severity, "entityType": _text(row.EntityType),
            "severityScore": priority,
            "entityId": _text(row.DealId), "entity": _text(row.Deal),
            "category": _text(row.AnomalyCategory), "evidence": _text(row.Evidence),
            "owner": _text(row.RepName), "question": _text(row.AnomalyType),
            "nextStep": _text(row.RecommendedAction), "revenue": revenue,
            "formattedRevenue": money(revenue),
        })

    declared_series = []
    for forecast, threshold in (("Commit", .35), ("Best Case", .25)):
        group = [d for d in closures if d["forecastCategory"] == forecast]
        defensible = [d for d in group if d["closureProbability"] >= threshold]
        declared = sum(d["revenue"] for d in group)
        retained = sum(d["revenue"] for d in defensible)
        declared_series.append({
            "forecast": forecast, "threshold": threshold, "declaredRevenue": declared,
            "formattedDeclaredRevenue": money(declared), "declaredDeals": len(group),
            "defensibleRevenue": retained, "formattedDefensibleRevenue": money(retained),
            "defensibleDeals": len(defensible), "screenedOutRevenue": declared - retained,
            "formattedScreenedOutRevenue": money(declared - retained),
            "retainedShare": retained / declared if declared else 0,
        })

    low = [d for d in closures if d["closureProbability"] < .5]
    low_revenue = sum(d["revenue"] for d in low)
    strong = [p for p in plays if p["confidence"] in ("High", "Very High")]
    benchmark = sum(p["peerRevenueBenchmark"] for p in plays)
    account_revenue = sum(f["revenue"] for f in findings)

    actions: list[dict] = []
    for deal in closures:
        actions.append({"key": f"closure:{deal['key']}", "theme": "closure", "priority": deal["riskBand"] if deal["riskBand"] != "Watch" else "Medium", "owner": "Not supplied", "dueDate": "Not supplied", "headline": f"Review {deal['deal']}", "description": deal["mainDriver"], "nextStep": "Review the model driver and validate the forecast category.", "revenueImpact": deal["revenue"], "formattedRevenueImpact": deal["formattedRevenue"], "revenueLabel": "SFDC ACV revenue", "revenueBasis": "deal_acv", "revenueEntityKey": deal["key"], "sourcePage": "low-probability", "options": _options()})
    for finding in findings:
        actions.append({"key": f"anomaly:{finding['key']}", "theme": "anomalies", "priority": finding["severity"], "owner": finding["owner"], "dueDate": "Not supplied", "headline": f"Investigate {finding['entity']}", "description": finding["evidence"], "nextStep": finding["nextStep"], "revenueImpact": finding["revenue"], "formattedRevenueImpact": finding["formattedRevenue"], "revenueLabel": "Deal value", "revenueBasis": "anomaly_report", "revenueEntityKey": finding["key"], "sourcePage": "account-anomalies", "options": _options()})
    for play in plays:
        actions.append({"key": f"opportunity:{play['key']}", "theme": "opportunities", "priority": "High" if play["confidence"] in ("High", "Very High") else "Medium", "owner": "Not supplied", "dueDate": "Not supplied", "headline": f"Validate {play['offering']}", "description": play["reason"], "nextStep": play["nextStep"], "revenueImpact": play["peerRevenueBenchmark"], "formattedRevenueImpact": play["formattedPeerRevenueBenchmark"], "revenueLabel": "Average won revenue", "revenueBasis": "peer_benchmark", "revenueEntityKey": play["key"], "sourcePage": "opportunities", "options": _options()})

    selected = [low[0]] if low else closures[:1]
    insights = []
    if selected:
        d = selected[0]
        insights.append({"key": "weekly:closure", "rank": 1, "theme": "closure", "title": "Low-probability deal needs review", "conclusion": f"{d['formattedRevenue']} has a {d['closureProbability']:.0%} model probability.", "evidence": [d["mainDriver"]], "nextStep": "Review the model driver and validate the forecast category.", "page": "low-probability", "entity": d["deal"], "actionKey": f"closure:{d['key']}"})
    if findings:
        f = findings[0]
        insights.append({"key": "weekly:anomaly", "rank": 2, "theme": "anomalies", "title": "Anomaly requires investigation", "conclusion": f["evidence"], "evidence": [f"{f['formattedRevenue']} deal value", f["nextStep"]], "nextStep": f["nextStep"], "page": "account-anomalies", "entity": f["entity"], "actionKey": f"anomaly:{f['key']}"})
    if plays:
        p = plays[0]
        insights.append({"key": "weekly:opportunity", "rank": 3, "theme": "opportunities", "title": "Cross-sell recommendation is ready", "conclusion": p["reason"], "evidence": [f"{p['formattedPeerRevenueBenchmark']} average won revenue"], "nextStep": p["nextStep"], "page": "opportunities", "entity": p["pilotAccount"], "actionKey": f"opportunity:{p['key']}"})

    return {
        "messages": [
            {"key": "opportunities", "title": "Cross-sell / upsell", "headline": f"{len(plays)} recommendations to validate", "summary": "Recommendations are sourced from the storyline workbook.", "signals": [{"label": "Recommendations", "value": str(len(plays))}], "page": "opportunities"},
            {"key": "anomalies", "title": "Anomaly detection", "headline": f"{len(findings)} anomalies to investigate", "summary": "Findings are sourced from the storyline workbook.", "signals": [{"label": "Findings", "value": str(len(findings))}], "page": "account-anomalies"},
            {"key": "closure", "title": "Deal closure", "headline": f"{len(low)} deals below 50% probability", "summary": "Probabilities and SHAP drivers are sourced from the storyline workbook.", "signals": [{"label": "Open deals", "value": str(len(closures))}], "page": "low-probability"},
        ],
        "opportunityPlays": plays,
        "opportunityOverview": {"recommendations": len(plays), "repeatableRecommendations": 0, "singleAccountRecommendations": len(plays), "accounts": len({p['pilotAccount'] for p in plays}), "strongRecommendations": len(strong), "veryHighRecommendations": sum(p['confidence'] == 'Very High' for p in plays), "repeatablePlays": 0, "topPlay": plays[0]['offering'] if plays else "Not supplied", "topPlayAccounts": 1 if plays else 0, "peerWonRevenueMedian": None, "formattedPeerWonRevenueMedian": "Not supplied", "peerRevenueBenchmark": benchmark, "formattedPeerRevenueBenchmark": money(benchmark)},
        "anomalyFindings": findings,
        "anomalyOverview": {"stalledDeals": 0, "stalledAccounts": 0, "stalledPastDue": 0, "stalledRevenue": 0, "formattedStalledRevenue": "Not supplied", "longestSilenceDays": 0, "accountFindings": len(findings), "accountsAffected": len({f['entityId'] for f in findings}), "criticalAccountFindings": sum(f['severity'] == 'Critical' for f in findings), "accountRevenue": account_revenue, "formattedAccountRevenue": money(account_revenue), "stagnationBands": [], "forecastCalls": []},
        "stalledDeals": [], "closureExceptions": closures,
        "closureModel": {"available": True, "testAuc": None, "text": "Probability and SHAP driver values are provided by the storyline workbook."},
        "closureOverview": {"series": declared_series, "lowProbabilityRevenue": low_revenue, "formattedLowProbabilityRevenue": money(low_revenue), "lowProbabilityDeals": len(low), "slippageRevenue": 0, "formattedSlippageRevenue": "Not supplied", "slipEvents": 0, "totalSlipDays": 0, "slippedPastDueDeals": 0, "stats": {"openDeals": len(closures), "highRiskDeals": sum(d['riskBucketLabel'] in ('Critical', 'High') for d in closures), "pastDueDeals": 0, "stalledDeals": 0, "slippedDeals": 0}},
        "slippageDeals": [], "actions": actions,
        "actionOverview": {"totalActions": len(actions), "uniqueDealActions": len(closures), "dealAcvRevenue": sum(d['revenue'] for d in closures), "formattedDealAcvRevenue": money(sum(d['revenue'] for d in closures)), "accountActions": len(findings), "accountBookRevenue": account_revenue, "formattedAccountBookRevenue": money(account_revenue), "growthActions": len(plays), "growthBenchmark": benchmark, "formattedGrowthBenchmark": money(benchmark)},
        "weeklyBanner": {"tone": "danger", "headline": f"{money(low_revenue)} revenue below 50% probability", "subline": "All values shown in the Executive use cases come from the storyline workbook.", "stats": [{"label": "Open deals", "value": str(len(closures)), "tone": "accent"}, {"label": "Below 50%", "value": str(len(low)), "tone": "danger"}, {"label": "Anomalies", "value": str(len(findings)), "tone": "warn"}], "supporting": [{"key": "closure", "tone": "danger", "label": "Deal closure likelihood", "headline": f"{money(low_revenue)} below 50% probability", "subline": f"{len(low)} supplied deal records.", "page": "low-probability"}, {"key": "anomalies", "tone": "warn", "label": "Anomaly detection", "headline": f"{len(findings)} supplied findings", "subline": "From the anomaly table.", "page": "account-anomalies"}, {"key": "opportunities", "tone": "good", "label": "Cross-sell and upsell", "headline": f"{len(plays)} supplied recommendations", "subline": "From the enrichment-potential table.", "page": "opportunities"}]},
        "weeklyInsights": insights,
    }
