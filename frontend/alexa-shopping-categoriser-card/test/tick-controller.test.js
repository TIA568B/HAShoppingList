import assert from "node:assert/strict";
import { test } from "node:test";

import { ItemState, TickController } from "../src/tick-controller.js";

// A controllable timer/sleep harness so tests are deterministic.
function harness(opts = {}) {
  const timers = [];
  const calls = [];
  const errors = [];
  let changes = 0;
  const controller = new TickController({
    updateItem: async (uid, status) => {
      calls.push({ uid, status });
      if (opts.failUpdate) throw new Error("boom");
    },
    onError: (e) => errors.push(e),
    onChange: () => {
      changes += 1;
    },
    setTimer: (fn) => {
      const handle = { fn, cancelled: false };
      timers.push(handle);
      return handle;
    },
    clearTimer: (h) => {
      if (h) h.cancelled = true;
    },
    sleep: async () => {},
    retries: opts.retries ?? 3,
  });
  return {
    controller,
    calls,
    errors,
    fireTimers: () => timers.filter((t) => !t.cancelled).forEach((t) => t.fn()),
    get changes() {
      return changes;
    },
  };
}

test("tap sends completion immediately and enters undo window", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  assert.deepEqual(h.calls, [{ uid: "u1", status: "completed" }]);
  assert.equal(h.controller.getState("u1"), ItemState.UNDO_WINDOW);
  assert.equal(h.controller.isUndoable("u1"), true);
});

test("undo within window sends reversing needs_action and clears", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  await h.controller.undo("u1", "oat milk");
  assert.deepEqual(h.calls, [
    { uid: "u1", status: "completed" },
    { uid: "u1", status: "needs_action" },
  ]);
  assert.equal(h.controller.getState("u1"), null);
});

test("window expiry drops the affordance with no extra call", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  h.fireTimers();
  assert.equal(h.controller.getState("u1"), ItemState.COMPLETED);
  assert.equal(h.controller.isUndoable("u1"), true); // still undoable after expiry
  assert.equal(h.calls.length, 1); // no extra call on expiry
});

test("independent per-item undo windows", async () => {
  const h = harness();
  await h.controller.tap("u1", "milk", 9);
  await h.controller.tap("u2", "bread", 9);
  await h.controller.undo("u1", "milk");
  assert.equal(h.controller.getState("u1"), null);
  assert.equal(h.controller.getState("u2"), ItemState.UNDO_WINDOW);
});

test("failed completion after retries reverts and surfaces an error (Req 5.4)", async () => {
  const h = harness({ failUpdate: true });
  await h.controller.tap("u1", "oat milk", 9);
  assert.equal(h.controller.getState("u1"), null); // reverted
  assert.equal(h.errors.length, 1);
  assert.equal(h.errors[0].action, "complete");
});

test("card gone during undo window: completion already synced, nothing dropped", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  // Simulate teardown before expiry.
  h.controller.dispose();
  // The completion call was already sent on tap.
  assert.deepEqual(h.calls, [{ uid: "u1", status: "completed" }]);
});

test("inbound delete during undo window cancels the affordance (source wins)", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  assert.equal(h.controller.isUndoable("u1"), true);
  // Source no longer has u1 (deleted on Alexa directly).
  h.controller.reconcile(new Set(), new Map());
  assert.equal(h.controller.getState("u1"), null);
});

test("inbound uncheck during undo window adopts source state", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  // Source still has u1 but now shows it unchecked (reversed elsewhere).
  h.controller.reconcile(new Set(["u1"]), new Map([["u1", false]]));
  assert.equal(h.controller.getState("u1"), null);
});

test("failed undo leaves item completed (safe direction)", async () => {
  const h = harness();
  await h.controller.tap("u1", "oat milk", 9);
  // Now make updates fail for the undo call.
  h.controller._updateItem = async () => {
    throw new Error("boom");
  };
  await h.controller.undo("u1", "oat milk");
  assert.equal(h.controller.getState("u1"), ItemState.COMPLETED);
});
