import { useState } from "react";
import type { ReactNode } from "react";
import type { Provenance } from "../api/types";
import { ProvenanceMark } from "./Provenance";
import "./Panel.css";

interface PanelProps {
  title: string;
  subtitle?: string;
  provenance?: Provenance;
  note?: string;
  /** The table twin. Every chart has one: it is the accessible path to values
   *  that colour alone cannot carry, and researchers want the numbers anyway. */
  table?: ReactNode;
  children: ReactNode;
  span?: number;
  stale?: boolean;
}

export function Panel({
  title,
  subtitle,
  provenance,
  note,
  table,
  children,
  span = 6,
  stale = false,
}: PanelProps) {
  const [showTable, setShowTable] = useState(false);

  return (
    <section className="panel" style={{ gridColumn: `span ${span}` }}>
      <header className="panel__head">
        <div className="panel__titles">
          <h2 className="panel__title">{title}</h2>
          {subtitle && <p className="panel__subtitle">{subtitle}</p>}
        </div>
        <div className="panel__tools">
          {provenance && <ProvenanceMark value={provenance} />}
          {table && (
            <div className="panel__toggle" role="group" aria-label={`${title} view`}>
              <button
                type="button"
                aria-pressed={!showTable}
                onClick={() => setShowTable(false)}
              >
                Chart
              </button>
              <button
                type="button"
                aria-pressed={showTable}
                onClick={() => setShowTable(true)}
              >
                Table
              </button>
            </div>
          )}
        </div>
      </header>

      <div className={`panel__body${stale ? " panel__body--stale" : ""}`}>
        {showTable && table ? table : children}
      </div>

      {note && <p className="panel__note">{note}</p>}
    </section>
  );
}
