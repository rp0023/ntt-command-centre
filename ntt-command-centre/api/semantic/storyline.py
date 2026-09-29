"""Executive use-case payloads sourced only from the supplied storyline workbook."""

from __future__ import annotations

import functools
import statistics
import re
from collections import Counter

import pandas as pd

from config import DATA_DIR, MOVEMENT_CSV, OPPORTUNITIES_CSV
from .measures import money
from llm import closure_actions as CA


CLOSURE_SOURCE = DATA_DIR / "Deal Closure Probability 29th Sept.xlsx"
ENRICHMENT_SOURCE = DATA_DIR / "Deal Enrichment 29th Sept.xlsx"
ANOMALY_SOURCE = DATA_DIR / "Anamoly  Detection 29th Sept.xlsx"
_RISK = {1: "Critical", 2: "High", 3: "Watch", 4: "Low", 5: "Low"}


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


def _brief_insights(closures: list[dict], low: list[dict], findings: list[dict], plays: list[dict]) -> dict[str, dict]:
    """Narrative, headline stats and one action for each use-case card in the Brief."""
    brief: dict[str, dict] = {}

    risky = [d for d in closures if d["riskBucketLabel"] in ("Critical", "High")]
    top_deal = max(low, key=lambda d: d["revenue"]) if low else None
    avg_probability = sum(d["closureProbability"] for d in closures) / len(closures) if closures else 0
    brief["closure"] = {
        "narrative": (f"The largest at-risk deal, {top_deal['deal']}, carries {top_deal['formattedRevenue']} "
                      f"at {top_deal['closureProbability']:.0%} probability.") if top_deal else "",
        "stats": [
            {"label": "Open deals", "value": str(len(closures))},
            {"label": "Below 50%", "value": str(len(low))},
            {"label": "Critical / High risk", "value": str(len(risky))},
            {"label": "Avg probability", "value": f"{avg_probability:.0%}"},
        ],
        "action": (f"Review the {_plural(len(risky), 'Critical or High risk deal', 'Critical and High risk deals')} "
                   "and re-validate their forecast category this week.") if risky
                  else "Re-validate the forecast category on every deal below 50%.",
    }

    critical = [f for f in findings if f["severity"] == "Critical"]
    high = sum(f["severity"] == "High" for f in findings)
    deal_rows = {f["entityId"]: f for f in findings if f["entityType"] == "Opportunity"}
    deal_value = sum(f["revenue"] for f in deal_rows.values())
    levels = Counter(f["entityType"] for f in findings)
    level_text = ", ".join(_plural(n, {"Opportunity": "deal", "Rep": "rep", "Account": "account", "Industry": "industry"}.get(k, k.lower()),
                                   {"Opportunity": "deals", "Rep": "reps", "Account": "accounts", "Industry": "industries"}.get(k, k.lower() + "s"))
                           for k, n in levels.most_common())
    category, category_count = (Counter(f["category"] for f in findings).most_common(1)[0]
                                if findings else ("", 0))
    brief["anomalies"] = {
        "narrative": (f"They cover {level_text}, and {category} accounts for {category_count} of them.") if findings else "",
        "stats": [
            {"label": "Findings", "value": str(len(findings))},
            {"label": "Critical", "value": str(len(critical))},
            {"label": "High", "value": str(high)},
            {"label": "Flagged deal GP", "value": money(deal_value)},
        ],
        "action": (f"Investigate the {_plural(len(critical), 'Critical finding', 'Critical findings')} first, "
                   f"starting with {critical[0]['entity']} ({ANOMALY_TYPES.get(critical[0]['question'], (critical[0]['question'],))[0].lower()}).") if critical
                  else "Work through the High severity findings with each deal owner.",
    }

    strong = sum(p["confidence"] in ("High", "Very High") for p in plays)
    accounts = len({p["pilotAccount"] for p in plays})
    median_won = statistics.median(p["peerRevenueBenchmark"] for p in plays) if plays else 0
    offering, offering_count = (Counter(p["offering"] for p in plays).most_common(1)[0]
                                if plays else ("", 0))
    brief["opportunities"] = {
        "narrative": (f"They cover {_plural(accounts, 'account', 'accounts')}, and {offering} "
                      f"is the top recommendation at {offering_count} of {len(plays)}.") if plays else "",
        "stats": [
            {"label": "Recommendations", "value": str(len(plays))},
            {"label": "High confidence", "value": str(strong)},
            {"label": "Accounts", "value": str(accounts)},
            {"label": "Median peer won revenue", "value": money(median_won)},
        ],
        "action": (f"Validate the {_plural(strong, 'high-confidence recommendation', 'high-confidence recommendations')} "
                   f"with account owners, starting with {offering}.") if strong
                  else "Validate the recommendations with account owners.",
    }
    return brief


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


_MISSING = "Not in workbook"


def _count(value: object, one: str, many: str) -> str:
    if pd.isna(value):
        return f"{many}: {_MISSING.lower()}"
    n = int(value)
    return f"{n} {one if n == 1 else many}"


def _share(value: object, scale: float = 100) -> str:
    return _MISSING if pd.isna(value) else f"{float(value) * scale:.0f}%"


