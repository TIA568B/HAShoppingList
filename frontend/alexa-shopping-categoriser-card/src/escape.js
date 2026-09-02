// Safe text helpers. The card NEVER injects raw user text as HTML; it uses
// textContent for DOM writes. escapeHtml is provided only for the rare case of building
// a string that will be assigned to a trusted template, and is defensive by default.

export function escapeHtml(value) {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Set text content safely on an element (preferred over innerHTML for user text).
export function setText(el, value) {
  el.textContent = value == null ? "" : String(value);
}
