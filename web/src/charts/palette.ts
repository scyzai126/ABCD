/**
 * Series colour assignment.
 *
 * Colour follows the entity, never its rank: IGH is blue whether it is the
 * biggest bar or filtered down to nothing, so a reader who learned "IGH is blue"
 * is never misled by a filter repainting the survivors.
 *
 * Slots and their light/dark steps come from the validated categorical palette;
 * the CSS custom properties carry the mode swap.
 */

export const CHAIN_COLOR: Record<string, string> = {
  IGH: "var(--series-1)",
  IGK: "var(--series-2)",
  IGL: "var(--series-3)",
};

/**
 * Fill steps for large areas.
 *
 * A ribbon segment or a bar covers far more of the screen than a legend swatch,
 * and at full chroma it stops reading as a measurement and starts reading as a
 * block of paint. Same hue, same entity -- softened only where the area is big.
 */
export const CHAIN_FILL: Record<string, string> = {
  IGH: "var(--series-1-fill)",
  IGK: "var(--series-2-fill)",
  IGL: "var(--series-3-fill)",
};

export const CHAIN_ORDER = ["IGH", "IGK", "IGL"];

export const ISOTYPE_COLOR: Record<string, string> = {
  IgM: "var(--series-1)",
  IgD: "var(--series-2)",
  IgA: "var(--series-3)",
  IgG: "var(--series-4)",
  IgE: "var(--series-5)",
};

export const ISOTYPE_FILL: Record<string, string> = {
  IgM: "var(--series-1-fill)",
  IgD: "var(--series-2-fill)",
  IgA: "var(--series-3-fill)",
  IgG: "var(--series-4-fill)",
  IgE: "var(--series-5-fill)",
};

/** Nominal categories with no natural order get one colour for every bar --
 *  darkening by value would double-encode the bar length. */
export const SINGLE_SERIES = "var(--series-1)";
export const SINGLE_SERIES_FILL = "var(--series-1-fill)";

export function chainColor(chain: string): string {
  return CHAIN_COLOR[chain] ?? SINGLE_SERIES;
}

export function chainFill(chain: string): string {
  return CHAIN_FILL[chain] ?? SINGLE_SERIES_FILL;
}

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
const plain = new Intl.NumberFormat("en");

/** Stat-tile values auto-compact; table cells stay exact. */
export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return value >= 10_000 ? compact.format(value) : plain.format(value);
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return plain.format(value);
}

export function formatDecimal(value: number | null | undefined, places = 1): string {
  if (value === null || value === undefined) return "--";
  return value.toFixed(places);
}

/** CDR3 lengths are stored in nucleotides; three of them make one codon. */
export function toAminoAcids(nucleotides: number): number {
  return nucleotides / 3;
}
