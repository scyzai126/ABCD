import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { StudyOverview } from "../api/types";
import { formatCount } from "../charts/palette";
import { DataTable } from "../components/DataTable";
import { Message } from "../components/Message";
import { Panel } from "../components/Panel";
import { useAsync } from "../state/useAsync";
import { DashboardView } from "./DashboardView";
import "./StudyDashboard.css";

/** Descriptors the decks put on the study page. Most are unfilled today, so the
 *  panel names each one and says it is missing rather than hiding the gap. */
const DESCRIPTORS: { key: keyof StudyOverview; label: string }[] = [
  { key: "title", label: "Title" },
  { key: "summary", label: "Summary" },
];

export function StudyDashboard() {
  const { studyId } = useParams();
  const id = Number(studyId);
  const study = useAsync(() => api.study(id), [id]);
  const subjects = useAsync(() => api.subjects(id), [id]);
  const samples = useAsync(() => api.samples(id), [id]);

  if (study.error) {
    return (
      <Message title={`Could not load study ${studyId}`} tone="problem">
        <p>{study.error.message}</p>
      </Message>
    );
  }

  const name = study.data?.study_name ?? `Study ${studyId}`;

  return (
    <DashboardView
      level="study"
      studyId={id}
      title={name}
      subtitle={study.data?.title ?? "This study has no title or abstract recorded yet."}
      scopeNote={`Showing every sample in ${name}. Use the filters to narrow the slice further.`}
    >
      <div className="study__grid">
        <Panel title="Study record" subtitle="As held in the database" span={4}>
          <dl className="study__fields">
            {DESCRIPTORS.map(({ key, label }) => (
              <div key={key}>
                <dt>{label}</dt>
                <dd className={study.data?.[key] ? "" : "study__missing"}>
                  {(study.data?.[key] as string) || "Not recorded"}
                </dd>
              </div>
            ))}
            <div>
              <dt>Largest clone</dt>
              <dd>{formatCount(study.data?.largest_clonesize)} receptors</dd>
            </div>
            <div>
              <dt>Paired heavy and light</dt>
              <dd>
                {formatCount(study.data?.count_igh_igk_pair)} kappa,{" "}
                {formatCount(study.data?.count_igh_igl_pair)} lambda
              </dd>
            </div>
          </dl>
        </Panel>

        <Panel
          title="Subjects"
          subtitle={`${subjects.data?.length ?? 0} in this study`}
          span={4}
        >
          <DataTable
            caption="Subjects in this study"
            columns={[
              { key: "subject_name", header: "Subject" },
              { key: "disease_reported", header: "Disease" },
              { key: "count_bcrs", header: "BCRs", align: "right" },
            ]}
            rows={(subjects.data ?? []) as unknown as Record<string, unknown>[]}
          />
        </Panel>

        <Panel title="Samples" subtitle={`${samples.data?.length ?? 0} in this study`} span={4}>
          <DataTable
            caption="Samples in this study"
            columns={[
              { key: "sample_name", header: "Sample" },
              { key: "subject_name", header: "Subject" },
              { key: "tissue", header: "Tissue" },
              { key: "count_bcrs", header: "BCRs", align: "right" },
            ]}
            rows={(samples.data ?? []) as unknown as Record<string, unknown>[]}
          />
        </Panel>
      </div>
    </DashboardView>
  );
}
