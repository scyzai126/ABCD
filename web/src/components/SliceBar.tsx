import { useFilters } from "../state/FilterProvider";
import { countActive, isEmpty } from "../state/filters";
import "./SliceBar.css";

interface Chip {
  key: string;
  label: string;
  remove: () => void;
}

/**
 * What the numbers below are actually about.
 *
 * The rail holds the controls; this row states the slice in words, directly above
 * the charts it scopes, so a reader arriving at a filtered link knows what they
 * are looking at without reading the rail.
 */
export function SliceBar({
  labels,
  scopeNote = "Showing every sample in the database. Use the filters to narrow the slice.",
}: {
  labels: { celltypes: Map<number, string>; subjects: Map<number, string>; samples: Map<number, string> };
  /** What is on screen before any filter is applied. A study page is already
   *  narrowed to one study, so it must not claim to show everything. */
  scopeNote?: string;
}) {
  const { filters, update, clear } = useFilters();

  if (isEmpty(filters)) {
    return <p className="slice slice--all">{scopeNote}</p>;
  }

  const chips: Chip[] = [
    ...listChips(filters.chain, "Chain", (value) => value, (next) => update({ chain: next })),
    ...listChips(
      filters.celltypeId,
      "Cell type",
      (value) => labels.celltypes.get(value) ?? `#${value}`,
      (next) => update({ celltypeId: next }),
    ),
    ...listChips(
      filters.alleleSegment,
      "Segment",
      (value) => value,
      (next) => update({ alleleSegment: next }),
    ),
    ...listChips(
      filters.subjectId,
      "Subject",
      (value) => labels.subjects.get(value) ?? `#${value}`,
      (next) => update({ subjectId: next }),
    ),
    ...listChips(
      filters.sampleId,
      "Sample",
      (value) => labels.samples.get(value) ?? `#${value}`,
      (next) => update({ sampleId: next }),
    ),
  ];

  return (
    <div className="slice">
      <span className="slice__lead">
        {countActive(filters)} {countActive(filters) === 1 ? "filter" : "filters"}
      </span>
      <ul className="slice__chips" role="list">
        {chips.map((chip) => (
          <li key={chip.key}>
            <button type="button" className="slice__chip" onClick={chip.remove}>
              <span className="slice__kind">{chip.label}</span>
              <span className="slice__value">{chip.key.split("::")[1]}</span>
              <span aria-hidden="true" className="slice__x">
                &times;
              </span>
              <span className="visually-hidden">Remove filter</span>
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="slice__clear" onClick={clear}>
        Clear all
      </button>
    </div>
  );
}

function listChips<T extends string | number>(
  values: T[],
  kind: string,
  label: (value: T) => string,
  onChange: (next: T[]) => void,
): Chip[] {
  return values.map((value) => ({
    key: `${kind}::${label(value)}`,
    label: kind,
    remove: () => onChange(values.filter((v) => v !== value)),
  }));
}

