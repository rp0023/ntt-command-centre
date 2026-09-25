import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ExecutiveAction, ExecutiveMessage, ExecutivePayload, ExecutiveTheme,
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

function MessagePanel({ message, compact = false }: { message: ExecutiveMessage; compact?: boolean }) {
  const { setPage } = useApp();
  return (
    <article className={`exec-message exec-message--${message.key}`}>
      <p className="exec-eyebrow">{message.title}</p>
      <h2>{message.headline}</h2>
      <p className="exec-message__summary">{message.summary}</p>
      <dl className="exec-signals">
        {message.signals.slice(0, 3).map((signal) => (
          <div key={signal.label}><dt>{signal.label}</dt><dd>{signal.value}</dd></div>
        ))}
      </dl>
      {!compact ? null : (
        <button className="exec-link" type="button" onClick={() => setPage(message.page)}>
          Open {message.title}
        </button>
      )}
    </article>
  );
}

function ActionLink({ action }: { action: ExecutiveAction }) {
  const { openAction } = useApp();
  return (
    <button type="button" className="exec-action-link" onClick={() => openAction(action.key)}>
      <span><b>{action.headline}</b><small>{action.owner} · due {action.dueDate}</small></span>
      <span aria-hidden="true">→</span>
    </button>
  );
}

function RelatedActions({ actions, theme }: { actions: ExecutiveAction[]; theme?: ExecutiveTheme }) {
  const shown = theme ? actions.filter((action) => action.theme === theme) : actions.slice(0, 3);
  if (!shown.length) return null;
  return (
    <section className="exec-section" aria-labelledby={`actions-${theme ?? "brief"}`}>
      <div className="exec-section__head"><div><p className="exec-eyebrow">Next</p>
        <h2 id={`actions-${theme ?? "brief"}`}>{theme ? "Actions from this signal" : "Top actions"}</h2></div></div>
      <div className="exec-action-links">{shown.map((a) => <ActionLink key={a.key} action={a} />)}</div>
    </section>
  );
}

function Brief({ data }: { data: ExecutivePayload }) {
  const { setPage } = useApp();
  return <>
    {data.weeklyBanner && <section className={`exec-weekly-banner exec-weekly-banner--${data.weeklyBanner.tone}`} aria-labelledby="weekly-banner-title">
      <div className="exec-weekly-banner__copy"><p className="exec-eyebrow">Weekly pipeline brief</p>
        <h2 id="weekly-banner-title">{data.weeklyBanner.headline}</h2><p>{data.weeklyBanner.subline}</p></div>
      <dl className="exec-weekly-banner__stats">{data.weeklyBanner.stats.map(stat => <div key={stat.label} className={`exec-weekly-banner__stat exec-weekly-banner__stat--${stat.tone}`}><dt>{stat.label}</dt><dd>{stat.value}</dd></div>)}</dl>
    </section>}
    <section className="exec-section" aria-labelledby="weekly-focus-title">
      <div className="exec-section__head"><div><p className="exec-eyebrow">Top five this week</p><h2 id="weekly-focus-title">Pipeline and conversion decisions</h2><p>Ranked for decision quality, with the evidence and next step kept together.</p></div></div>
      <ol className="exec-weekly-list">{data.weeklyInsights.map(insight => <li key={insight.key} className={`exec-weekly-insight exec-weekly-insight--${insight.theme}`}>
        <span className="exec-weekly-insight__rank">{insight.rank}</span><div className="exec-weekly-insight__body"><div className="exec-weekly-insight__head"><span>{THEME_LABEL[insight.theme]}</span><h3>{insight.title}</h3></div>
          <p className="exec-weekly-insight__conclusion">{insight.conclusion}</p><ul>{insight.evidence.map((line, index) => <li key={index}>{line}</li>)}</ul><p className="exec-weekly-insight__next"><b>Do this:</b> {insight.nextStep}</p></div>
        <button type="button" className="exec-link exec-weekly-insight__open" onClick={() => setPage(insight.page)}>Open {THEME_LABEL[insight.theme]}</button>
      </li>)}</ol>
    </section>
    <nav className="exec-usecase-nav" aria-label="Executive intelligence use cases">{data.messages.map(message => <button key={message.key} type="button" onClick={() => setPage(message.page)}><span>{message.title}</span><b>{message.headline}</b><i aria-hidden="true">→</i></button>)}</nav>
  </>;
}

