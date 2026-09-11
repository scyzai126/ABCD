import { api } from "../api/client";
import type { Breakdown } from "../api/types";
import { BarList } from "../charts/BarList";
import { Cdr3Box, type Cdr3Row } from "../charts/Cdr3Box";
import { Ribbon } from "../charts/Ribbon";
import {
  chainColor,
  chainFill,
  ISOTYPE_COLOR,
  ISOTYPE_FILL,
  SINGLE_SERIES,
  SINGLE_SERIES_FILL,
} from "../charts/palette";
import { DataTable } from "../components/DataTable";
import { Message } from "../components/Message";
import { Panel } from "../components/Panel";
import { SliceBar } from "../components/SliceBar";
import { StatRow } from "../components/StatRow";
import { toggle } from "../state/filters";
import { useFilters } from "../state/FilterProvider";
import { useAsync } from "../state/useAsync";
import { useLabels } from "../state/useLabels";
import "./DashboardView.css";

interface DashboardViewProps {
  level: "project" | "study";
  studyId?: number;
  title: string;
  subtitle?: string;
  scopeNote?: string;
  children?: React.ReactNode;
}

/**
 * The chart set shared by the project and study dashboards.
 *
 * Both pages ask the same question at different scopes, so they run the same
 * component rather than two drifting copies.
 */
export function DashboardView({
  level,
  studyId,
  title,
  subtitle,
  scopeNote,
  children,
}: DashboardViewProps) {
  const { filters, update } = useFilters();
  const labels = useLabels();
  const state = useAsync(
    () => api.dashboard(filters, level, studyId),
    [JSON.stringify(filters), level, studyId],
  );

  if (state.error) {
    return (
      <Message title="Could not load the dashboard" tone="problem">
        <p>{state.error.message}</p>
      </Message>
    );
  }

  const dashboard = state.data;

  return (
    <div className="dash">
      <header className="dash__head">
        <h1 className="dash__title">{title}</h1>
        {subtitle && <p className="dash__subtitle">{subtitle}</p>}
      </header>

      <SliceBar labels={labels} scopeNote={scopeNote} />

      {children}

      {!dashboard ? (
        <p className="dash__loading">Loading…</p>
      ) : (
        <>
          <section className="dash__lead">
            <div className="dash__lead-head">
              <h2 className="dash__lead-title">Repertoire composition</h2>
              <p className="dash__lead-sub">
                Every receptor chain in the selection, by immunoglobulin locus.
              </p>
            </div>
            <Ribbon
              lead
              unit="chains"
              segments={chainSegments(dashboard.breakdowns.chain)}
              selected={filters.chain}
              onSelect={(chain) => update({ chain: toggle(filters.chain, chain) })}
            />
          </section>

          <StatRow kpis={dashboard.kpis} />

          {dashboard.notes.map((note) => (
            <p className="dash__note" key={note}>
              {note}
            </p>
          ))}

          <div className="dash__grid">
            <CelltypePanel breakdown={dashboard.breakdowns.celltype} stale={state.stale} />
            <Cdr3Panel breakdown={dashboard.breakdowns.cdr3} stale={state.stale} />
            <IsotypePanel breakdown={dashboard.breakdowns.isotype} stale={state.stale} />
            <AllelePanel breakdown={dashboard.breakdowns.allele} stale={state.stale} />
            <MutfreqPanel breakdown={dashboard.breakdowns.mutfreq} />
          </div>
        </>
      )}
    </div>
  );
}

function chainSegments(breakdown: Breakdown | undefined) {
  return (breakdown?.rows ?? []).map((row) => ({
    key: String(row.chain),
    label: String(row.chain),
    value: Number(row.count),
    color: chainColor(String(row.chain)),
    fill: chainFill(String(row.chain)),
  }));
}

function CelltypePanel({ breakdown, stale }: { breakdown: Breakdown; stale: boolean }) {
  const { filters, update } = useFilters();
  const rows = breakdown.rows.map((row) => ({
    key: (row.annotated_celltype_id as number | null) ?? "other",
    label: String(row.annotated_celltype_name),
    value: Number(row.count),
  }));

  return (
    <Panel
      title="Cell types"
      subtitle="Annotated populations carrying a receptor"
      provenance={breakdown.provenance}
      note={
        breakdown.note ||
        "The ten largest populations; the rest are folded together. Most of the long tail carries five receptors or fewer."
      }
      span={6}
      stale={stale}
      table={
        <DataTable
          caption="Receptors by annotated cell type"
          columns={[
            { key: "label", header: "Cell type" },
            { key: "value", header: "Count", align: "right" },
          ]}
          rows={rows}
        />
      }
    >
      <BarList
        data={rows}
        color={SINGLE_SERIES_FILL}
        valueLabel="receptors"
        selected={filters.celltypeId}
        onSelect={(datum) =>
          typeof datum.key === "number" &&
          update({ celltypeId: toggle(filters.celltypeId, datum.key) })
        }
      />
    </Panel>
  );
}

