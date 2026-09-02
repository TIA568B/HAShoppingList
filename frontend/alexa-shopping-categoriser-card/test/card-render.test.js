import assert from "node:assert/strict";
import { test } from "node:test";

import { installDom } from "./dom-stub.js";

installDom();
const { AlexaShoppingCategoriserCard } = await import("../src/card.js");

function makeHass(shopGroups, extra = {}) {
  return {
    states: {
      "sensor.test": {
        state: "1",
        attributes: {
          attributes_version: 3,
          source_entity_id: "todo.src",
          total_unchecked: 1,
          uncategorised_count: 0,
          options: { grace_period_seconds: 9, show_completed: false, collapse_empty_categories: true },
          category_definitions: [],
          shop_definitions: [],
          shop_groups: shopGroups,
          ...extra,
        },
      },
    },
    callService: async () => {},
  };
}

function mountCard(hass) {
  const card = new AlexaShoppingCategoriserCard();
  card.setConfig({ entity: "sensor.test" });
  card.hass = hass;
  return card;
}

test("empty category (0 unchecked) is not rendered", () => {
  const hass = makeHass([
    {
      name: "No Preference",
      collapsed: false,
      categories: [
        { name: "Fruit & Veg", collapsed: false, items: [{ uid: "u1", name: "carrots", checked: false, shop: "No Preference", category: "Fruit & Veg" }] },
        { name: "Bakery", collapsed: true, items: [] },
      ],
    },
  ]);
  const card = mountCard(hass);
  const catHeaders = card.shadowRoot.byClass("asc-cat-header").map((e) => e.text());
  assert.ok(catHeaders.some((t) => t.includes("Fruit & Veg")));
  assert.ok(!catHeaders.some((t) => t.includes("Bakery")), "empty Bakery must not render");
});

test("shop with only empty categories is not rendered", () => {
  const hass = makeHass([
    {
      name: "Aldi",
      collapsed: false,
      categories: [{ name: "Milk", collapsed: true, items: [] }],
    },
    {
      name: "No Preference",
      collapsed: false,
      categories: [
        { name: "Frozen", collapsed: false, items: [{ uid: "u2", name: "pizza", checked: false, shop: "No Preference", category: "Frozen" }] },
      ],
    },
  ]);
  const card = mountCard(hass);
  const shopHeaders = card.shadowRoot.byClass("asc-shop-header").map((e) => e.text());
  assert.ok(!shopHeaders.some((t) => t.includes("Aldi")), "empty Aldi shop must not render");
  assert.ok(shopHeaders.some((t) => t.includes("No Preference")));
});

test("item name is written as text, not HTML (XSS-safe)", () => {
  const hass = makeHass([
    {
      name: "No Preference",
      collapsed: false,
      categories: [
        { name: "Fruit & Veg", collapsed: false, items: [{ uid: "u1", name: "<img src=x onerror=alert(1)>", checked: false, shop: "No Preference", category: "Fruit & Veg" }] },
      ],
    },
  ]);
  const card = mountCard(hass);
  const names = card.shadowRoot.byClass("asc-name").map((e) => e.text());
  // The raw string is preserved verbatim as text content (never parsed as HTML).
  assert.ok(names.some((t) => t.includes("<img")));
});


// --- per-item pencil edit menu (0.5.0) -----------------------------------

function makeHassWithItem(calls, { fail = false } = {}) {
  return {
    states: {
      "sensor.test": {
        state: "1",
        attributes: {
          attributes_version: 3,
          source_entity_id: "todo.src",
          total_unchecked: 1,
          uncategorised_count: 0,
          options: {
            grace_period_seconds: 9,
            show_completed: false,
            collapse_empty_categories: true,
          },
          category_definitions: [
            { name: "Milk", keywords: ["milk"] },
            { name: "Sauces", keywords: ["sauce"] },
          ],
          shop_definitions: [
            { name: "Aldi", keywords: [] },
            { name: "Tesco", keywords: [] },
          ],
          shop_groups: [
            {
              name: "No Preference",
              collapsed: false,
              categories: [
                {
                  name: "Milk",
                  collapsed: false,
                  items: [
                    {
                      uid: "u1",
                      name: "oat milk",
                      checked: false,
                      shop: "No Preference",
                      category: "Milk",
                    },
                  ],
                },
              ],
            },
          ],
        },
      },
    },
    callService: async (domain, service, data) => {
      calls.push({ domain, service, data });
      if (fail) throw new Error("Unknown shop");
    },
  };
}

function openEditMenu(card) {
  const pencil = card.shadowRoot.byClass("asc-edit")[0];
  pencil.dispatch("click");
  return card.shadowRoot.byClass("asc-edit-menu")[0];
}

test("pencil opens an edit menu with shop + category option buttons and no text inputs", () => {
  const card = mountCard(makeHassWithItem([]));
  assert.equal(card.shadowRoot.byClass("asc-edit-menu").length, 0); // closed by default
  const menu = openEditMenu(card);
  assert.ok(menu, "edit menu opens on pencil click");
  // No text inputs anywhere in the menu (hotkey-safe).
  const inputs = menu.query((e) => e.tagName === "input");
  assert.equal(inputs.length, 0);
  // Shop options include the shops + No Preference; category options include cats + Uncategorised.
  const opts = menu.byClass("asc-edit-opt").map((b) => b.text());
  assert.ok(opts.includes("Aldi") && opts.includes("No Preference"));
  assert.ok(opts.includes("Milk") && opts.includes("Uncategorised"));
});

