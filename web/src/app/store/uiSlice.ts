import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

export interface UiState {
  sidebarOpen: boolean;
  themeMode: 'light' | 'dark';
  selectedOpportunityId: string | null;
}

const initialState: UiState = { sidebarOpen: true, themeMode: 'light', selectedOpportunityId: null };

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarOpen(state, action: PayloadAction<boolean>) {
      state.sidebarOpen = action.payload;
    },
    toggleTheme(state) {
      state.themeMode = state.themeMode === 'light' ? 'dark' : 'light';
    },
    setSelectedOpportunity(state, action: PayloadAction<string | null>) {
      state.selectedOpportunityId = action.payload;
    },
    closeDrawer(state) {
      state.selectedOpportunityId = null;
    },
  },
});

export const { toggleSidebar, setSidebarOpen, toggleTheme, setSelectedOpportunity, closeDrawer } = uiSlice.actions;
export default uiSlice.reducer;
