import { useEffect, useRef, useState } from "react";

export interface AsyncState<T> {
  data: T | undefined;
  error: Error | undefined;
  /** True while a refetch is in flight and previous data is still on screen. */
  stale: boolean;
  loading: boolean;
}

/**
 * Fetch that keeps the frame.
 *
 * On a refetch the previous result stays mounted and is dimmed rather than
 * replaced by a skeleton, so filtering never causes a layout jump.
 */
export function useAsync<T>(fetcher: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [stale, setStale] = useState(false);
  const hasData = useRef(false);

  useEffect(() => {
    let cancelled = false;
    setStale(hasData.current);
    setError(undefined);

    fetcher()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        hasData.current = true;
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setStale(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, error, stale, loading: data === undefined && error === undefined };
}
