import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ExecutiveAction, ExecutivePayload, ExecutiveTheme,
  MetaPayload, Urgency, ViewPayload,
} from "../api/types";
import { MoreFilters } from "../components/FilterBar";
import { longDate } from "../lib/format";
import { useApp } from "../state/AppStateProvider";

type SavedDecision = {
  optionKey: string; status: string; reason?: string; updatedAt: string;
};
type DecisionMap = Record<string, SavedDecision>;

const THEME_LABEL: Record<ExecutiveTheme, string> = {
  opportunities: "Opportunities", anomalies: "Anomalies", closure: "Closure Risk",
};
const PRIORITY: Record<Urgency, number> = { Critical: 0, High: 1, Medium: 2, Low: 3 };

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
            <div className="exec-brief-modal__buttons"><button type="button" className="exec-evidence-link" onClick={() => { onClose(); setPage(overview.page); }}>View details</button>{insight?.actionKey && <button type="button" className="exec-link" onClick={() => { onClose(); openAction(insight.actionKey!); }}>Open action</button>}</div>
          </article>;
        })}</div>
      </>) : null}
    </section>
  </div>;
}

function Brief({ data, modalOpen, closeModal }: {
  data: ExecutivePayload; modalOpen: boolean; closeModal: () => void;
}) {
  const { setPage, openAction } = useApp();
  const [selectedInsightKey, setSelectedInsightKey] = useState<string | null>(null);
  const selectedInsight = data.weeklyInsights.find(item => item.key === selectedInsightKey);
  const selectedAction = selectedInsight?.actionKey
    ? data.actions.find(action => action.key === selectedInsight.actionKey
      && action.theme === selectedInsight.theme)
    : undefined;
  return <>
    <BriefModal data={data} open={modalOpen} onClose={closeModal} />
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
      <div className="exec-section__head"><div><h2 id="weekly-focus-title">Decisions this week</h2></div></div>
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

function Opportunities({ data }: { data: ExecutivePayload }) {
  const { openAction } = useApp();
  const overview = data.opportunityOverview;
  return <><section className="exec-domain-overview" aria-labelledby="opportunity-overview-title">
    <div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Cross-sell and upsell overview</p><h2 id="opportunity-overview-title">Where a repeatable customer play is visible</h2></div>
      <details className="exec-info"><summary aria-label="How opportunity recommendations are calculated">i</summary><div><b>How this is calculated</b><p>Recommendations come from the supplied cross-sell model. A repeatable play is the same offering recommended for at least two accounts. Strong recommendations are marked High or Very High by the source model. Comparable ACV is the median source-reported average won revenue for peer accounts; it is context, not projected upsell revenue.</p></div></details>
    </div>
    <div className="exec-domain-leads"><div><strong>{overview.recommendations}</strong><span>recommendations across {overview.accounts} accounts</span></div><div><strong>{overview.repeatablePlays}</strong><span>repeatable plays{overview.topPlay ? ` · ${overview.topPlay} leads across ${overview.topPlayAccounts} accounts` : ""}</span></div></div>
    <div className="exec-domain-stats"><div><strong>{overview.accounts}</strong><span>Accounts</span></div><div><strong>{overview.strongRecommendations}</strong><span>High / very high</span></div><div><strong>{overview.veryHighRecommendations}</strong><span>Very high</span></div><div><strong>{overview.repeatablePlays}</strong><span>Repeatable plays</span></div><div><strong>{overview.topPlayAccounts}</strong><span>Accounts in top play</span></div><div><strong>{overview.formattedPeerWonRevenueMedian}</strong><span>Median peer-win ACV</span></div></div>
  </section>
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">Ranked worklist</p><h2>Plays ready for a pilot</h2></div><span>{data.opportunityPlays.length} shown</span></div>
      <div className="exec-list">{data.opportunityPlays.map((p, i) => { const action = data.actions.find(item => item.key === `opportunity:${p.key}`); return <article className="exec-row exec-row--with-action" key={p.key}>
        <div className="exec-rank">{i + 1}</div><div className="exec-row__main"><h3>{p.offering}</h3><p>{p.reason}</p><strong>{p.pilotAccount}</strong></div>
        <dl className="exec-row__facts"><div><dt>Customers</dt><dd>{p.customerCount}</dd></div><div><dt>Owners</dt><dd>{p.ownerCount}</dd></div><div><dt>Confidence</dt><dd>{p.confidence}</dd></div><div><dt>Best pilot</dt><dd>{p.pilotAccount}</dd></div></dl>
        <div className="exec-row__action"><span>The action</span><strong>{action?.nextStep ?? p.nextStep}</strong>{action && <button type="button" className="exec-link" onClick={() => openAction(action.key)}>Open action</button>}</div>
      </article>; })}</div></section></>;
}

function Anomalies({ data }: { data: ExecutivePayload }) {
  const { openAction } = useApp();
  const [severity, setSeverity] = useState("All");
  const [category, setCategory] = useState("All");
  const [findingOwner, setFindingOwner] = useState("All");
  const [stalledOwner, setStalledOwner] = useState("All");
  const rows = data.anomalyFindings.filter((f) => (severity === "All" || f.severity === severity) && (category === "All" || f.category === category) && (findingOwner === "All" || f.owner === findingOwner));
  const stalledRows = data.stalledDeals.filter(d => stalledOwner === "All" || d.owner === stalledOwner);
  const overview = data.anomalyOverview;
  const forecastMix = overview.forecastCalls.filter(group => group.deals > 0).map(group => `${group.deals} ${group.call}`).join(", ");
  return <><section className="exec-domain-overview" aria-labelledby="anomaly-overview-title">
    <div className="exec-domain-overview__head"><div><p className="exec-eyebrow">Pipeline and account overview</p><h2 id="anomaly-overview-title">Stagnant deals and account anomalies</h2></div>
      <details className="exec-info"><summary aria-label="How stagnant deals and account anomalies are defined">i</summary><div><b>Definitions</b><p>A stagnant deal is open with no logged field change for at least 60 days. Stalled ACV Revenue covers every stalled deal in the current scope; the table lists the five longest-silent deals. Account findings are separate signals, and a deal or account can meet more than one condition.</p></div></details>
    </div>
    <div className="exec-domain-leads"><div><strong>{overview.stalledDeals}</strong><span>stagnant deals across {overview.stalledAccounts} accounts · {overview.stalledPastDue} are past due</span></div><div><strong>{overview.accountFindings}</strong><span>account anomalies across {overview.accountsAffected} accounts · {overview.criticalAccountFindings} critical</span></div></div>
    <div className="exec-domain-stats"><div><strong>{overview.stalledDeals}</strong><span>Stagnant deals</span></div><div><strong>{overview.formattedStalledRevenue}</strong><span>Stalled ACV Revenue</span></div><div><strong>{overview.stalledPastDue}</strong><span>Also past due</span></div><div><strong>{overview.longestSilenceDays}d</strong><span>Longest silence</span></div><div><strong>{overview.accountFindings}</strong><span>Account anomalies</span></div><div><strong>{overview.criticalAccountFindings}</strong><span>Critical findings</span></div></div>
  </section>
  <section className="exec-section exec-anomaly-insights" aria-labelledby="stagnation-title">
    <div className="exec-section__head"><div><p className="exec-eyebrow">How long they have been still</p><h2 id="stagnation-title">Stagnant-deal inactivity</h2></div><details className="exec-info"><summary aria-label="Why inactivity matters">i</summary><div><b>Why this matters</b><p>Each band contains open deals with no logged field change. The supplied anomaly guide treats this as a worklist for confirming the deal’s real status, updating it, or closing it out; it is not a final verdict on a deal.</p></div></details></div>
    <div className="exec-anomaly-silence">{overview.stagnationBands.map((band, index) => <div key={band.label} className="exec-anomaly-silence__row"><div className="exec-anomaly-silence__label">{band.label}</div><div className="exec-anomaly-silence__bar-wrap"><div className={`exec-anomaly-silence__bar exec-anomaly-silence__bar--${index === 0 ? "blue" : index === 1 ? "gold" : "red"}`} style={{ width: `${band.share * 100}%` }} /></div><div className="exec-anomaly-silence__meta">{band.deals} deals · {band.formattedRevenue}</div></div>)}</div>
    <p className="exec-anomaly-silence__caption">Forecast-call mix: {forecastMix}. The five rows below are the longest-silent examples.</p>
  </section>
  <section className="exec-section exec-anomaly-table">
    <div className="exec-section__head"><div><p className="exec-eyebrow">Pipeline inactivity</p><h2>Deals with no recent movement</h2><p>Each action below is backed by a matching stalled-pipeline finding from the supplied anomaly output.</p></div><div className="exec-controls"><label>Owner<select value={stalledOwner} onChange={e => setStalledOwner(e.target.value)}><option>All</option>{[...new Set(data.stalledDeals.map(d => d.owner))].sort().map(v => <option key={v}>{v}</option>)}</select></label></div></div>
    <div className="exec-anomaly-table__wrap">
      <table className="exec-anomaly-table__table">
        <thead>
          <tr><th>Account and line</th><th>Owner</th><th>ACV Revenue</th><th>Call</th><th>Days in stage</th><th>Days silent</th><th>Stage</th><th>Action</th></tr>
        </thead>
        <tbody>
          {stalledRows.map(d => {
            const action = d.actionKey ? data.actions.find(item => item.key === d.actionKey) : undefined;
            return <tr key={d.key}>
              <td><div className="exec-anomaly-table__account"><strong>{d.account}</strong><span>{d.deal}</span></div></td>
              <td>{d.owner}</td>
              <td><span className="exec-anomaly-table__money">{d.dealValueLabel}</span></td>
              <td><span className={`exec-anomaly-table__call exec-anomaly-table__call--${d.call.toLowerCase().includes("best") ? "best" : "commit"}`}>{d.call}</span></td>
              <td>{d.daysInStage}</td>
              <td>{d.silenceDays}</td>
              <td>{d.stage}</td>
              <td>{action ? <div className="exec-anomaly-table__action"><span>{action.nextStep}</span><button type="button" className="exec-link" onClick={() => openAction(action.key)}>Open action</button></div> : <span aria-label="No backend action available">—</span>}</td>
            </tr>;
          })}
        </tbody>
      </table>
    </div>
    {!stalledRows.length && <p className="exec-empty">No stagnant open deal matches this owner.</p>}
  </section>
  <section className="exec-section">
    <div className="exec-section__head"><div><p className="exec-eyebrow">Account-level findings</p><h2>Investigate the account pattern</h2></div><div className="exec-controls"><label>Severity<select value={severity} onChange={(e) => setSeverity(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></label><label>Category<select value={category} onChange={(e) => setCategory(e.target.value)}><option>All</option>{[...new Set(data.anomalyFindings.map(f => f.category))].sort().map(v => <option key={v}>{v}</option>)}</select></label><label>Owner<select value={findingOwner} onChange={e => setFindingOwner(e.target.value)}><option>All</option>{[...new Set(data.anomalyFindings.map(f => f.owner))].sort().map(v => <option key={v}>{v}</option>)}</select></label></div></div>
    <div className="exec-list">{rows.map((f) => { const action = data.actions.find(item => item.key === `anomaly:${f.key}`); return <article className="exec-row exec-row--with-action" key={f.key}><span className={`exec-badge exec-badge--${f.severity.toLowerCase()}`}>{f.severity}</span><div className="exec-row__main"><h3>{f.entity}</h3><p>{f.evidence}</p><strong>{f.question}</strong></div><dl className="exec-row__facts"><div><dt>Category</dt><dd>{f.category}</dd></div><div><dt>Owner</dt><dd>{f.owner}</dd></div></dl><div className="exec-row__action"><span>The action</span><strong>{f.nextStep}</strong>{action && <button type="button" className="exec-link" onClick={() => openAction(action.key)}>Open action</button>}</div></article>; })}</div>
    {!rows.length && <p className="exec-empty">No findings match these local filters.</p>}
  </section></>;
}

function ClosureRisk({ data }: { data: ExecutivePayload }) {
  const { openAction } = useApp();
  const [band, setBand] = useState("All"); const [forecast, setForecast] = useState("All"); const [stage, setStage] = useState("All"); const [owner, setOwner] = useState("All");
  const rows = data.closureExceptions.filter(d => (band === "All" || d.riskBand === band) && (forecast === "All" || d.forecastCategory === forecast) && (stage === "All" || d.stage === stage) && (owner === "All" || d.owner === owner));
  const options = (key: "forecastCategory" | "stage" | "owner") => [...new Set(data.closureExceptions.map(d => d[key]))].sort();
  return <>
    <section className="exec-revenue-overview" aria-labelledby="closure-revenue-title">
      <div className="exec-revenue-overview__head"><div><p className="exec-eyebrow">Declared against defensible</p><h2 id="closure-revenue-title">Revenue confidence by forecast category</h2></div>
        <details className="exec-info"><summary aria-label="How defensible revenue is calculated">i</summary><div><b>How this is calculated</b><p>Declared includes every open deal in the forecast category. Defensible keeps Commit deals at or above 35% model closure probability and Best Case deals at or above 25%. These are screening thresholds for review, not a forecast guarantee. Account cycle context compares the planned total cycle with at least three prior closed deals at the same account; it flags a mismatch only when the planned cycle is at least 30 days and 25% shorter than the account median. This context does not change model probability. {data.closureModel.text}</p></div></details>
      </div>
      <div className="exec-revenue-series">{data.closureOverview.series.map(series => {
        const retained = series.retainedShare == null ? 0 : Math.max(0, Math.min(100, series.retainedShare * 100));
        return <article key={series.forecast} className={`exec-revenue-series__item exec-revenue-series__item--${series.forecast === "Commit" ? "commit" : "best-case"}`}>
          <div className="exec-revenue-line"><span>{series.forecast} · declared</span><strong>{series.formattedDeclaredRevenue}</strong></div>
          <div className="exec-revenue-track" aria-hidden="true"><span className="exec-revenue-fill exec-revenue-fill--declared" /></div>
          <div className="exec-revenue-line"><span>{series.forecast} · defensible</span><strong>{series.formattedDefensibleRevenue}</strong></div>
          <div className="exec-revenue-track" aria-hidden="true"><span className="exec-revenue-fill exec-revenue-fill--defensible" style={{ width: `${retained}%` }} /></div>
          <p>{series.defensibleDeals == null ? "Model scoring is unavailable for this category." : <>{series.defensibleDeals} of {series.declaredDeals} deals remain · {series.formattedScreenedOutRevenue} needs stronger evidence or reclassification</>}</p>
        </article>;
      })}</div>
      <div className="exec-pipeline-stats" aria-label="Pipeline status">
        <div><strong>{data.closureOverview.stats.openDeals}</strong><span>Open deals</span></div>
        <div><strong>{data.closureOverview.stats.highRiskDeals}</strong><span>High / critical</span></div>
        <div><strong>{data.closureOverview.stats.pastDueDeals}</strong><span>Past due</span></div>
        <div><strong>{data.closureOverview.stats.stalledDeals}</strong><span>Stalled</span></div>
        <div><strong>{data.closureOverview.stats.slippedDeals}</strong><span>Slipped</span></div>
        <details className="exec-info exec-info--stats"><summary aria-label="About pipeline status definitions">i</summary><div><b>What these stats mean</b><p>High / critical uses the observable risk score. Past due compares the close date with the data cut. Stalled reflects prolonged inactivity; slipped means the close date moved later at least once. A deal may appear in more than one group.</p></div></details>
      </div>
    </section>
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">Exceptions</p><h2>Commit first, then Best Case</h2><p>Every scenario keeps its evidence and action together.</p></div><div className="exec-controls"><label>Risk<select value={band} onChange={e => setBand(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Watch</option><option>Low</option></select></label><label>Forecast<select value={forecast} onChange={e => setForecast(e.target.value)}><option>All</option>{options("forecastCategory").map(v => <option key={v}>{v}</option>)}</select></label><label>Stage<select value={stage} onChange={e => setStage(e.target.value)}><option>All</option>{options("stage").map(v => <option key={v}>{v}</option>)}</select></label><label>Owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{options("owner").map(v => <option key={v}>{v}</option>)}</select></label></div></div>
      <div className="exec-list">{rows.map(d => { const action = data.actions.find(item => item.key === `closure:${d.key}`); return <article className="exec-row exec-row--with-action" key={d.key}><span className={`exec-score exec-score--${d.riskBand.toLowerCase()}`}>{d.riskScore}</span><div className="exec-row__main"><h3>{d.deal}</h3><p>{d.account} · {d.mainDriver}</p><strong>{d.owner} · closes {d.closeDate ?? "date unavailable"}</strong></div><dl className="exec-row__facts"><div><dt>Forecast</dt><dd>{d.forecastCategory}</dd></div><div><dt>Risk</dt><dd>{d.riskBand}</dd></div><div><dt>Closure probability</dt><dd>{d.closureProbability == null ? "—" : `${Math.round(d.closureProbability * 100)}%`}</dd></div><div><dt>Deterioration</dt><dd>{d.deterioration}</dd></div><div><dt>Silence</dt><dd>{d.silenceDays == null ? "—" : `${d.silenceDays} days`}</dd></div><div><dt>ACV Revenue</dt><dd>{d.formattedRevenue}</dd></div>{d.accountCycleContext && <div className={`exec-account-cycle${d.accountCycleMismatch ? " exec-account-cycle--warn" : ""}`}><dt>Account decision cycle</dt><dd>{d.accountCycleContext}</dd></div>}</dl><div className="exec-row__action"><span>The action</span><strong>{action?.nextStep ?? "Validate the evidence and assign an owner."}</strong>{action && <button type="button" className="exec-link" onClick={() => openAction(action.key)}>Open action</button>}</div></article>; })}</div>
      {!rows.length && <p className="exec-empty">No commitments match these local filters.</p>}
    </section></>;
}

type ActionView = "all" | "urgent" | "week" | "review" | "monitoring" | "actioned" | "open";

function ActionsCenter({ data, asOf }: { data: ExecutivePayload; asOf: string }) {
  const { state } = useApp();
  const storageKey = `ntt.executive-actions.v1:${state.identity}`;
  const [saved, setSaved] = useState<DecisionMap>({});
  const [view, setView] = useState<ActionView>("urgent");
  const [theme, setTheme] = useState("All");
  const [owner, setOwner] = useState("All");
  const [sort, setSort] = useState("priority");
  const [expanded, setExpanded] = useState<string | null>(state.actionKey);
  const [pending, setPending] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const refs = useRef<Record<string, HTMLElement | null>>({});
  useEffect(() => { try { setSaved(JSON.parse(localStorage.getItem(storageKey) ?? "{}")); } catch { setSaved({}); } }, [storageKey]);
  useEffect(() => { if (!state.actionKey) return; setView("all"); setExpanded(state.actionKey); requestAnimationFrame(() => refs.current[state.actionKey!]?.focus()); }, [state.actionKey]);
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
    .filter(a => matchesView(a) && (theme === "All" || a.theme === theme) && (owner === "All" || a.owner === owner))
    .sort((a, b) => sort === "due" ? a.dueDate.localeCompare(b.dueDate) : PRIORITY[a.priority] - PRIORITY[b.priority] || a.dueDate.localeCompare(b.dueDate)),
  [data.actions, saved, view, theme, owner, sort, asOf]);
  const save = (a: ExecutiveAction, optionKey: string) => {
    const option = a.options.find(o => o.key === optionKey); if (!option) return;
    const reason = (reasons[a.key] ?? "").trim(); if (option.needsReason && !reason) return;
    const next = { ...saved, [a.key]: { optionKey, status: option.status, ...(reason ? { reason } : {}), updatedAt: new Date().toISOString() } };
    setSaved(next); localStorage.setItem(storageKey, JSON.stringify(next));
    setPending(p => ({ ...p, [a.key]: "" })); setReasons(r => ({ ...r, [a.key]: "" }));
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
  return <section className="exec-actions" aria-labelledby="action-center-title">
    <div className="exec-action-center__head"><div><p className="exec-eyebrow">What to commit now?</p><h2 id="action-center-title">Action Center</h2><p>Execute, delegate, snooze, or dismiss. Decisions are saved in this browser for {state.identity}.</p></div><div className="exec-controls"><label>Theme<select value={theme} onChange={e => setTheme(e.target.value)}><option>All</option><option value="opportunities">Cross-sell / Upsell</option><option value="anomalies">Anomaly Detection</option><option value="closure">Deal Closure</option></select></label><label>Owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{owners.map(v => <option key={v}>{v}</option>)}</select></label><label>Sort<select value={sort} onChange={e => setSort(e.target.value)}><option value="priority">Priority</option><option value="due">Due date</option></select></label></div></div>
    <div className="exec-action-summary" aria-label="Action summary"><button type="button" onClick={() => setView("urgent")}><span>Urgent</span><strong>{counts.urgent}</strong></button><button type="button" onClick={() => setView("week")}><span>Due this week</span><strong>{counts.week}</strong></button><button type="button" onClick={() => setView("review")}><span>Delegated</span><strong>{counts.review}</strong></button><button type="button" onClick={() => setView("actioned")}><span>Executed</span><strong>{counts.actioned}</strong></button><button type="button" onClick={() => setView("open")}><span>Still open</span><strong>{counts.open}</strong></button></div>
    <div className="exec-action-tabs" role="tablist" aria-label="Action status">{tabs.map(tab => <button key={tab.key} type="button" role="tab" aria-selected={view === tab.key} className={view === tab.key ? "is-active" : ""} onClick={() => setView(tab.key)}>{tab.label}<span>{tab.count}</span></button>)}</div>
    <div className="exec-action-cards">{rows.map(a => {
      const selected = pending[a.key] ?? ""; const option = a.options.find(o => o.key === selected); const open = expanded === a.key;
      const options = [...a.options].sort((left, right) => order.indexOf(left.status) - order.indexOf(right.status));
      return <article className={`exec-action-card exec-action-card--${a.theme}${open ? " is-open" : ""}`} key={a.key} tabIndex={-1} ref={el => { refs.current[a.key] = el; }}>
        <button type="button" className="exec-action-card__summary" onClick={() => setExpanded(open ? null : a.key)} aria-expanded={open}><span className="exec-action-card__theme">{THEME_LABEL[a.theme]}</span><span className={`exec-badge exec-badge--${a.priority.toLowerCase()}`}>{a.priority}</span><span className="exec-status">{effectiveStatus(a)}</span><strong>{a.headline}</strong><small>{a.owner} · due {a.dueDate}</small><span className="exec-action-card__toggle" aria-hidden="true">{open ? "−" : "+"}</span></button>
        {open && <div className="exec-action-card__body"><div className="exec-action-card__copy"><span>Why this matters</span><p>{a.description}</p><span>Next step</span><strong>{a.nextStep}</strong>{a.formattedRevenueImpact && <small>Relevant ACV Revenue: {a.formattedRevenueImpact}</small>}</div><div className="exec-action-card__buttons">{options.map(o => <button key={o.key} type="button" className={`exec-decision exec-decision--${o.status.toLowerCase().replace(" ", "-")}`} onClick={() => choose(a, o.key)}>{buttonLabel(o.status)}</button>)}</div>{option?.needsReason && <div className="exec-action-card__reason"><label>Reason required<textarea value={reasons[a.key] ?? ""} onChange={e => setReasons(r => ({ ...r, [a.key]: e.target.value }))} placeholder={`Why ${buttonLabel(option.status).toLowerCase()} this action?`} required /></label><button type="button" className="exec-save" disabled={!(reasons[a.key] ?? "").trim()} onClick={() => save(a, selected)}>Confirm {buttonLabel(option.status)}</button></div>}{saved[a.key] && <small className="exec-action-card__updated">Updated {new Date(saved[a.key].updatedAt).toLocaleString()}</small>}</div>}
      </article>;
    })}</div>{!rows.length && <p className="exec-empty">No actions match this view.</p>}
  </section>;
}

export function ExecutivePage({ payload, meta }: { payload: ViewPayload; meta: MetaPayload | null }) {
  const { state, onFilter, setFilter, clearFilters } = useApp(); const data = payload.executive;
  const briefSeenKey = `ntt.executive-brief.seen:${state.identity}`;
  const [briefModalOpen, setBriefModalOpen] = useState(() => sessionStorage.getItem(briefSeenKey) !== "1");
  useEffect(() => { setBriefModalOpen(sessionStorage.getItem(briefSeenKey) !== "1"); }, [briefSeenKey]);
  const closeBriefModal = () => { sessionStorage.setItem(briefSeenKey, "1"); setBriefModalOpen(false); };
  if (!data) return <section className="pv exec" aria-labelledby="exec-contract-error">
    <div className="pv-error" role="alert">
      <p className="pv-error__label">Executive pages could not load</p>
      <h1 className="pv-error__title" id="exec-contract-error">The web app is connected to an older API process</h1>
      <p className="pv-error__detail">Stop the existing servers, start this project with <code>ntt-command-centre/run.sh</code>, then reload the page.</p>
    </div>
  </section>;
  const isBrief = payload.page === "tldr";
  return <section className={`pv exec${isBrief ? " pv--executive-brief" : ""}`} aria-labelledby="pv-question"><header className="pv-head"><div className="pv-head__text"><h1 className="pv-head__question" id="pv-question">{payload.label}</h1><p className="exec-head__subheading">{payload.question}</p><p className="pv-head__meta">{payload.scope.label} · {payload.quarter} · as of {longDate(payload.asOf)}</p></div><div className="pv-head__controls">{isBrief && <button type="button" className="exec-link exec-link--quiet" onClick={() => setBriefModalOpen(true)}>Open overview</button>}<MoreFilters dimensions={meta?.dimensions ?? []} active={state.filters} onSet={setFilter} onClear={clearFilters} /></div></header>
    {payload.filters.length > 0 && <div className="pv-filters" aria-label="Active filters"><span className="pv-filters__label">Filtered</span>{payload.filters.map(f => <button type="button" className="pv-filters__chip" key={f.dim} onClick={()=>onFilter(f.dim as "country"|"quarter",f.value)}><span className="pv-filters__dim">{f.label}</span><span className="pv-filters__value">{f.value}</span><span className="pv-filters__x" aria-hidden="true">×</span></button>)}<button type="button" className="pv-filters__clear" onClick={clearFilters}>Clear all</button></div>}
    {isBrief && <Brief data={data} modalOpen={briefModalOpen} closeModal={closeBriefModal} />}{payload.page === "opportunities" && <Opportunities data={data} />}{payload.page === "anomalies" && <Anomalies data={data} />}{payload.page === "closure-risk" && <ClosureRisk data={data} />}{payload.page === "action-center" && <ActionsCenter data={data} asOf={payload.asOf} />}
  </section>;
}
