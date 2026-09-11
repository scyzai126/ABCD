import type { Kpi } from "../api/types";
import { formatCompact } from "../charts/palette";
import { ProvenanceMark } from "./Provenance";
import "./StatRow.css";

/**
 * The headline counts.
 *
 * These are figures, not charts -- a bar chart of eight unrelated totals would be
 * a category error. Each carries its provenance so a filtered count never passes
 * for a stored one.
 */
export function StatRow({ kpis }: { kpis: Kpi[] }) {
  return (
    <dl className="stats">
      {kpis.map((kpi) => (
        <div className="stats__tile" key={kpi.key} title={kpi.note || undefined}>
          <dt className="stats__label">{kpi.label}</dt>
          <dd className="stats__value">{formatCompact(kpi.value)}</dd>
          <div className="stats__mark">
            <ProvenanceMark value={kpi.provenance} />
          </div>
        </div>
      ))}
    </dl>
  );
}
