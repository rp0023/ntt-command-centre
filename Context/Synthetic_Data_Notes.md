# NA Synthetic SFDC Data — Generation Notes

_Updated after validating against the "NTT Agentic Pipeline Intelligence Data Walkthrough"
transcript (2026-09-09) and the "Synth Data & Insights approach Validation" transcript
(2026-09-11). Each call is the ground-truth source for anything it explicitly states —
where a later call conflicts with an earlier one or with the Excel/Word docs, the most
recent explicit statement wins._

## Round 2 changes (2026-09-11 call) — dates, contract term, and budget methodology
- **CreateDate is now 1 Jan – 31 Aug 2026; CloseDate is now 1 Apr – 31 Dec 2026** (both
  single-year, not the earlier multi-year 2024-2027 spread). Per Praveen: CreateDate covers
  the prior FY's Q4 plus the current FY's first two quarters (NTT's fiscal year starts in
  April — "FI26 ... is from April to now"); CloseDate covers the current FY's first three
  quarters ("you always look at 3 quarters of pipeline"). **CloseDate ≥ CreateDate is now a
  hard rule with zero exceptions** ("make sure the close date is always after created
  date") — the earlier "close before create" anomaly has been removed entirely, and the
  earlier "stale opportunity" anomaly (which shifted CreateDate 18-30 months back) was also
  removed since it no longer fits this window; "stalled" pipeline is now represented only in
  the Movement table (no recent updates), not by distorting the fact table's dates.
- **`Quarter` now uses NTT's fiscal calendar** (April-start), e.g. `FY26-Q1` = Apr-Jun 2026.
  Only 3 values ever appear (`FY26-Q1/Q2/Q3`) since CloseDate never falls in Jan-Mar.
- **ContractTermMonths is null for every portfolio except SDIS.** Praveen: "product is a
  one-time sale, there's no term for it... the technology side of business, product and
  technical services, is all about deployment... VBR will not have any duration... SDIS will
  have term, 12 months, 30 months, whatever." So Product/Technical Services/VBR/Consulting
  Services always have TCV = ACV (no term multiplier); only SDIS lines get a real term
  (12/18/24/30/36 months, weighted). This is the one other approved exception to "no blanks"
  besides AccountGroup, per your explicit instruction this round.
- **Budget rebuilt as a proper Country → LOB → Portfolio hierarchy, tracked for both
  Revenue and GP** (previously LOB and Portfolio were two independent flat breakdowns of the
  same total, and only GP was tracked). Now `LOBPortfolioQuarterlyBudget_ACVRevenue` /
  `_ACVGp` give the actual nested cell for each row's own (Quarter, LOB, Portfolio)
  combination, replacing the old `PortfolioQuarterlyBudget_ACVGP` / `LOBQuarterlyBudget_ACVGP`
  columns — matching "budget is like 200 million, distributed by 4 LOBs... within
  networking, the portfolios add up." Revenue/Portfolio splits use **$ revenue share**
  (not the # Opp count share used for category sampling — a dollar budget should follow
  dollar mix). GP per cell is derived from Revenue using the rough margin targets Praveen
  gave for budgeting specifically: Product ~8%, SDIS ~25%, VBR ~3%, Technical
  Services/Consulting ~30% ("services GP should be around 30%") — these are deliberately
  different from the historical actual GM% used for line-level generation, since Praveen
  drew an explicit distinction between budget *targets* and historical *actuals*.
  The period budget is set **once** (anchored to this dataset's own total Closed/Won revenue
  ×1.2 stretch, since Praveen's own ~$1,000M/~18% figures are company-wide and would dwarf a
  ~2,050-opportunity NA POC sample) and rolled down through a fixed, mild seasonality curve
  across quarters/months — not re-randomized independently per quarter as before ("budget by
  month, then the quarter rolls up").

## Files
1. **`NA_Synthetic_SFDC_Opportunities.xlsx`** (~3,030 rows, one row = one Opportunity Line) —
   the primary deliverable. Sheet `Opportunities` is the fact table, denormalized with
   quarterly/monthly KPI, Budget, Gap and RAG columns. Sheet `Distribution Comparison`
   checks the synthetic categorical mix against the input workbook's given distribution
   (see "Distribution validation" below) — mirrors the structure of the input workbook's
   own Excel/Distrbution tab. `NA_Synthetic_SFDC_Opportunities.csv` is kept alongside as
   the same data in flat-file form for tools that don't read `.xlsx`.
2. **`NA_Synthetic_SFDC_Opportunity_Movement.csv`** (~38,500 rows) — a field-level change
   log per opportunity (Stage, ForecastCategory, Confidence, ACV Revenue/GP, CloseDate:
   old value → new value → timestamp → changed by). This is the table the transcript says
   the real anomaly-detection use cases actually run on (stalled deals, backward regression,
   value shrinkage, stage skipping, rep behavioral patterns).
3. **`Anomaly_Ground_Truth.csv`** (~170 rows) — which opportunities were seeded with which
   movement anomaly. **This is a DS-testing aid, not part of the "real" data** — a live SFDC
   export would never have a ground-truth label column. Use it to score your detection
   model's precision/recall; don't feed it into feature engineering.

## Distribution validation (2026-09-10)
Checked the synthetic `Opportunities` data's categorical mix (Stage, ForecastCategory, LOB,
Portfolio) against the input workbook's own "Distrbution" tab — see the `Distribution
Comparison` sheet. This caught and fixed a real bug: LOB and Portfolio had been sampled
using the tab's **$ ACV Revenue share** (e.g. VBR = 0.35% of lines) instead of its **# Opp
count share** (VBR is actually ~11.8% of *lines*, just low-value-per-line — high count, low
revenue, which also explains its 98% GM%). A categorical frequency distribution should
match record counts, not dollar-weighted share, so this was corrected. Random per-record
sampling was also replaced with **quota allocation** (exact integer counts matching the
given proportions, then shuffled) for Stage, ForecastCategory, LOB and Portfolio, removing
residual sampling noise that pure random draws leave at this sample size. Result: every
category now matches the given distribution to within 0.1 percentage points (was up to ~2pp
before). The $ revenue-share distribution is also reproduced (not just the category mix) via
per-category average-deal-size multipliers derived from the tab (revenue share ÷ count
share) — see `LOB_REL_SIZE` / `PORTFOLIO_REL_SIZE` in the generation script.

## Scope
- Region fixed to `North America` (Country = United States 85% / Canada 15%), per the
  transcript ("in North America we broadly have United States and Canada").
- Fact-table grain: **Opportunity Line**. One OpportunityCode can have multiple
  OpportunityLineCodes — one per offering (product line, technical services line, SDIS
  line, etc.), exactly as Praveen described. Opportunity-level fields (Account*, Stage,
  ForecastCategory, Confidence, dates, Owners, OrderType) repeat across all lines of the
  same opportunity; line-level fields (LOB, Portfolio, ACV/TCV) vary per line.
- 2,050 opportunities across 650 accounts (361 with 2+ opportunities via power-law reuse),
  70 sales reps.

## Corrections made after the transcript (these override the earlier build)
- **LOB reduced to the 4 real values**: Networking, Security, Data Center, Digital
  Workplace (Customer Experience folds into Digital Workplace). Praveen was explicit:
  "we within our business have 4 LOBs." The Distribution tab's 7-value breakdown was
  merged down into these 4, preserving relative weight.
- **Portfolio reduced to the 5 real values**: Product, Technical Services, SDIS, VBR,
  Consulting Services — matching the "sub-portfolio" hierarchy Praveen walked through
  (Product → hardware/software, Technical Services, SDIS, Technology Consulting) plus VBR
  from the dictionary. The Distribution tab's 6-value breakdown was merged down into these.
- **OrderType is New Business / Renewal / Expansion** (50/40/10 weighted). The transcript
  only mentioned "new and renew" verbally, but the written follow-up doc (`ntt meta
  data.docx`, which is confirmed to be the promised follow-up email content) explicitly
  lists all three as the MVP consideration example, so it takes precedence as the more
  authoritative documented source — Expansion is kept as a genuine minority value rather
  than dropped.
- **ForecastCategory is no longer a fixed lookup from Stage** for the middle stages.
  Praveen: "it is not like every opportunity in Proposal will be mapped only to Commit —
  it can be either Commit or Best Case," and "Finalist is *definitely* mapped to Commit,
  sometimes Proposal is also mapped to Commit." So Proposal/Proposal Evaluation/Finalist
  now draw from a realistic probability distribution over categories as **normal
  generation logic**, not an anomaly. Identification, Requirements Definition, Deal Won,
  and Deal Lost remain (near) deterministic, per Praveen's explicit "if Requirements
  Definition were Commit, that'd be wrong" — only ~0.5% of those get a genuine violation,
  matching his "there will be one exception, but that's not the norm."
- **Confidence is jittered**, not an exact 0/20/40/60/80/100 — it's manually keyed by the
  rep, so it varies around the stage's typical anchor.
- **AccountGroup is legitimately blank ~67% of the time.** Praveen: "it will be blank for
  some of the rows" — the sibling-account de-dup mapping isn't always done. This is the one
  intentional exception to the "no blanks" rule, per your explicit sign-off, because it's
  how the client says the real field behaves. Every other column is fully populated.
- ~~ContractTermMonths correlates with Portfolio: Product always 12-month, multi-year terms
  on Technical Services/SDIS/Consulting/VBR~~ — **superseded in Round 2 below**: only SDIS
  has a term at all; every other portfolio is null/one-time.

## Rules still followed as before
- Stage progression order (Identification → Requirements Definition → Qualification →
  Proposal → Proposal Evaluation → Finalist → Deal Won/Lost) and the 8-value stage mix
  weighted from the Distribution tab's `# Opp` counts.
- TCV = ACV for one-time lines, TCV = ACV × term for SDIS's term-bearing lines (see Round 2
  above for which portfolios get a term at all).
