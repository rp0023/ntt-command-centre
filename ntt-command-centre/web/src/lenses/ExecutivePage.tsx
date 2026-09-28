import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ExecutiveAction, ExecutivePayload, ExecutiveTheme,
  MetaPayload, Urgency, ViewPayload,
} from "../api/types";
import { MoreFilters } from "../components/FilterBar";
import { longDate, moneyExact, shortDate } from "../lib/format";
import { useApp } from "../state/AppStateProvider";

type SavedDecision = {
  optionKey: string; status: string; reason?: string; updatedAt: string;
};
type DecisionMap = Record<string, SavedDecision>;

const THEME_LABEL: Record<ExecutiveTheme, string> = {
  opportunities: "Opportunities", anomalies: "Anomalies", closure: "Closure Risk",
};
const PRIORITY: Record<Urgency, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 };

// The low-probability list uses a strict <50% rule.  Keep one decimal here so
// a 49.6% prediction is not presented as 50% while still appearing in that list.
function closureProbability(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function ContextAsk({ label, query, overlay = false, text = "Ask" }: { label: string; query: string; overlay?: boolean; text?: string }) {
  const { openAsk } = useApp();
  return <button
    type="button"
    className={`exec-context-ask${overlay ? " exec-context-ask--overlay" : ""}`}
    onClick={(event) => { event.stopPropagation(); openAsk(query); }}
    title={`Ask about ${label}`}
    aria-label={`Ask about ${label}`}
  ><span aria-hidden="true">✦</span>{text}</button>;
}

function BriefModal({ data, open, onClose }: { data: ExecutivePayload; open: boolean; onClose: () => void }) {
  const { setPage, openAction } = useApp();
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const priorOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = priorOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previousFocus.current?.focus();
    };
  }, [open, onClose]);
  if (!open || !data.weeklyBanner) return null;
  return <div className="exec-brief-modal" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="exec-brief-modal__panel" role="dialog" aria-modal="true" aria-labelledby="exec-brief-modal-title">
      <header className="exec-brief-modal__head"><div><p className="exec-eyebrow">Weekly overview</p><h2 id="exec-brief-modal-title">Before I open the workspace</h2></div><button ref={closeRef} type="button" onClick={onClose} aria-label="Close executive overview">×</button></header>
      <article className="exec-brief-modal__hero"><p className="exec-eyebrow">NTT Deal Intelligence · Now</p><h3>{data.weeklyBanner.headline}</h3><p>{data.weeklyBanner.subline}</p></article>
      {data.weeklyBanner.supporting.length > 0 ? (<>
        <p className="exec-brief-modal__divider"><span>One insight and one action from each use case</span></p>
        <div className="exec-brief-modal__cards">{data.weeklyBanner.supporting.map(overview => {
          const insight = data.weeklyInsights.find(item => item.theme === overview.key);
          const summary = insight?.conclusion ?? overview.subline;
          const actionText = insight?.nextStep ?? "Review the evidence and decide the next step.";
          return <article key={overview.key} className={`exec-brief-modal__card exec-brief-modal__card--${overview.tone}`}>
            <div className="exec-brief-modal__card-head">
              <p className="exec-eyebrow">{overview.label}</p>
              <strong className="exec-brief-modal__card-value">{overview.headline}</strong>
            </div>
            <div className="exec-brief-modal__row">
              <div className="exec-brief-modal__copy"><p>{summary}</p>{insight && <ul>{insight.evidence.slice(0, 2).map((line, index) => <li key={index}>{line}</li>)}</ul>}</div>
              <div className="exec-brief-modal__action"><span>Action</span><strong>{actionText}</strong></div>
            </div>
            <div className="exec-brief-modal__buttons"><button type="button" className="exec-evidence-link" onClick={() => { onClose(); setPage(overview.page); }}>View details</button>{insight?.actionKey && <button type="button" className="exec-link exec-link--action" onClick={() => { onClose(); openAction(insight.actionKey!); }}>Open action</button>}</div>
          </article>;
        })}</div>
      </>) : null}
    </section>
  </div>;
}

function BriefLegacy({ data }: { data: ExecutivePayload }) {
  const { setPage, openAction } = useApp();
  const [selectedInsightKey, setSelectedInsightKey] = useState<string | null>(null);
  const selectedInsight = data.weeklyInsights.find(item => item.key === selectedInsightKey);
  const selectedAction = selectedInsight?.actionKey
    ? data.actions.find(action => action.key === selectedInsight.actionKey
      && action.theme === selectedInsight.theme)
    : undefined;
  return <>
    {data.weeklyBanner && <section className="exec-weekly-banners" aria-labelledby="weekly-banner-title">
      <article className={`exec-weekly-banner exec-weekly-banner--primary exec-weekly-banner--${data.weeklyBanner.tone}`}>
        <div className="exec-weekly-banner__copy"><p className="exec-eyebrow">This week</p>
          <h2 id="weekly-banner-title">{data.weeklyBanner.headline}</h2><p>{data.weeklyBanner.subline}</p></div>
        <dl className="exec-weekly-banner__stats">{data.weeklyBanner.stats.map(stat => <div key={stat.label} className={`exec-weekly-banner__stat exec-weekly-banner__stat--${stat.tone}`}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>)}</dl>
      </article>
      {data.weeklyBanner.supporting.length > 0 && data.weeklyBanner.supporting.map(banner => <article key={banner.key} className={`exec-weekly-banner exec-weekly-banner--supporting exec-weekly-banner--${banner.tone}`}>
        <button type="button" onClick={() => setPage(banner.page)} className="exec-weekly-banner__supporting-link"><div className="exec-weekly-banner__copy">
          <p className="exec-eyebrow">{banner.label}</p>
          <h3>{banner.headline}</h3>
        </div></button>
        <details className="exec-info exec-info--brief"><summary aria-label={`Details for ${banner.label}`}>i</summary><div><b>{banner.label}</b><p>{banner.subline}</p></div></details>
      </article>)}
    </section>}
    <section className="exec-section" aria-labelledby="weekly-focus-title">
      <div className="exec-section__head"><div><p className="exec-eyebrow">Five insights, five actions</p><h2 id="weekly-focus-title">What surfaced and what to do about it</h2></div></div>
      <div className={`exec-weekly-layout${selectedInsight ? " exec-weekly-layout--selected" : ""}`}>
        <div className="exec-weekly-cards" role="group" aria-label="Weekly decisions">
          {data.weeklyInsights.map(insight => <button key={insight.key} type="button" className={`exec-weekly-card exec-weekly-card--${insight.theme}${selectedInsight?.key === insight.key ? " is-selected" : ""}`} aria-expanded={selectedInsight?.key === insight.key} onClick={() => setSelectedInsightKey(current => current === insight.key ? null : insight.key)}>
            <span className="exec-weekly-card__top"><span className="exec-weekly-card__theme">{THEME_LABEL[insight.theme]}</span><span className="exec-weekly-card__rank">{insight.rank}</span></span>
            <strong>{insight.title}</strong>
            <span className="exec-weekly-card__conclusion">{insight.conclusion}</span>
            <span className="exec-weekly-card__prompt">{selectedInsight?.key === insight.key ? "Hide details" : "View details"}</span>
          </button>)}
        </div>
        {selectedInsight && <aside className={`exec-weekly-detail exec-weekly-detail--${selectedInsight.theme}`} aria-labelledby="weekly-detail-title">
          <div className="exec-weekly-detail__head"><span>{THEME_LABEL[selectedInsight.theme]} · Decision {selectedInsight.rank}</span><h3 id="weekly-detail-title">{selectedInsight.title}</h3></div>
          <p className="exec-weekly-detail__conclusion">{selectedInsight.conclusion}</p>
          <section className="exec-weekly-detail__evidence" aria-labelledby="weekly-detail-evidence"><h4 id="weekly-detail-evidence">Evidence</h4><ul>{selectedInsight.evidence.map((line, index) => <li key={`${selectedInsight.key}-evidence-${index}`}>{line}</li>)}</ul></section>
          <section className="exec-weekly-detail__action" aria-labelledby="weekly-detail-action"><h4 id="weekly-detail-action">Recommended action</h4>
            {selectedAction ? <><p>{selectedAction.description}</p><strong>{selectedAction.nextStep}</strong><span>{selectedAction.owner} · due {selectedAction.dueDate}</span></> : <p>{selectedInsight.nextStep}</p>}
          </section>
          <div className="exec-weekly-detail__buttons"><button type="button" className="exec-evidence-link" onClick={() => setPage(selectedInsight.page)}>See evidence</button>{selectedAction && <button type="button" className="exec-link" onClick={() => openAction(selectedAction.key)}>Take action</button>}</div>
        </aside>}
      </div>
    </section>
  </>;
}

