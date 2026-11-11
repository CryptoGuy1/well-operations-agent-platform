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
