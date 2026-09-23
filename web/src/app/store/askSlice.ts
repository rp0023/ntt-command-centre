import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { AskPack } from '@/types';

const askSlice = createSlice({
  name: 'ask',
  initialState: { pack: null as AskPack | null },
  reducers: {
    setAskPack(state, action: PayloadAction<AskPack | null>) {
      state.pack = action.payload;
    },
  },
});

export const { setAskPack } = askSlice.actions;
export default askSlice.reducer;
