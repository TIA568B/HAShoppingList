import assert from "node:assert/strict";
import { test } from "node:test";

import { installDom } from "./dom-stub.js";

installDom();
const { stopKeyboardPropagation, setText, escapeHtml } = await import("../src/escape.js");

test("stopKeyboardPropagation stops keydown/keyup/keypress but not default", () => {
  const input = document.createElement("input");
  stopKeyboardPropagation(input);

  for (const type of ["keydown", "keyup", "keypress"]) {
    let stopped = false;
    let prevented = false;
    input.dispatch(type, {
      key: "c",
      stopPropagation: () => {
        stopped = true;
      },
      preventDefault: () => {
        prevented = true;
      },
    });
    assert.equal(stopped, true, `${type} should stop propagation (avoids HA hotkeys)`);
    assert.equal(prevented, false, `${type} must NOT preventDefault (typing still works)`);
  }
});

test("setText and escapeHtml basics still hold", () => {
  const el = document.createElement("span");
  setText(el, "<x>");
  assert.equal(el.textContent, "<x>");
  assert.equal(escapeHtml("<a>"), "&lt;a&gt;");
});
