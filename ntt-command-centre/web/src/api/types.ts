/**
 * The wire contract, as the semantic layer actually serves it.
 *
 * Do not add a field here that `api/` does not send. Add it to the Python
 * payload first, verify it against a real response, then mirror it here.
 */

export type Tone = "accent" | "good" | "warn" | "danger" | "neutral";
export type CountBasis = "opportunities" | "lines";
export type PersonaKey = "ae" | "manager" | "executive";

/** Pages are persona-scoped; the union is every page any persona can reach. */
export type Lens =
  | "my-day" | "my-deals" | "my-accounts" | "my-record"
  | "pod-pulse" | "rep-benchmark" | "process" | "calibration" | "pod-whitespace"
  | "tldr" | "opportunities" | "low-probability" | "slippage-risk" | "stagnated-deals" | "account-anomalies" | "action-center";

export type DimKey =
  | "stage" | "forecast" | "lob" | "portfolio" | "industry"
  | "orderType" | "quarter" | "country" | "rep" | "account"
  | "riskBand" | "anomalyCategory";

export type Measure = "gp" | "revenue";
export type Urgency = "Critical" | "High" | "Medium" | "Low";
export type Format = "currency" | "percent" | "number" | "days";
export type RiskBand = "Low" | "Watch" | "High" | "Critical";

export type Shape =
  | "categorical×measure"
  | "temporal×measure"
  | "categorical×categorical×measure"
  | "categorical×series×measure"
  | "target×actual"
  | "bridge"
  | "temporal×measure×measure"
  | "cohort×stage"
  | "x×y×size"
  | "categorical×measure×width"
  | "hierarchy×measure"
  | "source×target×measure"
  | "entity×start×end"
  | "table";

/** One generated or computed sentence. `lens` is what licenses it to exist:
 *  a `state` sentence is only allowed when no chart on screen says the same. */
export interface Sentence {
  text: string;
  lens: "cause" | "norm" | "delta" | "action" | "answer" | "state";
  claim?: string | null;
  bold?: string[];
}

export interface Narrative {
  headline: string;
  sentences: Sentence[];
  provider?: string;
  model?: string;
  latencyMs?: number;
  degraded?: boolean;
  cached?: boolean;
  reason?: string;
  /** Provider diagnostics. Carried for debugging; never rendered to a user. */
  attempts?: { provider: string; ms: number; outcome: string }[];
  /** Sentences the server removed. Shown in the provenance drawer, not hidden. */
  dropped?: { text: string; reason: string }[];
  rejected?: { text: string; rejectedTokens: string[] }[];
}

export interface Kpi {
  key: string;
  label: string;
  value: number;
  formatted: string;
  sub: string;
  tone: Tone;
  /** Colour encodes goodness, not sign: past-due rising is red. */
  direction: "up-good" | "up-bad" | "neutral";
  /** A glyph key, resolved to a mark by the tile. Never a brand or product name. */
  icon?: string;
  /** A genuine monthly series, or empty. The server omits it rather than
   *  faking one for a snapshot measure — see `measures.trend`. */
  spark?: number[];
}

export type MetricBannerPart =
  | { kind: "text"; text: string }
  | { kind: "metric"; metricKey: string };

export interface MetricBanner {
  key: string;
  prominence: "primary" | "supporting";
  tone: Tone;
  statement: MetricBannerPart[];
  subline: string;
  /** Present only when this metric carries a genuine series of three or more points. */
  trendMetricKey?: string | null;
}

/** A row-shaped payload, or an object payload for the structured chart types
 *  (heat grid, mekko, sankey, gantt, combo, treemap, bubble). Each module
 *  narrows it to the payload its own CONTRACT entry declares. */
export type ChartData = Record<string, unknown>[] | Record<string, unknown>;

export interface ChartSpec {
  id: string;
  title: string;
  subtitle: string;
  shape: Shape;
  /** Resolved server-side; the client re-runs the same rule as a check. */
  repositoryKey: string;
  data: ChartData;
  /** Which field of a row carries x, y, the series and the target. Only the
   *  row-shaped types use it; the structured payloads name their own fields. */
  encoding?: {
    x: string;
    y: string;
    series?: string;
    target?: string;
    label?: string;
  };
  measureLabel: string;
  format: Format;
  clickDim?: DimKey | null;
  /** Page-wide selectors placed beside the chart that represents them. */
  filterDims?: DimKey[];
  countBasis?: CountBasis | null;
  basisNote?: string | null;
  /** Claim keys this chart puts on screen. The AI may not restate them. */
  says: string[];
  footnote?: string | null;
  height?: number | null;
  /** What "no rows" means for THIS chart. Rendered instead of mounting the
   *  module at all, so a legitimately empty slice reads as a finding rather
   *  than as a generic blank. */
  emptyMessage?: string | null;
}

