import type { AskResult, DealFilters, PersonaId, ViewPayload } from '@/types';
import { filtersToQuery } from '@/app/store/filtersSlice';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '';

function qs(params: Record<string, string | string[] | undefined>): string {
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v == null || v === '') continue;
    if (Array.isArray(v)) v.forEach((x) => u.append(k, x));
    else u.set(k, v);
  }
  const s = u.toString();
  return s ? `?${s}` : '';
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  meta: (persona: PersonaId) => get<Record<string, unknown>>(`/api/meta${qs({ persona })}`),
  view: (lens: string, persona: PersonaId, filters: DealFilters) =>
    get<ViewPayload>(`/api/view${qs({ lens, persona, ...filtersToQuery(filters) })}`),
  alerts: (persona: PersonaId) => get<{ items: AlertItem[] }>(`/api/alerts${qs({ persona })}`),
  opportunity: (code: string, persona: PersonaId) => get<Record<string, unknown>>(`/api/opportunity/${encodeURIComponent(code)}${qs({ persona })}`),
  ask: async (question: string, persona: PersonaId, filters: DealFilters): Promise<AskResult> => {
    const r = await fetch(`${BASE}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, persona, filters }),
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
  },
};

export interface AlertItem {
  id: string;
  severity: string;
  title: string;
  subtitle: string;
  opportunityCode: string;
  value: number;
}
