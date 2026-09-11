import { formatCount } from "./palette";
import "./Ribbon.css";

export interface RibbonSegment {
  key: string;
  label: string;
  value: number;
  /** The legend swatch: a small mark, so full chroma. */
  color: string;
  /** The bar itself: a large area, so the softened step. Defaults to `color`. */
  fill?: string;
}

interface RibbonProps {
  segments: RibbonSegment[];
  /** Large type on the segment labels; used for the page's opening chart. */
  lead?: boolean;
  unit: string;
  onSelect?: (key: string) => void;
  selected?: string[];
}

/**
 * One part-to-whole bar.
 *
 * This is the shape of a repertoire: what proportion of it is heavy chain, kappa
 * and lambda. It opens the dashboard because it is the most characteristic thing
 * about the dataset -- more so than any single count.
 *
 * Segments are separated by a 2px gap in the surface colour rather than a stroke,
 * so nothing but data carries ink.
 */
export function Ribbon({ segments, lead = false, unit, onSelect, selected = [] }: RibbonProps) {
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  if (total === 0) {
    return <p className="ribbon__empty">Nothing matches the current filters.</p>;
  }

  return (
    <div className={`ribbon${lead ? " ribbon--lead" : ""}`}>
      <div className="ribbon__bar" role="img" aria-label={ariaLabel(segments, total, unit)}>
        {segments.map((segment) => (
          <span
            key={segment.key}
            className="ribbon__segment"
            style={{
              flexGrow: segment.value,
              background: segment.fill ?? segment.color,
            }}
            title={`${segment.label}: ${formatCount(segment.value)} ${unit} (${share(segment.value, total)})`}
          />
        ))}
      </div>

      <ul className="ribbon__legend" role="list">
        {segments.map((segment) => {
          const isSelected = selected.includes(segment.key);
          const Row = onSelect ? "button" : "div";
          return (
            <li key={segment.key}>
              <Row
                className={`ribbon__key${isSelected ? " ribbon__key--on" : ""}`}
                {...(onSelect
                  ? {
                      type: "button" as const,
                      onClick: () => onSelect(segment.key),
                      "aria-pressed": isSelected,
                    }
                  : {})}
              >
                <span className="ribbon__swatch" style={{ background: segment.color }} />
                <span className="ribbon__name">{segment.label}</span>
                <span className="ribbon__value num">{formatCount(segment.value)}</span>
                <span className="ribbon__share num">{share(segment.value, total)}</span>
              </Row>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function share(value: number, total: number): string {
  return `${((value / total) * 100).toFixed(1)}%`;
}

function ariaLabel(segments: RibbonSegment[], total: number, unit: string): string {
  const parts = segments.map((s) => `${s.label} ${formatCount(s.value)} ${share(s.value, total)}`);
  return `${formatCount(total)} ${unit}: ${parts.join(", ")}`;
}
