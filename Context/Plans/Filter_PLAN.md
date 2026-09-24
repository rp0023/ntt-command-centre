# Move Filters to Their Relevant Page Sections

## Summary

Remove the full-width filter deck above every page. Place filter controls beside the chart or table that represents the selected dimension, while keeping their existing page-wide behavior.

- Every selection continues to refetch and recompute the complete page.
- Active filters move directly below the page heading.
- Dimensions without a natural chart location remain available through a compact **More filters** popover.
- Profit/Revenue moves beside the page question.
- Existing URLs, role scope, calculations, chart clicks, and filter values remain compatible.

## Interface and Data Changes

Add contextual dimensions to chart specifications:

```ts
interface ChartSpec {
  // existing fields
  filterDims?: DimKey[];
}
```

`filterDims` identifies dimensions represented by that chart and suitable for controls in its header. It does not change `clickDim`; chart marks retain their existing filtering behavior.

Author these relationships in the semantic layer:

| Context | Filter dimensions |
|---|---|
| Stage breakdown, funnel, and stage flow | `stage` |
| Overdue stack | `forecast` |
| Margin mix and coverage grid | `lob`, `portfolio` |
| Industry flow | `industry`, `lob` |
| Account treemap, whitespace table, and account growth list | `account` |
| Stalled pipeline and rep benchmark | `rep` |
| Plan bridge and monthly plan chart | `quarter` |
| LOB or portfolio coverage bullets | Their corresponding dimension |
| Other charts | No contextual selector |

Derived chart filters such as `riskBand` and `anomalyCategory` remain available through their clickable marks and active chips because `/api/meta` does not provide selector values for them.

## Implementation Changes

- Remove the shell-level `FilterBar` from `App`.
- Pass scoped metadata into `PageView` and introduce reusable filter-field components backed by `/api/meta`.
- Add `setFilter(dim, value)` to the app context for selectors; chart marks and action scopes continue using toggle behavior.
- Render each chart’s `filterDims` as compact, labeled selectors in its header. Include an “All” option that clears that dimension and state clearly that the selection filters the page.
- Add a **More filters** button beside the page heading. Its accessible popover contains persona-permitted dimensions that are not assigned to any displayed chart, plus Clear all.
- Move the Profit/Revenue segmented control into the page heading beside scope and date metadata.
- Move active filter chips from below the action list to immediately below the page heading. Preserve fixed-scope chips, individual removal, Clear all, and server-confirmed values.
- Preserve URL parameters and single-value-per-dimension behavior. Page navigation continues retaining filters; authentication or identity changes continue clearing them.
- On narrow screens, wrap the heading actions and use the More filters popover for space-constrained controls. Maintain touch targets, Escape and outside-click dismissal, focus restoration, keyboard access, both themes, and reduced-motion behavior.
- Update loading skeletons after removing the shell filter deck.
- Update the README and business/user-flow documentation to describe contextual page filters, active chips, More filters, and the new measure-switch location.

## Test Plan

- Verify every `filterDims` entry is a registered dimension, permitted for the current persona, and has scoped values in metadata.
- Verify every persona-permitted dimension appears either contextually or in More filters, without duplication.
- Confirm contextual selectors, More filters, chart clicks, action scopes, chip removal, and Clear all produce the expected URL and server request.
- Confirm any selection refreshes banners, narrative inputs, actions, charts, and page-specific content together.
- Verify changing one value replaces the previous value for that dimension and “All” clears it.
- Verify `riskBand` and `anomalyCategory` chart filtering remains functional.
- Test Profit/Revenue switching, deep-link restoration, page navigation, role changes, and row-level scope.
- Keyboard-test selectors and the More filters popover, including focus restoration and Escape.
- Check desktop, tablet, and mobile layouts in light and dark themes.
- Run the frontend production build, semantic verification suite, authentication tests, and browser walkthroughs for Sales, Manager, and Executive accounts.

## Assumptions

- Contextual filters continue to affect the whole page so percentages and denominators remain consistent.
- More filters contains only dimensions not already exposed by a chart on the current page.
- Native scoped selector values remain sourced from `/api/meta`; no client-side aggregation or filtering is introduced.
- This changes filter placement and presentation without changing business calculations or supporting multiple simultaneous values for one dimension.
