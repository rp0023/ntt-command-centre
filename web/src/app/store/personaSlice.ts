import { createSlice, type PayloadAction } from '@reduxjs/toolkit';
import type { PersonaId } from '@/types';
import { DEFAULT_PERSONA } from '@/constants/personas';

const personaSlice = createSlice({
  name: 'persona',
  initialState: { current: DEFAULT_PERSONA as PersonaId },
  reducers: {
    setPersona(state, action: PayloadAction<PersonaId>) {
      state.current = action.payload;
    },
  },
});

export const { setPersona } = personaSlice.actions;
export default personaSlice.reducer;
