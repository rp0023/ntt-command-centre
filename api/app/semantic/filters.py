from __future__ import annotations

from typing import Any

import pandas as pd

from app.semantic.loader import Store
from app.semantic.rls import Principal


def apply_filters(df: pd.DataFrame, filters: dict[str, Any] | None) -> pd.DataFrame:
    if not filters:
        return df
    out = df
    mapping = {
        "countries": "country",
        "lobs": "lob",
        "portfolios": "portfolio",
        "stages": "stage",
        "forecasts": "forecast_category",
        "orderTypes": "order_type",
        "owners": "owner",
        "quarters": "quarter",
        "industries": "industry",
    }
    for key, col in mapping.items():
        vals = filters.get(key) or []
        if vals and col in out.columns:
            out = out[out[col].isin(vals)]
    search = (filters.get("search") or "").strip()
    if search:
        needle = search.lower()
        cols = [c for c in ("opportunity_name", "account_name", "opportunity_code", "owner") if c in out.columns]
        if cols:
            mask = False
            for c in cols:
                mask = mask | out[c].fillna("").astype(str).str.lower().str.contains(needle, regex=False)
            out = out[mask]
    return out


def slice_lines(store: Store, principal: Principal, filters: dict | None) -> pd.DataFrame:
    return apply_filters(principal.apply_lines(store.lines), filters)


def slice_opps(store: Store, principal: Principal, filters: dict | None) -> pd.DataFrame:
    f = dict(filters or {})
    # Opportunity grain has lobs/portfolios as concatenated strings; LOB/portfolio
    # filters must be applied on lines then rolled up, otherwise we drop mixed-LOB deals.
    line_keys = {}
    for k in ("lobs", "portfolios"):
        if f.get(k):
            line_keys[k] = f.pop(k)
    lines = slice_lines(store, principal, {**f, **line_keys} if line_keys else f)
    codes = set(lines["opportunity_code"].unique())
    opps = principal.apply_opps(store.opportunities)
    opps = opps[opps["opportunity_code"].isin(codes)]
    return apply_filters(opps, f)


def filter_options(lines: pd.DataFrame) -> dict:
    def uniq(col: str) -> list[str]:
        return sorted(lines[col].dropna().astype(str).unique().tolist())

    return {
        "countries": uniq("country"),
        "lobs": uniq("lob"),
        "portfolios": uniq("portfolio"),
        "stages": uniq("stage"),
        "forecasts": uniq("forecast_category"),
        "orderTypes": uniq("order_type"),
        "owners": uniq("owner"),
        "quarters": uniq("quarter"),
        "industries": uniq("industry"),
    }