function Opportunities({ data }: { data: ExecutivePayload }) {
  return <><MessagePanel message={data.messages[0]} />
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">Ranked worklist</p><h2>Plays ready for a pilot</h2></div><span>{data.opportunityPlays.length} shown</span></div>
      <div className="exec-list">{data.opportunityPlays.map((p, i) => <article className="exec-row" key={p.key}>
        <div className="exec-rank">{i + 1}</div><div className="exec-row__main"><h3>{p.offering}</h3><p>{p.reason}</p><strong>{p.nextStep}</strong></div>
        <dl className="exec-row__facts"><div><dt>Customers</dt><dd>{p.customerCount}</dd></div><div><dt>Owners</dt><dd>{p.ownerCount}</dd></div><div><dt>Confidence</dt><dd>{p.confidence}</dd></div><div><dt>Best pilot</dt><dd>{p.pilotAccount}</dd></div></dl>
      </article>)}</div></section><RelatedActions actions={data.actions} theme="opportunities" /></>;
}

function Anomalies({ data }: { data: ExecutivePayload }) {
  const [severity, setSeverity] = useState("All");
  const [agreement, setAgreement] = useState("All");
  const rows = data.anomalyFindings.filter((f) => (severity === "All" || f.severity === severity) && (agreement === "All" || f.agreement === agreement));
  return <><MessagePanel message={data.messages[1]} /><section className="exec-section">
    <div className="exec-section__head"><div><p className="exec-eyebrow">Prioritized findings</p><h2>Investigate the evidence</h2></div><div className="exec-controls"><label>Severity<select value={severity} onChange={(e) => setSeverity(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></label><label>Detector<select value={agreement} onChange={(e) => setAgreement(e.target.value)}><option>All</option>{[...new Set(data.anomalyFindings.map(f => f.agreement))].map(v => <option key={v}>{v}</option>)}</select></label></div></div>
    <div className="exec-list">{rows.map((f) => <article className="exec-row" key={f.key}><span className={`exec-badge exec-badge--${f.severity.toLowerCase()}`}>{f.severity}</span><div className="exec-row__main"><h3>{f.entity}</h3><p>{f.evidence}</p><strong>{f.question}</strong></div><dl className="exec-row__facts"><div><dt>Entity</dt><dd>{f.entityType}</dd></div><div><dt>Agreement</dt><dd>{f.agreement}</dd></div><div><dt>Owner</dt><dd>{f.owner}</dd></div></dl></article>)}</div>
    {!rows.length && <p className="exec-empty">No findings match these local filters.</p>}
  </section><RelatedActions actions={data.actions} theme="anomalies" /></>;
}

function ClosureRisk({ data }: { data: ExecutivePayload }) {
  const [band, setBand] = useState("All"); const [stage, setStage] = useState("All"); const [owner, setOwner] = useState("All");
  const rows = data.closureExceptions.filter(d => (band === "All" || d.riskBand === band) && (stage === "All" || d.stage === stage) && (owner === "All" || d.owner === owner));
  const options = (key: "stage" | "owner") => [...new Set(data.closureExceptions.map(d => d[key]))].sort();
  return <><MessagePanel message={data.messages[2]} /><aside className="exec-disclosure"><b>Directional model</b><span>{data.closureModel.text}</span></aside>
    <section className="exec-section"><div className="exec-section__head"><div><p className="exec-eyebrow">Exceptions</p><h2>Commitments requiring evidence</h2></div><div className="exec-controls"><label>Risk<select value={band} onChange={e => setBand(e.target.value)}><option>All</option><option>Critical</option><option>High</option><option>Watch</option><option>Low</option></select></label><label>Stage<select value={stage} onChange={e => setStage(e.target.value)}><option>All</option>{options("stage").map(v => <option key={v}>{v}</option>)}</select></label><label>Owner<select value={owner} onChange={e => setOwner(e.target.value)}><option>All</option>{options("owner").map(v => <option key={v}>{v}</option>)}</select></label></div></div>
      <div className="exec-list">{rows.map(d => <article className="exec-row" key={d.key}><span className={`exec-score exec-score--${d.riskBand.toLowerCase()}`}>{d.riskScore}</span><div className="exec-row__main"><h3>{d.deal}</h3><p>{d.account} · {d.mainDriver}</p><strong>{d.owner} · closes {d.closeDate ?? "date unavailable"}</strong></div><dl className="exec-row__facts"><div><dt>Risk</dt><dd>{d.riskBand}</dd></div><div><dt>Closure probability</dt><dd>{d.closureProbability == null ? "—" : `${Math.round(d.closureProbability * 100)}%`}</dd></div><div><dt>Silence</dt><dd>{d.silenceDays == null ? "—" : `${d.silenceDays} days`}</dd></div><div><dt>ACV Revenue</dt><dd>{d.formattedRevenue}</dd></div></dl></article>)}</div>
      {!rows.length && <p className="exec-empty">No commitments match these local filters.</p>}
    </section><RelatedActions actions={data.actions} theme="closure" /></>;
}

function ActionsCenter({ data }: { data: ExecutivePayload }) {
  const { state } = useApp(); const storageKey = `ntt.executive-actions.v1:${state.identity}`;
  const [saved, setSaved] = useState<DecisionMap>({}); const [theme, setTheme] = useState("All");
  const [status, setStatus] = useState("All"); const [priority, setPriority] = useState("All"); const [owner, setOwner] = useState("All"); const [sort, setSort] = useState("priority");
  const [expanded, setExpanded] = useState<string | null>(state.actionKey); const [pending, setPending] = useState<Record<string, string>>({}); const [reasons, setReasons] = useState<Record<string, string>>({});
  const refs = useRef<Record<string, HTMLElement | null>>({});
  useEffect(() => { try { setSaved(JSON.parse(localStorage.getItem(storageKey) ?? "{}")); } catch { setSaved({}); } }, [storageKey]);
  useEffect(() => { if (!state.actionKey) return; setExpanded(state.actionKey); requestAnimationFrame(() => refs.current[state.actionKey!]?.focus()); }, [state.actionKey]);
  const effectiveStatus = (a: ExecutiveAction) => saved[a.key]?.status ?? "New";
  const owners = [...new Set(data.actions.map(a => a.owner))].sort();
  const rows = useMemo(() => data.actions.filter(a => (theme === "All" || a.theme === theme) && (status === "All" || effectiveStatus(a) === status) && (priority === "All" || a.priority === priority) && (owner === "All" || a.owner === owner)).sort((a,b) => sort === "due" ? a.dueDate.localeCompare(b.dueDate) : PRIORITY[a.priority] - PRIORITY[b.priority] || a.dueDate.localeCompare(b.dueDate)), [data.actions, saved, theme, status, priority, owner, sort]);
  const save = (a: ExecutiveAction, optionKey: string) => { const option = a.options.find(o => o.key === optionKey); if (!option) return; const reason = (reasons[a.key] ?? "").trim(); if (option.needsReason && !reason) return; const next = { ...saved, [a.key]: { optionKey, status: option.status, ...(reason ? { reason } : {}), updatedAt: new Date().toISOString() } }; setSaved(next); localStorage.setItem(storageKey, JSON.stringify(next)); setPending(p => ({...p, [a.key]: ""})); };
  return <section className="exec-section exec-actions"><div className="exec-section__head"><div><p className="exec-eyebrow">Decision workspace</p><h2>Actions from the three leadership signals</h2><p>Saved in this browser · private to {state.identity}</p></div><div className="exec-controls"><label>Theme<select value={theme} onChange={e=>setTheme(e.target.value)}><option>All</option><option value="opportunities">Opportunities</option><option value="anomalies">Anomalies</option><option value="closure">Closure Risk</option></select></label><label>Status<select value={status} onChange={e=>setStatus(e.target.value)}><option>All</option>{["New","In Review","Actioned","Monitoring","Dismissed"].map(v=><option key={v}>{v}</option>)}</select></label><label>Priority<select value={priority} onChange={e=>setPriority(e.target.value)}><option>All</option>{["Critical","High","Medium","Low"].map(v=><option key={v}>{v}</option>)}</select></label><label>Owner<select value={owner} onChange={e=>setOwner(e.target.value)}><option>All</option>{owners.map(v=><option key={v}>{v}</option>)}</select></label><label>Sort<select value={sort} onChange={e=>setSort(e.target.value)}><option value="priority">Priority</option><option value="due">Due date</option></select></label></div></div>
    <div className="exec-list">{rows.map(a => { const selected = pending[a.key] ?? ""; const option = a.options.find(o=>o.key===selected); const open = expanded === a.key; return <article className={`exec-action${open ? " is-open" : ""}`} key={a.key} tabIndex={-1} ref={el=>{refs.current[a.key]=el;}}><button type="button" className="exec-action__summary" onClick={()=>setExpanded(open?null:a.key)} aria-expanded={open}><span className={`exec-badge exec-badge--${a.priority.toLowerCase()}`}>{a.priority}</span><span><b>{a.headline}</b><small>{THEME_LABEL[a.theme]} · {a.owner} · due {a.dueDate}</small></span><span className="exec-status">{effectiveStatus(a)}</span><span aria-hidden="true">{open ? "−" : "+"}</span></button>{open && <div className="exec-action__body"><p>{a.nextStep}</p>{a.formattedRevenueImpact && <p><b>Relevant ACV Revenue:</b> {a.formattedRevenueImpact}</p>}<label>Decision<select value={selected} onChange={e=>setPending(p=>({...p,[a.key]:e.target.value}))}><option value="">Choose…</option>{a.options.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}</select></label>{option?.needsReason && <label>Reason<textarea value={reasons[a.key] ?? ""} onChange={e=>setReasons(r=>({...r,[a.key]:e.target.value}))} required /></label>}<button type="button" className="exec-save" disabled={!option || (!!option.needsReason && !(reasons[a.key]??"").trim())} onClick={()=>save(a,selected)}>Save decision</button>{saved[a.key] && <small>Updated {new Date(saved[a.key].updatedAt).toLocaleString()}</small>}</div>}</article>; })}</div>{!rows.length && <p className="exec-empty">No actions match these filters.</p>}</section>;
}

export function ExecutivePage({ payload, meta }: { payload: ViewPayload; meta: MetaPayload | null }) {
  const { state, onFilter, setFilter, clearFilters } = useApp(); const data = payload.executive;
  if (!data) return <section className="pv exec" aria-labelledby="exec-contract-error">
    <div className="pv-error" role="alert">
      <p className="pv-error__label">Executive pages could not load</p>
      <h1 className="pv-error__title" id="exec-contract-error">The web app is connected to an older API process</h1>
      <p className="pv-error__detail">Stop the existing servers, start this project with <code>ntt-command-centre/run.sh</code>, then reload the page.</p>
    </div>
  </section>;
  return <section className="pv exec" aria-labelledby="pv-question"><header className="pv-head"><div className="pv-head__text"><h1 className="pv-head__question" id="pv-question">{payload.question}</h1><p className="pv-head__meta">{payload.scope.label} · {payload.quarter} · as of {longDate(payload.asOf)}</p></div><div className="pv-head__controls"><MoreFilters dimensions={meta?.dimensions ?? []} active={state.filters} onSet={setFilter} onClear={clearFilters} /></div></header>
    {payload.filters.length > 0 && <div className="pv-filters" aria-label="Active filters"><span className="pv-filters__label">Filtered</span>{payload.filters.map(f => <button type="button" className="pv-filters__chip" key={f.dim} onClick={()=>onFilter(f.dim as "country"|"quarter",f.value)}><span className="pv-filters__dim">{f.label}</span><span className="pv-filters__value">{f.value}</span><span className="pv-filters__x" aria-hidden="true">×</span></button>)}<button type="button" className="pv-filters__clear" onClick={clearFilters}>Clear all</button></div>}
    {payload.page === "tldr" && <Brief data={data} />}{payload.page === "opportunities" && <Opportunities data={data} />}{payload.page === "anomalies" && <Anomalies data={data} />}{payload.page === "closure-risk" && <ClosureRisk data={data} />}{payload.page === "action-center" && <ActionsCenter data={data} />}
  </section>;
}
