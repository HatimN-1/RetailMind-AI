import { useCallback, useEffect, useState } from 'react';

export function useLoad<T>(load: () => Promise<T>, deps: readonly unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    load().then(value => { if (active) setData(value); })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : 'Une erreur est survenue'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
    // Dependencies intentionally provided by each caller; refresh forces reload.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, refresh]);
  const reload = useCallback(() => setRefresh(r => r + 1), []);
  return { data, loading, error, reload };
}