def _closure_details(row: object, risk: str) -> list[dict]:
    """Info-panel rows for one deal, taken only from the Deal Closure workbook."""
    stage_pace = row.avg_days_completed_stage
    age = row.deal_age_at_cutoff_days
    gm = row.gm_pct_at_cutoff
    return [
        {"label": "Model criticality", "value": f"{risk} · {_text(row.Risk_Bucket_Label, _MISSING)}"},
        {"label": "Relative risk", "value": _text(row.Risk_Bucket_Relative_Label, _MISSING)},
        {"label": "Forecast", "value": _text(row.forecast_at_cutoff, _MISSING)},
        {"label": "Stage", "value": _text(row.OpportunityStage, _MISSING)},
        {"label": "Deal type", "value": " · ".join(_text(v, _MISSING) for v in (row.DealType, row.ProductBusinessUnit, row.ServiceCategory))},
        {"label": "Primary driver", "value": _text(row.Main_Driving_Force, _MISSING)},
        {"label": "Activity history", "value": " · ".join((
            _count(row.n_stage_changes, "stage change", "stage changes"),
            _count(row.n_forecast_changes, "forecast change", "forecast changes"),
            _count(row.n_revenue_revisions, "revenue revision", "revenue revisions")))},
        {"label": "Deal age", "value": _MISSING if pd.isna(age) else f"{int(age)} days"},
        {"label": "Stage pace", "value": _MISSING if pd.isna(stage_pace) else f"{float(stage_pace):.1f} avg days per completed stage"},
        {"label": "Rep confidence", "value": _share(row.confidence_at_cutoff)},
        {"label": "GM %", "value": _MISSING if pd.isna(gm) else f"{float(gm):.1f}%"},
        {"label": "Owner win rate", "value": _share(row.owner_historical_win_rate)},
        {"label": "Owner", "value": _MISSING},
        {"label": "Close date", "value": _MISSING},
        {"label": "Silence", "value": _MISSING},
    ]


_DEFAULT_CLOSURE_STEP = "Review the model driver and validate the forecast category."
_LATE_STAGES = ("Proposal", "Proposal Evaluation", "Finalist")


def closure_facts(row: object) -> dict[str, str]:
    """The display-formatted workbook figures one deal's action may cite."""
    return {
        "Deal": _text(row.OpportunityName), "Account": _text(row.AccountName),
        "Stage": _text(row.OpportunityStage), "Forecast": _text(row.forecast_at_cutoff),
        "Model probability": f"{_number(row.Predicted_WinProbability):.1%}",
        "Rep confidence": f"{_number(row.confidence_at_cutoff):.0%}",
        "Stage changes": str(int(_number(row.n_stage_changes))),
        "Deal age": f"{int(_number(row.deal_age_at_cutoff_days))} days",
        "Revenue": money(_number(row.SFDC_ACV_Revenue)),
        "Owner win rate": f"{_number(row.owner_historical_win_rate):.0%}",
        "Primary driver": _text(row.Main_Driving_Force),
    }


def _closure_action(row: object, facts: dict[str, str]) -> str:
    """One deal-specific next step, chosen from the workbook signals in priority order."""
    stage, forecast = facts["Stage"], facts["Forecast"]
    probability, rep, age = facts["Model probability"], facts["Rep confidence"], facts["Deal age"]
    gap = _number(row.confidence_at_cutoff) - _number(row.Predicted_WinProbability)
    moves = int(_number(row.n_stage_changes))
    days = int(_number(row.deal_age_at_cutoff_days))
    driver = re.search(r"\(([^)]+)\) decreased", facts["Primary driver"])

    if forecast == "Commit":
        step = (f"Challenge the Commit call: rep confidence is {rep} but the model gives {probability}. "
                "Ask the owner for signed-order evidence or move it to Best Case.")
    elif forecast == "Best Case" and gap >= .3:
        step = (f"Test the Best Case call: rep confidence of {rep} is far above the model's {probability}. "
                "Get a dated buyer decision or downgrade it to Pipeline.")
    elif forecast == "Best Case" and days >= 365:
        step = (f"Reset the timeline: the deal is {age} old and still in {stage}. "
                "Get a dated decision from the buyer or take it out of Best Case.")
    elif forecast == "Best Case" and stage == "Finalist":
        step = (f"Secure the award: it is at Finalist with {probability} probability. "
                "Confirm the remaining competitors and agree a signed close plan with the buyer.")
    elif forecast == "Best Case":
        step = (f"Convert the proposal: agree evaluation criteria and a decision date with the buyer "
                f"to justify the Best Case call at {probability}.")
    elif stage == "Identification" and moves >= 3:
        step = (f"Find out why it slipped back: {moves} stage changes, yet it now sits in Identification. "
                "Re-qualify the buyer's need and timeline before investing more effort.")
    elif forecast == "Omitted" and stage in _LATE_STAGES:
        step = (f"Confirm the deal is still live: it is at {stage} but omitted from the forecast "
                f"with {rep} rep confidence. Have the owner re-forecast it or close it out.")
    elif driver and stage in _LATE_STAGES:
        step = (f"Move the proposal forward: agree evaluation criteria and a decision date with the buyer, "
                f"since the {driver.group(1)} stage is the biggest drag on its {probability} probability.")
    elif stage == "Identification" and days >= 365:
        step = (f"Qualify or close out: {age} in Identification with no stage movement. "
                "Confirm a named buyer, budget and timeline this week, or mark it lost.")
    elif stage == "Identification":
        step = (f"Book a discovery meeting to qualify need, budget and timeline; "
                f"after {age} the deal has not left Identification.")
    else:
        return _DEFAULT_CLOSURE_STEP
    if _number(row.SFDC_ACV_Revenue) >= 500_000:
        step += f" Escalate to sales leadership given the {facts['Revenue']} at stake."
    return step


