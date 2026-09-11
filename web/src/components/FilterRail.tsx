import { useMemo, useState } from "react";
import { api } from "../api/client";
import type { AlleleInfo, FacetAvailability, SampleOverview, SubjectOverview } from "../api/types";
import { useAsync } from "../state/useAsync";
import { useMediaQuery } from "../state/useMediaQuery";
import { countActive, toggle } from "../state/filters";
import { useFilters } from "../state/FilterProvider";
import { CHAIN_COLOR } from "../charts/palette";
import "./FilterRail.css";

/**
 * One filter surface for the whole page.
 *
 * Facets are not hard-coded: the API reports which ones have values behind them,
 * and the unpopulated ones are listed together at the bottom with the reason. That
 * way the rail tells the truth about this dataset today, and gains the metadata
 * filters automatically once the pipeline fills those columns.
 */
export function FilterRail() {
  const { filters, update, clear } = useFilters();
  // On a phone the rail sits above the content, so leaving every facet expanded
  // would bury the dashboard under a screen and a half of checkboxes.
  const stacked = useMediaQuery("(max-width: 900px)");
  const facets = useAsync(() => api.facets(), []);
  const subjects = useAsync(() => api.subjects(), []);
  const samples = useAsync(() => api.samples(), []);
  const alleles = useAsync(() => api.alleles(), []);

  const byField = useMemo(() => {
    const map = new Map<string, FacetAvailability>();
    (facets.data ?? []).forEach((facet) => map.set(facet.field, facet));
    return map;
  }, [facets.data]);

  const unavailable = (facets.data ?? []).filter((facet) => !facet.available);

  const sections = (
    <>
      <Section title="Chain" hint="Immunoglobulin locus" open active={filters.chain.length}>
        <CheckList
          items={(byField.get("chain")?.values ?? []).map((value) => ({
            id: String(value.value),
            label: String(value.label),
            count: value.count,
            swatch: CHAIN_COLOR[String(value.value)],
          }))}
          selected={filters.chain}
          onToggle={(id) => update({ chain: toggle(filters.chain, id) })}
        />
      </Section>

      <Section title="Cell type" hint="Annotated by the GEX pipeline" scroll active={filters.celltypeId.length}>
        <CheckList
          items={(byField.get("celltype_id")?.values ?? []).map((value) => ({
            id: String(value.value),
            label: String(value.label),
            count: value.count,
          }))}
          selected={filters.celltypeId.map(String)}
          onToggle={(id) =>
            update({ celltypeId: toggle(filters.celltypeId, Number(id)) })
          }
        />
      </Section>

      <Section title="Allele segment" hint="Derived from the allele name" active={filters.alleleSegment.length}>
        <CheckList
          items={(byField.get("allele_segment")?.values ?? []).map((value) => ({
            id: String(value.value),
            label: String(value.label),
            count: value.count,
            mono: true,
          }))}
          selected={filters.alleleSegment}
          onToggle={(id) => update({ alleleSegment: toggle(filters.alleleSegment, id) })}
        />
      </Section>

      <Section
        title="Allele"
        hint={`${alleles.data?.length ?? 0} germline V and J alleles`}
        active={filters.alleleId.length}
      >
        <AlleleSearch
          alleles={alleles.data ?? []}
          selected={filters.alleleId}
          onToggle={(id) => update({ alleleId: toggle(filters.alleleId, id) })}
        />
      </Section>

      <Section title="Subject" hint={`${subjects.data?.length ?? 0} in the database`} scroll active={filters.subjectId.length}>
        <CheckList
          items={(subjects.data ?? []).map((subject: SubjectOverview) => ({
            id: String(subject.subject_id),
            label: subject.subject_name ?? `Subject ${subject.subject_id}`,
            count: subject.count_bcrs,
          }))}
          selected={filters.subjectId.map(String)}
          onToggle={(id) => update({ subjectId: toggle(filters.subjectId, Number(id)) })}
        />
      </Section>

      <Section title="Sample" hint={`${samples.data?.length ?? 0} in the database`} scroll active={filters.sampleId.length}>
        <CheckList
          items={(samples.data ?? []).map((sample: SampleOverview) => ({
            id: String(sample.sample_id),
            label: sample.sample_name ?? `Sample ${sample.sample_id}`,
            count: sample.count_bcrs,
          }))}
          selected={filters.sampleId.map(String)}
          onToggle={(id) => update({ sampleId: toggle(filters.sampleId, Number(id)) })}
        />
      </Section>

      {unavailable.length > 0 && (
        <details className="rail__unavailable">
          <summary>
            {unavailable.length} filters waiting on metadata
          </summary>
          <p className="rail__unavailable-intro">
            These are the study and subject descriptors the portal is designed to
            facet by. None of the columns hold values in the loaded dataset, so the
            filters stay off. They switch on by themselves once the pipeline
            populates them -- nothing here needs changing.
          </p>
          <ul>
            {unavailable.map((facet) => (
              <li key={facet.field}>
                <span>{facet.label}</span>
                <span className="rail__level">{facet.level}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </>
  );

  const active = countActive(filters);

  if (stacked) {
    return (
      <aside className="rail rail--stacked" aria-label="Filters">
        <details className="rail__disclosure">
          <summary>
            <span>Filters</span>
            {active > 0 && <span className="rail__badge">{active} active</span>}
          </summary>
          <div className="rail__disclosure-body">
            <button type="button" className="rail__clear" onClick={clear}>
              Clear all
            </button>
            {sections}
          </div>
        </details>
      </aside>
    );
  }

  return (
    <aside className="rail" aria-label="Filters">
      <div className="rail__head">
        <h2 className="rail__title">Filters</h2>
        <button type="button" className="rail__clear" onClick={clear}>
          Clear all
        </button>
      </div>
      {sections}
    </aside>
  );
}

function Section({
  title,
  hint,
  scroll = false,
  open = false,
  active = 0,
  children,
}: {
  title: string;
  hint?: string;
  scroll?: boolean;
  open?: boolean;
  active?: number;
  children: React.ReactNode;
}) {
  return (
    <details className="rail__section" open={open || active > 0}>
      <summary className="rail__section-head">
        <span className="rail__section-title">{title}</span>
        {active > 0 && <span className="rail__section-count num">{active}</span>}
        <span className="rail__chevron" aria-hidden="true" />
      </summary>
      {hint && <p className="rail__hint">{hint}</p>}
      <div className={scroll ? "rail__scroll" : undefined}>{children}</div>
    </details>
  );
}

interface CheckItem {
  id: string;
  label: string;
  count?: number | null;
  swatch?: string;
  mono?: boolean;
}

function CheckList({
  items,
  selected,
  onToggle,
}: {
  items: CheckItem[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  if (items.length === 0) {
    return <p className="rail__empty">Loading…</p>;
  }
  const max = Math.max(...items.map((item) => item.count ?? 0), 1);
  return (
    <ul className="rail__list" role="list">
      {items.map((item) => {
        const checked = selected.includes(item.id);
        const share = ((item.count ?? 0) / max) * 100;
        return (
          <li key={item.id}>
            <label className={`rail__item${checked ? " rail__item--on" : ""}`}>
              {/* A share bar behind each row: the rail reports the shape of the
                  data, not just the names of its categories. */}
              <span className="rail__share" style={{ width: `${share}%` }} aria-hidden="true" />
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggle(item.id)}
              />
              {item.swatch && (
                <span className="rail__swatch" style={{ background: item.swatch }} />
              )}
              <span className={`rail__label${item.mono ? " mono" : ""}`}>{item.label}</span>
              {item.count !== null && item.count !== undefined && (
                <span className="rail__count num">{item.count.toLocaleString("en")}</span>
              )}
            </label>
          </li>
        );
      })}
    </ul>
  );
}

/**
 * The allele picker.
 *
 * Three hundred and forty-one values will not fit in a rail as a checkbox list,
 * and scrolling to IGHV4-38-2*02 is nobody's idea of a filter. A search field
 * narrows first; selected alleles stay pinned at the top so a choice never
 * scrolls out of sight while you look for the next one.
 */
function AlleleSearch({
  alleles,
  selected,
  onToggle,
}: {
  alleles: AlleleInfo[];
  selected: number[];
  onToggle: (id: number) => void;
}) {
  const [term, setTerm] = useState("");

  const shown = useMemo(() => {
    const needle = term.trim().toLowerCase();
    const matches = needle
      ? alleles.filter(
          (a) =>
            a.vj_allele_name.toLowerCase().includes(needle) ||
            (a.vj_allele_segment ?? "").toLowerCase().includes(needle),
        )
      : alleles;
    const picked = matches.filter((a) => selected.includes(a.vj_allele_id));
    const rest = matches.filter((a) => !selected.includes(a.vj_allele_id));
    // The list arrives ordered by usage, so the untyped view leads with the
    // alleles anyone is most likely to want.
    return [...picked, ...rest].slice(0, 60);
  }, [alleles, term, selected]);

  if (alleles.length === 0) {
    return <p className="rail__empty">Loading…</p>;
  }

  return (
    <div className="rail__search">
      <input
        type="search"
        className="rail__search-input"
        value={term}
        placeholder="Search alleles, e.g. IGHV1-18"
        onChange={(event) => setTerm(event.target.value)}
        aria-label="Search alleles"
      />
      <div className="rail__scroll">
        <CheckList
          items={shown.map((allele) => ({
            id: String(allele.vj_allele_id),
            label: allele.vj_allele_name,
            count: allele.count_vj_allele,
            mono: true,
          }))}
          selected={selected.map(String)}
          onToggle={(id) => onToggle(Number(id))}
        />
      </div>
      {shown.length === 0 && <p className="rail__empty">No allele matches that.</p>}
    </div>
  );
}