export interface RiskFactor {
  key: string;
  label: string;
  points: number;
  detail: string;
}

export interface ActionCard {
  n: number;
  key: string;
  persona: PersonaKey;
  entity: { type: string; id: string; label: string };
  headline: string;
  why: string[];
  /** The literal rule that fired, shown behind "Why this fired". */
  predicate: string;
  owner: string;
  nextStep: string;
  severity: number;
  urgency: number;
  priority: number;
  urgencyLabel: Urgency;
  valueAtStake: number;
  framing: "risk" | "opportunity";
  /** What sort of decision it is. A page ranks its rail by this, so the cards
   *  that answer the page's question come first — see `actions.PAGE_FOCUS`. */
  kind?: "deal" | "rep_pattern" | "coverage" | "concentration" | "growth";
  scopeTo?: { dim: DimKey; value: string } | null;
  drill?: string | null;
}

/**
 * One of the three things the platform watches, as the executive brief states
 * it: a name, one line, two or three figures already formatted by the server,
 * and the page that proves it. Sent under `extras.useCases` on the brief only.
 */
export interface UseCase {
  key: "opportunities" | "anomalies" | "closure";
  title: string;
  oneLine: string;
  figures: { label: string; formatted: string }[];
  page: Lens;
  cta: string;
}

export interface Scope {
  label: string;
  predicate: string;
  persona: PersonaKey;
  identity: string;
}

export interface ViewPayload {
  page: Lens;
  label: string;
  question: string;
  persona: PersonaKey;
  asOf: string;
  fy: string;
  quarter: string;
  scope: Scope;
  filters: { dim: string; label: string; value: string }[];
  measure: Measure;
  kpis: Kpi[];
  metricBanners: MetricBanner[];
  narrative: Narrative;
  actions: ActionCard[];
  charts: ChartSpec[];
  /** Union of every chart's `says`. Passed to the AI so it cannot repeat them. */
  chartsSay: string[];
  extras: Record<string, unknown>;
  measures: Record<string, unknown>;
  executive?: ExecutivePayload;
  pageRevenueSummary?: { value: number | null; formatted: string; label: string } | null;
}

