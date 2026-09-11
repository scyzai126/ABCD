/** Mirrors the FastAPI response models. */

export type Provenance =
  | "exact"
  | "aggregated"
  | "approximate"
  | "unavailable"
  | "empty";

export type Grain = "study" | "subject" | "sample";

export type Measure =
  | "summary"
  | "chain"
  | "celltype"
  | "chain_celltype"
  | "allele"
  | "allele_celltype"
  | "clonesize";

export interface FacetValue {
  value: string | number;
  label: string;
  count: number | null;
}

export interface FacetAvailability {
  field: string;
  label: string;
  level: Grain;
  kind: "categorical" | "numeric" | "temporal";
  available: boolean;
  distinct_count: number;
  derived: boolean;
  note: string;
  values: FacetValue[];
  min: number | null;
  max: number | null;
}

export interface Kpi {
  key: string;
  label: string;
  value: number | null;
  provenance: Provenance;
  note: string;
}

export interface Breakdown {
  key: string;
  label: string;
  source: string;
  provenance: Provenance;
  rows: Record<string, unknown>[];
  note: string;
}

export interface Dashboard {
  level: "project" | "study";
  study_id: number | null;
  kpis: Kpi[];
  breakdowns: Record<string, Breakdown>;
  notes: string[];
}

export interface QueryResult {
  total: number;
  page: number;
  page_size: number;
  columns: string[];
  rows: Record<string, unknown>[];
  provenance: Record<string, Provenance>;
  notes: string[];
}

export interface StudyOverview {
  study_id: number;
  study_name: string | null;
  title: string | null;
  summary: string | null;
  count_bcrs: number | null;
  count_igh_igk_pair: number | null;
  count_igh_igl_pair: number | null;
  count_igm: number | null;
  count_igd: number | null;
  count_iga: number | null;
  count_igg: number | null;
  count_ige: number | null;
  clonesize_mean: number | null;
  clonesize_median: number | null;
  largest_clonesize: number | null;
}

export interface SubjectOverview {
  subject_id: number;
  subject_name: string | null;
  study_id: number;
  study_name: string | null;
  organism: string | null;
  biological_sex: string | null;
  age: number | null;
  disease_reported: string | null;
  count_bcrs: number | null;
}

export interface SampleOverview {
  sample_id: number;
  sample_name: string | null;
  subject_id: number;
  subject_name: string | null;
  study_id: number;
  study_name: string | null;
  tissue: string | null;
  cell_type: string | null;
  time_collected: string | null;
  count_bcrs: number | null;
}

export interface Health {
  status: string;
  database: {
    studies: number;
    subjects: number;
    samples: number;
    celltypes: number;
    alleles: number;
    bcrs: number;
    connected_as: string;
  };
  facets: { declared: number; populated: number };
}

export interface MeasureInfo {
  name: Measure;
  label: string;
  grains: Grain[];
  dimensions: string[];
  additive_columns: string[];
  mean_columns: string[];
  percentile_columns: string[];
  empty_columns: string[];
}

export interface AlleleInfo {
  vj_allele_id: number;
  vj_allele_name: string;
  vj_allele_segment: string | null;
  vj_allele_gene: string | null;
  allele_number: string | null;
  count_vj_allele: number;
}