@functools.lru_cache(maxsize=1)
def _account_reps() -> dict[str, str]:
    """AccountCode -> account owner, from the opportunities metadata file.

    The enrichment workbook carries no rep; every recommended account has
    exactly one AccountOwnerFullName in opportunities.csv, so this is a lookup,
    not an inference. A code with several owners lists them all.
    """
    try:
        opps = pd.read_csv(OPPORTUNITIES_CSV, usecols=["AccountCode", "AccountOwnerFullName"])
    except (OSError, ValueError):
        return {}
    owners = opps.dropna().groupby("AccountCode").AccountOwnerFullName.agg(lambda v: sorted(set(v)))
    return {code: " / ".join(names) for code, names in owners.items()}


_PEERS = re.compile(r'"([^"]+)"')
_SIMILAR = re.compile(r"(\d+) of this account's closest-matching peers by product mix \(avg similarity (\d+%)\)")
_BUNDLE = re.compile(r"(\d+%) of other (.+?) accounts \(n=(\d+)\)")
_BASKET = re.compile(r"Accounts with (.+?) go on to also have .+? (\d+%) of the time -- ([\d.]+x) more often than chance, based on (\d+) accounts")


def _growth_evidence(why: str) -> dict:
    """The structured facts inside the workbook's free-text Why column."""
    out: dict = {"peers": _PEERS.findall(why)}
    if m := _SIMILAR.search(why):
        out["similarPeers"], out["similarity"] = m.group(1), m.group(2)
    if m := _BUNDLE.search(why):
        out["bundleShare"], out["bundleIndustry"], out["bundleSize"] = m.group(1), m.group(2), m.group(3)
    if m := _BASKET.search(why):
        out["basketFrom"], out["basketRate"], out["basketLift"], out["basketAccounts"] = m.groups()
    return out


def _growth_action(offering: str, confidence: str, ev: dict) -> str:
    """One recommendation-specific next step, built from its own evidence."""
    product = offering.removeprefix("Add ")
    peers = ev["peers"][:2]
    refs = " and ".join(peers)
    if "basketFrom" in ev:
        return (f"Propose {product} now: accounts with {ev['basketFrom']} add it {ev['basketLift']} more often "
                f"than chance ({ev['basketRate']} of {ev['basketAccounts']} accounts). Use {refs} as reference customers.")
    if "bundleShare" in ev:
        if confidence in ("High", "Very High"):
            return (f"Pitch {product} as the {ev['bundleIndustry']} standard: {ev['bundleShare']} of the other "
                    f"{ev['bundleSize']} {ev['bundleIndustry']} accounts already buy it. Book a scoping call this quarter.")
        return (f"Raise {product} at the next account review and gauge interest; {ev['bundleShare']} of the other "
                f"{ev['bundleSize']} {ev['bundleIndustry']} accounts already buy it.")
    if "similarPeers" in ev:
        if confidence in ("High", "Very High"):
            return (f"Open a {product} conversation using {refs} as references; {ev['similarPeers']} of its closest "
                    f"peers ({ev['similarity']} product-mix similarity) already buy it.")
        return (f"Qualify interest in {product} before committing presales time; {ev['similarPeers']} close peers "
                f"({ev['similarity']} similarity) already buy it, including {peers[0].rstrip('.') if peers else 'peer accounts'}.")
    return f"Validate {product} with the account owner."


def _growth_details(row: object, ev: dict, same_offer: list[dict]) -> list[dict]:
    """Info-panel rows for one recommendation: workbook fields plus the lookups."""
    reps = sorted({p["rep"] for p in same_offer})
    methods = int(_number(row.NumMethods))
    return [
        {"label": "Recommendation ID", "value": _text(row.RecommendationId, _MISSING)},
        {"label": "Industry", "value": _text(row.Industry, _MISSING)},
        {"label": "Method", "value": f"{_text(row.Methods, _MISSING)} ({methods} method{'' if methods == 1 else 's'})"},
        {"label": "Evidence", "value": _text(row.Why, _MISSING)},
        {"label": "Reference peers", "value": ", ".join(ev["peers"]) or _MISSING},
        {"label": "Current products", "value": _text(row.CurrentProducts, _MISSING)},
        {"label": "Avg won GP (peers)", "value": money(_number(row.AvgWonGp))},
        {"label": "Current won GP", "value": money(_number(row.CurrentWonGp))},
        {"label": "Customers", "value": f"{len(same_offer)} account{'' if len(same_offer) == 1 else 's'} with this recommendation"},
        {"label": "Owners", "value": f"{len(reps)} ({', '.join(reps)})"},
    ]


