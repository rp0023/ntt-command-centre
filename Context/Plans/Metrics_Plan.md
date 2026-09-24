# Replace KPI Cards with Metric Summary Banners

## Summary

Replace the separate KPI cards on all 15 Sales, Manager, and Executive pages with three curated insight banners:

- One full-width primary banner containing the page’s main conclusion.
- Two half-width supporting banners underneath.
- All five or six existing metrics remain visible and individually clickable.
- Metric calculations, filtering, role scope, measure switching, and Ask interactions remain unchanged.
- Banner wording is deterministic and authored in the semantic layer; no LLM generates KPI copy.

## Implementation Changes

### Banner data contract

Keep the existing `kpis` array for metric values and compatibility. Add `metricBanners` to each view payload:

```ts
interface MetricBanner {
  key: string;
  prominence: "primary" | "supporting";
  tone: Tone;
  statement: Array<
    | { kind: "text"; text: string }
    | { kind: "metric"; metricKey: string }
  >;
  subline: string;
  trendMetricKey?: string | null;
}
```

- Metric segments obtain their displayed value, tone, label, direction, subtext, and popover content from the matching KPI.
- Every KPI key must appear in exactly one banner statement.
- `trendMetricKey` may reference only a KPI with at least three real sparkline points. Otherwise the trend area is omitted.
- The banner tone is explicitly selected when its copy is authored; it is never inferred in the browser.
- Unknown or duplicate metric references fail semantic verification rather than silently disappearing.

### Curated page summaries

Create three banners per page with these fixed groupings and statement intentions:

| Page | Primary banner | Supporting banner 1 | Supporting banner 2 |
|---|---|---|---|
| My day | Calls needed + value at risk | Customer calls + past-due value | Open pipeline + typical silence |
| My deals | Past-due + stalled value | Slipped dates + shrunk deals | Worst risk score + open pipeline |
| My accounts | Customer count + one-line customers | Biggest customer contribution | Growth ideas + best opening |
| My record | Win rate + won value | Deals closed + average win | Sales cycle + usual loss stage |
| Pod pulse | Reps to coach + deals to chase | Value at risk + team pipeline | Stalled share + team win rate |
| Rep benchmark | Reps outside pattern + furthest outlier | Win-rate spread + team win rate | Biggest book + rep count |
| Process | Deals started + final-stage conversion | Win rate + skipped stages | Sales cycle + lost deals |
| Calibration | Oversizing + undersizing + reversals | Shrunk deals + stalled share | Team win rate |
| Pod whitespace | Missing-line upside + best opening | Four-line customer value lift | Assignable ideas + repeating plays |
| Executive brief | Won value + pipeline coverage | Open pipeline + value at risk | Largest customer + margin |
| Performance | Won value + plan attainment | Coverage + current-quarter delivery | Next-quarter gap + best month |
| Structure | Revenue + margin | Largest customer + top-five concentration | Largest industry + largest line |
| Risks | Money involved + findings + critical findings | Pipeline at risk + people flagged | Upside findings |
| Growth | Repeatable plays + biggest play | Growth ideas + confidence | Peer value + owners to brief |
| Actions | Decisions + critical decisions + money involved | Empty targets + coverage | Opportunities to sell |

The copy builder will use the server-formatted KPI values inside short business sentences, while each banner subline combines the existing explanatory text without introducing new calculations.

### Frontend presentation

Replace `KpiRow` in the page template with a `MetricBannerGroup`:

- Desktop: primary banner spans the full width; supporting banners form a two-column row.
- Mobile and narrow tablet: all three banners stack in reading order.
- Use the reference treatment: restrained surface, thin border, tone-colored left rule, large statement, muted supporting line, and compact optional trend on the primary banner.
- Remove tile icons, raised-card effects, and the six-column KPI grid.
- Render metric statement segments as inline buttons. Selecting one opens the existing KPI detail popover with its label, value, explanation, direction, and “Ask about this number” action.
- Preserve Escape, outside-click dismissal, focus restoration, touch targets, screen-reader announcements, and selected-state behavior.
- Update loading skeletons to one wide banner and two supporting banners.
- Render missing values as the existing `—` value and page-authored empty wording; never invent a zero or trend.
- Support both themes through existing color tokens and respect reduced-motion settings.

### Documentation and compatibility

- Update the page-flow documentation from “KPI cards” to “curated metric summary banners.”
- Keep the existing KPI schema during this migration so calculations, tests, Ask prompts, and possible API consumers remain compatible.
- Update stale component documentation that refers to fourteen pages or a six-tile layout.

## Test Plan

- Verify all 15 pages return exactly three banners and that every returned KPI is referenced exactly once.
- Verify banner references use valid KPI keys, trend references contain real history, and server-formatted values appear unchanged.
- Confirm role and row-level scope, filters, and GP/revenue switching update both KPI values and banner statements without stale content.
- Test five-metric pages (`my-accounts` and `pod-whitespace`) and empty-data states.
- Keyboard-test every inline metric: focus, Enter/Space, popover focus, Ask action, Escape, outside click, and focus restoration.
- Check primary/supporting layout at desktop, tablet, and mobile widths in light and dark themes.
- Update the page skeleton and confirm it does not shift materially when banners load.
- Run the frontend production build, semantic regression suite, authentication/scope tests, and browser walkthroughs for Sales, Manager, and Executive roles.

## Assumptions

- “Banner” means the one-primary-plus-two-supporting hierarchy shown in the first screenshot.
- All current metrics remain visible; summarization changes their presentation and wording, not the underlying measures.
- Existing metric popovers and Ask behavior remain available through clickable inline values.
- Banner summaries are deterministic server-authored content and do not require model availability.
