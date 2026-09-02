// Settings panels for the card: live editors for categories and shops (Option A,
// docs/plans/feature-map-management/02). Pure DOM builder — no direct HA access; the card
// injects async action callbacks (which call the existing integration services) and an
// error/refresh path. All user text is written via setText (never innerHTML). Reordering is
// intentionally NOT offered in 0.4.0 (decision OQ-B, deferred).

import { setText, stopKeyboardPropagation } from "./escape.js";

// Parse a comma-separated keyword string into a clean list.
export function parseKeywords(text) {
  if (!text) return [];
  return text
    .split(",")
    .map((k) => k.trim())
    .filter((k) => k.length > 0);
}

function button(label, onClick, { className, ariaLabel } = {}) {
  const b = document.createElement("button");
  setText(b, label);
  if (className) b.className = className;
  if (ariaLabel) b.setAttribute("aria-label", ariaLabel);
  b.addEventListener("click", onClick);
  return b;
}

function labelledInput(labelText, value, placeholder) {
  const wrap = document.createElement("label");
  wrap.className = "asc-field";
  const span = document.createElement("span");
  setText(span, labelText);
  const input = document.createElement("input");
  input.type = "text";
  input.value = value == null ? "" : String(value);
  if (placeholder) input.placeholder = placeholder;
  input.setAttribute("aria-label", labelText);
  stopKeyboardPropagation(input);
  wrap.append(span, input);
  return { wrap, input };
}

// Build one editable row for a definition (category or shop): name + keywords + Save/Delete.
function definitionRow(def, { onSave, onDelete }) {
  const row = document.createElement("div");
  row.className = "asc-def-row";

  const name = labelledInput("Name", def.name, "name");
  const keywords = labelledInput("Keywords", (def.keywords || []).join(", "), "comma, separated");

  const save = button(
    "Save",
    () =>
      onSave({
        originalName: def.name,
        newName: name.input.value.trim(),
        keywords: parseKeywords(keywords.input.value),
      }),
    { className: "asc-def-save", ariaLabel: `Save ${def.name}` },
  );
  const del = button("Delete", () => onDelete({ name: def.name }), {
    className: "asc-def-delete",
    ariaLabel: `Delete ${def.name}`,
  });

  row.append(name.wrap, keywords.wrap, save, del);
  return row;
}

// Build the "add new" form for a definition list.
function addForm(kind, { onAdd }) {
  const form = document.createElement("div");
  form.className = "asc-def-add";
  const name = labelledInput(`New ${kind} name`, "", "name");
  const keywords = labelledInput("Keywords", "", "comma, separated");
  const add = button(
    "Add",
    () => {
      const newName = name.input.value.trim();
      if (!newName) return;
      onAdd({ name: newName, keywords: parseKeywords(keywords.input.value) });
      name.input.value = "";
      keywords.input.value = "";
    },
    { className: "asc-def-addbtn", ariaLabel: `Add ${kind}` },
  );
  form.append(name.wrap, keywords.wrap, add);
  return form;
}

function subPanel(titleText, defs, handlers, kind) {
  const section = document.createElement("section");
  section.className = "asc-settings-sub";
  const heading = document.createElement("h4");
  setText(heading, titleText);
  section.appendChild(heading);

  for (const def of defs || []) {
    section.appendChild(
      definitionRow(def, { onSave: handlers.onSave, onDelete: handlers.onDelete }),
    );
  }
  section.appendChild(addForm(kind, { onAdd: handlers.onAdd }));
  return section;
}

/**
 * Render the collapsible settings panel.
 * @param {object} opts
 * @param {Array} opts.categoryDefs  from sensor `category_definitions`
 * @param {Array} opts.shopDefs       from sensor `shop_definitions`
 * @param {boolean} opts.open         card-local open/closed state
 * @param {()=>void} opts.onToggle    toggle open/closed
 * @param {object} opts.category      { onAdd, onSave, onDelete }
 * @param {object} opts.shop          { onAdd, onSave, onDelete }
 * @param {()=>void} [opts.onReloadDefaults]  optional reload-defaults action (M5)
 */
export function renderSettings(opts) {
  const root = document.createElement("section");
  root.className = "asc-settings";

  const toggle = button(opts.open ? "Settings ▾" : "Settings ▸", opts.onToggle, {
    className: "asc-settings-toggle",
    ariaLabel: "Toggle settings",
  });
  toggle.setAttribute("aria-expanded", String(!!opts.open));
  root.appendChild(toggle);

  if (!opts.open) return root;

  root.appendChild(subPanel("Categories", opts.categoryDefs, opts.category, "category"));
  root.appendChild(subPanel("Shops", opts.shopDefs, opts.shop, "shop"));

  if (opts.onReloadDefaults) {
    root.appendChild(opts.onReloadDefaults());
  }
  return root;
}
