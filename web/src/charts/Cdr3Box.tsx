import { useState } from "react";
import { chainFill, formatDecimal } from "./palette";
import "./Cdr3Box.css";

export interface Cdr3Row {
  chain: string;
  count: number;
  cdr3_mean: number | null;
  p05: number | null;
  p25: number | null;
  median: number | null;
  p75: number | null;
  p95: number | null;
}

/**
 * CDR3 length distribution, one box per chain.
 *
 * The five stored percentiles are exactly a box plot's five numbers, so this is
 * the distribution the database actually holds rather than a reconstruction.
 *
 * Splitting by chain is not cosmetic: heavy chains average about 46 nucleotides
 * and light chains about 27, so a merged axis would describe a population that
 * does not exist.
 */
export function Cdr3Box({ rows }: { rows: Cdr3Row[] }) {
  const [unit, setUnit] = useState<"nt" | "aa">("nt");

  const plottable = rows.filter((r) => r.p05 !== null && r.p95 !== null);
  if (plottable.length === 0) {
    return (
      <p className="cdr3__empty">
        Percentiles are not available for the current selection, so no distribution can
        be drawn. Clear the filter, or read the mean from the table view.
      </p>
    );
  }

  const convert = (value: number) => (unit === "aa" ? value / 3 : value);
  const lo = Math.floor(Math.min(...plottable.map((r) => convert(r.p05!))) - 2);
  const hi = Math.ceil(Math.max(...plottable.map((r) => convert(r.p95!))) + 2);
  const position = (value: number) => ((convert(value) - lo) / (hi - lo)) * 100;

  const ticks = axisTicks(lo, hi);

  return (
    <div className="cdr3">
      <div className="cdr3__controls">
        <div className="cdr3__toggle" role="group" aria-label="CDR3 length unit">
          <button type="button" aria-pressed={unit === "nt"} onClick={() => setUnit("nt")}>
            Nucleotides
          </button>
          <button type="button" aria-pressed={unit === "aa"} onClick={() => setUnit("aa")}>
            Amino acids
          </button>
        </div>
      </div>

      <ul className="cdr3__rows" role="list">
        {plottable.map((row) => (
          <li key={row.chain} className="cdr3__row">
            <span className="cdr3__chain">{row.chain}</span>
            <span
              className="cdr3__track"
              title={summary(row, unit)}
              role="img"
              aria-label={summary(row, unit)}
            >
              <span className="cdr3__grid" aria-hidden="true">
                {ticks.map((tick) => (
                  <span
                    key={tick}
                    className="cdr3__gridline"
                    style={{ left: `${((tick - lo) / (hi - lo)) * 100}%` }}
                  />
                ))}
              </span>
              <span
                className="cdr3__whisker"
                style={{
                  left: `${position(row.p05!)}%`,
                  width: `${position(row.p95!) - position(row.p05!)}%`,
                }}
              />
              <span
                className="cdr3__box"
                style={{
                  left: `${position(row.p25!)}%`,
                  width: `${boxWidth(position(row.p25!), position(row.p75!))}%`,
                  background: chainFill(row.chain),
                }}
              />
              {row.median !== null &&
                boxWidth(position(row.p25!), position(row.p75!)) > 3 && (
                  <span className="cdr3__median" style={{ left: `${position(row.median)}%` }} />
                )}
              {row.cdr3_mean !== null && (
                <span
                  className="cdr3__mean"
                  style={{ left: `${position(row.cdr3_mean)}%` }}
                  title={`Mean ${formatDecimal(convert(row.cdr3_mean))} ${unit}`}
                />
              )}
            </span>
            <span className="cdr3__median-value num">
              {row.median === null ? "--" : formatDecimal(convert(row.median))}
            </span>
          </li>
        ))}
      </ul>

      <div className="cdr3__axis" aria-hidden="true">
        <span className="cdr3__chain" />
        <span className="cdr3__axis-track">
          {ticks.map((tick) => (
            <span
              key={tick}
              className="cdr3__tick num"
              style={{ left: `${((tick - lo) / (hi - lo)) * 100}%` }}
            >
              {tick}
            </span>
          ))}
        </span>
        <span className="cdr3__median-value" />
      </div>

      <p className="cdr3__key">
        Box spans the 25th to 75th percentile, whisker the 5th to 95th; the rule marks
        the median and the ringed dot the mean.
      </p>
    </div>
  );
}

/**
 * Light-chain CDR3 lengths are so tightly distributed that p25 and p75 are often
 * the same value. The box still has to be visible, and a median rule drawn inside
 * one that narrow would erase it, so the floor is a mark you can actually see.
 */
function boxWidth(p25: number, p75: number): number {
  return Math.max(p75 - p25, 1.6);
}

function summary(row: Cdr3Row, unit: "nt" | "aa"): string {
  const convert = (value: number | null) =>
    value === null ? "--" : formatDecimal(unit === "aa" ? value / 3 : value);
  return (
    `${row.chain}: median ${convert(row.median)} ${unit}, ` +
    `p25 ${convert(row.p25)}, p75 ${convert(row.p75)}, ` +
    `p05 ${convert(row.p05)}, p95 ${convert(row.p95)}, ` +
    `mean ${convert(row.cdr3_mean)}`
  );
}

/** Clean round ticks across the domain. */
function axisTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 60 ? 15 : span > 30 ? 10 : span > 12 ? 5 : 2;
  const first = Math.ceil(lo / step) * step;
  const ticks: number[] = [];
  for (let value = first; value <= hi; value += step) ticks.push(value);
  return ticks;
}
