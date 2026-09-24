/** Curated page summaries over the existing, referenceable KPI contract. */
import {
  Fragment,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type FocusEvent as ReactFocusEvent,
} from "react";
import type { Kpi, MetricBanner } from "../api/types";
import { useApp } from "../state/AppStateProvider";
import { SIZE, Solid, solidFor } from "./icons";

const DIRECTION: Record<Kpi["direction"], { lead: string; rest: string }> = {
  "up-good": {
    lead: "Higher is better.",
    rest: "A rising figure here is good news; its colour says how it stands now.",
  },
  "up-bad": {
    lead: "Lower is better.",
    rest: "A rising figure here is a warning; its colour says how it stands now.",
  },
  neutral: {
    lead: "Neither direction is better.",
    rest: "This figure describes the scope rather than scoring it.",
  },
};

function BannerSpark({ kpi }: { kpi: Kpi }) {
  const points = kpi.spark ?? [];
  if (points.length < 3) return null;
  const width = 150;
  const height = 32;
  const lo = Math.min(...points);
  const span = Math.max(...points) - lo || 1;
  const x = (i: number) => 2 + (i / (points.length - 1)) * (width - 4);
  const y = (v: number) => height - 3 - ((v - lo) / span) * (height - 6);
  const path = points.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const last = points.length - 1;
  return (
    <div className={`metric-banner__trend metric-banner__trend--${kpi.tone}`}>
      <span className="metric-banner__trend-label">{kpi.label} trend</span>
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-hidden="true">
        <path d={`${path} L${width - 2} ${height} L2 ${height} Z`} className="metric-banner__trend-fill" />
        <path d={path} className="metric-banner__trend-line" />
        <circle cx={x(last)} cy={y(points[last])} r="2.4" className="metric-banner__trend-dot" />
      </svg>
    </div>
  );
}

function MetricPopover({ kpi, id, anchor, onClose }: {
  kpi: Kpi;
  id: string;
  anchor: HTMLElement | null;
  onClose: () => void;
}) {
  const { openAsk } = useApp();
  const ref = useRef<HTMLDivElement | null>(null);
  const [place, setPlace] = useState({ flip: false, above: false });
  const direction = DIRECTION[kpi.direction];

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const bounds = el.getBoundingClientRect();
    const margin = 12;
    const roomAbove = anchor ? anchor.getBoundingClientRect().top - margin : 0;
    setPlace({
      flip: bounds.right > window.innerWidth - margin,
      above: bounds.bottom > window.innerHeight - margin && roomAbove >= bounds.height,
    });
  }, [anchor]);

  useEffect(() => {
    ref.current?.focus({ preventScroll: true });
  }, []);

  return (
    <div
      className={[
        "kpi-pop",
        `kpi-pop--${kpi.tone}`,
        place.flip ? "kpi-pop--flip" : "",
        place.above ? "kpi-pop--above" : "",
      ].filter(Boolean).join(" ")}
      id={id}
      ref={ref}
      role="dialog"
      aria-label={`${kpi.label}: ${kpi.formatted}`}
      tabIndex={-1}
    >
      <div className="kpi-pop__head">
        <span className="kpi-row__icon kpi-pop__mark" aria-hidden="true">
          <Solid name={solidFor(kpi.icon)} size={SIZE.hero} />
        </span>
        <div className="kpi-pop__title">
          <h3 className="kpi-pop__label">{kpi.label}</h3>
          <span className="kpi-pop__value">{kpi.formatted}</span>
        </div>
      </div>
      <p className="kpi-pop__sub">{kpi.sub}</p>
      <p className="kpi-pop__dir"><strong>{direction.lead}</strong> {direction.rest}</p>
      <div className="kpi-pop__actions">
        <button
          type="button"
          className="kpi-pop__btn kpi-pop__btn--ask"
          onClick={() => {
            onClose();
            openAsk(`What is behind ${kpi.label.toLowerCase()}?`);
          }}
        >
          Ask about this number
        </button>
        <button type="button" className="kpi-pop__btn" onClick={onClose}>Close</button>
      </div>
    </div>
  );
}

function InlineMetric({ kpi, open, onToggle, onClose }: {
  kpi: Kpi;
  open: boolean;
  onToggle: () => void;
  onClose: () => void;
}) {
  const wrapRef = useRef<HTMLSpanElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const popoverId = useId();
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      closeRef.current();
      buttonRef.current?.focus();
    };
    const onPointer = (event: MouseEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) closeRef.current();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open]);

  const onBlur = (event: ReactFocusEvent<HTMLSpanElement>) => {
    if (open && event.relatedTarget && !wrapRef.current?.contains(event.relatedTarget)) onClose();
  };

  return (
    <span className={`metric-banner__anchor${open ? " metric-banner__anchor--open" : ""}`} ref={wrapRef} onBlur={onBlur}>
      <button
        type="button"
        ref={buttonRef}
        className={`metric-banner__metric metric-banner__metric--${kpi.tone}`}
        aria-label={`${kpi.label}: ${kpi.formatted}. Open details.`}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? popoverId : undefined}
        onClick={onToggle}
      >
        {kpi.formatted}
      </button>
      {open ? <MetricPopover kpi={kpi} id={popoverId} anchor={wrapRef.current} onClose={() => {
        onClose();
        buttonRef.current?.focus();
      }} /> : null}
    </span>
  );
}

function Banner({ banner, byKey, openKey, setOpenKey }: {
  banner: MetricBanner;
  byKey: Map<string, Kpi>;
  openKey: string | null;
  setOpenKey: (key: string | null) => void;
}) {
  const trend = banner.trendMetricKey ? byKey.get(banner.trendMetricKey) : undefined;
  return (
    <article className={`metric-banner metric-banner--${banner.prominence} metric-banner--${banner.tone}`}>
      <div className="metric-banner__copy">
        <div className="metric-banner__statement" role="heading" aria-level={2}>
          {banner.statement.map((part, index) => {
            if (part.kind === "text") return <Fragment key={index}>{part.text}</Fragment>;
            const kpi = byKey.get(part.metricKey);
            if (!kpi) return null;
            return (
              <InlineMetric
                key={`${part.metricKey}-${index}`}
                kpi={kpi}
                open={openKey === part.metricKey}
                onToggle={() => setOpenKey(openKey === part.metricKey ? null : part.metricKey)}
                onClose={() => setOpenKey(null)}
              />
            );
          })}
        </div>
        <p className="metric-banner__subline">{banner.subline}</p>
      </div>
      {banner.prominence === "primary" && trend ? <BannerSpark kpi={trend} /> : null}
    </article>
  );
}

export function MetricBannerGroup({ banners, kpis }: { banners: MetricBanner[]; kpis: Kpi[] }) {
  const [openKey, setOpenKey] = useState<string | null>(null);
  const byKey = useMemo(() => new Map(kpis.map((kpi) => [kpi.key, kpi])), [kpis]);
  useEffect(() => setOpenKey(null), [banners, kpis]);
  return (
    <section className="metric-banners" aria-label="Key figures for the current scope">
      <p className="visually-hidden" role="status" aria-live="polite">
        {kpis.length} key figures updated
      </p>
      {banners.map((banner) => (
        <Banner key={banner.key} banner={banner} byKey={byKey} openKey={openKey} setOpenKey={setOpenKey} />
      ))}
    </section>
  );
}
