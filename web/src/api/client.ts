import type {
  AlleleInfo,
  Dashboard,
  MeasureInfo,
  FacetAvailability,
  Health,
  QueryResult,
  SampleOverview,
  StudyOverview,
  SubjectOverview,
} from "./types";
import type { FilterState } from "../state/filters";

const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function get<T>(path: string, params?: URLSearchParams): Promise<T> {
  const url = params?.toString() ? `${BASE}${path}?${params}` : `${BASE}${path}`;
  const response = await fetch(url);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep the status text */
    }
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

/** Turn the UI's filter state into the query parameters every endpoint accepts. */
export function filterParams(filters: FilterState): URLSearchParams {
  const params = new URLSearchParams();
  filters.studyId.forEach((v) => params.append("study_id", String(v)));
  filters.subjectId.forEach((v) => params.append("subject_id", String(v)));
  filters.sampleId.forEach((v) => params.append("sample_id", String(v)));
  filters.chain.forEach((v) => params.append("chain", v));
  filters.celltypeId.forEach((v) => params.append("celltype_id", String(v)));
  filters.alleleId.forEach((v) => params.append("allele_id", String(v)));
  filters.alleleSegment.forEach((v) => params.append("allele_segment", v));
  Object.entries(filters.metadata).forEach(([field, values]) =>
    values.forEach((v) => params.append("meta", `${field}:${v}`)),
  );
  return params;
}

export const api = {
  health: () => get<Health>("/health"),
  facets: () => get<FacetAvailability[]>("/meta/facets"),
  measures: () => get<MeasureInfo[]>("/meta/measures"),
  alleles: () => get<AlleleInfo[]>("/meta/alleles", new URLSearchParams({ limit: "5000" })),
  studies: () => get<StudyOverview[]>("/studies"),
  study: (id: number) => get<StudyOverview>(`/studies/${id}`),
  subjects: (studyId?: number) =>
    get<SubjectOverview[]>(
      "/subjects",
      studyId ? new URLSearchParams({ study_id: String(studyId) }) : undefined,
    ),
  samples: (studyId?: number) =>
    get<SampleOverview[]>(
      "/samples",
      studyId ? new URLSearchParams({ study_id: String(studyId) }) : undefined,
    ),

  dashboard: (filters: FilterState, level: "project" | "study", studyId?: number) => {
    const params = filterParams(filters);
    params.set("level", level);
    if (studyId !== undefined) params.set("scope_study_id", String(studyId));
    return get<Dashboard>("/dashboard", params);
  },

  query: (
    filters: FilterState,
    options: { measure: string; grain: string; page: number; pageSize: number },
  ) => {
    const params = filterParams(filters);
    params.set("measure", options.measure);
    params.set("grain", options.grain);
    params.set("page", String(options.page));
    params.set("page_size", String(options.pageSize));
    return get<QueryResult>("/query", params);
  },

  exportUrl: (
    filters: FilterState,
    options: { measure: string; grain: string; format: "csv" | "tsv" },
  ) => {
    const params = filterParams(filters);
    params.set("measure", options.measure);
    params.set("grain", options.grain);
    params.set("format", options.format);
    return `${BASE}/query/export?${params}`;
  },
};
