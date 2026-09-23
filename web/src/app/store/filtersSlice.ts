import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { DealFilters } from '@/types';

const filtersSlice = createSlice({
  name: 'filters',
  initialState: { value: {} as DealFilters },
  reducers: {
    setFilters(state, action: PayloadAction<DealFilters>) {
      state.value = action.payload;
    },
    patchFilters(state, action: PayloadAction<Partial<DealFilters>>) {
      state.value = { ...state.value, ...action.payload };
    },
    clearFilters(state) {
      state.value = {};
    },
  },
});

export const { setFilters, patchFilters, clearFilters } = filtersSlice.actions;
export default filtersSlice.reducer;

export function countActiveFilters(filters: DealFilters): number {
  return Object.values(filters).filter((v) => (Array.isArray(v) ? v.length > 0 : Boolean(v))).length;
}

export function filtersToQuery(filters: DealFilters): Record<string, string | string[]> {
  const q: Record<string, string | string[]> = {};
  const map: [keyof DealFilters, string][] = [
    ['countries', 'country'],
    ['lobs', 'lob'],
    ['portfolios', 'portfolio'],
    ['stages', 'stage'],
    ['forecasts', 'forecast'],
    ['orderTypes', 'orderType'],
    ['owners', 'owner'],
    ['quarters', 'quarter'],
    ['industries', 'industry'],
  ];
  for (const [k, qp] of map) {
    const v = filters[k];
    if (Array.isArray(v) && v.length) q[qp] = v;
  }
  if (filters.search) q.search = filters.search;
  return q;
}
