import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Grain, Provenance } from "../api/types";
import { Message } from "../components/Message";
import { provenanceNote } from "../components/Provenance";
import { SliceBar } from "../components/SliceBar";
import { useFilters } from "../state/FilterProvider";
import { useAsync } from "../state/useAsync";
import { useLabels } from "../state/useLabels";
import "./QueryDownload.css";

const PAGE_SIZE = 50;

/**
 * Query and download.
 *
 * The preview and the file come from the same query, so what is on screen is what
 * lands in the file -- only the pagination differs. Every exported row carries the
 * study it came from.
 */
export function QueryDownload() {
  const { filters } = useFilters();
  const labels = useLabels();
  const measures = useAsync(() => api.measures(), []);

  const [measure, setMeasure] = useState("chain");
  const [grain, setGrain] = useState<Grain>("sample");
  const [page, setPage] = useState(1);

  const selected = measures.data?.find((m) => m.name === measure);

  // Not every face of the cube is stored at every level.
  useEffect(() => {
    if (selected && !selected.grains.includes(grain)) setGrain(selected.grains[0]);
  }, [selected, grain]);

  useEffect(() => setPage(1), [measure, grain, JSON.stringify(filters)]);

  const result = useAsync(
    () => api.query(filters, { measure, grain, page, pageSize: PAGE_SIZE }),
    [measure, grain, page, JSON.stringify(filters)],
  );

  const totalPages = result.data ? Math.max(1, Math.ceil(result.data.total / PAGE_SIZE)) : 1;

  return (
    <div className="query">
      <header>
        <h1 className="query__title">Query and download</h1>
        <p className="query__subtitle">
          Pick a statistic and a level, narrow it with the filters, then take the whole
          result as a file. Every row is tagged with the study it came from.
        </p>
      </header>

      <SliceBar labels={labels} />

      <div className="query__controls">
        <label className="query__field">
          <span>Statistic</span>
          <select value={measure} onChange={(event) => setMeasure(event.target.value)}>
            {(measures.data ?? []).map((option) => (
              <option key={option.name} value={option.name}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="query__field">
          <span>Level</span>
          <select
            value={grain}
            onChange={(event) => setGrain(event.target.value as Grain)}
          >
            {(selected?.grains ?? ["sample"]).map((option) => (
              <option key={option} value={option}>
                {option === "study" ? "Per study" : option === "subject" ? "Per subject" : "Per sample"}
              </option>
            ))}
          </select>
        </label>

        <div className="query__downloads">
          <a
            className="query__download"
            href={api.exportUrl(filters, { measure, grain, format: "csv" })}
          >
            Download CSV
          </a>
          <a
            className="query__download"
            href={api.exportUrl(filters, { measure, grain, format: "tsv" })}
          >
            Download TSV
          </a>
        </div>
      </div>

      {result.error ? (
        <Message title="That query could not run" tone="problem">
          <p>{result.error.message}</p>
        </Message>
      ) : !result.data ? (
        <p className="query__loading">Loading…</p>
      ) : (
        <>
          <div className="query__summary">
            <span className="num">{result.data.total.toLocaleString("en")}</span> rows
            {result.data.total > PAGE_SIZE && (
              <>
                {" "}&mdash; showing {(page - 1) * PAGE_SIZE + 1} to{" "}
                {Math.min(page * PAGE_SIZE, result.data.total)}
              </>
            )}
          </div>

          {result.data.notes.map((note) => (
            <p className="query__note" key={note}>
              {note}
            </p>
          ))}

          <div className={`query__table-wrap${result.stale ? " query__table-wrap--stale" : ""}`}>
            <table className="query__table">
              <thead>
                <tr>
                  {result.data.columns.map((column) => (
                    <th key={column} scope="col">
                      <span>{humanise(column)}</span>
                      <ColumnMark provenance={result.data!.provenance[column]} />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.data.rows.map((row, index) => (
                  <tr key={index}>
                    {result.data!.columns.map((column) => (
                      <td key={column} className={cellClass(column, row[column])}>
                        {formatCell(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <nav className="query__pager" aria-label="Result pages">
              <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span className="num">
                Page {page} of {totalPages}
              </span>
              <button
                type="button"
                disabled={page === totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </nav>
          )}
        </>
      )}
    </div>
  );
}

function ColumnMark({ provenance }: { provenance: Provenance | undefined }) {
  if (!provenance || provenance === "exact") return null;
  const short =
    provenance === "empty"
      ? "no data"
      : provenance === "unavailable"
        ? "not available"
        : provenance === "approximate"
          ? "approximate"
          : "summed";
  return (
    <span className="query__colmark" title={provenanceNote(provenance)}>
      {short}
    </span>
  );
}

function humanise(column: string): string {
  return column
    .replace(/_/g, " ")
    .replace(/\bcdr3\b/i, "CDR3")
    .replace(/\bvj\b/i, "V/J")
    .replace(/\bigh\b/gi, "IGH")
    .replace(/^./, (c) => c.toUpperCase());
}

function cellClass(column: string, value: unknown): string {
  const classes: string[] = [];
  if (typeof value === "number") classes.push("query__num");
  if (column.includes("allele_name") || column.includes("segment") || column.includes("gene")) {
    classes.push("mono");
  }
  if (value === null) classes.push("query__null");
  return classes.join(" ");
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "--";
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString("en") : value.toFixed(2);
  }
  return String(value);
}
