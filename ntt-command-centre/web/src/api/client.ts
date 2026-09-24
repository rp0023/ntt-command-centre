/** Authenticated API transport. Identity is resolved by the server, never query parameters. */
import type { ActionCard, AskResponse, DealDetail, Digest, MetaPayload, Narrative, ViewPayload, PersonaKey, Lens } from "./types";
const BASE = import.meta.env.VITE_API_BASE ?? "";
const ACCESS_KEY = "ntt.session.v2";
export const LOCKED_EVENT = "ntt:locked";
export interface SessionUser {
  id: string; name: string; email: string; role: PersonaKey; roleLabel: string;
  identity: string; scopeLabel: string; home: Lens; pages: Lens[];
}
interface Session { token: string; expiresAt: string }
export interface Access extends Session { user: SessionUser }
let memory: Session | null = null;
let generation = 0;
const pending = new Set<AbortController>();
export function sessionGeneration() { return generation; }
export function readAccess(): Session | null {
  try {
    const raw = sessionStorage.getItem(ACCESS_KEY);
    if (raw) memory = JSON.parse(raw) as Session;
  } catch { /* In-memory session still works if storage is unavailable. */ }
  if (!memory || typeof memory.token !== "string" || !(Date.parse(memory.expiresAt) > Date.now())) return null;
  return memory;
}
function writeAccess(a: Session) {
  generation++;
  memory = { token: a.token, expiresAt: a.expiresAt };
  try { sessionStorage.setItem(ACCESS_KEY, JSON.stringify(memory)); } catch { /* memory fallback */ }
}
export function clearAccess() {
  generation++;
  memory = null;
  pending.forEach(c => c.abort());
  pending.clear();
  try { sessionStorage.removeItem(ACCESS_KEY); localStorage.removeItem("ntt.access"); } catch { /* unavailable storage */ }
}
function locked() {
  clearAccess();
  window.dispatchEvent(new CustomEvent(LOCKED_EVENT));
}
export interface Ctx {
  persona: string; identity: string; filters: Record<string, string | null>; measure: string;
}
function qs(ctx: Ctx, extra: Record<string, string | undefined> = {}): string {
  const p = new URLSearchParams();
  p.set("measure", ctx.measure);
  for (const [k, v] of Object.entries(ctx.filters)) if (v) p.set(k, v);
  for (const [k, v] of Object.entries(extra)) if (v !== undefined) p.set(k, v);
  return p.toString();
}
export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); }
}
async function request<T>(path: string, method: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const token = readAccess()?.token;
  const epoch = generation;
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  pending.add(controller);
  try {
    const r = await fetch(`${BASE}${path}`, {
      method, signal: controller.signal,
      headers: { ...(token ? { authorization: `Bearer ${token}` } : {}), ...(body === undefined ? {} : { "content-type": "application/json" }) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (epoch !== generation) throw new DOMException("Session changed", "AbortError");
    if (!r.ok) {
      if (r.status === 401) locked();
      let detail = r.statusText;
      try { detail = (await r.json()).detail ?? detail; } catch { /* non-JSON error */ }
      throw new ApiError(typeof detail === "string" ? detail : r.statusText, r.status);
    }
    const result = await r.json() as T;
    if (epoch !== generation) throw new DOMException("Session changed", "AbortError");
    return result;
  } finally {
    pending.delete(controller);
    signal?.removeEventListener("abort", abort);
  }
}
const get = <T,>(path: string, signal?: AbortSignal) => request<T>(path, "GET", undefined, signal);
const post = <T,>(path: string, body: unknown, signal?: AbortSignal) => request<T>(path, "POST", body, signal);
export const auth = {
  login: async (email: string, password: string, signal?: AbortSignal): Promise<Access> => {
    const r = await fetch(`${BASE}/api/auth/login`, {
      method: "POST", headers: { "content-type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password }), signal,
    });
    if (!r.ok) throw new ApiError(r.status === 401 ? "Email or password is incorrect" : r.statusText, r.status);
    const a = await r.json() as Access;
    writeAccess(a);
    return a;
  },
  me: (signal?: AbortSignal) => get<SessionUser>("/api/auth/me", signal),
  logout: () => {
    const url = new URL(window.location.href);
    url.search = "";
    url.hash = "";
    window.history.replaceState(null, "", url);
    locked();
  },
};

export const api = {
  meta: (ctx: Ctx, signal?: AbortSignal) =>
    get<MetaPayload>(`/api/meta?${qs(ctx)}`, signal),

  view: (ctx: Ctx, page: string, signal?: AbortSignal) =>
    get<ViewPayload>(`/api/view?${qs(ctx, { page })}`, signal),

  actions: (ctx: Ctx, limit = 12, signal?: AbortSignal) =>
    get<{ actions: ActionCard[] }>(
      `/api/actions?${qs(ctx, { limit: String(limit) })}`, signal),

  deal: (ctx: Ctx, code: string, signal?: AbortSignal) =>
    get<DealDetail>(`/api/deal/${encodeURIComponent(code)}?${qs(ctx)}`, signal),

  anomalies: (ctx: Ctx, limit = 80, signal?: AbortSignal) =>
    get<Record<string, unknown>>(
      `/api/anomalies?${qs(ctx, { limit: String(limit) })}`, signal),

  accounts: (ctx: Ctx, signal?: AbortSignal) =>
    get<Record<string, unknown>>(`/api/accounts?${qs(ctx)}`, signal),

  budget: (ctx: Ctx, signal?: AbortSignal) =>
    get<Record<string, unknown>>(`/api/budget?${qs(ctx)}`, signal),

  // ---- AI surfaces. Each carries what is already on screen. ---------------
  brief: (ctx: Ctx, page: string, chartsSay: string[], signal?: AbortSignal) =>
    get<Narrative>(
      `/api/ai/brief?${qs(ctx, { page, chartsSay: JSON.stringify(chartsSay) })}`,
      signal),

  /** `chart` is the id of the chart the question is about, when it is about
   *  one; the server then answers from that chart's rows rather than the
   *  whole slice, and the reply is words only. */
  ask: (ctx: Ctx, q: string, chartsSay: string[], signal?: AbortSignal,
        chart?: { id: string; page: string }) =>
    get<AskResponse>(
      `/api/ai/ask?${qs(ctx, { q, chartsSay: JSON.stringify(chartsSay),
                               chart: chart?.id, page: chart?.page })}`, signal),

  explain: (ctx: Ctx, card: ActionCard, chartsSay: string[], signal?: AbortSignal) =>
    post<Narrative & { evidence?: unknown[] }>(
      `/api/ai/explain?${qs(ctx, { chartsSay: JSON.stringify(chartsSay) })}`,
      card, signal),

  nextAction: (ctx: Ctx, code: string, signal?: AbortSignal) =>
    get<Narrative & { deal: DealDetail; evidence: unknown[] }>(
      `/api/ai/next-action/${encodeURIComponent(code)}?${qs(ctx)}`, signal),

  digest: (ctx: Ctx, days = 7, signal?: AbortSignal) =>
    get<Digest>(`/api/ai/digest?${qs(ctx, { days: String(days) })}`, signal),

  health: (signal?: AbortSignal) =>
    get<Record<string, unknown>>(`/api/health`, signal),
};