#: Readable name and plain-English meaning for each AnomalyType code in the
#: Anomaly Detection workbook. The meanings paraphrase the workbook's own
#: Evidence and RecommendedAction text for that type; they add no new facts.
ANOMALY_TYPES: dict[str, tuple[str, str]] = {
    "stalled_pipeline": ("Stalled pipeline", "An open deal with no field changes logged for an extended period."),
    "industry_concentration_risk": ("Industry concentration risk", "One industry holds an outsized share of total GP, so its budget cycles can swing the whole book."),
    "account_concentration_risk": ("Account concentration risk", "One account holds an outsized share of total GP (whale risk): losing it would hit results hard."),
    "rep_concentration_risk": ("Rep concentration risk", "One rep holds an outsized share of open pipeline GP (key-person risk if they are unavailable)."),
    "new_business_mix_risk": ("New business mix risk", "Few of the rep's opportunities are New Business; the pipeline leans on renewals."),
    "rep_value_shrink_rate": ("Deal value shrinkage", "Many of the rep's opportunities shrank well beyond peer norms after entry, pointing to sizing or qualification issues."),
    "rep_sandbagging_rate": ("Possible sandbagging", "The rep's opportunities grew well beyond peer norms after entry, suggesting deals are sized low at the start."),
    "win_rate_outlier": ("Win-rate outlier", "The rep's win rate on closed deals is far below peers."),
    "rep_forecast_reliability": ("Forecast reliability", "The rep's opportunities show forecast-category regressions, so their Commit and Best Case calls need discounting."),
    "deal_size_outlier": ("Deal size outlier", "A line amount sits beyond the peer interquartile-range fence; confirm it before it feeds pipeline roll-ups."),
    "portfolio_mix_imbalance": ("Portfolio mix imbalance", "A large account whose Services revenue is well below the North America target mix."),
    "whitespace_single_lob_account": ("Single line-of-business account", "The account buys from one line of business while similar-sized peers also buy others."),
}

_OPEN_EXCLUDED = ("Deal Won", "Deal Lost")


def _finding_revenue_label(entity_type: str, type_code: str) -> str:
    """What the workbook's DealValue measures for this finding.

    Checked against opportunities.csv: DealValue equals the SFDC_ACV_Gp sum over
    the deal's lines; over every opportunity (won, lost and open) of an account
    or industry; over the rep's open pipeline for rep concentration; over the
    rep's closed deals for a win-rate outlier; and over all of the rep's
    opportunities otherwise.
    """
    if entity_type == "Opportunity":
        return "Deal ACV GP"
    if entity_type == "Account":
        return "Account ACV GP (all opportunities)"
    if entity_type == "Industry":
        return "Industry ACV GP (all opportunities)"
    if entity_type == "Rep":
        return {"rep_concentration_risk": "Rep open-pipeline ACV GP",
                "win_rate_outlier": "Rep closed-deal ACV GP"}.get(type_code, "Rep ACV GP (all owned opportunities)")
    return "ACV GP"


@functools.lru_cache(maxsize=1)
def _opportunity_meta() -> dict[str, dict]:
    """Lookups from opportunities.csv / movement.csv, keyed by entity type then id."""
    cols = ["OpportunityCode", "OpportunityName", "AccountCode", "AccountName", "AccountIndustry",
            "OpportunityStage", "ForecastCategory", "OpportunityCreateDate", "OpportunityCloseDate",
            "OpportunityOwnerFullName", "AccountOwnerFullName", "SFDC_ACV_Revenue"]
    try:
        o = pd.read_csv(OPPORTUNITIES_CSV, usecols=cols)
    except (OSError, ValueError):
        return {"opportunity": {}, "account": {}, "rep": {}, "industry": {}}
    o["open"] = ~o.OpportunityStage.isin(_OPEN_EXCLUDED)
    names = lambda s: " / ".join(sorted(set(s.dropna())))  # noqa: E731

    opportunity = {}
    for code, g in o.groupby("OpportunityCode"):
        first = g.iloc[0]
        opportunity[code] = {
            "account": first.AccountName, "industry": first.AccountIndustry,
            "stage": first.OpportunityStage, "forecast": first.ForecastCategory,
            "created": first.OpportunityCreateDate, "close": first.OpportunityCloseDate,
            "owner": names(g.OpportunityOwnerFullName), "accountOwner": names(g.AccountOwnerFullName),
            "revenue": float(g.SFDC_ACV_Revenue.sum()), "lines": len(g),
        }
    try:
        m = pd.read_csv(MOVEMENT_CSV, usecols=["OpportunityCode", "ChangeDate"])
        for code, g in m.groupby("OpportunityCode"):
            if code in opportunity:
                opportunity[code]["lastChange"] = str(g.ChangeDate.max())
                opportunity[code]["changes"] = len(g)
    except (OSError, ValueError):
        pass

    def summary(g: pd.DataFrame) -> dict:
        return {"opportunities": g.OpportunityCode.nunique(),
                "open": g[g.open].OpportunityCode.nunique(),
                "accounts": g.AccountCode.nunique(),
                "accountOwners": g.AccountOwnerFullName.nunique(),
                "accountOwner": names(g.AccountOwnerFullName),
                "industry": names(g.AccountIndustry)}

    return {
        "opportunity": opportunity,
        "account": {code: summary(g) for code, g in o.groupby("AccountCode")},
        "rep": {rep: summary(g) for rep, g in o.groupby("OpportunityOwnerFullName")},
        "industry": {ind: summary(g) for ind, g in o.groupby("AccountIndustry")},
    }


