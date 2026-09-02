import assert from "node:assert/strict";
import { test } from "node:test";

import { CollapseState } from "../src/collapse-state.js";

test("manual shop toggle is independent per shop", () => {
  const c = new CollapseState();
  c.toggleShop("Aldi", false); // now collapsed
  assert.equal(c.isShopCollapsed("Aldi", false), true);
  assert.equal(c.isShopCollapsed("Asda", false), false); // unaffected
});

test("manual category toggle only affects that category within its shop", () => {
  const c = new CollapseState();
  c.toggleCategory("Aldi", "Milk", false);
  assert.equal(c.isCategoryCollapsed("Aldi", "Milk", false), true);
  assert.equal(c.isCategoryCollapsed("Aldi", "Bakery", false), false);
  assert.equal(c.isCategoryCollapsed("Asda", "Milk", false), false); // same cat name, other shop
});

test("server auto-collapse hint applies when no manual override", () => {
  const c = new CollapseState();
  assert.equal(c.isShopCollapsed("Aldi", true), true); // auto hint
  // Manual expand overrides the auto hint.
  c.toggleShop("Aldi", true); // toggles from auto(true) -> false
  assert.equal(c.isShopCollapsed("Aldi", true), false);
});

test("manual state persists across renders (independent of hint changes)", () => {
  const c = new CollapseState();
  c.toggleShop("Aldi", false); // collapsed
  // Even if the server later says auto-collapse=false, the manual collapse stays.
  assert.equal(c.isShopCollapsed("Aldi", false), true);
});

test("focusShop collapses all other shops", () => {
  const c = new CollapseState();
  c.focusShop("Asda", ["Aldi", "Asda", "Tesco", "No Preference"]);
  assert.equal(c.isShopCollapsed("Asda", false), false);
  assert.equal(c.isShopCollapsed("Aldi", false), true);
  assert.equal(c.isShopCollapsed("Tesco", false), true);
  assert.equal(c.isShopCollapsed("No Preference", false), true);
});
