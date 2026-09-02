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
