import { formatCount } from "./palette";
import "./BarList.css";

export interface BarDatum {
  key: string | number;
  label: string;
  value: number;
  /** Secondary identifier shown beside the label, e.g. an allele's segment. */
  meta?: string;
  mono?: boolean;
}

interface BarListProps {
  data: BarDatum[];
  color?: string;
  valueLabel: string;
  onSelect?: (datum: BarDatum) => void;
  selected?: (string | number)[];
}

/**
 * Horizontal bars for nominal categories.
 *
 * One colour for every bar: the categories have no natural order, so shading by
 * value would burn the colour channel restating the bar length. Values sit at the
 * tips, which is what makes the chart readable without hovering.
 */
export function BarList({
  data,
  color = "var(--series-1)",
  valueLabel,
  onSelect,
  selected = [],
}: BarListProps) {
  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <ul className="barlist" role="list">
      {data.map((datum) => {
        const share = (datum.value / max) * 100;
        const isSelected = selected.includes(datum.key);
        const Row = onSelect ? "button" : "div";
        return (
          <li key={datum.key} className="barlist__row">
            <Row
              className={`barlist__hit${isSelected ? " barlist__hit--on" : ""}`}
              {...(onSelect
                ? {
                    type: "button" as const,
                    onClick: () => onSelect(datum),
                    "aria-pressed": isSelected,
                  }
                : {})}
              title={`${datum.label}: ${formatCount(datum.value)} ${valueLabel}`}
            >
              <span className={`barlist__label${datum.mono ? " mono" : ""}`}>
                {datum.label}
                {datum.meta && <span className="barlist__meta">{datum.meta}</span>}
              </span>
              <span className="barlist__track">
                <span
                  className="barlist__fill"
                  style={{ width: `${share}%`, background: color }}
                />
              </span>
              <span className="barlist__value num">{formatCount(datum.value)}</span>
            </Row>
          </li>
        );
      })}
    </ul>
  );
}
