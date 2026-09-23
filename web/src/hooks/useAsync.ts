import { useCallback, useEffect, useRef, useState } from 'react';
import type { LoadStatus } from '@/types';

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]) {
  const [data, setData] = useState<T>();
  const [status, setStatus] = useState<LoadStatus>('loading');
  const [error, setError] = useState<Error>();
  const [nonce, setNonce] = useState(0);
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);
  useEffect(() => {
    let active = true;
    setStatus('loading');
    setError(undefined);
    fnRef
      .current()
      .then((res) => {
        if (!active) return;
        setData(res);
        setStatus('success');
      })
      .catch((e) => {
        if (!active) return;
        setError(e instanceof Error ? e : new Error(String(e)));
        setStatus('error');
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);
  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, status, error, reload };
}
