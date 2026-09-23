import { combineReducers, configureStore } from '@reduxjs/toolkit';
import uiReducer from './uiSlice';
import personaReducer from './personaSlice';
import filtersReducer from './filtersSlice';
import askReducer from './askSlice';

const rootReducer = combineReducers({ ui: uiReducer, persona: personaReducer, filters: filtersReducer, ask: askReducer });
const STORAGE_KEY = 'ntt-di-state-v1';

type PreloadedShape = Partial<ReturnType<typeof rootReducer>>;

function loadPersisted(): PreloadedShape | undefined {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return undefined;
    const saved = JSON.parse(raw);
    const preloaded: PreloadedShape = {};
    if (saved.filters) preloaded.filters = saved.filters;
    if (saved.persona) preloaded.persona = saved.persona;
    if (saved.themeMode === 'light' || saved.themeMode === 'dark') {
      preloaded.ui = { sidebarOpen: true, themeMode: saved.themeMode, selectedOpportunityId: null };
    }
    return Object.keys(preloaded).length ? preloaded : undefined;
  } catch {
    return undefined;
  }
}

export const store = configureStore({ reducer: rootReducer, preloadedState: loadPersisted() });

let saveTimer: ReturnType<typeof setTimeout> | null = null;
store.subscribe(() => {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      const s = store.getState();
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ filters: s.filters, persona: s.persona, themeMode: s.ui.themeMode }));
    } catch {
      /* ignore */
    }
  }, 250);
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
