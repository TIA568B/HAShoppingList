// Alexa Shopping List Categoriser — custom Lovelace card.
// Renders the shop-primary, category-secondary projection from the categorised sensor and
// drives tick/undo/add/shop interactions. All user text is written via textContent (never
// innerHTML), and only documented HA services/websocket APIs are used.

import { AddReconciler } from "./add-reconciler.js";
import { CollapseState } from "./collapse-state.js";
import { setText, stopKeyboardPropagation } from "./escape.js";
import { ItemState, TickController } from "./tick-controller.js";

const SUPPORTED_ATTRIBUTES_VERSION = 3;
const INTEGRATION_DOMAIN = "alexa_shopping_categoriser";

// Card build version, shown in a small footer so a deployed/cached-stale card is obvious
// at a glance (deploy verification). It is NOT hard-coded: the integration serves this
// module cache-busted with `?v=<manifest version>` (see frontend.py), so we read that same
// query off our own module URL. This guarantees the footer always reflects the version HA
// actually served. If the module was somehow loaded without the query (e.g. hand-added to a
// dashboard with a bare path), CARD_VERSION is null and the footer is omitted rather than
// showing a misleading fixed number.
export function versionFromUrl(moduleUrl) {
  try {
    return new URL(moduleUrl).searchParams.get("v");
  } catch (_err) {
    return null;
  }
}

export const CARD_VERSION = versionFromUrl(import.meta.url);

export class AlexaShoppingCategoriserCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._collapse = new CollapseState();
    this._adds = new AddReconciler();
    this._errors = [];
    this._reviewBannerDismissed = false;
    this._editingUid = null; // uid whose per-item edit menu is open (card-local)
    this._tick = new TickController({
      updateItem: (uid, status) => this._updateItem(uid, status),
      onError: (e) => this._pushError(e),
      onChange: () => this._render(),
    });
    this._built = false;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("alexa-shopping-categoriser-card: 'entity' is required");
    }
    this._config = {
      entity: config.entity,
      source_entity: config.source_entity || null,
      no_preference_position: config.no_preference_position === "first" ? "first" : "last",
    };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass && hass.states[this._config.entity];
    if (state) {
      const uids = new Set();
      const checkedByUid = new Map();
      const inbound = [];
      for (const shop of state.attributes.shop_groups || []) {
        for (const cat of shop.categories || []) {
          for (const item of cat.items || []) {
            uids.add(item.uid);
            checkedByUid.set(item.uid, !!item.checked);
            inbound.push(item);
          }
        }
      }
      this._tick.reconcile(uids, checkedByUid);
      const adopted = this._adds.reconcile(inbound);
      // Adopted placeholders now correspond to real uids; nothing else to do — the next
      // render uses the inbound projection directly.
      void adopted;
    }
    this._render();
  }

  getCardSize() {
    return 6;
  }

  // --- HA I/O (sanctioned calls only) -----------------------------------

  _sourceEntity(state) {
    return (
      this._config.source_entity ||
      (state && state.attributes && state.attributes.source_entity_id) ||
      null
    );
  }

  async _updateItem(uid, status) {
    const state = this._hass.states[this._config.entity];
    const source = this._sourceEntity(state);
    await this._hass.callService("todo", "update_item", {
      item: uid,
      status,
      entity_id: source,
    });
  }

  async _addItem(text) {
    const state = this._hass.states[this._config.entity];
    const source = this._sourceEntity(state);
    const token = this._adds.register(text);
    try {
      await this._hass.callService("todo", "add_item", { item: text, entity_id: source });
    } catch (err) {
      this._pushError({ name: text, action: "add", error: String(err) });
    }
    return token;
  }

  async _assignShop(itemText, shop) {
    await this._hass.callService(INTEGRATION_DOMAIN, "assign_shop", {
      item_text: itemText,
      shop,
    });
  }

  async _recategorise(itemText, category) {
    await this._hass.callService(INTEGRATION_DOMAIN, "recategorise_item", {
      item_text: itemText,
      category,
    });
  }

  // Generic integration-service caller used by the settings panels. Surfaces a
  // dismissible error (naming the action) on failure and never throws to the caller.
  async _callIntegration(service, data, actionLabel) {
    try {
      await this._hass.callService(INTEGRATION_DOMAIN, service, data);
      return true;
    } catch (err) {
      this._pushRawError(`Couldn't ${actionLabel}: ${this._serviceErrorMessage(err)}`);
      return false;
    }
  }

  _serviceErrorMessage(err) {
    // HA wraps ServiceValidationError; surface its message if present, else a generic hint.
    const msg = err && (err.message || err.error || (err.body && err.body.message));
    return typeof msg === "string" && msg.trim() ? msg : "please check the value and try again";
  }

  _pushError(e) {
    const label =
      e.action === "complete" ? "complete" : e.action === "undo" ? "undo" : e.action;
    this._pushRawError(`Failed to ${label} "${e.name}". Please try again.`);
  }

  _pushRawError(message) {
    this._errors.push(message);
    this._render();
  }

  // --- rendering (safe DOM; no innerHTML with user text) ----------------

  _render() {
    if (!this._config) return;
    const root = this.shadowRoot;
    if (!this._built) {
      root.innerHTML = "";
      const style = document.createElement("style");
      style.textContent = CARD_CSS;
      root.appendChild(style);
      this._container = document.createElement("ha-card");
      root.appendChild(this._container);
      this._built = true;
    }
    const container = this._container;
    // Clear children (rebuild body). Style node persists on the shadow root.
    container.replaceChildren();

    const state = this._hass && this._hass.states[this._config.entity];
    if (!state) {
      container.appendChild(this._msg("Sensor not found. Check the card 'entity'."));
      return;
    }
    if (state.state === "unavailable" || state.state === "unknown") {
      container.appendChild(this._msg("Shopping list is currently unavailable."));
      return;
    }

    const attrs = state.attributes || {};
    this._attrs = attrs; // cached for per-item edit menu (shop/category options)
    const version = attrs.attributes_version;
    if (typeof version === "number" && version > SUPPORTED_ATTRIBUTES_VERSION) {
      container.appendChild(
        this._msg("This card is out of date for the shopping list data. Please update the card."),
      );
      // Continue rendering what we understand rather than crashing.
    }

    this._renderErrors(container);
    this._renderReviewBanner(container, attrs);
    this._renderAddRow(container);

    const grace = (attrs.options && attrs.options.grace_period_seconds) || 9;
    let groups = [...(attrs.shop_groups || [])];
    if (this._config.no_preference_position === "first") {
      groups = groups.sort((a, b) =>
        a.name === "No Preference" ? -1 : b.name === "No Preference" ? 1 : 0,
      );
    }
    const allShopNames = groups.map((g) => g.name);

    let renderedShops = 0;
    for (const shop of groups) {
      const el = this._renderShop(shop, grace, allShopNames);
      if (el !== null) {
        container.appendChild(el);
        renderedShops += 1;
      }
    }

    if (renderedShops === 0) {
      container.appendChild(this._msg("Your shopping list is empty."));
    }

    if (CARD_VERSION) {
      const footer = document.createElement("div");
      footer.className = "asc-version";
      setText(footer, `v${CARD_VERSION}`);
      container.appendChild(footer);
    }
  }

  _msg(text) {
    const div = document.createElement("div");
    div.className = "asc-msg";
    setText(div, text);
    return div;
  }

  _renderErrors(container) {
    for (const err of this._errors) {
      const bar = document.createElement("div");
      bar.className = "asc-error";
      bar.setAttribute("role", "alert");
      const span = document.createElement("span");
      setText(span, err);
      const btn = document.createElement("button");
      setText(btn, "Dismiss");
      btn.setAttribute("aria-label", "Dismiss error");
      btn.addEventListener("click", () => {
        this._errors = this._errors.filter((e) => e !== err);
        this._render();
      });
      bar.append(span, btn);
      container.appendChild(bar);
    }
  }

  _renderReviewBanner(container, attrs) {
    if (this._reviewBannerDismissed) return;
    // First-setup intent (Req 1.7): show once when there is an uncategorised backlog.
    if (!attrs.uncategorised_count) return;
    const bar = document.createElement("div");
    bar.className = "asc-review";
    const span = document.createElement("span");
    setText(
      span,
      `You have ${attrs.uncategorised_count} uncategorised item(s). Review your categories to tidy them.`,
    );
    const btn = document.createElement("button");
    setText(btn, "Dismiss");
    btn.addEventListener("click", () => {
      this._reviewBannerDismissed = true;
      this._render();
    });
    bar.append(span, btn);
    container.appendChild(bar);
  }

  _renderAddRow(container) {
    const row = document.createElement("div");
    row.className = "asc-add";
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Add an item…";
    input.setAttribute("aria-label", "Add an item");
    stopKeyboardPropagation(input);
    const add = document.createElement("button");
    setText(add, "Add");
    const submit = () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      this._addItem(text);
    };
    add.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") submit();
    });
    row.append(input, add);
    container.appendChild(row);
  }

  _renderShop(shop, grace, allShopNames) {
    const section = document.createElement("section");
    section.className = "asc-shop";

    const shopUnchecked = (shop.categories || []).reduce(
      (n, c) => n + (c.items || []).filter((i) => !i.checked).length,
      0,
    );
    const collapsed = this._collapse.isShopCollapsed(shop.name, !!shop.collapsed);

    const header = document.createElement("button");
    header.className = "asc-shop-header";
    header.setAttribute("aria-expanded", String(!collapsed));
    setText(header, `${shop.name} (${shopUnchecked})`);
    header.addEventListener("click", () => {
      this._collapse.toggleShop(shop.name, !!shop.collapsed);
      this._render();
    });
    section.appendChild(header);

    const focus = document.createElement("button");
    focus.className = "asc-focus";
    setText(focus, "Focus");
    focus.setAttribute("aria-label", `Focus ${shop.name}`);
    focus.addEventListener("click", () => {
      this._collapse.focusShop(shop.name, allShopNames);
      this._render();
    });
    header.appendChild(focus);

    if (collapsed) return section;

    let renderedCategories = 0;
    for (const cat of shop.categories || []) {
      const el = this._renderCategory(shop, cat, grace);
      if (el !== null) {
        section.appendChild(el);
        renderedCategories += 1;
      }
    }
    // A shop with no non-empty categories is not displayed at all.
    if (renderedCategories === 0) return null;
    return section;
  }

  _renderCategory(shop, cat, grace) {
    const items = cat.items || [];
    const unchecked = items.filter((i) => !i.checked).length;
    // Empty categories (zero unchecked items) are not displayed at all — no header,
    // no placeholder. This matches the header count shown to the user.
    if (unchecked === 0) return null;

    const wrap = document.createElement("div");
    wrap.className = "asc-cat";
    const collapsed = this._collapse.isCategoryCollapsed(shop.name, cat.name, !!cat.collapsed);

    const header = document.createElement("button");
    header.className = "asc-cat-header";
    header.setAttribute("aria-expanded", String(!collapsed));
    setText(header, `${cat.name} (${unchecked})`);
    header.addEventListener("click", () => {
      this._collapse.toggleCategory(shop.name, cat.name, !!cat.collapsed);
      this._render();
    });
    wrap.appendChild(header);

    if (collapsed) return wrap;

    const list = document.createElement("ul");
    list.className = "asc-items";
    for (const item of items) {
      list.appendChild(this._renderItem(item, grace));
    }
    wrap.appendChild(list);
    return wrap;
  }

  _renderItem(item, grace) {
    const li = document.createElement("li");
    li.className = "asc-item";

    const checked = item.checked || this._tick.isUndoable(item.uid);
    const box = document.createElement("input");
    box.type = "checkbox";
    box.checked = checked;
    box.setAttribute("aria-label", item.name);
    box.addEventListener("change", () => {
      if (this._tick.isUndoable(item.uid) || item.checked) {
        this._tick.undo(item.uid, item.name);
      } else {
        this._tick.tap(item.uid, item.name, grace);
      }
    });

    const label = document.createElement("span");
    label.className = checked ? "asc-name checked" : "asc-name";
    setText(label, item.name);

    li.append(box, label);

    if (this._tick.isUndoable(item.uid)) {
      const undo = document.createElement("button");
      undo.className = "asc-undo";
      setText(undo, "Undo");
      undo.setAttribute("aria-label", `Undo ${item.name}`);
      undo.addEventListener("click", () => this._tick.undo(item.uid, item.name));
      li.appendChild(undo);
    }

    // Pencil: opens a card-local edit menu (set shop / set category). Buttons only — no
    // text inputs — so there is nothing that can leak keystrokes to HA hotkeys.
    const pencil = document.createElement("button");
    pencil.className = "asc-edit";
    setText(pencil, "\u270e"); // pencil glyph
    pencil.setAttribute("aria-label", `Edit ${item.name}`);
    pencil.setAttribute("title", "Set shop / category");
    pencil.addEventListener("click", () => {
      this._editingUid = this._editingUid === item.uid ? null : item.uid;
      this._render();
    });
    li.appendChild(pencil);

    if (this._editingUid === item.uid) {
      li.appendChild(this._renderEditMenu(item));
    }

    return li;
  }

  _renderEditMenu(item) {
    const attrs = this._attrs || {};
    const menu = document.createElement("div");
    menu.className = "asc-edit-menu";
    menu.setAttribute("role", "menu");

    // Options are sorted alphabetically (case-insensitive) so they are easy to scan; the
    // "No Preference" / "Uncategorised" defaults are pinned last, not sorted in.
    const byName = (a, b) => a.localeCompare(b, undefined, { sensitivity: "base" });
    const shopNames = [
      ...(attrs.shop_definitions || []).map((s) => s.name).sort(byName),
      "No Preference",
    ];
    const catNames = [
      ...(attrs.category_definitions || []).map((c) => c.name).sort(byName),
      "Uncategorised",
    ];

    menu.appendChild(
      this._optionGroup("Shop", shopNames, item.shop, (shop) =>
        this._setItemShop(item, shop),
      ),
    );
    menu.appendChild(
      this._optionGroup("Category", catNames, item.category, (category) =>
        this._setItemCategory(item, category),
      ),
    );
    return menu;
  }

  _optionGroup(title, names, current, onChoose) {
    const group = document.createElement("div");
    group.className = "asc-edit-group";
    const heading = document.createElement("div");
    heading.className = "asc-edit-heading";
    setText(heading, title);
    group.appendChild(heading);
    for (const name of names) {
      const btn = document.createElement("button");
      btn.className = name === current ? "asc-edit-opt current" : "asc-edit-opt";
      setText(btn, name);
      btn.setAttribute("role", "menuitemradio");
      btn.setAttribute("aria-checked", String(name === current));
      btn.addEventListener("click", () => onChoose(name));
      group.appendChild(btn);
    }
    return group;
  }

  async _setItemShop(item, shop) {
    this._editingUid = null;
    const ok = await this._callIntegration(
      "assign_shop",
      { item_text: item.name, shop, apply_to_uid: item.uid },
      `set shop for "${item.name}"`,
    );
    if (ok) this._render();
  }

  async _setItemCategory(item, category) {
    this._editingUid = null;
    const ok = await this._callIntegration(
      "recategorise_item",
      { item_text: item.name, category, apply_to_uid: item.uid },
      `set category for "${item.name}"`,
    );
    if (ok) this._render();
  }

  disconnectedCallback() {
    this._tick.dispose();
  }
}