function Brief({ data }: { data: ExecutivePayload }) {
  const { setPage, openAction } = useApp();
  const banner = data.weeklyBanner;
  if (!banner) return <BriefLegacy data={data} />;
  return <>
    <section className="brief-template" aria-labelledby="brief-template-title">
      <header className="brief-template__hero">
        <h2 id="brief-template-title"><span>{banner.headline.split(" ")[0]}</span>{banner.headline.slice(banner.headline.indexOf(" "))}</h2>
        <p>{banner.subline}</p>
        <ContextAsk label="this week's brief" text="What needs my attention?" query={`Explain this week's executive brief: ${banner.headline}. ${banner.subline} Walk through the five surfaced insights, their associated revenue, and the actions that should be prioritised first.`} />
      </header>
      <div className="brief-template__themes">{banner.supporting.map(item => <button key={item.key} type="button" onClick={() => setPage(item.page)} className={`brief-template__theme brief-template__theme--${item.tone}`}><span>{item.label}</span><strong>{item.headline}</strong></button>)}</div>
      <div className="brief-template__label"><span>Five insights, five actions</span><span>Left: what the agent surfaced. Right: what I do about it.</span></div>
      <div className="brief-template__rows">{data.weeklyInsights.map(insight => {
        const action = insight.actionKey ? data.actions.find(item => item.key === insight.actionKey) : undefined;
        return <article key={insight.key} className={`brief-template__row brief-template__row--${insight.theme}`}>
          <button type="button" className="brief-template__insight" onClick={() => setPage(insight.page)}><span className="brief-template__pill">{THEME_LABEL[insight.theme]}</span>{action?.formattedRevenueImpact && <b className="brief-template__revenue">{action.formattedRevenueImpact}</b>}<strong>{insight.title}</strong><p>{insight.conclusion}</p><small>{insight.evidence[0]}</small></button>
          <div className="brief-template__action"><span>The action</span><strong>{action?.nextStep ?? insight.nextStep}</strong>{action && <small>{action.owner} · {action.dueDate}</small>}<div className="brief-template__action-buttons"><ContextAsk label={insight.title} query={`Explain the weekly insight “${insight.title}”. Conclusion: ${insight.conclusion}. Evidence: ${insight.evidence.join("; ")}. Recommended next step: ${action?.nextStep ?? insight.nextStep}${action?.formattedRevenueImpact ? `. Associated revenue: ${action.formattedRevenueImpact}` : ""}.`} /><button type="button" className={`exec-link${action ? " exec-link--action" : ""}`} onClick={() => action ? openAction(action.key) : setPage(insight.page)}>{action ? "Open action" : "See detail"}</button></div></div>
        </article>;
      })}</div>
    </section>
  </>;
}

function Opportunities({ data }: { data: ExecutivePayload }) {
  const { openAction } = useApp();
  const overview = data.opportunityOverview;
  return <><section className="exec-domain-overview" aria-labelledby="opportunity-overview-title">
    <div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Cross-sell and upsell overview</p><h2 id="opportunity-overview-title">Where a repeatable customer play is visible</h2></div><ContextAsk label="growth-play overview" text="What should we pilot first?" query={`Explain the growth-play overview: ${overview.recommendations} recommendations across ${overview.accounts} accounts, ${overview.repeatablePlays} repeatable plays, and a ${overview.formattedPeerRevenueBenchmark} peer-based revenue benchmark. Identify the strongest evidence and the best pilot to run next.`} />
      <details className="exec-info"><summary aria-label="How opportunity recommendations are calculated">i</summary><div><b>How this is calculated</b><p>Recommendations come from the supplied cross-sell model. A repeatable play is the same offering recommended for at least two accounts. The revenue benchmark sums the source-reported peer-won revenue reference for the {overview.repeatableRecommendations} recommendations in these plays. {overview.singleAccountRecommendations} single-account recommendations are disclosed in the totals but are not promoted as repeatable plays. This benchmark is not pipeline, projected upside, or a forecast.</p></div></details>
    </div>
    <div className="exec-domain-leads"><div><strong>{overview.recommendations}</strong><span>recommendations across {overview.accounts} accounts</span></div><div><strong>{overview.repeatablePlays}</strong><span>repeatable plays{overview.topPlay ? ` · ${overview.topPlay} leads across ${overview.topPlayAccounts} accounts` : ""}</span></div></div>
    <div className="exec-domain-stats"><div><strong>{overview.accounts}</strong><span>Accounts</span></div><div><strong>{overview.recommendations}</strong><span>Source recommendations</span></div><div><strong>{overview.repeatableRecommendations}</strong><span>Recommendations in plays</span></div><div><strong>{overview.strongRecommendations}</strong><span>High / very high</span></div><div><strong>{overview.repeatablePlays}</strong><span>Repeatable plays</span></div><div><strong>{overview.formattedPeerRevenueBenchmark}</strong><span>Peer-based revenue benchmark</span></div></div>
  </section>
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">Ranked worklist</p><h2>Plays ready for a pilot</h2></div><span>{data.opportunityPlays.length} shown</span></div>
      <div className="exec-list">{data.opportunityPlays.map((p, i) => { const action = data.actions.find(item => item.key === `opportunity:${p.key}`); return <article className="exec-row exec-row--with-action exec-row--growth-play" key={p.key}>
        <div className="exec-rank">{i + 1}</div><div className="exec-row__main exec-askable"><h3>{p.offering}</h3><p>{p.reason}</p><strong>{p.pilotAccount}</strong><ContextAsk label={p.offering} overlay query={`Explain the ${p.offering} growth play. It covers ${p.customerCount} customers, has ${p.confidence} confidence, a ${p.formattedPeerRevenueBenchmark} peer-based revenue benchmark, and ${p.pilotAccount} is the proposed pilot. Show the source evidence and recommend the next step.`} /></div>
        <dl className="exec-row__facts"><div><dt>Customers</dt><dd>{p.customerCount}</dd></div><div><dt>Owners</dt><dd>{p.ownerCount}</dd></div><div><dt>Confidence</dt><dd>{p.confidence}</dd></div><div><dt>Revenue benchmark</dt><dd>{p.formattedPeerRevenueBenchmark}</dd></div></dl>
        <div className="exec-row__action"><span>The action</span><strong>{action?.nextStep ?? p.nextStep}</strong>{action && <button type="button" className="exec-link exec-link--action" onClick={() => openAction(action.key)}>Open action</button>}</div>
      </article>; })}</div></section></>;
}

