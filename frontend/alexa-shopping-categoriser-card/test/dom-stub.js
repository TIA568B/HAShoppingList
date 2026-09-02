// Minimal DOM stub for testing the card's rendering logic under node:test without a
// browser. Implements just enough of the element API the card uses (createElement,
// append/appendChild/replaceChildren, textContent, classList-ish className, attributes,
// addEventListener, attachShadow, customElements). Not a general-purpose DOM.

class StubElement {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this._text = "";
    this._listeners = {};
    this.className = "";
    this.type = "";
    this.checked = false;
    this.value = "";
    this.placeholder = "";
    this.style = {};
  }

  set textContent(v) {
    // Mirror the DOM: setting textContent replaces all children with a single text node.
    this._text = v == null ? "" : String(v);
    this.children = [];
  }
  get textContent() {
    // Own text (set via textContent) plus any child text, in document order. Children
    // appended after textContent was set are concatenated after the own text — which is
    // how the card builds a header label followed by a nested button.
    const childText = this.children.map((c) => c.textContent).join("");
    return (this._text || "") + childText;
  }

  set innerHTML(v) {
    // Track that innerHTML was set; the card only uses it to clear (""), never with user text.
    this._innerHTML = v;
    if (v === "") this.children = [];
  }
  get innerHTML() {
    return this._innerHTML || "";
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }
  append(...kids) {
    for (const k of kids) this.children.push(k);
  }
  replaceChildren(...kids) {
    this.children = [...kids];
  }
  setAttribute(k, v) {
    this.attributes[k] = String(v);
  }
  getAttribute(k) {
    return this.attributes[k] ?? null;
  }
  addEventListener(type, fn) {
    (this._listeners[type] = this._listeners[type] || []).push(fn);
  }
  dispatch(type, ev = {}) {
    for (const fn of this._listeners[type] || []) fn(ev);
  }
  attachShadow() {
    this.shadowRoot = new StubElement("#shadow");
    return this.shadowRoot;
  }

  // Test helpers.
  query(pred, acc = []) {
    for (const c of this.children) {
      if (pred(c)) acc.push(c);
      c.query(pred, acc);
    }
    return acc;
  }
  byClass(cls) {
    return this.query((e) => (e.className || "").split(" ").includes(cls));
  }
  text() {
    return this.textContent;
  }
}

export function installDom() {
  const doc = {
    createElement: (tag) => new StubElement(tag),
  };
  globalThis.document = doc;
  globalThis.HTMLElement = StubElement;
  globalThis.customElements = { get: () => undefined, define: () => {} };
  globalThis.window = globalThis;
  return doc;
}

export { StubElement };
