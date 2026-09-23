from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from app.config import ANOM_PATH, AS_OF, MOV_PATH, OPP_PATH

STAGE_ORDER = [
    "Identification",
    "Requirements Definition",
    "Qualification",
    "Proposal",
    "Proposal Evaluation",
    "Finalist",
    "Deal Won",
    "Deal Lost",
]
FORECAST_ORDER = ["Omitted", "Pipeline", "Best Case", "Commit", "Closed"]
CLOSED_STAGES = {"Deal Won", "Deal Lost"}
SERVICES_PORTFOLIOS = {"Technical Services", "SDIS", "Consulting Services", "VBR"}

COLMAP = {
    "OpportunityGlobalRegionName": "region",
    "OpportunityCountry": "country",
    "AccountCode": "account_code",
    "AccountName": "account_name",
    "AccountGroup": "account_group",
    "AccountIndustry": "industry",
    "OpportunityCode": "opportunity_code",
    "OpportunityLineCode": "line_code",
    "OpportunityName": "opportunity_name",
    "OpportunityStage": "stage",
    "Confidence": "confidence",
    "ForecastCategory": "forecast_category",
    "OpportunityCreateDate": "create_date",
    "OpportunityCloseDate": "close_date",
    "AccountOwnerFullName": "account_owner",
    "AccountOwnerEmailAdress": "account_owner_email",
    "OpportunityOwnerFullName": "owner",
    "OpportunityOwnerEmailAdress": "owner_email",
    "ProductBusinessUnit": "lob",
    "ServiceCategory": "portfolio",
    "OrderType": "order_type",
    "ContractTermMonths": "term_months",
    "SFDC_ACV_Revenue": "acv_revenue",
    "SFDC_ACV_Gp": "acv_gp",
    "SFDC_TCV_Revenue": "tcv_revenue",
    "SFDC_TCV_Gp": "tcv_gp",
    "GM_Percent": "gm_pct_row",
    "Quarter": "quarter",
    "Month": "month",
    "QuarterlyBudget_ACVRevenue": "q_budget_rev",
    "QuarterlyBudget_ACVGp": "q_budget_gp",
    "QuarterlyGap_ACVGP": "q_gap_gp",
    "QuarterlyTotalPipeline_ACVGP": "q_tp_gp",
    "TP_RAGStatus": "tp_rag",
    "QuarterlyQualifiedPipeline_ACVGP": "q_qp_gp",
    "QP_RAGStatus": "qp_rag",
    "LOBPortfolioQuarterlyBudget_ACVRevenue": "cell_budget_rev",
    "LOBPortfolioQuarterlyBudget_ACVGp": "cell_budget_gp",
    "MonthlyBudget_ACVRevenue": "m_budget_rev",
    "MonthlyBudget_ACVGp": "m_budget_gp",
    "MonthlyClosedPlusCommit_ACVGP": "m_closed_commit_gp",
    "ClosedCommit_RAGStatus": "cc_rag",
    "LOBPortfolioMonthlyBudget_ACVRevenue": "m_cell_budget_rev",
    "LOBPortfolioMonthlyBudget_ACVGp": "m_cell_budget_gp",
}


def _prep_lines(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in COLMAP if c not in df.columns]
    if missing:
        raise ValueError(f"Opportunities file is missing columns: {missing}")
    out = df.rename(columns=COLMAP).copy()
    for c in ("create_date", "close_date"):
        out[c] = pd.to_datetime(out[c], errors="coerce")
    for c in ("acv_revenue", "acv_gp", "tcv_revenue", "tcv_gp", "confidence", "gm_pct_row", "term_months"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    as_of = pd.Timestamp(AS_OF)
    out["is_open"] = ~out["stage"].isin(CLOSED_STAGES)
    out["is_won"] = out["stage"].eq("Deal Won")
    out["is_lost"] = out["stage"].eq("Deal Lost")
    out["is_qualified"] = out["is_open"] & out["stage"].ne("Identification")
    out["is_services"] = out["portfolio"].isin(SERVICES_PORTFOLIOS)
    out["past_due"] = out["is_open"] & out["close_date"].lt(as_of)
    out["gm_pct"] = out["acv_gp"] / out["acv_revenue"].replace(0, pd.NA)
    out["as_of"] = as_of
    return out


def _prep_movement(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [c.strip() for c in out.columns]
    out = out.rename(
        columns={
            "ChangeId": "change_id",
            "OpportunityCode": "opportunity_code",
            "AccountName": "account_name",
            "OpportunityName": "opportunity_name",
            "FieldChanged": "field",
            "OldValue": "old_value",
            "NewValue": "new_value",
            "ChangeDate": "change_date",
            "ChangedByFullName": "changed_by",
            "ChangedByEmail": "changed_by_email",
        }
    )
    out["change_date"] = pd.to_datetime(out["change_date"], errors="coerce")
    return out


@dataclass(frozen=True)
class Store:
    lines: pd.DataFrame
    movement: pd.DataFrame
    opportunities: pd.DataFrame
    anomalies: pd.DataFrame


def _opportunity_grain(lines: pd.DataFrame) -> pd.DataFrame:
    agg = (
        lines.groupby("opportunity_code", as_index=False)
        .agg(
            opportunity_name=("opportunity_name", "first"),
            account_code=("account_code", "first"),
            account_name=("account_name", "first"),
            industry=("industry", "first"),
            country=("country", "first"),
            region=("region", "first"),
            stage=("stage", "first"),
            forecast_category=("forecast_category", "first"),
            confidence=("confidence", "first"),
            create_date=("create_date", "first"),
            close_date=("close_date", "first"),
            owner=("owner", "first"),
            owner_email=("owner_email", "first"),
            order_type=("order_type", "first"),
            acv_revenue=("acv_revenue", "sum"),
            acv_gp=("acv_gp", "sum"),
            tcv_revenue=("tcv_revenue", "sum"),
            line_count=("line_code", "nunique"),
            lobs=("lob", lambda s: ", ".join(sorted(set(s.dropna())))),
            portfolios=("portfolio", lambda s: ", ".join(sorted(set(s.dropna())))),
            is_open=("is_open", "first"),
            is_won=("is_won", "first"),
            is_lost=("is_lost", "first"),
            is_qualified=("is_qualified", "first"),
            past_due=("past_due", "first"),
            quarter=("quarter", "first"),
        )
    )
    agg["gm_pct"] = agg["acv_gp"] / agg["acv_revenue"].replace(0, pd.NA)
    return agg


@lru_cache(maxsize=1)
def load_store() -> Store:
    lines = _prep_lines(pd.read_excel(OPP_PATH, sheet_name="Opportunities"))
    movement = _prep_movement(pd.read_csv(MOV_PATH))
    opps = _opportunity_grain(lines)
    from app.semantic.anomalies import load_client_report

    if not ANOM_PATH.exists():
        raise FileNotFoundError(f"Client anomaly report not found at {ANOM_PATH}")
    anomalies = load_client_report(ANOM_PATH, opps, lines)
    return Store(lines=lines, movement=movement, opportunities=opps, anomalies=anomalies)


def reload() -> Store:
    from app.semantic.precompute import cached_ask_pack

    load_store.cache_clear()
    cached_ask_pack.cache_clear()
    return load_store()
