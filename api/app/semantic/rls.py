from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class Principal:
    key: str
    name: str
    role: str
    lens: str
    scope_label: str
    owner: str | None = None
    predicate: dict[str, str] = field(default_factory=dict)

    def apply_lines(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df
        for col, val in self.predicate.items():
            out = out[out[col] == val]
        if self.owner:
            out = out[out["owner"] == self.owner]
        return out

    def apply_opps(self, df: pd.DataFrame) -> pd.DataFrame:
        return self.apply_lines(df)


PERSONAS: dict[str, Principal] = {
    "executive": Principal(
        key="executive",
        name="Vikesh",
        role="Tells the North America pipeline story to entity stakeholders.",
        lens="TLDR, coverage vs plan, and the three decisions that cannot wait.",
        scope_label="North America · all LOBs",
    ),
    "sales": Principal(
        key="sales",
        name="Account executive",
        role="Works the book every day — stages, slips, and what to do this week.",
        lens="My open book, at-risk deals, and the next recommended action.",
        scope_label="North America · my book",
        # Bound at request time to a representative owner so RLS is visible.
    ),
    "manager": Principal(
        key="manager",
        name="Sales manager",
        role="Benchmarks the team, spots systematic mistakes, coaches upsell.",
        lens="Rep patterns, anomaly concentration, and training opportunities.",
        scope_label="North America · sales team",
    ),
}

DEFAULT_PERSONA = "sales"


def resolve(persona: str | None, owner: str | None = None) -> Principal:
    key = (persona or DEFAULT_PERSONA).lower()
    if key not in PERSONAS:
        key = DEFAULT_PERSONA
    p = PERSONAS[key]
    if key == "sales":
        return Principal(
            key=p.key,
            name=p.name,
            role=p.role,
            lens=p.lens,
            scope_label=f"North America · {owner}" if owner else p.scope_label,
            owner=owner,
        )
    return p