export type ExecutiveTheme = "opportunities" | "anomalies" | "closure";
export interface ExecutiveMessage {
  key: ExecutiveTheme;
  title: string;
  headline: string;
  summary: string;
  signals: { label: string; value: string }[];
  page: Lens;
}
export interface ExecutivePlay {
  key: string; offering: string; customerCount: number; ownerCount: number;
  confidence: string; pilotAccount: string; pilotOwner: string;
  peerRevenueBenchmark: number; formattedPeerRevenueBenchmark: string;
  nextStep: string; reason: string;
}
export interface ExecutiveFinding {
  key: string; severity: Urgency; entityType: string; entityId: string; entity: string;
  category: string; evidence: string; owner: string;
  question: string; nextStep: string;
  revenue: number; formattedRevenue: string;
}
export interface ExecutiveStalledDeal {
  key: string; deal: string; account: string; owner: string; stage: string;
  silenceDays: number; daysInStage: number; pastDueDays: number; dealValue: number;
  dealValueLabel: string; call: string; closeDate: string | null;
  evidence: string | null; nextStep: string | null; priority: Urgency | null;
  actionKey: string | null;
}
export interface OpportunityOverview {
  recommendations: number; repeatableRecommendations: number;
  singleAccountRecommendations: number; accounts: number; strongRecommendations: number;
  veryHighRecommendations: number; repeatablePlays: number;
  topPlay: string; topPlayAccounts: number;
  peerWonRevenueMedian: number | null; formattedPeerWonRevenueMedian: string;
  peerRevenueBenchmark: number; formattedPeerRevenueBenchmark: string;
}
export interface AnomalyOverview {
  stalledDeals: number; stalledAccounts: number; stalledPastDue: number;
  stalledRevenue: number; formattedStalledRevenue: string;
  longestSilenceDays: number; accountFindings: number;
  accountsAffected: number; criticalAccountFindings: number;
  accountRevenue: number; formattedAccountRevenue: string;
  stagnationBands: { label: string; deals: number; revenue: number; formattedRevenue: string; share: number }[];
  forecastCalls: { call: string; deals: number; revenue: number; formattedRevenue: string }[];
}
export interface ClosureException {
  key: string; deal: string; account: string; owner: string; stage: string;
  forecastCategory: string;
  riskBand: RiskBand; riskScore: number; closureProbability: number | null;
  riskBucket: number | null; riskBucketLabel: string;
  mainDriver: string; closeDate: string | null; silenceDays: number | null;
  accountCycleDays: number | null; accountCycleSampleSize: number;
  plannedCycleDays: number | null; accountCycleGapDays: number;
  accountCycleMismatch: boolean; accountCycleContext: string | null;
  isStalled: boolean; closeDateSlips: number; slipDays: number;
  deterioration: string;
  revenue: number; formattedRevenue: string;
}
export interface ExecutiveSlippageDeal {
  key: string; account: string; deal: string; line: string;
  owner: string; accountOwner: string;
  revenue: number; formattedRevenue: string;
  forecastCategory: string; riskBand: RiskBand;
  evidence: string | null; nextStep: string | null; priority: Urgency | null;
  closeDateSlips: number; slipDays: number;
  pastDueDays: number; closeDate: string | null;
}
export interface ClosureRevenueSeries {
  forecast: "Commit" | "Best Case"; threshold: number;
  declaredRevenue: number; formattedDeclaredRevenue: string; declaredDeals: number;
  defensibleRevenue: number | null; formattedDefensibleRevenue: string;
  defensibleDeals: number | null; screenedOutRevenue: number | null;
  formattedScreenedOutRevenue: string; retainedShare: number | null;
}
export interface ClosureOverview {
  series: ClosureRevenueSeries[];
  lowProbabilityRevenue: number; formattedLowProbabilityRevenue: string;
  lowProbabilityDeals: number;
  slippageRevenue: number; formattedSlippageRevenue: string;
  slipEvents: number; totalSlipDays: number; slippedPastDueDeals: number;
  stats: {
    openDeals: number; highRiskDeals: number; pastDueDeals: number;
    stalledDeals: number; slippedDeals: number;
  };
}
export interface ExecutiveActionOption {
  key: string; label: string; status: string; needsReason: boolean;
}
export interface ExecutiveAction {
  key: string; theme: ExecutiveTheme; priority: Urgency; owner: string;
  dueDate: string; headline: string; description: string; nextStep: string;
  revenueImpact?: number; formattedRevenueImpact?: string;
  revenueLabel?: string;
  revenueBasis?: "deal_acv" | "account_book_acv" | "peer_benchmark" | "anomaly_report";
  revenueEntityKey?: string; sourcePage?: Lens;
  options: ExecutiveActionOption[];
}
export interface ExecutiveActionOverview {
  totalActions: number; uniqueDealActions: number;
  dealAcvRevenue: number; formattedDealAcvRevenue: string;
  accountActions: number; accountBookRevenue: number; formattedAccountBookRevenue: string;
  growthActions: number; growthBenchmark: number; formattedGrowthBenchmark: string;
}
export interface ExecutiveWeeklyBanner {
  tone: Tone; headline: string; subline: string;
  stats: { label: string; value: string; tone: Tone }[];
  supporting: { key: string; tone: Tone; label: string; headline: string; subline: string; page: Lens }[];
}
export interface ExecutiveWeeklyInsight {
  key: string; rank: number; theme: ExecutiveTheme; title: string;
  conclusion: string; evidence: string[]; nextStep: string;
  page: Lens; entity: string; actionKey?: string;
}
export interface ExecutivePayload {
  messages: ExecutiveMessage[];
  opportunityPlays: ExecutivePlay[];
  opportunityOverview: OpportunityOverview;
  anomalyFindings: ExecutiveFinding[];
  anomalyOverview: AnomalyOverview;
  stalledDeals: ExecutiveStalledDeal[];
  closureExceptions: ClosureException[];
  slippageDeals: ExecutiveSlippageDeal[];
  closureModel: { available: boolean; testAuc?: number | null; text: string };
  closureOverview: ClosureOverview;
  actions: ExecutiveAction[];
  actionOverview: ExecutiveActionOverview;
  weeklyBanner: ExecutiveWeeklyBanner | null;
  weeklyInsights: ExecutiveWeeklyInsight[];
}

export interface PersonaDef {
  key: PersonaKey;
  label: string;
  role: string;
  jtbd: string;
  home: Lens;
  pages: Lens[];
  accent: string;
  scopeColumn: string | null;
}

export interface IdentityOption {
  id: string;
  label: string;
  openDeals?: number;
  opportunities?: number;
  gp?: number;
  reps?: number;
  pod?: string;
}

