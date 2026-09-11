import type { Provenance } from "../api/types";
import "./Provenance.css";

const COPY: Record<Provenance, { short: string; long: string }> = {
  exact: {
    short: "exact",
    long: "Read directly from the stored aggregate at this level.",
  },
  aggregated: {
    short: "summed",
    long: "Recomputed by summing the sample level. Counts are additive, so this is exact.",
  },
  approximate: {
    short: "approximate",
    long: "A count-weighted mean of pre-aggregated means, not a mean of the underlying values.",
  },
  unavailable: {
    short: "not available",
    long: "Percentiles cannot be recovered from pre-aggregated data under this filter, so no value is shown rather than a misleading one.",
  },
  empty: {
    short: "no data",
    long: "The column exists but holds no values in this dataset.",
  },
};

/**
 * Every number that is not read straight from storage says so, next to itself.
 * The dashboards recalculate under any filter; this is what keeps that honest.
 */
export function ProvenanceMark({ value }: { value: Provenance }) {
  if (value === "exact") return null;
  const copy = COPY[value];
  return (
    <span className={`provenance provenance--${value}`} title={copy.long}>
      {copy.short}
    </span>
  );
}

export function provenanceNote(value: Provenance): string {
  return COPY[value].long;
}
