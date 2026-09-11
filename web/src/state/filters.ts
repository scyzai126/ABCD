/** The one filter slice every page and chart reads from. */

export interface FilterState {
  studyId: number[];
  subjectId: number[];
  sampleId: number[];
  chain: string[];
  celltypeId: number[];
  alleleId: number[];
  alleleSegment: string[];
  metadata: Record<string, string[]>;
}

export const EMPTY_FILTERS: FilterState = {
  studyId: [],
  subjectId: [],
  sampleId: [],
  chain: [],
  celltypeId: [],
  alleleId: [],
  alleleSegment: [],
  metadata: {},
};

export function isEmpty(filters: FilterState): boolean {
  return (
    filters.studyId.length === 0 &&
    filters.subjectId.length === 0 &&
    filters.sampleId.length === 0 &&
    filters.chain.length === 0 &&
    filters.celltypeId.length === 0 &&
    filters.alleleId.length === 0 &&
    filters.alleleSegment.length === 0 &&
    Object.keys(filters.metadata).length === 0
  );
}

export function countActive(filters: FilterState): number {
  return (
    filters.studyId.length +
    filters.subjectId.length +
    filters.sampleId.length +
    filters.chain.length +
    filters.celltypeId.length +
    filters.alleleId.length +
    filters.alleleSegment.length +
    Object.values(filters.metadata).reduce((n, v) => n + v.length, 0)
  );
}

/** Toggle one value in a list-valued facet. */
export function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}

const LIST_KEYS: (keyof FilterState)[] = [
  "studyId",
  "subjectId",
  "sampleId",
  "chain",
  "celltypeId",
  "alleleId",
  "alleleSegment",
];

const NUMERIC_KEYS = new Set(["studyId", "subjectId", "sampleId", "celltypeId", "alleleId"]);

/** Filters live in the URL, so a filtered view is a link someone can send. */
export function toSearchParams(filters: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  for (const key of LIST_KEYS) {
    const values = filters[key] as (string | number)[];
    if (values.length) params.set(key, values.join(","));
  }
  for (const [field, values] of Object.entries(filters.metadata)) {
    if (values.length) params.set(`meta.${field}`, values.join(","));
  }
  return params;
}

export function fromSearchParams(params: URLSearchParams): FilterState {
  const filters: FilterState = {
    ...EMPTY_FILTERS,
    metadata: {},
  };
  for (const key of LIST_KEYS) {
    const raw = params.get(key);
    if (!raw) continue;
    const parts = raw.split(",").filter(Boolean);
    (filters[key] as unknown) = NUMERIC_KEYS.has(key) ? parts.map(Number) : parts;
  }
  params.forEach((value, key) => {
    if (key.startsWith("meta.") && value) {
      filters.metadata[key.slice(5)] = value.split(",").filter(Boolean);
    }
  });
  return filters;
}
