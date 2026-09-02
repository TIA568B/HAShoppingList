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

// Prevent keystrokes typed into a form field from bubbling out of the card and triggering
// Home Assistant's global keyboard shortcuts (e.g. "c" quick-bar, "e", "a"). HA listens for
// these on document; without this, typing a category/shop name fires shortcuts and the
// field is unusable. We stop propagation but do NOT preventDefault, so normal typing works.
export function stopKeyboardPropagation(el) {
  for (const type of ["keydown", "keyup", "keypress"]) {
    el.addEventListener(type, (e) => e.stopPropagation());
  }
}