- Budgets never exist at account level — "Accounts don't have budget, simple as that." KPI
  formulas (Gap, TP, QP, Closed+Commit, RAG thresholds) computed per quarter/month and joined
  back onto every row (denormalized, as you asked). Budget is still a synthetic target
  (no exact current-year actuals were ever provided) — treat RAG outcomes as illustrative,
  though the *method* (Country → LOB → Portfolio, Revenue + GP, annual-then-rolldown) is now
  aligned with how NTT says it's actually done (see Round 2).

## Movement/History table — what's in it
For each opportunity: a simulated timeline of Stage, ForecastCategory (+ Confidence),
ACV Revenue/GP, and occasional CloseDate-slip changes from creation to its final recorded
state, attributed to the Opportunity Owner. Amount fields start at `0 → initial estimate`,
mirroring Praveen's own example ("amount was 0, but it has become 550,000").

Seeded anomalies (named directly in the transcript), listed in `Anomaly_Ground_Truth.csv`:
- **stage_skip** (~4% of eligible opportunities) — the log jumps straight from an early
  stage to a much later one, skipping the intermediate stage-change entries ("opportunities
  which skipped all stages").
- **stalled** (~8% of open opportunities, biased toward higher-value ones) — no field
  changes logged in the last 60-150 days despite being open, mirroring "an opportunity
  contributing 20% of a region's target that hasn't moved for 60 days."
- **backward_regression** (concentrated in 2 specific reps, chosen fresh each regeneration
  run from the most active reps — check the current run's console output or filter
  `Anomaly_Ground_Truth.csv` for `backward_regression`; rare elsewhere) — ForecastCategory
  logged moving backward (e.g. Commit → Best Case) instead of only progressing forward,
  matching "a particular person putting them in commit and then after a week it comes back
  to best case."
- **value_shrinkage** (concentrated in 2 other specific reps, same selection approach as
  above; rare elsewhere) — the logged deal value starts 3-5x the final closed/settled value
  and shrinks over successive revisions, matching "when we logged it... it was really large
  value, but
  by the time we closed, it became one-third or one-fifth of what it was... if there's a
  pattern to it, every time this guy does the same thing, it's a problem." Using only 2
  reps per pattern is deliberate — it's what makes the behavioral pattern statistically
  findable by grouping on `ChangedByFullName`.

## Known simplifications / open items
- `AccountIndustry` categories and proportions are still invented (only "Public Sector" was
  ever given as an example) — not addressed by the transcript.
- Company names are synthetic, not real entities.
- The transcript mentions ~20-22 "GMNC" (Global Multinational) accounts that DO have
  account-level budgets, and a deeper Portfolio hierarchy (Service Division → Category →
  Subcategory, e.g. product hardware vs. software). Both were explicitly deferred by the
  client on the call ("let's not get into that level of detail") — not modeled here.
- The promised follow-up email content is `ntt meta data.docx` (already reconciled — its
  Region/LOB/Portfolio text matches word-for-word what the corrections above already used,
  which cross-confirms those corrections; its Stage/Confidence/ForecastCategory table is
  used as the majority/anchor mapping per stage, with the realistic rep-judgment variance
  Praveen described verbally layered on top for Proposal/Proposal Evaluation/Finalist; its
  OrderType example values (New Business/Renewal/Expansion) are used as authoritative over
  the transcript's simpler verbal "new and renew").
- **RAG reads mostly Red for `FY26-Q3`** in the current run — that's expected, not a bug:
  `TODAY` (2026-09-15) falls inside `FY26-Q2`, so `FY26-Q3` (Oct-Dec) hasn't happened yet and
  has zero Closed/Won, leaving its full budget as Gap. Also note only ~11.5% of records sit
  in an active/open stage at all (the given Stage distribution is dominated by Deal
  Lost/Deal Won), so Total/Qualified Pipeline is naturally thin relative to a budget
  calibrated off Closed/Won — this mirrors Praveen's own point that thin win rates mean "3x
  is not sufficient... the pipeline should be much more than 3x." Don't read the RAG mix as
  something to tune toward "looks healthier" — it falls out of the given distribution.
- The exact **budget stretch factor (1.2x Closed/Won revenue)**, **seasonality curve**, and
  **portfolio budget-GM% targets** (8/25/3/30/30%) are reasonable interpretations of
  admittedly rough, verbally-given numbers ("something like this to make it real," "I don't
  know the distribution for services and product") — flag if NTT sends firmer figures.