function Cdr3Panel({ breakdown, stale }: { breakdown: Breakdown; stale: boolean }) {
  const rows = breakdown.rows as unknown as Cdr3Row[];
  return (
    <Panel
      title="CDR3 length"
      subtitle="The antigen-contacting loop, by locus"
      provenance={breakdown.provenance}
      note={breakdown.note || undefined}
      span={6}
      stale={stale}
      table={
        <DataTable
          caption="CDR3 length percentiles by chain"
          columns={[
            { key: "chain", header: "Chain" },
            { key: "count", header: "Chains", align: "right" },
            { key: "cdr3_mean", header: "Mean", align: "right" },
            { key: "p05", header: "p05", align: "right" },
            { key: "p25", header: "p25", align: "right" },
            { key: "median", header: "Median", align: "right" },
            { key: "p75", header: "p75", align: "right" },
            { key: "p95", header: "p95", align: "right" },
          ]}
          rows={rows as unknown as Record<string, unknown>[]}
        />
      }
    >
      <Cdr3Box rows={rows} />
    </Panel>
  );
}

function IsotypePanel({ breakdown, stale }: { breakdown: Breakdown; stale: boolean }) {
  const segments = breakdown.rows
    .map((row) => ({
      key: String(row.isotype),
      label: String(row.isotype),
      value: Number(row.count),
      color: ISOTYPE_COLOR[String(row.isotype)] ?? SINGLE_SERIES,
      fill: ISOTYPE_FILL[String(row.isotype)] ?? SINGLE_SERIES_FILL,
    }))
    .filter((segment) => segment.value > 0);

  return (
    <Panel
      title="Isotypes"
      subtitle="Heavy chain constant region"
      provenance={breakdown.provenance}
      note={breakdown.note || undefined}
      span={5}
      stale={stale}
      table={
        <DataTable
          caption="Receptors by isotype"
          columns={[
            { key: "isotype", header: "Isotype" },
            { key: "count", header: "Count", align: "right" },
          ]}
          rows={breakdown.rows}
        />
      }
    >
      {segments.length === 0 ? (
        <Message title="No isotype breakdown for this slice">
          <p>{breakdown.note}</p>
        </Message>
      ) : (
        <Ribbon segments={segments} unit="receptors" />
      )}
    </Panel>
  );
}

function AllelePanel({ breakdown, stale }: { breakdown: Breakdown; stale: boolean }) {
  const rows = breakdown.rows.map((row) => ({
    key: Number(row.vj_allele_id),
    label: String(row.vj_allele_name),
    meta: String(row.vj_allele_segment ?? ""),
    value: Number(row.count),
    mono: true,
  }));

  return (
    <Panel
      title="V and J allele usage"
      subtitle={`The ${rows.length} most used germline alleles`}
      provenance={breakdown.provenance}
      note={breakdown.note || undefined}
      span={7}
      stale={stale}
      table={
        <DataTable
          caption="Most used V and J alleles"
          columns={[
            { key: "label", header: "Allele", mono: true },
            { key: "meta", header: "Segment", mono: true },
            { key: "value", header: "Count", align: "right" },
          ]}
          rows={rows}
        />
      }
    >
      <BarList data={rows} color={SINGLE_SERIES_FILL} valueLabel="rearrangements" />
    </Panel>
  );
}

function MutfreqPanel({ breakdown }: { breakdown: Breakdown }) {
  return (
    <Panel
      title="Somatic hypermutation"
      subtitle="Mutation frequency away from germline"
      provenance={breakdown.provenance}
      span={12}
    >
      <Message title="Not computed for this dataset">
        <p>{breakdown.note}</p>
        <p>
          The schema carries six mutation-frequency statistics beside every CDR3
          statistic, and the CDR3 half is fully populated. Re-running the mutation
          step upstream would fill this panel with no change here.
        </p>
      </Message>
    </Panel>
  );
}

