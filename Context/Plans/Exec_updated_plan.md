# Minimal Executive Experience with Actions Center

## Summary

Replace the current six-page Executive dashboard with five focused tabs built around the three messages introduced in the Brief:

1. **Brief** — What needs attention?
2. **Opportunities** — Which plays are ready to run?
3. **Anomalies** — What looks unusual enough to investigate?
4. **Closure Risk** — Which commitments are least likely to close?
5. **Actions Center** — What is owned, due, or waiting?

Remove Executive plan bridges, coverage gaps, margin/profit reporting, business-structure pages, generic charts, and LOB/industry analysis. Keep Revenue only where it materially helps prioritize a closure decision.

Sales and Manager experiences remain unchanged.

## Executive Information Design

- **Brief**
  - Show three deterministic message panels: Opportunities, Anomalies, and Closure Risk.
  - Each contains one conclusion, up to three operational signals, and a link to its dedicated tab.
  - Show only the top three cross-domain actions below them.
  - Remove metric-banner groups, default AI narrative, charts, plan tables, and model-detail blocks.
- **Opportunities**
  - Show the same Opportunities message and signals used on Brief.
  - Present up to five ranked plays with offering, customer count, owner count, confidence, strongest pilot account, and recommended next step.
  - Omit peer-GP estimates because no equivalent revenue estimate exists.
- **Anomalies**
  - Show the same Anomalies message and signals used on Brief.
  - Present a prioritized finding list with severity, affected entity, detector agreement, evidence, responsible owner, and investigation question.
  - Do not display GP-based value-at-stake.
- **Closure Risk**
  - Show the same Closure Risk message and signals used on Brief.
  - Present up to ten exceptions with deal, account, owner, risk band, score, closure probability, main driver, close date, silence duration, and ACV GP where useful.
  - Keep the weak-model disclosure visible and describe the model as directional.
- **Actions Center**
  - Show actions generated only from Opportunities, Anomalies, and Closure Risk.
  - Use a single compact list with theme, priority, owner, due date, current status, next step, and optional Revenue impact.
  - Filter by theme, status, priority, and owner. Sort by priority or due date; remove value-at-stake sorting.
  - Domain pages link directly to the corresponding expanded action with `?page=action-center&action=<key>`.

## Contracts, Navigation, and State

- Replace the Executive page registry with `tldr`, `opportunities`, `anomalies`, `closure-risk`, and `action-center`.
- Redirect legacy Executive URLs:
  - `growth` → `opportunities`
  - `risks` → `anomalies`
  - `actions` → `action-center`
  - `performance` and `structure` → `tldr`
- Add a typed Executive payload containing:
  - Canonical `messages` shared by Brief and detail pages.
  - Ranked opportunity plays, anomaly findings, or closure exceptions as appropriate.
  - Executive actions tagged with `theme: opportunities | anomalies | closure`.
  - Optional Revenue impact; no GP, margin, coverage, budget, or profit-plan fields.
- Build the three canonical messages once in the semantic layer and reuse the same headline, summary, and signals on Brief and the matching detail page.
- Remove charts from all Executive pages and suppress the generic metric banners, AI panel, and full ActionRail there. Keep the floating Ask entry point.
- Fix the Executive measure to Revenue and remove the Profit/Revenue switch. Reject Executive Ask requests for profit, margin, GP plan, gap, or coverage data.
- Limit cross-page Executive scope controls to Country and Quarter. Use local list controls for risk band, stage, owner, severity, detector agreement, theme, and action status.
- Ensure Executive deal details and API payloads omit GP fields and profit wording. Internal algorithms may continue using source GP where required, but it must not be serialized or presented to the Executive.
- Replace existing Executive coverage and concentration actions with a maximum of four stable actions per message domain, deduplicated by entity or play.
- Persist Actions Center decisions in browser local storage, namespaced by authenticated identity:
  - Store action key, chosen option, resulting status, optional reason, and update timestamp.
  - Default unseen actions to `New`.
  - Require a reason for options marked `needsReason`.
  - Merge stored state only into currently returned actions; retain dormant entries if an action later reappears.
  - Display “Saved in this browser” so the demo does not imply CRM write-back.
  - Logout must not erase action history, and another account must never see it.

## Test Plan

- Verify Executive navigation contains exactly five tabs and legacy URLs redirect correctly.
- Verify Sales and Manager pages, measures, filters, and actions remain unchanged.
- Confirm every Brief message exactly matches the headline and signals on its destination page.
- Assert Executive payloads and visible copy contain no GP, gross-profit, margin, budget, coverage, gap, or profit-plan fields; Revenue appears only in Closure Risk and relevant actions.
- Confirm all Executive pages return no generic charts and render only their focused message, worklist, and relevant actions.
- Test opportunity, anomaly, and closure empty states without adding substitute charts or invented financial values.
- Verify Actions Center filtering, due-date ordering, deep links, reason validation, reload persistence, logout/login persistence, and isolation between accounts.
- Confirm Executive Ask refuses excluded profit questions and Executive deal details omit profit data.
- Browser-test all five tabs at desktop and mobile widths in both themes, including keyboard navigation and action focus restoration.
- Run the frontend production build, semantic regression suite, authentication/scope tests, and update the business-flow and application documentation to the new 14-page total.

## Assumptions

- “Excluding profits views or data” applies to all Executive UI, Executive API payloads, deal details, and Ask responses.
- Revenue is shown only when it helps prioritize a concrete closure decision; Opportunities and Anomalies remain operational and count-based.
- The Actions Center is a browser-persistent demo workspace and does not write to Salesforce or the server.
- The three Brief messages are deterministic semantic-layer content rather than LLM-generated copy.