export interface MetaPayload {
  asOf: string;
  fy: string;
  quarter: string;
  persona: {
    active: {
      persona: PersonaKey;
      label: string;
      role: string;
      jtbd: string;
      identity: string;
      identityLabel: string;
      predicate: string;
      home: Lens;
      pages: Lens[];
      denyMeasures: string[];
      accent: string;
    };
    personas: PersonaDef[];
    identities: Record<PersonaKey, IdentityOption[]>;
    rosterRule: string;
  };
  pages: { key: Lens; label: string; question: string }[];
  allPages: { key: Lens; persona: PersonaKey; label: string; question: string }[];
  dimensions: {
    key: DimKey;
    label: string;
    column: string;
    countBasis: CountBasis;
    basisNote: string;
    validated: boolean;
    description: string;
    values: string[];
  }[];
  measures: { key: Measure; label: string; default: boolean }[];
  data: Record<string, number>;
  provenance: {
    distribution: {
      column: string;
      category: string;
      given_pct: number;
      synthetic_pct: number;
      difference_pp: number;
      status: string;
    }[];
    note: string;
  };
  modelCard: ModelCard;
  dsModel: Record<string, unknown>;
  anomalyTaxonomy: { categories: { name: string; question: string }[] };
  stallThreshold: number;
}

export interface ModelCard {
  primary: Record<string, unknown> & { available: boolean; honestRead?: string };
  independent: Record<string, unknown>;
  riskModel: {
    name: string;
    kind: string;
    why: string;
    factors: { key: string; label: string; maxPoints: number }[];
    bands: { band: RiskBand; from: number; to: number }[];
  };
}

export interface DealDetail {
  opportunityCode: string;
  name: string;
  account: string;
  owner: string;
  stage: string;
  lob: string;
  portfolio: string;
  acvRevenue: number;
  acvGp: number;
  closeDate: string | null;
  riskScore: number;
  riskBand: RiskBand;
  riskFactors: RiskFactor[];
  valueAtRisk: number;
  quietDays: number | null;
  stagePath: string;
  pWin?: number;
  pWinSegment?: number | null;
  repConfidence?: number;
  confidenceGap?: number;
  expectedGp?: number;
  /** Which model produced pWin. "independent" means the DS drop does not
   *  cover this deal and this layer's own classifier stood in, in which case
   *  every DS field below is null: there is no SHAP driver for a number the
   *  DS model did not produce. */
  pWinSource?: "ds-model" | "independent";
  /** The DS model's per-deal SHAP sentence, verbatim from the workbook —
   *  "Stage progression (Identification) decreased win probability the most". */
  drivingForce?: string | null;
  /** The workbook feature behind that sentence, raw and in plain words. */
  driverFeature?: string | null;
  driverLabel?: string | null;
  /** Whether that feature pushed pWin up or down for this deal. */
  driverDirection?: "up" | "down" | null;
  /** The two above as one table-cell line, "Stage reached · lowers pWin",
   *  worded by the server so every surface prints the same words. */
  dsDriver?: string | null;
  /** The mapped model criticality (1 = Critical) and the label of the
   *  quantile-relative probability bucket. */
  riskBucket?: number | null;
  riskBucketLabel?: string | null;
  riskBucketRelativeLabel?: string | null;
  timeline: { date: string; field: string; from: string; to: string; by: string }[];
  benchmarks: {
    feature: string;
    label: string;
    value: number;
    benchmark: number;
    benchmarkMethod: string;
    direction: string;
    correlationWithWin: number;
    verdict: "GREEN" | "RED";
    aboveBenchmark: boolean;
    weakSignal: boolean;
    note: string | null;
  }[];
  findings: Record<string, unknown>[];
}

export interface AskResponse {
  question: string;
  plan?: Record<string, unknown>;
  answer: Narrative;
  /** Model-generated interpretation added to a fixed, server-derived action. */
  aiPerspective?: Narrative | null;
  chart?: ChartSpec | null;
  rows?: Record<string, unknown>[];
  shape?: Shape;
  chartWhy?: string;
  claim?: string;
  provider?: string;
  degraded?: boolean;
  refused?: boolean;
  cached?: boolean;
  /** Questions the server can answer, sent with a refusal so the panel can
   *  offer a way forward rather than a dead end. */
  suggestions?: string[];
}

export interface Digest {
  windowDays: number;
  asOf: string;
  totalChanges: number;
  opportunitiesTouched: number;
  byField: Record<string, number>;
  stageMoves: { opportunity: string; from: string; to: string; by: string; date: string }[];
  busiest: { opportunity_name: string; changes: number }[];
  note: string;
}
