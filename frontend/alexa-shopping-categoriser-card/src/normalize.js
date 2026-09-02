// Text normalisation mirroring the backend categoriser (docs/plans/07).
// Used only for add-reconciliation (matching an optimistic placeholder to the inbound
// item by normalized summary). Kept deliberately simple and dependency-free.

const QTY_RE = /^\s*(?:a\s+)?\d+\s*(?:[a-z]+)?\b/i;
const STRIP_PUNCT_RE = /[^\w\s'-]/gu;
const WHITESPACE_RE = /\s+/g;

const UNIT_WORDS = new Set([
  "x", "g", "kg", "mg", "ml", "l", "litre", "litres", "liter", "liters",
  "pack", "packs", "dozen", "bunch", "tin", "tins", "can", "cans",
  "bottle", "bottles", "box", "boxes", "bag", "bags",
]);

function stripLeadingUnitWord(text) {
  // Handle a leading "a <unit>" like "a dozen eggs" -> "eggs".
  const parts = text.split(/\s+/);
  if (parts.length > 1 && parts[0] === "a" && UNIT_WORDS.has(parts[1])) {
    return parts.slice(2).join(" ").trim();
  }
  return text;
}

function stripLeadingQuantity(text) {
  const match = text.match(QTY_RE);
  if (!match) {
    return stripLeadingUnitWord(text);
  }
  const remainder = text.slice(match[0].length).trim();
  if (!remainder) return text;
  const parts = remainder.split(/\s+/);
  if (parts.length > 1 && UNIT_WORDS.has(parts[0])) {
    return parts.slice(1).join(" ").trim();
  }
  return remainder;
}

export function normalize(text) {
  if (text == null) return "";
  const lowered = String(text).trim().toLowerCase();
  const stripped = stripLeadingQuantity(lowered);
  const cleaned = stripped.replace(STRIP_PUNCT_RE, " ");
  return cleaned.replace(WHITESPACE_RE, " ").trim();
}