function Anomalies({ data, accountOnly = false }: { data: ExecutivePayload; accountOnly?: boolean }) {
  const { openAction } = useApp();
  const [severity, setSeverity] = useState("All");
  const [category, setCategory] = useState("All");
  const [findingOwner, setFindingOwner] = useState("All");
  const [stalledOwner, setStalledOwner] = useState("All");
  const [stalledCall, setStalledCall] = useState("All");
  const [stalledStage, setStalledStage] = useState("All");
  const [silenceBand, setSilenceBand] = useState("All");
  const [revenueBand, setRevenueBand] = useState("All");
  const [stalledSort, setStalledSort] = useState("silence");
  const rows = data.anomalyFindings.filter((f) => (severity === "All" || f.severity === severity) && (category === "All" || f.category === category) && (findingOwner === "All" || f.owner === findingOwner));
  const stalledRows = data.stalledDeals.filter(d =>
    (stalledOwner === "All" || d.owner === stalledOwner)
    && (stalledCall === "All" || d.call === stalledCall)
    && (stalledStage === "All" || d.stage === stalledStage)
    && (silenceBand === "All"
      || (silenceBand === "60–90" && d.silenceDays <= 90)
      || (silenceBand === "91–180" && d.silenceDays >= 91 && d.silenceDays <= 180)
      || (silenceBand === "181+" && d.silenceDays >= 181))
    && (revenueBand === "All"
      || (revenueBand === "Under $25K" && d.dealValue < 25_000)
      || (revenueBand === "$25K–$50K" && d.dealValue >= 25_000 && d.dealValue < 50_000)
      || (revenueBand === "$50K+" && d.dealValue >= 50_000))
  ).sort((a, b) => stalledSort === "revenue"
    ? b.dealValue - a.dealValue || b.silenceDays - a.silenceDays
    : stalledSort === "stage"
      ? b.daysInStage - a.daysInStage || b.silenceDays - a.silenceDays
      : b.silenceDays - a.silenceDays || b.dealValue - a.dealValue);
  const overview = data.anomalyOverview;
  const forecastMix = overview.forecastCalls.filter(group => group.deals > 0).map(group => `${group.deals} ${group.call}`).join(", ");
  const activeForecastDeals = overview.forecastCalls.filter(group => group.call === "Commit" || group.call === "Best Case").reduce((sum, group) => sum + group.deals, 0);
  const omittedDeals = overview.forecastCalls.find(group => group.call === "Omitted")?.deals ?? 0;
  return <>{accountOnly && <section className="exec-domain-overview" aria-labelledby="account-revenue-title"><div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Revenue summary</p><h2 id="account-revenue-title">Account signals in the current revenue book</h2><p>Review concentration and account-quality signals before they affect renewals, forecast confidence, or expansion plans.</p></div><ContextAsk label="account anomaly overview" text="Which account needs review?" query={`Explain the ${overview.accountFindings} account anomalies affecting ${overview.accountsAffected} accounts, including the ${overview.criticalAccountFindings} critical signals. Identify concentration, affected revenue, and the first accounts to review.`} /></div><div className="exec-domain-leads"><div><strong>{overview.accountFindings}</strong><span>account anomalies across {overview.accountsAffected} accounts</span></div><div><strong>{overview.criticalAccountFindings}</strong><span>critical signals requiring review</span></div></div></section>}{!accountOnly && <section className="exec-domain-overview" aria-labelledby="anomaly-overview-title">
    <div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Pipeline inactivity</p><h2 id="anomaly-overview-title">Stagnant pipeline overview</h2></div><ContextAsk label="stagnant pipeline overview" text="Where is revenue stuck?" query={`Explain the stagnant pipeline overview: ${overview.stalledDeals} deals across ${overview.stalledAccounts} accounts with ${overview.formattedStalledRevenue} in associated ACV Revenue. Identify the biggest sources of inactivity and the highest-priority records.`} />
      <details className="exec-info"><summary aria-label="How stagnant deals are defined">i</summary><div><b>Definition</b><p>A stagnant deal is an open opportunity with no logged field change for at least 60 days. Stalled ACV Revenue is the sum of ACV Revenue across every matching deal in the current scope. Account-level anomaly logic is intentionally kept on the Account Anomalies tab.</p></div></details>
    </div>
    <div className="exec-domain-leads"><div><strong>{overview.stalledDeals}</strong><span>stagnant deals across {overview.stalledAccounts} accounts</span></div><div><strong>{overview.formattedStalledRevenue}</strong><span>total associated ACV Revenue</span></div></div>
    <div className="exec-domain-stats"><div><strong>{overview.stalledDeals}</strong><span>Stagnant deals</span></div><div><strong>{overview.formattedStalledRevenue}</strong><span>Stalled ACV Revenue</span></div><div><strong>{overview.stalledPastDue}</strong><span>Also past due</span></div><div><strong>{overview.longestSilenceDays}d</strong><span>Longest silence</span></div><div><strong>{activeForecastDeals}</strong><span>Commit / Best Case</span></div><div><strong>{omittedDeals}</strong><span>Omitted</span></div></div>
  </section>}
  {!accountOnly && <section className="exec-section exec-anomaly-insights" aria-labelledby="stagnation-title">
    <div className="exec-section__head"><div><p className="exec-eyebrow">How long they have been still</p><h2 id="stagnation-title">Stagnant-deal inactivity</h2></div><div className="exec-section__tools"><ContextAsk label="stagnation bands" text="Where has pipeline gone quiet?" query={`Explain the stagnant-deal inactivity bands and identify which silence band, deals, and associated ACV Revenue need attention first. The current forecast-call mix is ${forecastMix}.`} /><details className="exec-info"><summary aria-label="Why inactivity matters">i</summary><div><b>Why this matters</b><p>Each band contains open deals with no logged field change. The supplied anomaly guide treats this as a worklist for confirming the deal’s real status, updating it, or closing it out; it is not a final verdict on a deal.</p></div></details></div></div>
    <div className="exec-anomaly-silence">{overview.stagnationBands.map((band, index) => <div key={band.label} className="exec-anomaly-silence__row"><div className="exec-anomaly-silence__label">{band.label}</div><div className="exec-anomaly-silence__bar-wrap"><div className={`exec-anomaly-silence__bar exec-anomaly-silence__bar--${index === 0 ? "blue" : index === 1 ? "gold" : "red"}`} style={{ width: `${band.share * 100}%` }} /></div><div className="exec-anomaly-silence__meta">{band.deals} deals · {band.formattedRevenue}</div></div>)}</div>
    <p className="exec-anomaly-silence__caption">Forecast-call mix: {forecastMix}. The complete worklist below is ordered by longest silence by default.</p>
  </section>}
  {!accountOnly && <section className="exec-section exec-anomaly-table">
    <div className="exec-section__head"><div><p className="exec-eyebrow">Pipeline inactivity</p><h2>Deals with no recent movement</h2><p>{stalledRows.length} of {data.stalledDeals.length} stagnant deals shown. Revenue is deal-level ACV; use the filters to separate active forecast calls from Omitted pipeline.</p></div><div className="exec-controls"><label>Call<select value={stalledCall} onChange={e => setStalledCall(e.target.value)}><option>All</option>{[...new Set(data.stalledDeals.map(d => d.call))].sort().map(v => <option key={v}>{v}</option>)}</select></label><label>Stage<select value={stalledStage} onChange={e => setStalledStage(e.target.value)}><option>All</option>{[...new Set(data.stalledDeals.map(d => d.stage))].sort().map(v => <option key={v}>{v}</option>)}</select></label><label>Days silent<select value={silenceBand} onChange={e => setSilenceBand(e.target.value)}><option>All</option><option>60–90</option><option>91–180</option><option>181+</option></select></label><label>ACV Revenue<select value={revenueBand} onChange={e => setRevenueBand(e.target.value)}><option>All</option><option>Under $25K</option><option>$25K–$50K</option><option>$50K+</option></select></label><label>Owner<select value={stalledOwner} onChange={e => setStalledOwner(e.target.value)}><option>All</option>{[...new Set(data.stalledDeals.map(d => d.owner))].sort().map(v => <option key={v}>{v}</option>)}</select></label><label>Sort<select value={stalledSort} onChange={e => setStalledSort(e.target.value)}><option value="silence">Longest silent</option><option value="revenue">Highest ACV</option><option value="stage">Longest in stage</option></select></label></div></div>
    <div className="exec-anomaly-table__wrap exec-stagnated-table__wrap">
      <table className="exec-anomaly-table__table exec-stagnated-table">
        <thead>
          <tr><th>Account and line</th><th>Owner</th><th>ACV Revenue</th><th>Call</th><th>Days in stage</th><th>Days silent</th><th>Stage</th><th>Action</th></tr>
        </thead>
        <tbody>
          {stalledRows.map(d => {
            const action = d.actionKey ? data.actions.find(item => item.key === d.actionKey) : undefined;
            return <tr key={d.key}>
              <td><div className="exec-anomaly-table__account exec-askable"><strong>{d.account}</strong><span>{d.deal}</span><ContextAsk label={d.deal} overlay query={`Explain why ${d.deal} at ${d.account} is classified as stagnant. It has ${moneyExact(d.dealValue)} ACV Revenue, ${d.silenceDays} days without movement, ${d.daysInStage} days in ${d.stage}, a ${d.call} forecast call, and is owned by ${d.owner}. Recommend the next evidence-based action.`} /></div></td>
              <td>{d.owner}</td>
              <td><span className="exec-anomaly-table__money">{moneyExact(d.dealValue)}</span></td>
              <td><span className={`exec-anomaly-table__call exec-anomaly-table__call--${d.call.toLowerCase().includes("commit") ? "commit" : d.call.toLowerCase().includes("best") ? "best" : "other"}`}>{d.call}</span></td>
              <td>{d.daysInStage}</td>
              <td>{d.silenceDays}</td>
              <td>{d.stage}</td>
              <td><div className="exec-anomaly-table__action"><span>{action?.nextStep ?? d.nextStep ?? "Confirm the real status, update the deal, or close it out."}</span>{action && <button type="button" className="exec-link exec-link--action" onClick={() => openAction(action.key)}>Open action</button>}</div></td>
            </tr>;
          })}
        </tbody>
      </table>
    </div>
    {!stalledRows.length && <p className="exec-empty">No stagnant open deal matches these filters.</p>}
  </section>}
  {accountOnly && <section className="exec-section">
    <div className="exec-section__head"><div><p className="exec-eyebrow">Account-level findings</p><h2>Investigate the account pattern</h2></div><div className="exec-controls"><label>Severity<select value={severity} onChange={(e) => setSeverity(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></label><label>Category<select value={category} onChange={(e) => setCategory(e.target.value)}><option>All</option>{[...new Set(data.anomalyFindings.map(f => f.category))].sort().map(v => <option key={v}>{v}</option>)}</select></label><label>Owner<select value={findingOwner} onChange={e => setFindingOwner(e.target.value)}><option>All</option>{[...new Set(data.anomalyFindings.map(f => f.owner))].sort().map(v => <option key={v}>{v}</option>)}</select></label></div></div>
    <div className="exec-list">{rows.map((f) => { const action = data.actions.find(item => item.key === `anomaly:${f.key}`); return <article className="exec-row exec-row--with-action exec-row--account-anomaly" key={f.key}><span className={`exec-badge exec-badge--${f.severity.toLowerCase()}`}>{f.severity}</span><div className="exec-row__main exec-askable"><h3>{f.entity}</h3><p>{f.evidence}</p><strong>{f.question}</strong><ContextAsk label={f.entity} overlay query={`Explain the ${f.severity.toLowerCase()} ${f.category} anomaly for ${f.entity}. Evidence: ${f.evidence}. The owner is ${f.owner}. Validate why it was flagged and recommend the next action.`} /></div><dl className="exec-row__facts"><div><dt>Category</dt><dd>{f.category}</dd></div><div><dt>Owner</dt><dd>{f.owner}</dd></div></dl><div className="exec-row__action"><span>The action</span><strong>{f.nextStep}</strong>{action && <button type="button" className="exec-link exec-link--action" onClick={() => openAction(action.key)}>Open action</button>}</div></article>; })}</div>
    {!rows.length && <p className="exec-empty">No findings match these local filters.</p>}
  </section>}</>;
}

function ClosureRisk({ data, focus }: { data: ExecutivePayload; focus: "low" | "slippage" }) {
  const { openAction } = useApp();
  const [band, setBand] = useState("All"); const [forecast, setForecast] = useState("All"); const [stage, setStage] = useState("All"); const [owner, setOwner] = useState("All");
  const focusedRows = data.closureExceptions.filter(d => focus === "low" ? (d.closureProbability != null && d.closureProbability < 0.5) : d.closeDateSlips > 0);
  // Bucket 1 is the priority group; all other/missing buckets follow.
  // Risk score resolves ties within each group.
  const riskBucketTier = (bucket: number | null | undefined) => bucket === 1 ? 0 : 1;
  const rows = focusedRows.filter(d => (band === "All" || d.riskBucketLabel === band) && (forecast === "All" || d.forecastCategory === forecast) && (stage === "All" || d.stage === stage) && (owner === "All" || d.owner === owner)).sort((a, b) => riskBucketTier(a.riskBucket) - riskBucketTier(b.riskBucket) || b.riskScore - a.riskScore || b.revenue - a.revenue);
  const options = (key: "forecastCategory" | "stage" | "owner") => [...new Set(data.closureExceptions.map(d => d[key]))].sort();
  return <>
    <section className="exec-revenue-overview" aria-labelledby="closure-revenue-title">
      <div className="exec-revenue-overview__head"><div><p className="exec-eyebrow">Declared against defensible</p><h2 id="closure-revenue-title">Revenue confidence by forecast category</h2></div><ContextAsk label="revenue confidence visual" text="How much forecast can I believe?" query={`Explain the declared-versus-defensible revenue visual for ${focus === "low" ? "low probability to close" : "slippage risk"}. Compare Commit and Best Case, show which deals account for the screened-out revenue, and recommend the most important forecast correction.`} />
        <details className="exec-info"><summary aria-label="How defensible revenue is calculated">i</summary><div><b>How this is calculated</b><p>Declared is all open ACV Revenue in Commit or Best Case. Defensible retains Commit at 35% or higher and Best Case at 25% or higher, reflecting the different evidence expected from each forecast call. The worklist below separately identifies every deal below 50%. {data.closureModel.text}</p></div></details>
      </div>
      <div className="exec-revenue-series">{data.closureOverview.series.map(series => { const retained = series.retainedShare == null ? 0 : Math.max(0, Math.min(100, series.retainedShare * 100)); return <article key={series.forecast} className={`exec-revenue-series__item exec-revenue-series__item--${series.forecast === "Commit" ? "commit" : "best-case"}`}><div className="exec-revenue-line"><span>{series.forecast} · declared</span><strong>{series.formattedDeclaredRevenue}</strong></div><div className="exec-revenue-track" aria-hidden="true"><span className="exec-revenue-fill exec-revenue-fill--declared" /></div><div className="exec-revenue-line"><span>{series.forecast} · defensible</span><strong>{series.formattedDefensibleRevenue}</strong></div><div className="exec-revenue-track" aria-hidden="true"><span className="exec-revenue-fill exec-revenue-fill--defensible" style={{ width: `${retained}%` }} /></div><p>{series.defensibleDeals == null ? "Model scoring is unavailable for this category." : <>{series.defensibleDeals} of {series.declaredDeals} deals remain · {series.formattedScreenedOutRevenue} falls below the {Math.round(series.threshold * 100)}% threshold</>}</p></article>; })}</div>
      <div className="exec-pipeline-stats" aria-label="Deal closure statistics"><div><strong>{data.closureOverview.stats.openDeals}</strong><span>Open deals</span></div><div><strong>{data.closureOverview.lowProbabilityDeals}</strong><span>Below 50%</span></div><div><strong>{data.closureOverview.stats.pastDueDeals}</strong><span>Past due</span></div><div><strong>{data.closureOverview.stats.stalledDeals}</strong><span>Stalled</span></div><div><strong>{data.closureOverview.stats.slippedDeals}</strong><span>Slipped</span></div><details className="exec-info exec-info--stats"><summary aria-label="About deal closure statistics">i</summary><div><b>What these stats mean</b><p>Below 50% uses the model probability on open deals. Past due compares the current close date with the data cut. Stalled means prolonged inactivity. Slipped means the close date moved later at least once. A deal may meet more than one condition.</p></div></details></div>
    </section>
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">{focus === "low" ? "Probability review" : "Close-date review"}</p><h2>{focus === "low" ? "Low-confidence opportunities" : "Deals whose close date has slipped"}</h2><p>{focus === "low" ? "Prioritise deals below a 50% model probability, ordered by business risk." : "Validate the new close plan and whether the deal remains forecastable."}</p></div><div className="exec-controls"><label>Risk<select value={band} onChange={e => setBand(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Watch</option><option>Low</option></select></label><label>Forecast<select value={forecast} onChange={e => setForecast(e.target.value)}><option>All</option>{options("forecastCategory").map(v => <option key={v}>{v}</option>)}</select></label><label>Stage<select value={stage} onChange={e => setStage(e.target.value)}><option>All</option>{options("stage").map(v => <option key={v}>{v}</option>)}</select></label><label>Owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{options("owner").map(v => <option key={v}>{v}</option>)}</select></label></div></div>
      <div className="exec-list">{rows.map(d => { const action = data.actions.find(item => item.key === `closure:${d.key}`); return <article className="exec-row exec-row--with-action exec-row--closure-focus" key={d.key}><div className="exec-row__risk-score" title={`${d.riskBucketLabel} risk bucket`}><span className={`exec-score exec-score--${d.riskBucketLabel.toLowerCase()}`}>{d.riskBucket ?? "—"}</span><small>Risk bucket</small></div><div className="exec-row__main exec-askable"><h3>{d.deal}</h3><p>{d.account}</p><ContextAsk label={d.deal} overlay query={`Explain the closure risk for ${d.deal} at ${d.account}: ${closureProbability(d.closureProbability)} closure probability, ${moneyExact(d.revenue)} ACV Revenue, model criticality ${d.riskBucketLabel} (bucket ${d.riskBucket ?? "unknown"}), operational risk score ${Math.round(d.riskScore)}, ${d.forecastCategory} forecast, and primary driver ${d.mainDriver}. Recommend the next evidence-based action.`} /></div><dl className="exec-row__facts exec-row__facts--primary"><div><dt>Closure probability</dt><dd>{closureProbability(d.closureProbability)}</dd></div><div><dt>ACV Revenue</dt><dd>{moneyExact(d.revenue)}</dd></div></dl><details className="exec-info exec-row__info"><summary aria-label={`More information about ${d.deal}`}>i</summary><div><dl><div><dt>Model criticality</dt><dd>{d.riskBucketLabel} · bucket {d.riskBucket ?? "unknown"}</dd></div><div><dt>Operational risk</dt><dd>{d.riskBand} · score {d.riskScore}</dd></div><div><dt>Forecast</dt><dd>{d.forecastCategory}</dd></div><div><dt>Stage</dt><dd>{d.stage}</dd></div><div><dt>Owner</dt><dd>{d.owner}</dd></div><div><dt>Close date</dt><dd>{d.closeDate ?? "Date unavailable"}</dd></div><div><dt>Primary driver</dt><dd>{d.mainDriver}</dd></div><div><dt>Deterioration</dt><dd>{d.deterioration}</dd></div><div><dt>Silence</dt><dd>{d.silenceDays == null ? "—" : `${d.silenceDays} days`}</dd></div></dl></div></details><div className="exec-row__action"><span>The action</span><strong>{action?.nextStep ?? "Validate the evidence and assign an owner."}</strong>{action && <button type="button" className="exec-link exec-link--action" onClick={() => openAction(action.key)}>Open action</button>}</div></article>; })}</div>
      {!rows.length && <p className="exec-empty">No deals match these local filters.</p>}
    </section></>;
}

function SlippageRisk({ data }: { data: ExecutivePayload }) {
  const { openAction } = useApp();
  const [forecast, setForecast] = useState("All");
  const [owner, setOwner] = useState("All");
  const forecasts = [...new Set(data.slippageDeals.map(d => d.forecastCategory))].sort();
  const owners = [...new Set(data.slippageDeals.map(d => d.owner))].sort();
  const rows = data.slippageDeals
    .filter(d => (forecast === "All" || d.forecastCategory === forecast) && (owner === "All" || d.owner === owner))
    .sort((a, b) => b.closeDateSlips - a.closeDateSlips || b.slipDays - a.slipDays || b.pastDueDays - a.pastDueDays || b.revenue - a.revenue);
  const callTone = (call: string) => call.toLowerCase().includes("commit") ? "commit" : call.toLowerCase().includes("best") ? "best" : "other";

  return <>
    <section className="exec-domain-overview exec-slippage-overview" aria-labelledby="slippage-overview-title">
      <div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Close-date movement</p><h2 id="slippage-overview-title">Revenue exposed to repeated close-date movement</h2></div><ContextAsk label="slippage overview" text="What is driving slippage?" query={`Explain the slippage overview: ${data.closureOverview.stats.slippedDeals} slipped deals, ${data.closureOverview.formattedSlippageRevenue} in associated ACV Revenue, ${data.closureOverview.slipEvents} later re-dates, and ${data.closureOverview.totalSlipDays} total days slipped. Identify the deals driving the exposure and the first forecast decisions to make.`} />
        <details className="exec-info"><summary aria-label="How slippage is calculated">i</summary><div><b>How this is calculated</b><p>A re-date counts only when the movement log shows a close date moved later. Total days slipped is the sum of those later moves. Days past close compares the deal's current close date with the data cut; future-dated deals show a dash.</p></div></details>
      </div>
      <div className="exec-slippage-stats" aria-label="Slippage statistics">
        <div><strong>{data.closureOverview.stats.slippedDeals}</strong><span>Slipped deals</span></div>
        <div><strong>{data.closureOverview.formattedSlippageRevenue}</strong><span>Associated ACV Revenue</span></div>
        <div><strong>{data.closureOverview.slipEvents}</strong><span>Later re-dates</span></div>
        <div><strong>{data.closureOverview.totalSlipDays}</strong><span>Total days slipped</span></div>
        <div><strong>{data.closureOverview.slippedPastDueDeals}</strong><span>Now past close</span></div>
      </div>
    </section>
    <section className="exec-section exec-slippage-section">
      <div className="exec-section__head"><div><p className="exec-eyebrow">Close-date review</p><h2>Deals whose close date moved later</h2><p>Confirm the customer-backed close plan or reclassify the forecast call. Ordered by re-dates, total days slipped, overdue days, then ACV Revenue.</p></div><div className="exec-controls"><label>Forecast<select value={forecast} onChange={e => setForecast(e.target.value)}><option>All</option>{forecasts.map(v => <option key={v}>{v}</option>)}</select></label><label>Opportunity owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{owners.map(v => <option key={v}>{v}</option>)}</select></label></div></div>
      <div className="exec-anomaly-table__wrap exec-slippage-table__wrap">
        <table className="exec-anomaly-table__table exec-slippage-table">
          <colgroup><col /><col /><col /><col /><col /><col /><col /><col /><col /></colgroup>
          <thead><tr><th>Account and opportunity</th><th>Owners</th><th>ACV Revenue</th><th>Forecast call</th><th>Re-dates</th><th>Total days slipped</th><th>Days past close</th><th>Current close date</th><th>Action</th></tr></thead>
          <tbody>{rows.map(d => { const action = data.actions.find(item => item.key === `slippage:${d.key}`); return <tr key={d.key}>
            <td><div className="exec-anomaly-table__account exec-askable"><strong>{d.account}</strong><span>{d.deal}</span>{d.line && <small>{d.line}</small>}<ContextAsk label={d.deal} overlay query={`Explain the slippage risk for ${d.deal} at ${d.account}: ${moneyExact(d.revenue)} ACV Revenue, ${d.forecastCategory} forecast, ${d.closeDateSlips} later close-date moves totaling ${d.slipDays} days, ${d.pastDueDays > 0 ? `${d.pastDueDays} days past close` : "not currently past close"}, and current close date ${shortDate(d.closeDate)}. Show the movement evidence and recommend the next forecast action.`} /></div></td>
            <td><div className="exec-slippage-table__owners"><strong>{d.owner}</strong><span>Opportunity owner</span><small>{d.accountOwner} · Account owner</small></div></td>
            <td className="exec-anomaly-table__money">{moneyExact(d.revenue)}</td>
            <td><span className={`exec-anomaly-table__call exec-anomaly-table__call--${callTone(d.forecastCategory)}`}>{d.forecastCategory}</span></td>
            <td><span className={`exec-slippage-table__count${d.closeDateSlips >= 3 ? " exec-slippage-table__count--critical" : ""}`}>{d.closeDateSlips}</span></td>
            <td className="exec-slippage-table__days">{d.slipDays}</td>
            <td className={d.pastDueDays > 0 ? "exec-slippage-table__overdue" : ""}>{d.pastDueDays > 0 ? d.pastDueDays : "—"}</td>
            <td className="exec-slippage-table__date">{shortDate(d.closeDate)}</td>
            <td>{action && <div className="exec-anomaly-table__action"><span title={action.nextStep}>{action.nextStep}</span><button type="button" className="exec-link exec-link--action" onClick={() => openAction(action.key)}>Open action</button></div>}</td>
          </tr>; })}</tbody>
        </table>
      </div>
      {!rows.length && <p className="exec-empty">No slipped deals match these local filters.</p>}
    </section>
  </>;
}

type ActionView = "all" | "urgent" | "week" | "review" | "monitoring" | "actioned" | "open";
type WorkflowNotice = { title: string; detail: string; tone: "complete" | "review" | "monitor" | "dismiss" };

function ActionsCenter({ data, asOf }: { data: ExecutivePayload; asOf: string }) {
  const { state } = useApp();
  const storageKey = `ntt.executive-actions.v1:${state.identity}`;
  const [saved, setSaved] = useState<DecisionMap>({});
  const [view, setView] = useState<ActionView>("all");
  const [theme, setTheme] = useState("All");
  const [source, setSource] = useState("All");
  const [owner, setOwner] = useState("All");
  const [sort, setSort] = useState("priority");
  const [expanded, setExpanded] = useState<string | null>(state.actionKey);
  const [pending, setPending] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState<WorkflowNotice | null>(null);
  const refs = useRef<Record<string, HTMLElement | null>>({});
  useEffect(() => { try { setSaved(JSON.parse(localStorage.getItem(storageKey) ?? "{}")); } catch { setSaved({}); } }, [storageKey]);
  useEffect(() => { if (!state.actionKey) return; setView("all"); setExpanded(state.actionKey); requestAnimationFrame(() => refs.current[state.actionKey!]?.focus()); }, [state.actionKey]);
  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(null), 6500); return () => window.clearTimeout(timer); }, [notice]);
  const effectiveStatus = (a: ExecutiveAction) => saved[a.key]?.status ?? "New";
  const isOpen = (a: ExecutiveAction) => !["Actioned", "Dismissed"].includes(effectiveStatus(a));
  const dueThisWeek = (a: ExecutiveAction) => {
    const days = (Date.parse(`${a.dueDate}T00:00:00Z`) - Date.parse(`${asOf}T00:00:00Z`)) / 86_400_000;
    return days >= 0 && days <= 7 && isOpen(a);
  };
  const counts = {
    urgent: data.actions.filter(a => isOpen(a) && (a.priority === "Critical" || a.priority === "High")).length,
    week: data.actions.filter(dueThisWeek).length,
    review: data.actions.filter(a => effectiveStatus(a) === "In Review").length,
    monitoring: data.actions.filter(a => effectiveStatus(a) === "Monitoring").length,
    actioned: data.actions.filter(a => effectiveStatus(a) === "Actioned").length,
    open: data.actions.filter(isOpen).length,
  };
  const owners = [...new Set(data.actions.map(a => a.owner))].sort();
  const matchesView = (a: ExecutiveAction) => view === "all"
    || (view === "urgent" && isOpen(a) && (a.priority === "Critical" || a.priority === "High"))
    || (view === "week" && dueThisWeek(a))
    || (view === "review" && effectiveStatus(a) === "In Review")
    || (view === "monitoring" && effectiveStatus(a) === "Monitoring")
    || (view === "actioned" && effectiveStatus(a) === "Actioned")
    || (view === "open" && isOpen(a));
  const rows = useMemo(() => data.actions
    .filter(a => matchesView(a) && (theme === "All" || a.theme === theme) && (source === "All" || a.sourcePage === source) && (owner === "All" || a.owner === owner))
    .sort((a, b) => sort === "due" ? a.dueDate.localeCompare(b.dueDate)
      : sort === "revenue" ? (b.revenueImpact ?? 0) - (a.revenueImpact ?? 0) || PRIORITY[a.priority] - PRIORITY[b.priority]
        : PRIORITY[a.priority] - PRIORITY[b.priority] || a.dueDate.localeCompare(b.dueDate)),
  [data.actions, saved, view, theme, source, owner, sort, asOf]);
  const workflowNotice = (a: ExecutiveAction, status: string): WorkflowNotice => {
    const revenue = a.formattedRevenueImpact ? ` Associated revenue: ${a.formattedRevenueImpact}.` : "";
    if (status === "Actioned") return { tone: "complete", title: "Action executed", detail: `${a.nextStep} Owner: ${a.owner}.${revenue}` };
    if (status === "In Review") return { tone: "review", title: "Review delegated", detail: `${a.headline} is now assigned to ${a.owner} for review.${revenue}` };
    if (status === "Monitoring") return { tone: "monitor", title: "Follow-up scheduled", detail: `${a.headline} is marked for monitoring. ${a.owner} will retain the next-step context.${revenue}` };
    return { tone: "dismiss", title: "Action dismissed", detail: `${a.headline} has been removed from the active worklist.${revenue}` };
  };
  const save = (a: ExecutiveAction, optionKey: string) => {
    const option = a.options.find(o => o.key === optionKey); if (!option) return;
    const reason = (reasons[a.key] ?? "").trim(); if (option.needsReason && !reason) return;
    const next = { ...saved, [a.key]: { optionKey, status: option.status, ...(reason ? { reason } : {}), updatedAt: new Date().toISOString() } };
    setSaved(next); localStorage.setItem(storageKey, JSON.stringify(next));
    setPending(p => ({ ...p, [a.key]: "" })); setReasons(r => ({ ...r, [a.key]: "" }));
    setNotice(workflowNotice(a, option.status));
  };
  const choose = (a: ExecutiveAction, optionKey: string) => {
    const option = a.options.find(o => o.key === optionKey); if (!option) return;
    if (option.needsReason) setPending(p => ({ ...p, [a.key]: optionKey }));
    else save(a, optionKey);
  };
  const buttonLabel = (status: string) => ({ Monitoring: "Snooze", Dismissed: "Dismiss", "In Review": "Delegate", Actioned: "Execute" }[status] ?? status);
  const order = ["Monitoring", "Dismissed", "In Review", "Actioned"];
  const tabs: { key: ActionView; label: string; count: number }[] = [
    { key: "urgent", label: "Urgent", count: counts.urgent }, { key: "week", label: "This week", count: counts.week },
    { key: "review", label: "Delegated", count: counts.review }, { key: "monitoring", label: "Snoozed", count: counts.monitoring },
    { key: "actioned", label: "Executed", count: counts.actioned }, { key: "all", label: "All", count: data.actions.length },
  ];
  const sourceLabel = (page?: string) => ({
    opportunities: "Growth plays", "account-anomalies": "Account anomalies",
    "stagnated-deals": "Stagnated deals", "low-probability": "Low probability",
    "slippage-risk": "Slippage risk",
  }[page ?? ""] ?? "Action");
  const sources = [...new Set(data.actions.map(a => a.sourcePage).filter((page): page is NonNullable<typeof page> => Boolean(page)))];
  return <section className="exec-actions" aria-labelledby="action-center-title">
    {notice && <aside className={`exec-workflow-toast exec-workflow-toast--${notice.tone}`} role="status" aria-live="polite"><div><span>Workflow update</span><strong>{notice.title}</strong><p>{notice.detail}</p></div><button type="button" onClick={() => setNotice(null)} aria-label="Dismiss workflow notification">×</button></aside>}
    <div className="exec-action-center__head"><div><p className="exec-eyebrow">What to commit now?</p><h2 id="action-center-title">Action Center</h2><p>Every generated action is available here. Execute, delegate, snooze, or dismiss; decisions are saved in this browser for {state.identity}.</p></div><div className="exec-controls"><label>Theme<select value={theme} onChange={e => setTheme(e.target.value)}><option>All</option><option value="opportunities">Cross-sell / Upsell</option><option value="anomalies">Anomaly Detection</option><option value="closure">Deal Closure</option></select></label><label>Source<select value={source} onChange={e => setSource(e.target.value)}><option>All</option>{sources.map(v => <option key={v} value={v}>{sourceLabel(v)}</option>)}</select></label><label>Owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{owners.map(v => <option key={v}>{v}</option>)}</select></label><label>Sort<select value={sort} onChange={e => setSort(e.target.value)}><option value="priority">Priority</option><option value="revenue">Associated revenue · high to low</option><option value="due">Due date</option></select></label></div></div>
    <div className="exec-action-revenue" aria-label="Revenue associated with action items"><article className="exec-askable"><span>Unique deal ACV</span><strong>{data.actionOverview.formattedDealAcvRevenue}</strong><small>{data.actionOverview.uniqueDealActions} deals; duplicates across action types counted once</small><ContextAsk label="actionable deal ACV" overlay query={`Explain the ${data.actionOverview.formattedDealAcvRevenue} unique deal ACV represented in the Action Center across ${data.actionOverview.uniqueDealActions} deals. Break it down by source and priority without double-counting deals.`} /></article><article className="exec-askable"><span>Account-book ACV</span><strong>{data.actionOverview.formattedAccountBookRevenue}</strong><small>{data.actionOverview.accountActions} account actions; may overlap deal ACV</small><ContextAsk label="account-book ACV" overlay query={`Explain the ${data.actionOverview.formattedAccountBookRevenue} account-book ACV associated with ${data.actionOverview.accountActions} account actions. Identify overlap with deal actions and the highest-priority account signals.`} /></article><article className="exec-askable"><span>Growth benchmark</span><strong>{data.actionOverview.formattedGrowthBenchmark}</strong><small>{data.actionOverview.growthActions} plays; not pipeline or forecast</small><ContextAsk label="growth benchmark" overlay query={`Explain the ${data.actionOverview.formattedGrowthBenchmark} growth benchmark across ${data.actionOverview.growthActions} plays. Clarify why it is not pipeline or forecast and identify the plays with the strongest supporting evidence.`} /></article></div>
    <div className="exec-action-summary" aria-label="Action summary"><button type="button" onClick={() => setView("urgent")}><span>Urgent</span><strong>{counts.urgent}</strong></button><button type="button" onClick={() => setView("week")}><span>Due this week</span><strong>{counts.week}</strong></button><button type="button" onClick={() => setView("review")}><span>Delegated</span><strong>{counts.review}</strong></button><button type="button" onClick={() => setView("actioned")}><span>Executed</span><strong>{counts.actioned}</strong></button><button type="button" onClick={() => setView("open")}><span>Still open</span><strong>{counts.open}</strong></button></div>
    <div className="exec-action-tabs" role="tablist" aria-label="Action status">{tabs.map(tab => <button key={tab.key} type="button" role="tab" aria-selected={view === tab.key} className={view === tab.key ? "is-active" : ""} onClick={() => setView(tab.key)}>{tab.label}<span>{tab.count}</span></button>)}</div>
    <div className="exec-action-cards">{rows.map(a => {
      const selected = pending[a.key] ?? ""; const option = a.options.find(o => o.key === selected); const open = expanded === a.key;
      const options = [...a.options].sort((left, right) => order.indexOf(left.status) - order.indexOf(right.status));
      return <article className={`exec-action-card exec-action-card--${a.theme}${open ? " is-open" : ""}`} key={a.key} tabIndex={-1} ref={el => { refs.current[a.key] = el; }}><div className="exec-action-card__header">
        <button type="button" className="exec-action-card__summary" onClick={() => setExpanded(open ? null : a.key)} aria-expanded={open}><span className="exec-action-card__theme">{sourceLabel(a.sourcePage)}</span><span className={`exec-badge exec-badge--${a.priority.toLowerCase()}`}>{a.priority}</span>{effectiveStatus(a) !== "New" && <span className="exec-status">{effectiveStatus(a)}</span>}<strong>{a.headline}</strong><small>{a.owner} · due {a.dueDate}</small><span className="exec-action-card__toggle" aria-hidden="true">{open ? "⌃" : "⌄"}</span></button><ContextAsk label={a.headline} query={`Explain this ${sourceLabel(a.sourcePage)} action: ${a.headline}. It is ${a.priority} priority, owned by ${a.owner}, due ${a.dueDate}${a.formattedRevenueImpact ? `, with ${a.revenueLabel ?? "associated revenue"} of ${a.formattedRevenueImpact}` : ""}. Context: ${a.description}. Assess the evidence and advise whether to execute, delegate, snooze, or dismiss it.`} />
        </div>
        {open && <div className="exec-action-card__body"><div className="exec-action-card__copy"><span>Why this matters</span><p>{a.description}</p><span>Next step</span><strong>{a.nextStep}</strong>{a.formattedRevenueImpact && <small>{a.revenueLabel ?? "Associated revenue"}: {a.formattedRevenueImpact}</small>}</div><div className="exec-action-card__buttons">{options.map(o => <button key={o.key} type="button" className={`exec-decision exec-decision--${o.status.toLowerCase().replace(" ", "-")}`} onClick={() => choose(a, o.key)}>{buttonLabel(o.status)}</button>)}</div>{option?.needsReason && <div className="exec-action-card__reason"><label>Reason required<textarea value={reasons[a.key] ?? ""} onChange={e => setReasons(r => ({ ...r, [a.key]: e.target.value }))} placeholder={`Why ${buttonLabel(option.status).toLowerCase()} this action?`} required /></label><button type="button" className="exec-save" disabled={!(reasons[a.key] ?? "").trim()} onClick={() => save(a, selected)}>Confirm {buttonLabel(option.status)}</button></div>}{saved[a.key] && <small className="exec-action-card__updated">Updated {new Date(saved[a.key].updatedAt).toLocaleString()}</small>}</div>}
      </article>;
    })}</div>{!rows.length && <p className="exec-empty">No actions match this view.</p>}
  </section>;
}