def _finding_owner(row: object, meta: dict) -> str:
    """RepName when the workbook has it; otherwise the account owner, or a plain statement."""
    rep = _text(row.RepName, "")
    if rep:
        return rep
    kind, entity_id = _text(row.EntityType), _text(row.DealId)
    if kind == "Account" and entity_id in meta["account"]:
        return meta["account"][entity_id]["accountOwner"] or _MISSING
    if kind == "Industry" and entity_id in meta["industry"]:
        return f"Industry-level ({meta['industry'][entity_id]['accountOwners']} account owners)"
    return _MISSING


def _finding_details(row: object, meta: dict, type_label: str, type_meaning: str) -> list[dict]:
    """Info-panel rows: the workbook fields plus metadata looked up by entity id."""
    kind, entity_id = _text(row.EntityType), _text(row.DealId)
    code = _text(row.AnomalyType)
    rows = [
        {"label": "Anomaly ID", "value": _text(row.AnomalyId, _MISSING)},
        {"label": "Anomaly type", "value": f"{type_label} ({code})"},
        {"label": "What this means", "value": type_meaning},
        {"label": "Severity score", "value": f"{int(_number(row.Severity))} of 100"},
        {"label": "Entity ID", "value": entity_id},
    ]
    if kind == "Opportunity" and (d := meta["opportunity"].get(entity_id)):
        rows += [
            {"label": "Account", "value": d["account"]},
            {"label": "Industry", "value": d["industry"]},
            {"label": "Stage", "value": d["stage"]},
            {"label": "Forecast", "value": d["forecast"]},
            {"label": "Created", "value": str(d["created"])},
            {"label": "Close date", "value": str(d["close"])},
            {"label": "Opportunity owner", "value": d["owner"]},
            {"label": "Account owner", "value": d["accountOwner"]},
            {"label": "ACV revenue", "value": f"{money(d['revenue'])} across {d['lines']} line{'' if d['lines'] == 1 else 's'}"},
            {"label": "Last field change", "value": d.get("lastChange", _MISSING)},
            {"label": "Changes logged", "value": str(d.get("changes", 0))},
        ]
    elif kind == "Account" and (d := meta["account"].get(entity_id)):
        rows += [
            {"label": "Industry", "value": d["industry"]},
            {"label": "Account owner", "value": d["accountOwner"]},
            {"label": "Opportunities", "value": f"{d['opportunities']} ({d['open']} open)"},
        ]
    elif kind == "Rep" and (d := meta["rep"].get(entity_id)):
        rows += [
            {"label": "Opportunities owned", "value": f"{d['opportunities']} ({d['open']} open)"},
            {"label": "Accounts covered", "value": str(d["accounts"])},
        ]
    elif kind == "Industry" and (d := meta["industry"].get(entity_id)):
        rows += [
            {"label": "Accounts in industry", "value": str(d["accounts"])},
            {"label": "Account owners", "value": str(d["accountOwners"])},
            {"label": "Opportunities", "value": f"{d['opportunities']} ({d['open']} open)"},
        ]
    return rows


def _options() -> list[dict]:
    return [
        {"key": "complete", "label": "Complete", "status": "Complete", "needsReason": False},
        {"key": "delegate", "label": "Delegate", "status": "Delegated", "needsReason": False},
        {"key": "dismiss", "label": "Dismiss", "status": "Dismissed", "needsReason": True},
    ]


def refine_closure_actions() -> dict:
    """Ask the language layer to sharpen each deal's rule-chosen action (background use)."""
    closure_raw, _, _ = tables()
    drafts = []
    for row in closure_raw.itertuples(index=False):
        facts = closure_facts(row)
        drafts.append((facts, _closure_action(row, facts)))
    return CA.refine(drafts)


