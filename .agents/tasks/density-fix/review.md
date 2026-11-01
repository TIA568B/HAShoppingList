# Card density restored: 28px checkboxes, padding cut, ~10-12 items fit on screen

Checkpoint density fix rolling back bloat from v0.10.1 while keeping the strikethrough-with-undo UX. Checkbox size pinned at 28px (vs. original 20px, vs. previous oversized 36px), padding and gaps cut across the board (card 12px→8px, row 3px→2px, gaps 8px→6px, indent 10px→6px), undo button compacted to icon-only styling (2px 6px, 0.85em). CSS resets removed the WCAG-targeting `--min-tap` variable and per-shop focus's "Show all" toggle, simplifying the collapse logic. All 158 backend tests and 38 frontend tests pass. The commit tidies unrelated debris alongside (removed the focus toggle, removed add-field focus preservation, removed timeout wrapper around service calls).

**Watch for:** Focus logic simplified and `NO_PREFERENCE` constant removed — confirm these changes are intentional and don't mask a misunderstanding of shop grouping. Verify the add-field focus preservation removal won't regress mobile keyboard behavior. Confirm the retry timeout removal is safe (it was wrapping all retries; verify the intent was truly to remove it, not accidental deletion).

---

## High-level view

The card was rendering 4–5 items per screen after v0.10.1 bloated padding and checkbox sizing. This fix cuts padding/margins across all sections, brings checkboxes to 28px (responsive but not oversized), and uses compact inline styling for the undo button. The strikethrough-with-undo UX is untouched. Shop focus logic was simplified: Focus now always collapses other shops (no "Show all" toggle to undo the focus), and the `NO_PREFERENCE` constant was inlined into the focus handler. Add-field focus preservation code was removed, which could impact mobile keyboard stability if the field loses focus on state updates — verify this against mobile testing. The retry logic for service calls lost a per-attempt timeout wrapper; verify the intent (the wrap was defensive against network stalls). Collapse state now has fewer moving parts, but the core data model and card-local state tracking are unchanged.

---

<details>
<summary>Issues (3)</summary>

1. **Add-field focus preservation removed** — the field's value, focus state, and caret position were captured before rebuild and restored after. Removing this risks mobile keyboard dismissal on source entity updates. Verify this was tested on mobile or intentionally deprioritized.

2. **Retry timeout wrapper removed without explanation** — `withTimeout` was wrapping all `_sendWithRetry` calls with an 8s per-attempt timeout to fail fast on poor reception. Removing it makes retries depend entirely on the browser's default timeout (potentially tens of seconds). Confirm whether this is a deliberate trade-off (simpler retry logic) or accidental.

3. **Focus toggle removed** — the previous "Show all" button that toggled focus off is gone; Focus now always collapses other shops. Verify this is a product decision (users never used the toggle) and not unintentional loss of functionality.

</details>

---

<details>
<summary>Details</summary>

### Checkbox sizing and item density

Checkbox 36px→28px, row padding 3px→2px, gap 8px→6px. Font sizes: `.asc-name` 1.05em→0.95em, line-height 1.3→1.2. Strikethrough opacity 0.6→0.55. All tests pass confirming 28px target and density restoration to ~10-12 items per screen.

### Padding and spacing systematized

Card padding 12px→8px, shop margin 12px→8px, error/review banners 8px→6px, add-row gap 8px→6px, category indent 10px→4px, category header padding 4px→2px, edit menu padding 8px→6px and gap 16px→12px, edit buttons 10px 12px→4px 6px, version footer 10px→6px. Shop header font-size 1.15em→1em, category header 1.02em→0.95em. Changes are consistent (~30–40% reduction) and maintain hierarchy without tightness.

### Undo button compactness

Padding 8px 16px + 44px height constrained to `--min-tap` → 2px 6px, 0.85em, no height constraint. Now inline icon-like (still clickable and focus-accessible). Button text "Undo" remains readable.

### Focus and collapse logic simplifications

`isShopFocused()` and `expandAll()` removed from `CollapseState`; `focusShop()` now: collapse all except target. No "Show all" button — Focus is one-way. `NO_PREFERENCE` constant inlined (the string still appears in user-editable shop names; no semantic change). **Concern:** users cannot undo a focus without manually re-expanding each shop. Verify this is intentional product change, not accidental.

### Keyboard propagation simplification

`stopKeyboardPropagation` now single-phase (bubble) `stopPropagation` instead of dual-phase `stopImmediatePropagation`. Comment clarifies HA listens on `document`, not `window`. Should be functionally equivalent; regresses only if HA switches to capture-phase listening (not the case in 2026.8.3).

### Add-field focus preservation removed

Captured and restored add-item input's value, focus, and caret across re-renders to prevent keyboard dismissal on mobile when HA re-renders. **Regression risk:** mobile keyboard now dismisses on any source entity update. Verify this was tested on mobile or is an acceptable trade-off for density gains.

### Retry logic and timeout removal

`DEFAULT_RETRIES` 5→3. `withTimeout` wrapper (8s per-attempt timeout) deleted; retries now depend on browser default (potentially 30+ seconds). Backoff cap removed; delay grows unbounded (500ms → 1.5s → 4.5s). **Concern:** timeout was defensive against network stalls; removing it makes retries slower to fail on poor reception. Verify the intent (simpler logic) vs. accidental deletion.

### Unrelated removals

`stopKeyboardPropagation` dual-phase registration simplified, `_addInput` and `_addFocus` field tracking removed, focus "Show all" button and toggle removed.

### Test coverage

Frontend: 38/38 pass. Complete-on-tap, undo within window, window-expiry (no extra call), per-item windows independent, failed completion reverts, card-gone-during-undo, inbound changes cancel undo, collapse state persists, focus logic confirmed. Backend: 158/158 pass. No regression in categoriser, shop assignment, or services.

</details>

---

## File map

```
custom_components/alexa_shopping_categoriser/www/alexa-shopping-categoriser-card.js
  - Removed NO_PREFERENCE constant
  - Simplified CollapseState.focusShop() to always collapse others; removed isShopFocused()
    and expandAll()
  - Simplified stopKeyboardPropagation() to single-phase registration
  - Removed withTimeout wrapper around retries; reduced DEFAULT_RETRIES 5→3
  - Removed add-field focus preservation (_addInput, _addFocus tracking)
  - Removed focus "Show all" button and toggle logic in _renderShop()
  - Cut CSS padding/margins across all elements (12px→8px card, 3px→2px row, 8px→6px gaps)
  - Checkbox size 36px→28px; font sizes slightly smaller (0.95em, 0.85em)
  - Undo button 8px 16px padding and 44px height → 2px 6px, 0.85em
  - Strikethrough opacity 0.6→0.55

frontend/alexa-shopping-categoriser-card/src/card.js
  - Same CSS changes (mirrors the distribution file)
```

Full diff: `git show HEAD`

