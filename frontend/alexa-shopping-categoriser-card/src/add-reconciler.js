// Add reconciliation (finding REVIEW2-002, docs/plans/08 & 11).
// todo.add_item does not return the created uid, so an optimistically-added item carries
// a client token with no uid. On the next inbound refresh we adopt the first inbound
// needs_action item whose normalized summary matches, taking over its real uid. Unmatched
// placeholders are dropped after a bounded window.

import { normalize } from "./normalize.js";

export class AddReconciler {
  /**
   * @param {object} [opts]
   * @param {number} [opts.windowMs]  how long to keep an unmatched placeholder (default 30s)
   * @param {()=>number} [opts.now]   clock (test seam)
   */
  constructor(opts = {}) {
    this._windowMs = opts.windowMs ?? 30000;
    this._now = opts.now ?? (() => Date.now());
    /** @type {Map<string,{normalized:string, createdAt:number}>} placeholders by client token */
    this._pending = new Map();
  }

  /** Register an optimistic add; returns a client token used to track it. */
  register(text) {
    const token = `pending-${this._now()}-${Math.random().toString(36).slice(2)}`;
    this._pending.set(token, { normalized: normalize(text), createdAt: this._now() });
    return token;
  }

  get pendingCount() {
    return this._pending.size;
  }

  hasPending(token) {
    return this._pending.has(token);
  }

  /**
   * Given the inbound needs_action items, resolve placeholders.
   * @param {Array<{uid:string, name:string, checked:boolean}>} inboundItems
   * @returns {Array<{token:string, uid:string}>} adopted (token -> real uid) mappings
   */
  reconcile(inboundItems) {
    const adopted = [];
    const now = this._now();
    const availableByNorm = new Map();
    for (const item of inboundItems) {
      if (item.checked) continue;
      const norm = normalize(item.name);
      if (!availableByNorm.has(norm)) availableByNorm.set(norm, []);
      availableByNorm.get(norm).push(item.uid);
    }

    for (const [token, placeholder] of [...this._pending.entries()]) {
      const candidates = availableByNorm.get(placeholder.normalized);
      if (candidates && candidates.length) {
        const uid = candidates.shift();
        adopted.push({ token, uid });
        this._pending.delete(token);
        continue;
      }
      // Drop stale placeholders past the window.
      if (now - placeholder.createdAt > this._windowMs) {
        this._pending.delete(token);
      }
    }
    return adopted;
  }
}
