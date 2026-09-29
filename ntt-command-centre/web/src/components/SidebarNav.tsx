/**
 * The persona's own navigation.
 *
 * Grouped rather than a flat tab rail, because fourteen pages across three
 * profiles is a product, not a dashboard — and the grouping is itself
 * information: an AE's pages are their day, their deals, their accounts and
 * their record, in that order, which is the order they think in.
 *
 * Built from `meta.pages`, which the server derives from the persona. A profile
 * cannot see the NAME of a page belonging to someone else's job, so there is no
 * disabled state here and nothing to grey out.
 *
 * Each item carries its page's stated question as its title and its second
 * line, because the question is what tells you whether this is the page you
 * want — "Calibration" alone does not.
 */
import type { ExecutivePayload, Lens, PersonaKey } from "../api/types";
import { Icon, SIZE, type IconName } from "./icons";

export interface NavItem {
  key: Lens;
  label: string;
  question: string;
}

/** Which group a page belongs to, per persona. */
type NavGroup = {
  heading: string;
  pages: Lens[];
  emphasis?: "closure" | "anomaly" | "cross-sell";
};

const GROUPS: Record<PersonaKey, NavGroup[]> = {
  ae: [
    { heading: "Today", pages: ["my-day"] },
    { heading: "My book", pages: ["my-deals", "my-accounts"] },
    { heading: "Me", pages: ["my-record"] },
  ],
  manager: [
    { heading: "This week", pages: ["pod-pulse"] },
    { heading: "The people", pages: ["rep-benchmark", "calibration"] },
    { heading: "The process", pages: ["process", "pod-whitespace"] },
  ],
  executive: [
    { heading: "Weekly overview", pages: ["tldr"] },
    { heading: "Deal closure likelihood", pages: ["low-probability", "slippage-risk"], emphasis: "closure" },
    { heading: "Anomaly Detection", pages: ["stagnated-deals"], emphasis: "anomaly" },
    { heading: "Cross-sell and upsell", pages: ["opportunities"], emphasis: "cross-sell" },
    { heading: "Decision workflow", pages: ["action-center"] },
  ],
};

/**
 * The mark beside each page, from the shell's one icon set. Pages that ask
 * the same kind of question share a mark — growth and whitespace are both
 * "where is there more", performance is "how are we doing against plan" —
 * so the rail reads as families of questions rather than fifteen pictures.
 */
const ICON: Partial<Record<Lens, IconName>> = {
  "my-day": "today",
  "my-deals": "deals",
  "my-accounts": "accounts",
  "my-record": "record",
  "pod-pulse": "team",
  "rep-benchmark": "compare",
  process: "process",
  calibration: "calibrate",
  "pod-whitespace": "grow",
  tldr: "brief",
  opportunities: "grow",
  "low-probability": "deals",
  "slippage-risk": "process",
  "stagnated-deals": "risks",
  "account-anomalies": "accounts",
  "action-center": "decisions",
};

export function SidebarNav({
  persona,
  pages,
  current,
  onNavigate,
  executive,
  collapsed = false,
}: {
  persona: PersonaKey;
  pages: NavItem[];
  current: Lens;
  onNavigate: (page: Lens) => void;
  executive?: ExecutivePayload;
  collapsed?: boolean;
}) {
  const byKey = new Map(pages.map((p) => [p.key, p]));
  // Anything the server sent that this file has not been told where to put
  // still appears, in its own group, rather than silently vanishing.
  const placed = new Set(GROUPS[persona].flatMap((g) => g.pages));
  const groups = [
    ...GROUPS[persona]
      .map((g) => ({ heading: g.heading, emphasis: g.emphasis, items: g.pages.map((k) => byKey.get(k)).filter(Boolean) }))
      .filter((g) => g.items.length > 0),
    ...(pages.some((p) => !placed.has(p.key))
      ? [{ heading: "More", emphasis: undefined, items: pages.filter((p) => !placed.has(p.key)) }]
      : []),
  ] as { heading: string; emphasis?: NavGroup["emphasis"]; items: NavItem[] }[];
  const pageNumber = new Map(pages.map((page, index) => [page.key, index + 1]));
  const executiveLabels: Partial<Record<Lens, string>> = {
    tldr: "This week",
    opportunities: "Growth plays",
    "action-center": "Action center",
  };
  const executiveLabel = (page: NavItem) => executiveLabels[page.key] ?? page.label;
  const executiveSummary = (page: NavItem) => {
    if (!executive) return page.question;
    switch (page.key) {
      case "tldr":
        return executive.weeklyInsights.length
          ? `${executive.weeklyInsights.length} insights, ${executive.weeklyInsights.length} actions`
          : "Weekly insights and actions";
      case "low-probability":
        return `${executive.closureOverview.formattedLowProbabilityRevenue} below 50% probability`;
      case "slippage-risk":
        return `${executive.closureOverview.formattedSlippageRevenue} with moved close dates`;
      case "stagnated-deals":
        // Page payloads empty the other pages' lists, so the rail reads the
        // overview counts, which every page receives in full.
        return `${executive.anomalyOverview.accountFindings} findings · ${executive.anomalyOverview.criticalAccountFindings} critical`;
      case "account-anomalies":
        return `${executive.anomalyOverview.formattedAccountRevenue} under investigation`;
      case "opportunities":
        return `${executive.opportunityOverview.formattedPeerWonRevenueMedian} median peer benchmark`;
      default:
        return page.question;
    }
  };

  return (
    <nav className={`side side--${persona}${collapsed ? " side--collapsed" : ""}`} aria-label="Pages">
      {groups.map((g) => (
        <div className={`side__group${g.emphasis ? ` side__group--${g.emphasis}` : ""}`} key={g.heading}>
          <p className="side__heading">{g.heading}</p>
          <ul className="side__list">
            {g.items.map((p) => {
              const on = p.key === current;
              return (
                <li key={p.key}>
                  <button
                    type="button"
                    className={`side__item${on ? " side__item--on" : ""}`}
                    aria-current={on ? "page" : undefined}
                    title={p.question}
                    onClick={() => onNavigate(p.key)}
                  >
                    <span className="side__glyph" aria-hidden="true">
                      {persona === "executive"
                        ? String(pageNumber.get(p.key) ?? 0).padStart(2, "0")
                        : <Icon name={ICON[p.key] ?? "chevron"} size={SIZE.nav} />}
                    </span>
                    <span className="side__text">
                      <span className="side__label">{persona === "executive" ? executiveLabel(p) : p.label}</span>
                      <span className="side__question">{persona === "executive" ? executiveSummary(p) : p.question}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
