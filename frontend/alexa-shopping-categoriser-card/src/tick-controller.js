// Per-item tick / undo state machine — complete-on-tap + reversing undo (finding H-1,
// docs/plans/08 & 11). Pure of the DOM: I/O (service calls), timers, and change
// notifications are injected so this is unit-testable without a browser.
//
// Model:
//   Unchecked --tap--> (send completed) --success--> UndoWindow --expire--> Completed
//                                        --fail(retries)--> Unchecked (revert + error)
//   UndoWindow/Completed --undo--> (send needs_action) --success--> Unchecked
//   Source-wins reconcile cancels a local undo affordance if the source changed the uid.

export const ItemState = Object.freeze({
  UNCHECKED: "unchecked",
  COMPLETING: "completing",
  UNDO_WINDOW: "undo_window",
  COMPLETED: "completed",
  REVERSING: "reversing",
});

const DEFAULT_RETRIES = 3;

export class TickController {
  /**
   * @param {object} deps
   * @param {(uid:string, status:string)=>Promise<void>} deps.updateItem  send todo.update_item
   * @param {(item:{name:string,action:string})=>void} deps.onError       surface an error
   * @param {()=>void} deps.onChange                                       request a re-render
   * @param {(fn:()=>void, ms:number)=>any} [deps.setTimer]                timer factory (test seam)
   * @param {(handle:any)=>void} [deps.clearTimer]
   * @param {(ms:number)=>Promise<void>} [deps.sleep]                      backoff sleep (test seam)
   * @param {number} [deps.retries]
   */
  constructor(deps) {
    this._updateItem = deps.updateItem;
    this._onError = deps.onError || (() => {});
    this._onChange = deps.onChange || (() => {});
    this._setTimer = deps.setTimer || ((fn, ms) => setTimeout(fn, ms));
    this._clearTimer = deps.clearTimer || ((h) => clearTimeout(h));
    this._sleep = deps.sleep || ((ms) => new Promise((r) => setTimeout(r, ms)));
    this._retries = deps.retries ?? DEFAULT_RETRIES;
    /** @type {Map<string, {state:string, name:string, timer:any}>} */
    this._items = new Map();
  }

  /** Return the tracked local state for a uid, or null. */
  getState(uid) {
    const entry = this._items.get(uid);
    return entry ? entry.state : null;
  }

  /** True while the undo affordance should be shown for this uid. */
  isUndoable(uid) {
    const s = this.getState(uid);
    return s === ItemState.UNDO_WINDOW || s === ItemState.COMPLETED;
  }

  /**
   * User taps an unchecked item. Sends completion immediately; on success starts the
   * per-item undo window. On exhausted failure reverts and surfaces an error.
   */
  async tap(uid, name, gracePeriodSeconds) {
    this._set(uid, { state: ItemState.COMPLETING, name, timer: null });
    const ok = await this._sendWithRetry(uid, "completed", name, "complete");
    if (!ok) {
      this._clear(uid);
      return;
    }
    this._startUndoWindow(uid, name, gracePeriodSeconds);
  }

  /** User taps undo (within window or after completion). Reverses via needs_action. */
  async undo(uid, name) {
    const entry = this._items.get(uid);
    if (entry && entry.timer) this._clearTimer(entry.timer);
    this._set(uid, { state: ItemState.REVERSING, name: name ?? entry?.name, timer: null });
    const ok = await this._sendWithRetry(uid, "needs_action", name ?? entry?.name, "undo");
    if (ok) {
      this._clear(uid);
    } else {
      // Undo failed after retries: item stays completed (safe direction).
      this._set(uid, { state: ItemState.COMPLETED, name: name ?? entry?.name, timer: null });
    }
  }

  /**
   * Reconcile local state against an inbound projection. Source wins: if a tracked uid
   * is gone from the source, or its checked state was changed on Alexa directly, drop the
   * local undo affordance and adopt source state (finding M-7).
   * @param {Set<string>} sourceUids       uids present in the inbound projection
   * @param {Map<string,boolean>} checkedByUid  uid -> checked (from source)
   */
  reconcile(sourceUids, checkedByUid) {
    for (const [uid, entry] of [...this._items.entries()]) {
      // Only adopt source state for items that are in a resolved local state; an
      // in-flight COMPLETING/REVERSING call is left to resolve on its own.
      if (entry.state === ItemState.COMPLETING || entry.state === ItemState.REVERSING) {
        continue;
      }
      if (!sourceUids.has(uid)) {
        // Removed on Alexa directly -> cancel affordance.
        if (entry.timer) this._clearTimer(entry.timer);
        this._clear(uid);
        continue;
      }
      const sourceChecked = checkedByUid.get(uid);
      // If the source now shows unchecked while we think it is completed/undo-window,
      // the user (or Alexa) reversed it elsewhere -> adopt and drop the affordance.
      if (sourceChecked === false) {
        if (entry.timer) this._clearTimer(entry.timer);
        this._clear(uid);
      }
    }
  }

  /** Cancel all pending timers (card teardown). */
  dispose() {
    for (const entry of this._items.values()) {
      if (entry.timer) this._clearTimer(entry.timer);
    }
    this._items.clear();
  }

  // --- internals --------------------------------------------------------

  _startUndoWindow(uid, name, gracePeriodSeconds) {
    const ms = Math.max(1, Number(gracePeriodSeconds) || 9) * 1000;
    const timer = this._setTimer(() => {
      const entry = this._items.get(uid);
      if (entry && entry.state === ItemState.UNDO_WINDOW) {
        // Window expired: completion stands; drop the affordance (no extra call).
        this._set(uid, { state: ItemState.COMPLETED, name, timer: null });
      }
    }, ms);
    this._set(uid, { state: ItemState.UNDO_WINDOW, name, timer });
  }

  async _sendWithRetry(uid, status, name, action) {
    let delay = 500;
    for (let attempt = 1; attempt <= this._retries; attempt++) {
      try {
        await this._updateItem(uid, status);
        return true;
      } catch (err) {
        if (attempt >= this._retries) {
          this._onError({ name, action, error: String(err) });
          return false;
        }
        await this._sleep(delay);
        delay *= 3;
      }
    }
    return false;
  }

  _set(uid, entry) {
    this._items.set(uid, entry);
    this._onChange();
  }

  _clear(uid) {
    this._items.delete(uid);
    this._onChange();
  }
}