export function ExecutivePage({ payload, meta }: { payload: ViewPayload; meta: MetaPayload | null }) {
  const { state, onFilter, setFilter, clearFilters } = useApp(); const data = payload.executive;
  const briefSeenKey = `ntt.executive-brief.seen:${state.identity}`;
  const [briefModalOpen, setBriefModalOpen] = useState(() => sessionStorage.getItem(briefSeenKey) !== "1");
  useEffect(() => { setBriefModalOpen(sessionStorage.getItem(briefSeenKey) !== "1"); }, [briefSeenKey]);
  useEffect(() => { const open = () => setBriefModalOpen(true); window.addEventListener("ntt:open-brief", open); return () => window.removeEventListener("ntt:open-brief", open); }, []);
  const closeBriefModal = () => { sessionStorage.setItem(briefSeenKey, "1"); setBriefModalOpen(false); };
  if (!data) return <section className="pv exec" aria-labelledby="exec-contract-error">
    <div className="pv-error" role="alert">
      <p className="pv-error__label">Executive pages could not load</p>
      <h1 className="pv-error__title" id="exec-contract-error">The web app is connected to an older API process</h1>
      <p className="pv-error__detail">Stop the existing servers, start this project with <code>ntt-command-centre/run.sh</code>, then reload the page.</p>
    </div>
  </section>;
  const isBrief = payload.page === "tldr";
  const revenueSummary = payload.pageRevenueSummary;
  return <section className={`pv exec${isBrief ? " pv--executive-brief" : ""}`} aria-labelledby="pv-question"><BriefModal data={data} open={briefModalOpen} onClose={closeBriefModal} /><header className="pv-head"><div className="pv-head__text"><h1 className="pv-head__question" id="pv-question">{payload.label}</h1><p className="exec-head__subheading">{payload.question}</p>{!isBrief && revenueSummary && <div className="exec-page-revenue-wrap"><p className="exec-page-revenue"><span>Revenue in focus</span><strong>{revenueSummary.formatted}</strong><em>{revenueSummary.label}</em></p><ContextAsk label={`${payload.label} revenue`} query={`Explain the ${revenueSummary.formatted} revenue in focus for ${payload.label}: ${revenueSummary.label}. Use the current ${payload.scope.label} and ${payload.quarter} scope, show exactly which records contribute to it, and flag any overlap or exclusions.`} /></div>}<p className="pv-head__meta">{payload.scope.label} · {payload.quarter} · as of {longDate(payload.asOf)}</p></div><div className="pv-head__controls"><MoreFilters dimensions={meta?.dimensions ?? []} active={state.filters} onSet={setFilter} onClear={clearFilters} /></div></header>
    {payload.filters.length > 0 && <div className="pv-filters" aria-label="Active filters"><span className="pv-filters__label">Filtered</span>{payload.filters.map(f => <button type="button" className="pv-filters__chip" key={f.dim} onClick={()=>onFilter(f.dim as "country"|"quarter",f.value)}><span className="pv-filters__dim">{f.label}</span><span className="pv-filters__value">{f.value}</span><span className="pv-filters__x" aria-hidden="true">×</span></button>)}<button type="button" className="pv-filters__clear" onClick={clearFilters}>Clear all</button></div>}
    {isBrief && <Brief data={data} />}{payload.page === "opportunities" && <Opportunities data={data} />}{payload.page === "stagnated-deals" && <Anomalies data={data} />}{payload.page === "account-anomalies" && <Anomalies data={data} accountOnly />}{payload.page === "low-probability" && <ClosureRisk data={data} focus="low" />}{payload.page === "slippage-risk" && <SlippageRisk data={data} />}{payload.page === "action-center" && <ActionsCenter data={data} asOf={payload.asOf} />}
  </section>;
}
