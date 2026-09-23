from __future__ import annotations

"""Meanings copied from Anomaly_Reference_Guide.docx. Do not invent extra types."""

CATEGORIES = [
    {
        "id": "Sequence Integrity",
        "meaning": "Checks that a deal's own history makes logical sense — that it moved through the sales process in a sensible order.",
    },
    {
        "id": "Pipeline Coverage",
        "meaning": "Looks at whether the pipeline is healthy, active, and large enough — both for individual deals and for the business as a whole.",
    },
    {
        "id": "Value Integrity",
        "meaning": "Checks whether the dollar figures attached to a deal are trustworthy — the value itself, how it moved over time, and the profitability behind it.",
    },
    {
        "id": "Deal Governance",
        "meaning": "Focused on whether the sales process itself can be trusted — not whether the pipeline looks healthy, but whether the numbers were arrived at properly.",
    },
    {
        "id": "Rep Behavior",
        "meaning": "Looks for patterns that only become meaningful when they repeat for the same person, rather than being a one-off on a single deal.",
    },
    {
        "id": "Concentration & Cross-Sell",
        "meaning": "Looks at where the business may be overly dependent on a small number of accounts or industries, and where there's clear room to sell more into existing accounts. Cross-sell items are upside, not risks.",
    },
    {
        "id": "Multivariate ML",
        "meaning": "Uses a machine-learning model that looks at many signals about a deal together rather than checking one rule at a time.",
    },
]

