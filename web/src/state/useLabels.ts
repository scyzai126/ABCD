import { useMemo } from "react";
import { api } from "../api/client";
import { useAsync } from "./useAsync";

/** Id-to-name maps, so filter chips and tooltips can name what was selected. */
export function useLabels() {
  const facets = useAsync(() => api.facets(), []);
  const subjects = useAsync(() => api.subjects(), []);
  const samples = useAsync(() => api.samples(), []);

  return useMemo(() => {
    const celltypes = new Map<number, string>();
    facets.data
      ?.find((facet) => facet.field === "celltype_id")
      ?.values.forEach((value) => celltypes.set(Number(value.value), value.label));

    const subjectNames = new Map<number, string>();
    subjects.data?.forEach((subject) =>
      subjectNames.set(subject.subject_id, subject.subject_name ?? `#${subject.subject_id}`),
    );

    const sampleNames = new Map<number, string>();
    samples.data?.forEach((sample) =>
      sampleNames.set(sample.sample_id, sample.sample_name ?? `#${sample.sample_id}`),
    );

    return { celltypes, subjects: subjectNames, samples: sampleNames };
  }, [facets.data, subjects.data, samples.data]);
}
