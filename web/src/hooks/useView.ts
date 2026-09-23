import { useEffect } from 'react';
import { api } from '@/services/api';
import { useAsync } from '@/hooks/useAsync';
import { useAppDispatch, useAppSelector } from '@/app/store/hooks';
import { setAskPack } from '@/app/store/askSlice';
import type { ViewPayload } from '@/types';

export function useView(lens: string) {
  const persona = useAppSelector((s) => s.persona.current);
  const filters = useAppSelector((s) => s.filters.value);
  const dispatch = useAppDispatch();
  const result = useAsync(() => api.view(lens, persona, filters), [lens, persona, filters]);
  useEffect(() => {
    if (result.data?.askPack) dispatch(setAskPack(result.data.askPack));
  }, [result.data, dispatch]);
  return result as { data: ViewPayload | undefined; status: typeof result.status; error: typeof result.error; reload: typeof result.reload };
}
