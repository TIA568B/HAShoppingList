import assert from "node:assert/strict";
import { test } from "node:test";

import { escapeHtml } from "../src/escape.js";
import { normalize } from "../src/normalize.js";

test("normalize lowercases, trims, collapses whitespace", () => {
  assert.equal(normalize("  Oat   Milk "), "oat milk");
  assert.equal(normalize("MILK"), "milk");
});

test("normalize strips a leading quantity and unit", () => {
  assert.equal(normalize("2x oat milk"), "oat milk");
  assert.equal(normalize("1 litre milk"), "milk");
  assert.equal(normalize("a dozen eggs"), "eggs");
});

test("normalize keeps intra-word hyphen and apostrophe, drops other punctuation", () => {
  assert.equal(normalize("Free-Range Eggs!"), "free-range eggs");
  assert.equal(normalize("Ben's cookies"), "ben's cookies");
});

test("normalize handles empty/nullish", () => {
  assert.equal(normalize(""), "");
  assert.equal(normalize(null), "");
  assert.equal(normalize("   "), "");
});

test("escapeHtml neutralises angle brackets and quotes", () => {
  assert.equal(escapeHtml("<script>alert('x')</script>"), "&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;");
  assert.equal(escapeHtml('a & "b"'), "a &amp; &quot;b&quot;");
});