test("edit menu lists categories and shops alphabetically, sentinels pinned last", () => {
  // Deliberately unsorted definitions; the menu must render them alphabetically.
  const hass = makeHassWithItem([]);
  hass.states["sensor.test"].attributes.category_definitions = [
    { name: "Sauces", keywords: [] },
    { name: "Alcohol", keywords: [] },
    { name: "Milk", keywords: [] },
    { name: "Baking", keywords: [] },
  ];
  hass.states["sensor.test"].attributes.shop_definitions = [
    { name: "Tesco", keywords: [] },
    { name: "Aldi", keywords: [] },
    { name: "Morrisons", keywords: [] },
  ];
  const card = mountCard(hass);
  const menu = openEditMenu(card);
  const groups = menu.byClass("asc-edit-group");
  // Group 0 is Shop, group 1 is Category (render order in _renderEditMenu).
  const shopOpts = groups[0].byClass("asc-edit-opt").map((b) => b.text());
  const catOpts = groups[1].byClass("asc-edit-opt").map((b) => b.text());
  assert.deepEqual(shopOpts, ["Aldi", "Morrisons", "Tesco", "No Preference"]);
  assert.deepEqual(catOpts, ["Alcohol", "Baking", "Milk", "Sauces", "Uncategorised"]);
});

test("choosing a shop calls assign_shop with item_text + apply_to_uid", async () => {
  const calls = [];
  const card = mountCard(makeHassWithItem(calls));
  const menu = openEditMenu(card);
  const aldi = menu.byClass("asc-edit-opt").find((b) => b.text() === "Aldi");
  aldi.dispatch("click");
  await Promise.resolve();
  await Promise.resolve();
  assert.deepEqual(calls, [
    {
      domain: "alexa_shopping_categoriser",
      service: "assign_shop",
      data: { item_text: "oat milk", shop: "Aldi", apply_to_uid: "u1" },
    },
  ]);
});

test("choosing a category calls recategorise_item with item_text + apply_to_uid", async () => {
  const calls = [];
  const card = mountCard(makeHassWithItem(calls));
  const menu = openEditMenu(card);
  const sauces = menu.byClass("asc-edit-opt").find((b) => b.text() === "Sauces");
  sauces.dispatch("click");
  await Promise.resolve();
  await Promise.resolve();
  assert.deepEqual(calls, [
    {
      domain: "alexa_shopping_categoriser",
      service: "recategorise_item",
      data: { item_text: "oat milk", category: "Sauces", apply_to_uid: "u1" },
    },
  ]);
});

test("pencil toggles the menu closed on second click", () => {
  const card = mountCard(makeHassWithItem([]));
  openEditMenu(card);
  assert.equal(card.shadowRoot.byClass("asc-edit-menu").length, 1);
  card.shadowRoot.byClass("asc-edit")[0].dispatch("click");
  assert.equal(card.shadowRoot.byClass("asc-edit-menu").length, 0);
});

test("ticking an item is unaffected by the pencil affordance", () => {
  const calls = [];
  const card = mountCard(makeHassWithItem(calls));
  const box = card.shadowRoot.query((e) => e.tagName === "input" && e.type === "checkbox")[0];
  box.dispatch("change");
  // complete-on-tap sends update_item(completed) immediately.
  assert.ok(
    calls.some((c) => c.service === "update_item" && c.data.status === "completed"),
  );
});

// --- version footer (deploy verification) --------------------------------

test("version is derived from the module URL's ?v query, not hard-coded", async () => {
  const { versionFromUrl } = await import("../src/card.js");
  // Served form (frontend.py adds ?v=<manifest version>).
  assert.equal(versionFromUrl("http://ha.local/alexa_shopping_categoriser/card.js?v=0.6.0"), "0.6.0");
  assert.equal(versionFromUrl("http://ha.local/card.js?v=1.2.3&foo=bar"), "1.2.3");
  // Bare path (no cache-bust query) -> null, so the footer is omitted rather than lying.
  assert.equal(versionFromUrl("http://ha.local/card.js"), null);
  assert.equal(versionFromUrl("not a url"), null);
});

test("card shows a version footer when served with a version, omits it otherwise", async () => {
  const { CARD_VERSION } = await import("../src/card.js");
  const card = mountCard(makeHass([]));
  const footer = card.shadowRoot.byClass("asc-version")[0];
  if (CARD_VERSION) {
    assert.ok(footer, "version footer present when a version is known");
    assert.equal(footer.text(), `v${CARD_VERSION}`);
  } else {
    // In the test harness the module is loaded from a bare file:// URL (no ?v=),
    // so CARD_VERSION is null and the footer must be omitted.
    assert.equal(footer, undefined, "footer omitted when version is unknown");
  }
});
