import { createContext, useCallback, useContext, useMemo } from "react";
import type { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import {
  EMPTY_FILTERS,
  fromSearchParams,
  toSearchParams,
  type FilterState,
} from "./filters";

interface FilterContextValue {
  filters: FilterState;
  setFilters: (next: FilterState) => void;
  update: (patch: Partial<FilterState>) => void;
  clear: () => void;
}

const FilterContext = createContext<FilterContextValue | null>(null);

export function FilterProvider({ children }: { children: ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => fromSearchParams(searchParams), [searchParams]);

  const setFilters = useCallback(
    (next: FilterState) => {
      // Filters are URL state, so the back button steps through slices and a
      // filtered view can be shared as a link.
      setSearchParams(toSearchParams(next), { replace: false });
    },
    [setSearchParams],
  );

  const update = useCallback(
    (patch: Partial<FilterState>) => setFilters({ ...filters, ...patch }),
    [filters, setFilters],
  );

  const clear = useCallback(() => setFilters(EMPTY_FILTERS), [setFilters]);

  const value = useMemo(
    () => ({ filters, setFilters, update, clear }),
    [filters, setFilters, update, clear],
  );

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilters(): FilterContextValue {
  const value = useContext(FilterContext);
  if (!value) throw new Error("useFilters must be used inside a FilterProvider");
  return value;
}