const CARD_CSS = `
  ha-card { padding: 12px; display: block; }
  .asc-msg { padding: 12px; color: var(--secondary-text-color); }
  .asc-error { background: var(--error-color, #db4437); color: white; padding: 8px;
    border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; gap: 8px; }
  .asc-review { background: var(--primary-color, #03a9f4); color: white; padding: 8px;
    border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; gap: 8px; }
  .asc-add { display: flex; gap: 8px; margin-bottom: 12px; }
  .asc-add input { flex: 1; padding: 6px; }
  .asc-shop { margin-bottom: 10px; }
  .asc-shop-header { width: 100%; text-align: left; font-weight: 600; font-size: 1.05em;
    background: none; border: none; cursor: pointer; padding: 6px 0; color: var(--primary-text-color);
    display: flex; justify-content: space-between; align-items: center; }
  .asc-focus { font-size: 0.75em; font-weight: normal; }
  .asc-cat { margin-left: 10px; }
  .asc-cat-header { width: 100%; text-align: left; background: none; border: none; cursor: pointer;
    padding: 4px 0; color: var(--secondary-text-color); }
  .asc-items { list-style: none; margin: 0; padding: 0 0 0 10px; }
  .asc-item { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 3px 0; }
  .asc-name.checked { text-decoration: line-through; opacity: 0.6; }
  .asc-undo { margin-left: auto; }
  .asc-edit { margin-left: auto; background: none; border: none; cursor: pointer;
    font-size: 1.1em; line-height: 1; padding: 4px; color: var(--secondary-text-color); }
  .asc-undo + .asc-edit { margin-left: 0; }
  .asc-edit-menu { flex-basis: 100%; display: flex; flex-wrap: wrap; gap: 16px;
    padding: 8px 4px; margin: 4px 0; background: var(--secondary-background-color, #1c1c1c);
    border-radius: 6px; }
  .asc-edit-group { display: flex; flex-direction: column; gap: 2px; min-width: 120px; }
  .asc-edit-heading { font-size: 0.75em; text-transform: uppercase; opacity: 0.7; }
  .asc-edit-opt { text-align: left; background: none; border: none; cursor: pointer;
    padding: 6px 8px; border-radius: 4px; color: var(--primary-text-color); }
  .asc-edit-opt:hover { background: var(--primary-color, #03a9f4); color: white; }
  .asc-edit-opt.current { font-weight: 700; }
  .asc-version { margin-top: 10px; text-align: right; font-size: 0.7em; opacity: 0.5; }
  button:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: 2px; }
`;

// Expose the state enum for tests / debugging without importing internals.
AlexaShoppingCategoriserCard.ItemState = ItemState;
