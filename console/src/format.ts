const integer = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });

const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];

/** A whole number with thousands separators: 3,077. */
export function formatInteger(value: number): string {
  return integer.format(value);
}

/** Zero to ten as a word ("five"), larger numbers as digits. */
export function countWord(value: number): string {
  return (Number.isInteger(value) ? WORDS[value] : undefined) ?? formatInteger(value);
}

/** A rate (0 to 1) as a percentage with `digits` decimals; an undefined rate is "n/a". */
export function formatPercent(rate: number | null, digits = 1): string {
  if (rate === null) return "n/a";
  return `${(rate * 100).toFixed(digits)}%`;
}

const usd = new Intl.NumberFormat("en-GB", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

/** US dollars to four decimals ("USD 0.1270"); unknown is "n/a". */
export function formatUsd(value: number | null): string {
  return value === null ? "n/a" : `USD ${usd.format(value)}`;
}

/** A duration in milliseconds as seconds or minutes and seconds ("4 min 01 s"). */
export function formatDuration(ms: number | null): string {
  if (ms === null) return "n/a";
  if (ms < 1000) return `${ms} ms`;
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s} s`;
  return `${Math.floor(s / 60)} min ${String(s % 60).padStart(2, "0")} s`;
}

/** A value with its unit: "1,108.0 m", "2013-03-23". */
export function formatValue(value: string | number | null, unit: string | null = null): string {
  if (value === null) return "n/a";
  const text =
    typeof value === "number" ? value.toLocaleString("en-GB", { maximumFractionDigits: 6 }) : value;
  return unit ? `${text} ${unit}` : text;
}
