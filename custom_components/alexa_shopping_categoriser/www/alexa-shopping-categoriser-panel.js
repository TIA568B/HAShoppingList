// Sidebar panel wrapper for the Alexa Shopping List Categoriser card.
//
// Home Assistant loads this module for the custom sidebar panel and instantiates the
// <alexa-shopping-categoriser-panel> element, assigning `hass`, `narrow`, `route`, and
// `panel`. This wrapper hosts the existing custom card (<alexa-shopping-categoriser-card>)
// so the full categorised view gets a dedicated left-nav entry without a Lovelace dashboard.
//
// It discovers the categorised sensor automatically (by its documented attribute contract)
// and forwards `hass` to the card. No private backend contract beyond the sensor attributes.
//
// The card element is registered by the sibling card module; import it so the panel works
// even when the card resource has not been loaded by a dashboard yet.
//
// Cache-busting: this panel module's own URL carries the integration version query
// (?v=x.y.z). We propagate that same query onto the card import so a card update is never
// masked by the browser caching a bare "./card.js" (the panel URL busts, but a query-less
// relative import would not). Uses a dynamic import so we can derive the URL at runtime
// from import.meta.url.
(() => {
  const cardUrl = new URL("./alexa-shopping-categoriser-card.js", import.meta.url);
  const version = new URL(import.meta.url).searchParams.get("v");
  if (version) cardUrl.searchParams.set("v", version);
  import(cardUrl.href).catch((err) => {
    // eslint-disable-next-line no-console
    console.error("alexa-shopping-categoriser-panel: failed to load card module", err);
  });
})();

const CARD_TAG = "alexa-shopping-categoriser-card";
const PANEL_TAG = "alexa-shopping-categoriser-panel";

function findCategorisedEntity(hass, configured) {
  // Prefer an explicitly configured entity from the panel config.
  if (configured && hass.states[configured]) {
    return configured;
  }
  // Otherwise discover the integration's sensor by its attribute contract: it exposes
  // `attributes_version` and `shop_groups`. Pick the first match deterministically.
  const matches = [];
  for (const [entityId, state] of Object.entries(hass.states)) {
    if (!entityId.startsWith("sensor.")) continue;
    const attrs = state.attributes || {};
    if ("attributes_version" in attrs && "shop_groups" in attrs) {
      matches.push(entityId);
    }
  }
  matches.sort();
  return matches[0] || null;
}

class AlexaShoppingCategoriserPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._panelConfig = null;
    this._card = null;
    this._entity = null;
    this._message = null;
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  set panel(panel) {
    // panel.config carries any `config:` block from the panel registration.
    this._panelConfig = (panel && panel.config) || {};
    this._update();
  }

  // narrow/route are assigned by HA; unused but accepted without error.
  set narrow(_narrow) {}
  set route(_route) {}

  connectedCallback() {
    this._update();
  }

  _ensureChrome() {
    if (this._built) return;
    const style = document.createElement("style");
    style.textContent = `
      :host {
        display: block;
        height: 100%;
        background: var(--primary-background-color, #111);
        box-sizing: border-box;
      }
      .wrap {
        max-width: 700px;
        margin: 0 auto;
        padding: 16px;
        box-sizing: border-box;
      }
      .empty {
        padding: 24px;
        color: var(--secondary-text-color, #9e9e9e);
        text-align: center;
        font-family: var(--paper-font-body1_-_font-family, sans-serif);
      }
    `;
    this._wrap = document.createElement("div");
    this._wrap.className = "wrap";
    this.shadowRoot.append(style, this._wrap);
    this._built = true;
  }

  _showMessage(text) {
    this._ensureChrome();
    if (this._card) {
      this._card.remove();
      this._card = null;
    }
    if (!this._msgEl) {
      this._msgEl = document.createElement("div");
      this._msgEl.className = "empty";
      this._wrap.append(this._msgEl);
    }
    this._msgEl.textContent = text;
  }

  _update() {
    if (!this._hass) return;
    this._ensureChrome();

    const configured = this._panelConfig && this._panelConfig.entity;
    const entity = findCategorisedEntity(this._hass, configured);

    if (!entity) {
      this._showMessage(
        "No categorised shopping list found yet. Make sure the Alexa Shopping List " +
          "Categoriser integration is configured."
      );
      return;
    }

    // (Re)build the card if the target entity changed.
    if (!this._card || this._entity !== entity) {
      if (this._msgEl) {
        this._msgEl.remove();
        this._msgEl = null;
      }
      if (this._card) {
        this._card.remove();
      }
      this._card = document.createElement(CARD_TAG);
      const cfg = { type: `custom:${CARD_TAG}`, entity };
      if (this._panelConfig && this._panelConfig.source_entity) {
        cfg.source_entity = this._panelConfig.source_entity;
      }
      if (this._panelConfig && this._panelConfig.no_preference_position) {
        cfg.no_preference_position = this._panelConfig.no_preference_position;
      }
      this._card.setConfig(cfg);
      this._entity = entity;
      this._wrap.append(this._card);
    }

    this._card.hass = this._hass;
  }
}

if (!customElements.get(PANEL_TAG)) {
  customElements.define(PANEL_TAG, AlexaShoppingCategoriserPanel);
}
