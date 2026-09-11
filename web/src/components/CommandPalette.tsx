import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { FacetAvailability } from "../api/types";
import { CHAIN_COLOR } from "../charts/palette";
import { toggle } from "../state/filters";
import { useFilters } from "../state/FilterProvider";
import { useAsync } from "../state/useAsync";
import "./CommandPalette.css";

interface Entry {
  id: string;
  kind: "Chain" | "Cell type" | "Allele" | "Subject" | "Sample";
  label: string;
  detail?: string;
  count?: number | null;
  swatch?: string;
  mono?: boolean;
  active: boolean;
  apply: () => void;
}

const LIMIT = 40;

/**
 * Type-to-filter across every dimension at once.
 *
 * The rail can browse three chains and thirty-six cell types comfortably. It
 * cannot browse 341 alleles, and nobody wants to scroll to IGHV4-38-2*02 -- they
 * want to type it. This is the fast path; the rail stays for exploring.
 */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { filters, update } = useFilters();
  const [term, setTerm] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const facets = useAsync(() => api.facets(), []);
  const alleles = useAsync(() => api.alleles(), []);
  const subjects = useAsync(() => api.subjects(), []);
  const samples = useAsync(() => api.samples(), []);

  useEffect(() => {
    if (open) {
      setTerm("");
      setCursor(0);
      // Autofocus after the dialog paints, or the caret lands nowhere.
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  const entries = useMemo<Entry[]>(() => {
    const byField = new Map<string, FacetAvailability>();
    (facets.data ?? []).forEach((facet) => byField.set(facet.field, facet));
    const out: Entry[] = [];

    (byField.get("chain")?.values ?? []).forEach((value) => {
      const chain = String(value.value);
      out.push({
        id: `chain:${chain}`,
        kind: "Chain",
        label: chain,
        count: value.count,
        swatch: CHAIN_COLOR[chain],
        active: filters.chain.includes(chain),
        apply: () => update({ chain: toggle(filters.chain, chain) }),
      });
    });

    (byField.get("celltype_id")?.values ?? []).forEach((value) => {
      const id = Number(value.value);
      out.push({
        id: `celltype:${id}`,
        kind: "Cell type",
        label: value.label,
        count: value.count,
        active: filters.celltypeId.includes(id),
        apply: () => update({ celltypeId: toggle(filters.celltypeId, id) }),
      });
    });

    (alleles.data ?? []).forEach((allele) => {
      out.push({
        id: `allele:${allele.vj_allele_id}`,
        kind: "Allele",
        label: allele.vj_allele_name,
        detail: allele.vj_allele_segment ?? undefined,
        count: allele.count_vj_allele,
        mono: true,
        active: filters.alleleId.includes(allele.vj_allele_id),
        apply: () => update({ alleleId: toggle(filters.alleleId, allele.vj_allele_id) }),
      });
    });

    (subjects.data ?? []).forEach((subject) => {
      out.push({
        id: `subject:${subject.subject_id}`,
        kind: "Subject",
        label: subject.subject_name ?? `#${subject.subject_id}`,
        count: subject.count_bcrs,
        active: filters.subjectId.includes(subject.subject_id),
        apply: () => update({ subjectId: toggle(filters.subjectId, subject.subject_id) }),
      });
    });

    (samples.data ?? []).forEach((sample) => {
      out.push({
        id: `sample:${sample.sample_id}`,
        kind: "Sample",
        label: sample.sample_name ?? `#${sample.sample_id}`,
        detail: sample.subject_name ?? undefined,
        count: sample.count_bcrs,
        active: filters.sampleId.includes(sample.sample_id),
        apply: () => update({ sampleId: toggle(filters.sampleId, sample.sample_id) }),
      });
    });

    return out;
  }, [facets.data, alleles.data, subjects.data, samples.data, filters, update]);

  const results = useMemo(() => {
    const needle = term.trim().toLowerCase();
    const matching = needle
      ? entries.filter(
          (entry) =>
            entry.label.toLowerCase().includes(needle) ||
            entry.kind.toLowerCase().includes(needle) ||
            entry.detail?.toLowerCase().includes(needle),
        )
      : // With no search term, lead with what is already applied.
        [...entries].sort((a, b) => Number(b.active) - Number(a.active));
    return matching.slice(0, LIMIT);
  }, [entries, term]);

  useEffect(() => setCursor(0), [term]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setCursor((c) => Math.min(c + 1, results.length - 1));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setCursor((c) => Math.max(c - 1, 0));
      } else if (event.key === "Enter") {
        event.preventDefault();
        results[cursor]?.apply();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, results, cursor, onClose]);

  useEffect(() => {
    listRef.current?.children[cursor]?.scrollIntoView({ block: "nearest" });
  }, [cursor]);

  if (!open) return null;

  return (
    <div className="palette__scrim" onMouseDown={onClose} role="presentation">
      <div
        className="palette"
        role="dialog"
        aria-modal="true"
        aria-label="Filter the dataset"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <input
          ref={inputRef}
          className="palette__input"
          value={term}
          placeholder="Filter by chain, cell type, allele, subject or sample"
          onChange={(event) => setTerm(event.target.value)}
          aria-label="Search filters"
        />

        <ul className="palette__list" ref={listRef} role="listbox">
          {results.map((entry, index) => (
            <li key={entry.id}>
              <button
                type="button"
                role="option"
                aria-selected={index === cursor}
                className={`palette__row${index === cursor ? " palette__row--cursor" : ""}${
                  entry.active ? " palette__row--on" : ""
                }`}
                onMouseEnter={() => setCursor(index)}
                onClick={entry.apply}
              >
                <span className="palette__kind">{entry.kind}</span>
                {entry.swatch && (
                  <span className="palette__swatch" style={{ background: entry.swatch }} />
                )}
                <span className={`palette__label${entry.mono ? " mono" : ""}`}>
                  {entry.label}
                </span>
                {entry.detail && <span className="palette__detail">{entry.detail}</span>}
                {entry.count !== null && entry.count !== undefined && (
                  <span className="palette__count num">{entry.count.toLocaleString("en")}</span>
                )}
                <span className="palette__state">{entry.active ? "Applied" : ""}</span>
              </button>
            </li>
          ))}
          {results.length === 0 && <li className="palette__empty">Nothing matches that.</li>}
        </ul>

        <footer className="palette__footer">
          <span>
            <kbd>&uarr;</kbd>
            <kbd>&darr;</kbd> move
          </span>
          <span>
            <kbd>Enter</kbd> toggle
          </span>
          <span>
            <kbd>Esc</kbd> close
          </span>
        </footer>
      </div>
    </div>
  );
}
