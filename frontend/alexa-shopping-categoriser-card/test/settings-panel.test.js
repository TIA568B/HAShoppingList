import assert from "node:assert/strict";
import { test } from "node:test";

import { installDom } from "./dom-stub.js";

installDom();
const { renderSettings, parseKeywords } = await import("../src/settings-panel.js");

test("parseKeywords splits, trims, drops empties", () => {
  assert.deepEqual(parseKeywords("a, b ,, c"), ["a", "b", "c"]);
  assert.deepEqual(parseKeywords(""), []);
  assert.deepEqual(parseKeywords(null), []);
});

function baseOpts(overrides = {}) {
  return {
    categoryDefs: [{ name: "Milk", keywords: ["milk", "oat milk"] }],
    shopDefs: [{ name: "Aldi", keywords: ["nappies"] }],
    open: true,
    onToggle() {},
    category: { onAdd() {}, onSave() {}, onDelete() {} },
    shop: { onAdd() {}, onSave() {}, onDelete() {} },
    ...overrides,
  };
}

test("collapsed panel renders only the toggle", () => {
  const el = renderSettings(baseOpts({ open: false }));
  const toggles = el.byClass("asc-settings-toggle");
  assert.equal(toggles.length, 1);
  assert.equal(el.byClass("asc-settings-sub").length, 0);
});

test("open panel renders category and shop sub-panels with rows", () => {
  const el = renderSettings(baseOpts());
  assert.equal(el.byClass("asc-settings-sub").length, 2);
  // One existing row per def, plus an add form per sub-panel.
  assert.equal(el.byClass("asc-def-row").length, 2); // 1 category + 1 shop
  assert.equal(el.byClass("asc-def-add").length, 2);
});

test("add category dispatches add_category with parsed keywords", () => {
  const calls = [];
  const el = renderSettings(
    baseOpts({ category: { onAdd: (p) => calls.push(p), onSave() {}, onDelete() {} } }),
  );
  // First sub-panel is Categories; its add form is the first .asc-def-add.
  const addForm = el.byClass("asc-def-add")[0];
  const inputs = addForm.query((e) => e.tagName === "input");
  inputs[0].value = "Snacks";
  inputs[1].value = "crisps, nuts";
  addForm.byClass("asc-def-addbtn")[0].dispatch("click");
  assert.deepEqual(calls, [{ name: "Snacks", keywords: ["crisps", "nuts"] }]);
});

test("save category dispatches edit_category with rename + keywords", () => {
  const calls = [];
  const el = renderSettings(
    baseOpts({ category: { onAdd() {}, onSave: (p) => calls.push(p), onDelete() {} } }),
  );
  const row = el.byClass("asc-def-row")[0]; // Milk
  const inputs = row.query((e) => e.tagName === "input");
  inputs[0].value = "Dairy-free"; // rename
  inputs[1].value = "milk, oat milk, kefir";
  row.byClass("asc-def-save")[0].dispatch("click");
  assert.deepEqual(calls, [
    { originalName: "Milk", newName: "Dairy-free", keywords: ["milk", "oat milk", "kefir"] },
  ]);
});

test("delete shop dispatches delete_shop with the shop name", () => {
  const calls = [];
  const el = renderSettings(
    baseOpts({ shop: { onAdd() {}, onSave() {}, onDelete: (p) => calls.push(p) } }),
  );
  // Shops is the second sub-panel; its row is the second .asc-def-row.
  const row = el.byClass("asc-def-row")[1]; // Aldi
  row.byClass("asc-def-delete")[0].dispatch("click");
  assert.deepEqual(calls, [{ name: "Aldi" }]);
});

test("definition names are rendered as text, not HTML (XSS-safe)", () => {
  const el = renderSettings(
    baseOpts({ categoryDefs: [{ name: "<b>x</b>", keywords: [] }] }),
  );
  const row = el.byClass("asc-def-row")[0];
  const nameInput = row.query((e) => e.tagName === "input")[0];
  assert.equal(nameInput.value, "<b>x</b>"); // preserved verbatim as a value, never parsed
});

test("add with empty name does not dispatch", () => {
  const calls = [];
  const el = renderSettings(
    baseOpts({ category: { onAdd: (p) => calls.push(p), onSave() {}, onDelete() {} } }),
  );
  const addForm = el.byClass("asc-def-add")[0];
  addForm.byClass("asc-def-addbtn")[0].dispatch("click"); // name left blank
  assert.equal(calls.length, 0);
});
