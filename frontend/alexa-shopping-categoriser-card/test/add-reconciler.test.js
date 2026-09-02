import assert from "node:assert/strict";
import { test } from "node:test";

import { AddReconciler } from "../src/add-reconciler.js";
import { normalize } from "../src/normalize.js";

test("adopts inbound item by normalized summary", () => {
  const r = new AddReconciler();
  const token = r.register("2x Oat Milk");
  assert.equal(r.pendingCount, 1);
  const adopted = r.reconcile([{ uid: "amzn1.x", name: "oat milk", checked: false }]);
  assert.deepEqual(adopted, [{ token, uid: "amzn1.x" }]);
  assert.equal(r.pendingCount, 0);
});

test("ignores completed inbound items when matching", () => {
  const r = new AddReconciler();
  r.register("bread");
  const adopted = r.reconcile([{ uid: "u1", name: "bread", checked: true }]);
  assert.equal(adopted.length, 0);
  assert.equal(r.pendingCount, 1); // still pending
});

test("drops stale placeholders past the window", () => {
  let now = 1000;
  const r = new AddReconciler({ windowMs: 100, now: () => now });
  r.register("ghost item");
  now = 2000; // well past window
  const adopted = r.reconcile([]);
  assert.equal(adopted.length, 0);
  assert.equal(r.pendingCount, 0); // dropped
});

test("two placeholders of same text adopt distinct uids", () => {
  const r = new AddReconciler();
  const t1 = r.register("milk");
  const t2 = r.register("milk");
  const adopted = r.reconcile([
    { uid: "a", name: "milk", checked: false },
    { uid: "b", name: "milk", checked: false },
  ]);
  const tokens = adopted.map((a) => a.token).sort();
  assert.deepEqual(tokens, [t1, t2].sort());
  assert.equal(new Set(adopted.map((a) => a.uid)).size, 2);
});

test("normalize matches backend-style quantity stripping", () => {
  assert.equal(normalize("2x Oat Milk"), "oat milk");
  assert.equal(normalize("500g Pasta"), "pasta");
});
