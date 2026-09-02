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

// --- settings panel (M4) -------------------------------------------------

function makeHassWithDefs(calls, { fail = false } = {}) {
  return {
    states: {
      "sensor.test": {
        state: "1",
        attributes: {
          attributes_version: 3,
          source_entity_id: "todo.src",
          total_unchecked: 0,
          uncategorised_count: 0,
          options: { grace_period_seconds: 9, show_completed: false, collapse_empty_categories: true },
          category_definitions: [{ name: "Milk", keywords: ["milk"] }],
          shop_definitions: [{ name: "Aldi", keywords: ["nappies"] }],
          shop_groups: [],
        },
      },
    },
    callService: async (domain, service, data) => {
      calls.push({ domain, service, data });
      if (fail) {
        const err = new Error("Category 'Milk' already exists");
        throw err;
      }
    },
  };
}

test("settings panel is present and toggles open", () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls));
  const toggle = card.shadowRoot.byClass("asc-settings-toggle")[0];
  assert.ok(toggle, "settings toggle present");
  assert.equal(card.shadowRoot.byClass("asc-settings-sub").length, 0); // closed by default
  toggle.dispatch("click");
  assert.equal(card.shadowRoot.byClass("asc-settings-sub").length, 2); // open: categories + shops
});

test("adding a category calls add_category on the integration domain", async () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls));
  card.shadowRoot.byClass("asc-settings-toggle")[0].dispatch("click");
  const addForm = card.shadowRoot.byClass("asc-def-add")[0]; // Categories add form
  const inputs = addForm.query((e) => e.tagName === "input");
  inputs[0].value = "Snacks";
  inputs[1].value = "crisps";
  addForm.byClass("asc-def-addbtn")[0].dispatch("click");
  await Promise.resolve();
  await Promise.resolve();
  assert.deepEqual(calls, [
    {
      domain: "alexa_shopping_categoriser",
      service: "add_category",
      data: { name: "Snacks", keywords: ["crisps"] },
    },
  ]);
});

test("deleting a shop calls delete_shop", async () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls));
  card.shadowRoot.byClass("asc-settings-toggle")[0].dispatch("click");
  const shopRow = card.shadowRoot.byClass("asc-def-row")[1]; // Aldi
  shopRow.byClass("asc-def-delete")[0].dispatch("click");
  await Promise.resolve();
  await Promise.resolve();
  assert.deepEqual(calls, [
    { domain: "alexa_shopping_categoriser", service: "delete_shop", data: { name: "Aldi" } },
  ]);
});

test("a failing service surfaces a dismissible error naming the action", async () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls, { fail: true }));
  card.shadowRoot.byClass("asc-settings-toggle")[0].dispatch("click");
  const addForm = card.shadowRoot.byClass("asc-def-add")[0];
  addForm.query((e) => e.tagName === "input")[0].value = "Milk";
  addForm.byClass("asc-def-addbtn")[0].dispatch("click");
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
  const errors = card.shadowRoot.byClass("asc-error").map((e) => e.text());
  assert.ok(errors.some((t) => t.includes("add category") && t.includes("already exists")));
});

// --- reload defaults (M5) ------------------------------------------------

test("reload defaults is a two-step confirm: button then confirm calls reload_defaults", async () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls));
  card.shadowRoot.byClass("asc-settings-toggle")[0].dispatch("click");

  // Step 1: the plain button is shown, no confirm yet, no service call.
  assert.equal(card.shadowRoot.byClass("asc-reload-btn").length, 1);
  assert.equal(card.shadowRoot.byClass("asc-reload-confirm").length, 0);
  card.shadowRoot.byClass("asc-reload-btn")[0].dispatch("click");

  // Step 2: confirm/cancel shown; still no service call.
  assert.equal(calls.length, 0);
  assert.equal(card.shadowRoot.byClass("asc-reload-confirm").length, 1);
  card.shadowRoot.byClass("asc-reload-confirm")[0].dispatch("click");
  await Promise.resolve();
  await Promise.resolve();

  assert.deepEqual(calls, [
    { domain: "alexa_shopping_categoriser", service: "reload_defaults", data: {} },
  ]);
});

test("cancelling the reload confirm does not call the service", () => {
  const calls = [];
  const card = mountCard(makeHassWithDefs(calls));
  card.shadowRoot.byClass("asc-settings-toggle")[0].dispatch("click");
  card.shadowRoot.byClass("asc-reload-btn")[0].dispatch("click");
  card.shadowRoot.byClass("asc-reload-cancel")[0].dispatch("click");
  assert.equal(calls.length, 0);
  // Back to the plain button (confirm dismissed).
  assert.equal(card.shadowRoot.byClass("asc-reload-btn").length, 1);
  assert.equal(card.shadowRoot.byClass("asc-reload-confirm").length, 0);
});