TYPES = {
    "stage_skip": {
        "label": "Stage Skipping",
        "category": "Sequence Integrity",
        "meaning": "A deal's recorded history jumps straight from an early stage to a much later one, missing the steps in between.",
        "action": "Confirm the deal was genuinely worked through the stages it skipped. If it clusters on one rep or team, treat it as a coaching or process-adoption conversation.",
    },
    "forecast_regression": {
        "label": "Forecast Confidence Reversal",
        "category": "Sequence Integrity",
        "meaning": "A deal's sales confidence rating reached a high point at some stage and later dropped back down, rather than only building as the deal progressed.",
        "action": "Treat the rep's current confidence rating on this deal with some caution and ask for a fresh assessment.",
    },
    "stalled_pipeline": {
        "label": "Stalled Pipeline",
        "category": "Pipeline Coverage",
        "meaning": "An open deal that hasn't had any activity or update logged in a long time, even though it's still counted as active pipeline.",
        "action": "The account/opportunity owner should confirm the deal's real status, update it, or close it out.",
    },
    "sales_cycle_outlier": {
        "label": "Extended Sales Cycle",
        "category": "Pipeline Coverage",
        "meaning": "A deal — open or already closed — has taken considerably longer than the standard expected time to move through the sales process.",
        "action": "Review what is holding (or held) the deal up, and whether the extended timeline reflects genuine complexity or a process breakdown.",
    },
    "coverage_hole": {
        "label": "Coverage Gap",
        "category": "Pipeline Coverage",
        "meaning": "A combination of business line and product/service area that has a sales target assigned to it, but very little active pipeline behind it.",
        "action": "The regional or segment lead should prioritize generating new opportunities in this specific area.",
    },
    "win_rate_outlier": {
        "label": "Win-Rate Shortfall",
        "category": "Pipeline Coverage",
        "meaning": "A rep, business line, or product/service area whose rate of winning deals is well below what's typical elsewhere in the business.",
        "action": "Apply a higher pipeline-coverage expectation here until win rates recover, and investigate whether it's a qualification, competitive, or execution issue.",
    },
    "top_deal_dependency": {
        "label": "Concentrated Quarter Dependency",
        "category": "Pipeline Coverage",
        "meaning": "A large share of what's needed to hit a quarter's target rests on just a handful of very large deals.",
        "action": "Actively diversify the pipeline for that quarter rather than relying on a few large deals to land.",
    },
    "value_shrinkage": {
        "label": "Value Shrinkage",
        "category": "Value Integrity",
        "meaning": "A deal was originally logged at a considerably higher value than what it eventually settled at.",
        "action": "Review the rep's process for sizing and qualifying deals early on.",
    },
    "value_inflation": {
        "label": "Value Inflation",
        "category": "Value Integrity",
        "meaning": "A deal grew significantly in value compared to when it was first logged.",
        "action": "Confirm the growth reflects a genuine scope increase or upsell, rather than the deal being under-scoped at the outset.",
    },
    "deal_size_outlier": {
        "label": "Deal Size Outlier",
        "category": "Value Integrity",
        "meaning": "A deal's dollar value is unusually large or small compared to similar deals of the same type.",
        "action": "Double-check the amount was entered correctly before it feeds into pipeline totals and forecasts.",
    },
    "margin_outlier": {
        "label": "Margin Outlier",
        "category": "Value Integrity",
        "meaning": "A deal's profit margin is unusually high or low compared to similar deals of the same type.",
        "action": "For unusually low margins, review pricing or discounting; for unusually high margins, confirm the cost basis was captured correctly.",
    },
    "won_loss_making_deal": {
        "label": "Loss-Making Win",
        "category": "Value Integrity",
        "meaning": "A deal was won, but it generates zero or negative profit.",
        "action": "Finance or the deal desk should confirm this was a deliberate pricing decision rather than an error.",
    },
    "quarter_end_clustering": {
        "label": "Quarter-End Clustering",
        "category": "Deal Governance",
        "meaning": "An unusually large number of deals close right at the very end of a financial quarter, more than a natural, steady closing pattern would produce.",
        "action": "Spot-check a sample of these deals to confirm they closed organically, rather than being pulled forward to hit a deadline.",
    },
    "flash_close": {
        "label": "Flash Close",
        "category": "Deal Governance",
        "meaning": "A deal moved from open to won in an implausibly short time compared to how long similar deals normally take.",
        "action": "Confirm the deal's qualification history is genuine before relying on its numbers — it may have been worked outside the system and entered after the fact.",
    },
    "rep_forecast_reliability": {
        "label": "Rep Forecast Reliability",
        "category": "Rep Behavior",
        "meaning": "A rep whose deals show the Forecast Confidence Reversal pattern more often than their peers.",
        "action": "Discount this rep's confidence ratings and review their forecasting habits directly with them.",
    },
    "rep_value_shrink_rate": {
        "label": "Rep Value Shrink Rate",
        "category": "Rep Behavior",
        "meaning": "A rep whose deals shrink in value more often than their peers.",
        "action": "Review this rep's opportunity-qualification and sizing process specifically.",
    },
    "rep_sandbagging_rate": {
        "label": "Rep Sandbagging Rate",
        "category": "Rep Behavior",
        "meaning": "A rep whose deals grow in value well beyond their initial estimate more often than their peers — the opposite pattern to shrinkage.",
        "action": "Coach on early sizing accuracy; this rep may be consistently under-forecasting their deals' true potential.",
    },
    "rep_concentration_risk": {
        "label": "Rep Pipeline Concentration",
        "category": "Rep Behavior",
        "meaning": "One rep holds an unusually large share of the total open pipeline.",
        "action": "A succession/coverage-planning matter for leadership — consider the business risk if this rep were unavailable.",
    },
    "new_business_mix_risk": {
        "label": "New-Business Mix Risk",
        "category": "Rep Behavior",
        "meaning": "A rep's deals are almost entirely renewals, with very little new business.",
        "action": "Check this rep's pipeline-generation activity — over-reliance on renewals is a growth risk.",
    },
    "industry_concentration_risk": {
        "label": "Industry Concentration Risk",
        "category": "Concentration & Cross-Sell",
        "meaning": "An unusually large share of total business is concentrated in a single industry.",
        "action": "Review diversification strategy and exposure to that industry's specific budget cycles.",
    },
    "account_concentration_risk": {
        "label": "Account Concentration Risk",
        "category": "Concentration & Cross-Sell",
        "meaning": "An unusually large share of total business is concentrated in a single account.",
        "action": "Assess the impact of losing this account and plan retention/diversification accordingly.",
    },
    "whitespace_single_lob_account": {
        "label": "Cross-Sell Whitespace",
        "category": "Concentration & Cross-Sell",
        "meaning": "A large account only buys from a single business line, when similarly-sized accounts typically buy from several.",
        "action": "Consider pitching the business line(s) this account doesn't yet have, based on what similar accounts have found value in.",
    },
    "portfolio_mix_imbalance": {
        "label": "Portfolio Mix Imbalance",
        "category": "Concentration & Cross-Sell",
        "meaning": "A large account's spend is heavily skewed toward one type of offering with very little of another, compared to the business's overall target mix.",
        "action": "Explore attaching the underrepresented offering type for this account.",
    },
    "ml_multivariate_outlier": {
        "label": "Multivariate Outlier",
        "category": "Multivariate ML",
        "meaning": "A deal that doesn't resemble its peers when many signals are considered together, even if no single signal on its own looks unusual.",
        "action": "Review manually — this is a ranking signal meant to prioritize deals for a closer look, not a specific, explainable rule.",
    },
}


def catalog_payload(counts: dict[str, int] | None = None) -> list[dict]:
    counts = counts or {}
    out = []
    for t, meta in TYPES.items():
        out.append(
            {
                "type": t,
                "label": meta["label"],
                "category": meta["category"],
                "meaning": meta["meaning"],
                "action": meta["action"],
                "count": int(counts.get(t, 0)),
            }
        )
    return out