def payload() -> dict:
    closure_raw, growth_raw, anomaly_raw = tables()

    closures: list[dict] = []
    # The workbook is one row per opportunity line, and a multi-line opportunity
    # repeats its OpportunityCode. Rows, actions and saved decisions all need a
    # unique key, so a repeated code is qualified with its line code.
    repeated = set(closure_raw.OpportunityCode[closure_raw.OpportunityCode.duplicated(keep=False)])
    for row in closure_raw.itertuples(index=False):
        revenue = _number(row.SFDC_ACV_Revenue)
        bucket = int(_number(row.Risk_Bucket)) or None
        probability = _number(row.Predicted_WinProbability)
        details = _closure_details(row, _RISK.get(bucket, "Low"))
        facts = closure_facts(row)
        rule_step = _closure_action(row, facts)
        refined = CA.lookup(facts, rule_step)
        closures.append({
            "key": (f"{_text(row.OpportunityCode)}-{_text(row.OpportunityLineCode)}"
                    if row.OpportunityCode in repeated else _text(row.OpportunityCode)),
            "deal": _text(row.OpportunityName),
            "account": _text(row.AccountName), "owner": _MISSING, "stage": _text(row.OpportunityStage),
            "forecastCategory": _text(row.forecast_at_cutoff), "riskBand": _RISK.get(bucket, "Low"),
            "riskScore": 0, "closureProbability": probability, "riskBucket": bucket,
            "riskBucketLabel": _RISK.get(bucket, "Low"), "mainDriver": _text(row.Main_Driving_Force),
            "closeDate": None, "silenceDays": None, "accountCycleDays": None,
            "accountCycleSampleSize": 0, "plannedCycleDays": None, "accountCycleGapDays": 0,
            "accountCycleMismatch": False, "accountCycleContext": None, "isStalled": False,
            "closeDateSlips": 0, "slipDays": 0,
            "deterioration": next(d["value"] for d in details if d["label"] == "Activity history"),
            "details": details,
            "nextStep": refined or rule_step, "nextStepSource": "ai" if refined else "rules",
            "revenue": revenue, "formattedRevenue": money(revenue),
        })

    plays: list[dict] = []
    reps = _account_reps()
    for row in growth_raw.itertuples(index=False):
        benchmark = _number(row.AvgWonRevenue)
        offering, confidence = _text(row.Recommendation), _text(row.Confidence)
        evidence = _growth_evidence(_text(row.Why, ""))
        rep = reps.get(_text(row.AccountCode), _MISSING)
        plays.append({
            "key": _text(row.RecommendationId), "offering": offering,
            "customerCount": 1, "ownerCount": 0, "confidence": confidence,
            "pilotAccount": _text(row.AccountName), "pilotOwner": rep, "rep": rep,
            "peerRevenueBenchmark": benchmark, "formattedPeerRevenueBenchmark": money(benchmark),
            "nextStep": _growth_action(offering, confidence, evidence),
            "reason": _text(row.Why), "_row": row, "_evidence": evidence,
        })
    # Customers and owners are counted across every account that received the
    # same recommendation, so they describe the play rather than one row.
    for play in plays:
        same_offer = [p for p in plays if p["offering"] == play["offering"]]
        play["customerCount"] = len(same_offer)
        play["ownerCount"] = len({p["rep"] for p in same_offer if p["rep"] != _MISSING})
        play["details"] = _growth_details(play.pop("_row"), play.pop("_evidence"), same_offer)
    offer_counts = Counter(p["offering"] for p in plays)
    repeatable = {o: n for o, n in offer_counts.items() if n >= 2}
    top_play, top_play_accounts = offer_counts.most_common(1)[0] if plays else ("Not supplied", 0)
    # AvgWonRevenue is a per-recommendation peer average, and every row of the
    # same offering repeats it, so a sum double-counts. The median and range
    # describe the evidence without implying a pipeline total.
    peer_values = [p["peerRevenueBenchmark"] for p in plays]
    peer_median = statistics.median(peer_values) if peer_values else None
    peer_min, peer_max = (min(peer_values), max(peer_values)) if peer_values else (0, 0)

    findings: list[dict] = []
    meta = _opportunity_meta()
    for row in anomaly_raw.itertuples(index=False):
        type_code = _text(row.AnomalyType)
        type_label, type_meaning = ANOMALY_TYPES.get(type_code, (type_code.replace("_", " ").capitalize(), _MISSING))
        priority = int(_number(row.Severity))
        severity = "Critical" if priority >= 95 else "High" if priority >= 85 else "Medium"
        revenue = _number(row.DealValue)
        findings.append({
            "key": _text(row.AnomalyId), "severity": severity, "entityType": _text(row.EntityType),
            "severityScore": priority,
            "entityId": _text(row.DealId), "entity": _text(row.Deal),
            "category": _text(row.AnomalyCategory), "evidence": _text(row.Evidence),
            "owner": _finding_owner(row, meta), "question": type_code,
            "typeLabel": type_label, "typeMeaning": type_meaning,
            "revenueLabel": _finding_revenue_label(_text(row.EntityType), type_code),
            "details": _finding_details(row, meta, type_label, type_meaning),
            "nextStep": _text(row.RecommendedAction), "revenue": revenue,
            "formattedRevenue": money(revenue),
        })
    # Findings sit at different levels (deal, account, industry, rep) and the
    # higher levels contain the lower ones, so only deal-level GP is added up.
    entity_counts = Counter(f["entityType"] for f in findings)
    deal_findings = [f for f in findings if f["entityType"] == "Opportunity"]
    deal_finding_revenue = sum(f["revenue"] for f in {f["entityId"]: f for f in deal_findings}.values())

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
        actions.append({"key": f"closure:{deal['key']}", "theme": "closure", "priority": deal["riskBand"] if deal["riskBand"] != "Watch" else "Medium", "owner": deal["owner"], "dueDate": "Not supplied", "headline": f"Review {deal['deal']}", "description": deal["mainDriver"], "nextStep": deal["nextStep"], "nextStepSource": deal["nextStepSource"], "revenueImpact": deal["revenue"], "formattedRevenueImpact": deal["formattedRevenue"], "revenueLabel": "Deal ACV revenue", "revenueSource": "Deal Closure Probability workbook", "revenueBasis": "deal_acv", "revenueEntityKey": deal["key"], "sourcePage": "low-probability", "options": _options()})
    for finding in findings:
        actions.append({"key": f"anomaly:{finding['key']}", "theme": "anomalies", "priority": finding["severity"], "owner": finding["owner"], "dueDate": "Not supplied", "headline": f"Investigate {finding['entity']}", "description": finding["evidence"], "nextStep": finding["nextStep"], "revenueImpact": finding["revenue"], "formattedRevenueImpact": finding["formattedRevenue"], "revenueLabel": finding["revenueLabel"], "revenueSource": "Anomaly Detection workbook", "revenueBasis": "anomaly_report", "revenueEntityKey": finding["key"], "sourcePage": "stagnated-deals", "options": _options()})
    for play in plays:
        actions.append({"key": f"opportunity:{play['key']}", "theme": "opportunities", "priority": "High" if play["confidence"] in ("High", "Very High") else "Medium", "owner": play["rep"], "dueDate": "Not supplied", "headline": f"Validate {play['offering']}", "description": play["reason"], "nextStep": play["nextStep"], "revenueImpact": play["peerRevenueBenchmark"], "formattedRevenueImpact": play["formattedPeerRevenueBenchmark"], "revenueLabel": "Peer avg won revenue (benchmark)", "revenueSource": "Deal Enrichment workbook", "revenueBasis": "peer_benchmark", "revenueEntityKey": play["key"], "sourcePage": "opportunities", "options": _options()})

    # The Brief shows the single largest item of each use case by its revenue
    # figure. Ties keep workbook order, and a tie is named so it is not hidden.
    def tied_with(items: list[dict], top: dict, value_key: str, name_key: str) -> str:
        others = [x[name_key].rstrip(".") for x in items if x is not top and x[value_key] == top[value_key]]
        return f", tied with {others[0]}" + (f" and {len(others) - 1} more" if len(others) > 1 else "") if others else ""

    insights = []
    pool = low or closures
    if pool:
        d = max(pool, key=lambda x: x["revenue"])
        insights.append({
            "key": "weekly:closure", "rank": 1, "theme": "closure",
            "title": "Largest deal below 50% probability" if low else "Largest open deal",
            "subjectLabel": "Account", "subject": d["account"],
            "subjectMeta": "",
            "conclusion": (f"{d['formattedRevenue']} of ACV revenue at a {d['closureProbability']:.1%} model probability, "
                           f"the largest of the {len(pool)} deals{' below 50%' if low else ''}{tied_with(pool, d, 'revenue', 'deal')}."),
            "evidence": [d["mainDriver"]], "nextStep": d["nextStep"], "page": "low-probability",
            "entity": d["deal"], "actionKey": f"closure:{d['key']}",
        })
    if findings:
        f = max(findings, key=lambda x: x["revenue"])
        subject_label = {"Opportunity": "Deal", "Account": "Account", "Industry": "Industry", "Rep": "Rep"}.get(f["entityType"], f["entityType"])
        insights.append({
            "key": "weekly:anomaly", "rank": 2, "theme": "anomalies",
            "title": f"Largest anomaly: {f['typeLabel'].lower()}",
            "subjectLabel": subject_label, "subject": f["entity"],
            "subjectMeta": f"Owner: {f['owner']}" if f["entityType"] in ("Opportunity", "Account") else "",
            "conclusion": (f"{f['evidence']}. It carries the largest figure of the {len(findings)} findings: "
                           f"{f['formattedRevenue']} of {f['revenueLabel']}{tied_with(findings, f, 'revenue', 'entity')}."),
            "evidence": [f"Severity {f['severityScore']} of 100 ({f['severity']})"],
            "nextStep": f["nextStep"], "page": "stagnated-deals", "entity": f["entity"],
            "actionKey": f"anomaly:{f['key']}",
        })
    if plays:
        rank = {"Very High": 0, "High": 1, "Medium": 2, "Low": 3}
        p = min(plays, key=lambda x: (-x["peerRevenueBenchmark"], rank.get(x["confidence"], 9)))
        insights.append({
            "key": "weekly:opportunity", "rank": 3, "theme": "opportunities",
            "title": f"Highest-value recommendation: {p['offering']}",
            "subjectLabel": "Company", "subject": p["pilotAccount"],
            "subjectMeta": f"Rep: {p['rep']}",
            "conclusion": (f"{p['formattedPeerRevenueBenchmark']} peer average won revenue, the highest benchmark of the "
                           f"{len(plays)} recommendations{tied_with(plays, p, 'peerRevenueBenchmark', 'pilotAccount')}."),
            "evidence": [p["reason"]], "nextStep": p["nextStep"], "page": "opportunities",
            "entity": p["pilotAccount"], "actionKey": f"opportunity:{p['key']}",
        })

    brief = _brief_insights(closures, low, findings, plays)

    return {
        "messages": [
            {"key": "opportunities", "title": "Cross-sell / upsell", "headline": f"{len(plays)} recommendations to validate", "summary": "Recommendations are sourced from the storyline workbook.", "signals": [{"label": "Recommendations", "value": str(len(plays))}], "page": "opportunities"},
            {"key": "anomalies", "title": "Anomaly detection", "headline": f"{len(findings)} anomalies to investigate", "summary": "Findings are sourced from the storyline workbook.", "signals": [{"label": "Findings", "value": str(len(findings))}], "page": "stagnated-deals"},
            {"key": "closure", "title": "Deal closure", "headline": f"{len(low)} deals below 50% probability", "summary": "Probabilities and SHAP drivers are sourced from the storyline workbook.", "signals": [{"label": "Open deals", "value": str(len(closures))}], "page": "low-probability"},
        ],
        "opportunityPlays": plays,
        "opportunityOverview": {"recommendations": len(plays), "repeatableRecommendations": sum(repeatable.values()), "singleAccountRecommendations": len(plays) - sum(repeatable.values()), "accounts": len({p['pilotAccount'] for p in plays}), "strongRecommendations": len(strong), "veryHighRecommendations": sum(p['confidence'] == 'Very High' for p in plays), "repeatablePlays": len(repeatable), "topPlay": top_play, "topPlayAccounts": top_play_accounts, "peerWonRevenueMedian": peer_median, "formattedPeerWonRevenueMedian": money(peer_median) if plays else "Not supplied", "peerWonRevenueMin": peer_min, "formattedPeerWonRevenueMin": money(peer_min), "peerWonRevenueMax": peer_max, "formattedPeerWonRevenueMax": money(peer_max), "peerRevenueBenchmark": benchmark, "formattedPeerRevenueBenchmark": money(benchmark)},
        "anomalyFindings": findings,
        "anomalyOverview": {"stalledDeals": 0, "stalledAccounts": 0, "stalledPastDue": 0, "stalledRevenue": 0, "formattedStalledRevenue": "Not supplied", "longestSilenceDays": 0, "accountFindings": len(findings), "accountsAffected": len({f['entityId'] for f in findings}), "criticalAccountFindings": sum(f['severity'] == 'Critical' for f in findings), "accountRevenue": account_revenue, "formattedAccountRevenue": money(account_revenue), "entityCounts": dict(entity_counts), "categoryCounts": dict(Counter(f["category"] for f in findings)), "highFindings": sum(f["severity"] == "High" for f in findings), "dealFindings": len({f["entityId"] for f in deal_findings}), "dealFindingRevenue": deal_finding_revenue, "formattedDealFindingRevenue": money(deal_finding_revenue), "stagnationBands": [], "forecastCalls": []},
        "stalledDeals": [], "closureExceptions": closures,
        "closureModel": {"available": True, "testAuc": None, "text": "Probability and SHAP driver values are provided by the storyline workbook."},
        "closureOverview": {"series": declared_series, "lowProbabilityRevenue": low_revenue, "formattedLowProbabilityRevenue": money(low_revenue), "lowProbabilityDeals": len(low), "slippageRevenue": 0, "formattedSlippageRevenue": "Not supplied", "slipEvents": 0, "totalSlipDays": 0, "slippedPastDueDeals": 0, "stats": {"openDeals": len(closures), "highRiskDeals": sum(d['riskBucketLabel'] in ('Critical', 'High') for d in closures), "pastDueDeals": 0, "stalledDeals": 0, "slippedDeals": 0}},
        "slippageDeals": [], "actions": actions,
        "actionOverview": {"totalActions": len(actions), "uniqueDealActions": len(closures), "dealAcvRevenue": sum(d['revenue'] for d in closures), "formattedDealAcvRevenue": money(sum(d['revenue'] for d in closures)), "accountActions": len(findings), "accountBookRevenue": account_revenue, "formattedAccountBookRevenue": money(account_revenue), "growthActions": len(plays), "growthBenchmark": benchmark, "formattedGrowthBenchmark": money(benchmark), "closureActions": len(closures), "closureRevenue": sum(d['revenue'] for d in closures), "formattedClosureRevenue": money(sum(d['revenue'] for d in closures)), "anomalyDealActions": len({f["entityId"] for f in deal_findings}), "anomalyEntityActions": len(findings) - len(deal_findings), "anomalyDealGp": deal_finding_revenue, "formattedAnomalyDealGp": money(deal_finding_revenue), "growthMedian": peer_median, "formattedGrowthMedian": money(peer_median) if plays else "Not supplied"},
        "weeklyBanner": {"tone": "danger", "headline": f"{money(low_revenue)} of revenue is below 50% win probability", "subline": "Three use cases, one action each. All figures come from the storyline workbook.", "stats": [{"label": "Open deals", "value": str(len(closures)), "tone": "accent"}, {"label": "Below 50%", "value": str(len(low)), "tone": "danger"}, {"label": "Anomalies", "value": str(len(findings)), "tone": "warn"}], "supporting": [{"key": "closure", "tone": "danger", "label": "Deal closure likelihood", "headline": f"{money(low_revenue)} of revenue is below 50% win probability", "subline": f"{len(low)} supplied deal records.", **brief["closure"], "page": "low-probability"}, {"key": "anomalies", "tone": "warn", "label": "Anomaly detection", "headline": f"{len(findings)} {'anomaly needs' if len(findings) == 1 else 'anomalies need'} investigation", "subline": "From the anomaly table.", **brief["anomalies"], "page": "stagnated-deals"}, {"key": "opportunities", "tone": "good", "label": "Cross-sell and upsell", "headline": f"{len(plays)} cross-sell and upsell {'recommendation is' if len(plays) == 1 else 'recommendations are'} ready to validate", "subline": "From the enrichment-potential table.", **brief["opportunities"], "page": "opportunities"}]},
        "weeklyInsights": insights,
    }
