export type PersonaId = 'executive' | 'sales' | 'manager';
export type LoadStatus = 'idle' | 'loading' | 'success' | 'error';

export interface PersonaDef {
  id: PersonaId;
  name: string;
  role: string;
  lens: string;
}

export interface DealFilters {
  countries?: string[];
  lobs?: string[];
  portfolios?: string[];
  stages?: string[];
  forecasts?: string[];
  orderTypes?: string[];
  owners?: string[];
  quarters?: string[];
  industries?: string[];
  search?: string;
}

export interface KpiPayload {
  asOf: string;
  fy: string;
  lines: number;
  opportunities: number;
  accounts: number;
  openOpportunities: number;
  wonOpportunities: number;
  lostOpportunities: number;
  pipelineAcv: number;
  wonAcv: number;
  totalAcv: number;
  totalGp: number;
  gmPct: number;
  servicesGmPct: number;
  servicesGmTarget: number;
  budgetAcv: number;
  coverage: number;
  coverageTarget: number;
  pastDueOpportunities: number;
  pastDueAcv: number;
  qualifiedAcv: number;
  commitAcv: number;
  bestCaseAcv: number;
  avgOpenConfidence: number;
}

export interface ActionItem {
  id: string;
  urgency: string;
  title: string;
  why: string;
  owner: string;
  value: number;
  opportunityCode: string;
  cta: string;
}

export interface ChartSpec {
  type: string;
  title?: string;
  subtitle?: string;
  data?: unknown;
  rows?: string[];
  cols?: string[];
  values?: number[][];
  nodes?: { name: string }[];
  links?: { source: number; target: number; value: number }[];
}

export interface ViewPayload {
  lens: string;
  principal: { id: string; name: string; scopeLabel: string; owner?: string | null };
  kpis: KpiPayload;
  tldr: string[];
  actions: ActionItem[];
  charts: Record<string, unknown>;
  anomalySummary?: Record<string, unknown>[];
  anomalyCatalog?: Record<string, unknown>[];
  anomalySource?: { file: string; rowsInFile: number; rowsInScope: number; matchedToExcel: number; unmatchedToExcel: number };
  opportunities?: Record<string, unknown>[];
  anomalies?: Record<string, unknown>[];
  askPack?: AskPack;
}

export interface AskResult {
  answer: string;
  tldr: string;
  chart: ChartSpec;
  provider: string;
  suggestions: string[];
}

export interface AskPackItem {
  key?: string;
  text?: string;
  answer: string;
  tldr: string;
  chart?: ChartSpec;
  provider?: string;
  suggestions?: string[];
}

export interface AskPack {
  persona?: string;
  prompts: AskPackItem[];
  charts: Record<string, Record<string, AskPackItem>>;
}
