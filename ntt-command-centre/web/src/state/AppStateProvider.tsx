/**
 * One reducer, mirrored into the URL, provided to the tree.
 *
 * The URL write is `pushState` on a real state change and `replaceState` on the
 * initial hydrate, so the back button walks the user's actual decisions rather
 * than every keystroke in the Ask box.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import { useSession } from "./SessionContext";
import type { Ctx } from "../api/client";
import type { DimKey, Lens, Measure } from "../api/types";
import {
  INITIAL,
  type Action,
  type AppState,
  type AskSeed,
  fromQuery,
  reducer,
  toQuery,
} from "./filters";

interface Api {
  state: AppState;
  dispatch: (a: Action) => void;
  /** The context every API call carries. Memoised so effects do not re-fire. */
  ctx: Ctx;
  setPage: (p: Lens) => void;
  openAction: (key: string) => void;
  onFilter: (dim: DimKey, value: string) => void;
  setFilter: (dim: DimKey, value: string | null) => void;
  clearFilters: () => void;
  setMeasure: (m: Measure) => void;
  /** Open the main Ask panel, optionally about a question and with turns carried over from a chart's Ask. */
  openAsk: (query?: string, seed?: AskSeed | null) => void;
  closeAsk: () => void;
  openDrawer: (d: string) => void;
  closeDrawer: () => void;
}

const C = createContext<Api | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const user = useSession();
  const enforce = (s: AppState): AppState => ({
    ...s, persona: user.role, identity: user.identity,
    page: user.pages.includes(s.page) ? s.page : user.home,
    measure: user.role === "executive" ? "revenue" : s.measure,
  });
  const [state, dispatch] = useReducer(
    (s: AppState, action: Action) => enforce(reducer(s, action)),
    INITIAL,
    (init) => {
      const parsed = fromQuery(window.location.search);
      const permitted = !parsed.page || user.pages.includes(parsed.page);
      return enforce({ ...init, ...parsed, page: parsed.page ?? user.home,
        filters: permitted ? { ...init.filters, ...parsed.filters } : { ...init.filters },
        drawer: permitted ? parsed.drawer ?? null : null });
    },
  );

  const first = useRef(true);
  useEffect(() => {
    const q = toQuery(state);
    const url = `${window.location.pathname}?${q}`;
    if (first.current) {
      first.current = false;
      window.history.replaceState(null, "", url);
      return;
    }
    if (`?${q}` !== window.location.search) window.history.pushState(null, "", url);
  }, [state]);

  useEffect(() => {
    const onPop = () => dispatch({ type: "fromUrl", state: fromQuery(window.location.search) });
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  // The persona accent is a document-level attribute so CSS can resolve
  // --persona once rather than every component threading a colour.
  useEffect(() => {
    document.documentElement.setAttribute("data-persona", state.persona);
  }, [state.persona]);

  const ctx: Ctx = useMemo(
    () => ({
      persona: state.persona,
      identity: state.identity,
      filters: state.filters as Record<string, string | null>,
      measure: state.measure,
    }),
    [state.persona, state.identity, state.filters, state.measure],
  );

  const value: Api = useMemo(
    () => ({
      state,
      dispatch,
      ctx,
      setPage: (page) => dispatch({ type: "page", page }),
      openAction: (actionKey) => dispatch({ type: "page", page: "action-center", actionKey }),
      onFilter: (dim, value) => dispatch({ type: "toggleFilter", dim, value }),
      setFilter: (dim, value) => dispatch({ type: "setFilter", dim, value }),
      clearFilters: () => dispatch({ type: "clearFilters" }),
      setMeasure: (measure) => dispatch({ type: "measure", measure }),
      openAsk: (query, seed) => dispatch({ type: "ask", open: true, query, seed }),
      closeAsk: () => dispatch({ type: "ask", open: false }),
      openDrawer: (d) => dispatch({ type: "drawer", drawer: d }),
      closeDrawer: () => dispatch({ type: "drawer", drawer: null }),
    }),
    [state, ctx],
  );

  return <C.Provider value={value}>{children}</C.Provider>;
}

export function useApp(): Api {
  const v = useContext(C);
  if (!v) throw new Error("useApp must be used inside AppStateProvider");
  return v;
}

/** A stable callback that scopes the page from a chart mark or an action card. */
export function useScopeTo() {
  const { onFilter, setPage } = useApp();
  return useCallback(
    (scope: { dim: DimKey; value: string } | null | undefined, page?: Lens) => {
      if (scope) onFilter(scope.dim, scope.value);
      if (page) setPage(page);
    },
    [onFilter, setPage],
  );
}
