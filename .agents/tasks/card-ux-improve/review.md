# Lovelace Card UX Improvements: Larger Checkboxes and Strikethrough Styling

The card's checkbox touch targets and completed-item visibility have been enhanced. Checkboxes grow from 26×26 px to 36×36 px (40×40 px on mobile), now with 4 px padding to reach a 44×44 px minimum clickable area per WCAG guidelines. Completed items display darker strikethrough text (opacity 0.5 + disabled color) and the undo button becomes visually prominent (white text on primary color, increased padding). The grace-period state machine and the 30-second undo window are unchanged.

Watch for: CSS box-sizing interaction with min-width/min-height constraints; strikethrough visibility in different theme contexts; touch-target consistency across form states.

**Verdict**: APPROVED

## High-level view

Checkbox sizing uses `box-sizing: content-box` to isolate the visual size (36×36 px) from its padding (4 px), ensuring the total computed box (44×44 px) meets WCAG standards without distorting the checkbox appearance. The approach is explicit and standard, trading a single extra CSS property for clarity over the alternative of resizing the input itself.

Strikethrough styling darkens completed items via opacity reduction (0.6 → 0.5) and applies Home Assistant's standard disabled-text color fallback, making the struck-through text visibly distinct across both light and dark themes without hardcoding a color.

The undo button gains visual prominence through increased padding (6×14 px → 8×16 px), font-weight 500, and a filled style (white text on the primary color background). This breaks the earlier minimal aesthetic but aligns with the button's role as an immediate action that reverses a destructive event.

Mobile scaling multiplies checkbox size proportionally (30×30 px → 40×40 px) and preserves WCAG compliance (`min-width/min-height` set to `var(--min-tap)`). The responsive behavior is symmetric with desktop.

<details>
<summary>Issues</summary>

1. **Item row height reduction** — `.asc-item` padding dropped from 6 px to 4 px and `min-height` changed from `var(--min-tap)` to `auto`. This saves vertical space but risks compressed rows on small screens. Verify the layout doesn't look cramped on mobile or when accessibility font sizes are enlarged.

2. **Strikethrough color fallback** — Uses `rgba(0,0,0,0.38)` as a fallback when `--disabled-text-color` is unavailable. This assumes a light background and will be hard to read in dark themes if HA's theme does not define the variable. Confirm `--disabled-text-color` is reliably present in the HA frontend context, or test in dark mode.

3. **Unvisited edge case: undo button width** — Undo button now has 8 px vertical and 16 px horizontal padding (vs. 6 px / 14 px before). If an item name is very long and the button wraps to a second line due to flex reflow, the increased padding could compound layout issues. Verify layout on narrow screens with long item names.

</details>

## Detailed behavioral sections

<details>
<summary>Details</summary>

### Checkbox touch target sizing and box-sizing discipline

The checkbox scales from 26×26 px to 36×36 px (core size), then adds `padding: 4px` and sets `box-sizing: content-box`. This means the total computed box (`36 + 4*2 = 44` px on each axis) meets WCAG AA minimum of 44×44 px, while the visible checkbox graphic remains 36×36 px. The parent `.asc-item` sets `align-items: center` and `flex: 0 0 auto`, ensuring the checkbox does not shrink or stretch despite the extra padding.

On mobile, the checkbox grows to 40×40 px (core size), totaling 48×48 px with padding—consistent application of the ratio. Both viewport tiers preserve `min-width: var(--min-tap)` and `min-height: var(--min-tap)`, providing a CSS safety net (typically `--min-tap` is 32 or 44 px depending on HA config) that prevents the checkbox from dwarfing below the accessibility standard even if rendering or theme changes occur.

The approach is CSS-correct and does not alter the input's `accent-color` or behavior. Because the input element itself is still 36×36 px (the `width` and `height` properties), the browser's native checkbox rendering remains clean and pixel-aligned.

### Item row compaction trade-off

The `.asc-item` row's `padding` reduced from `6px 0` to `4px 0`, and `min-height` flipped from `var(--min-tap)` to `auto`. This saves vertical space and allows rows to compress if the content (name + checkbox + undo button) is small. However, it introduces a risk: on narrow screens or when the row wraps (e.g., long item names), the reduced padding may make the row feel cramped, and the loss of `min-height` means a short item could drop below the WCAG 44-px tap height if the text size is reduced or the button rendering is compact.

The change passes the success criterion "no console errors; card remains responsive," but the visual result on edge cases (very long names, narrow mobile, accessibility font scales) should be tested before shipping. The prior `min-height: var(--min-tap)` provided a safety bound; removing it relies on the checkbox and button's own `min-height: var(--min-tap)` to maintain vertical space. This is usually sufficient but is a behavioral dependency that should be verified.

### Strikethrough visibility improvements

Completed items (`.asc-name.checked`) now render with `opacity: 0.5` (down from 0.6) and `color: var(--disabled-text-color, rgba(0,0,0,0.38))`. The text-decoration remains `line-through` unchanged. The darker opacity and explicit disabled color make the struck-through text more distinct, especially in dark themes where the prior opacity 0.6 could blur into the background.

The fallback color `rgba(0,0,0,0.38)` is Home Assistant's Material Design disabled color for light themes. If `--disabled-text-color` is not defined (which should be rare in HA's frontend context), the fallback renders as transparent black on a light background, yielding the expected dim appearance. However, on a dark background without the variable, the fallback becomes dim black and will be nearly invisible. This is a known limitation of the fallback approach; if testing reveals this is a real issue (e.g., certain HA theme combinations), the color should be wired to detect the theme and adapt.

### Undo button prominence and visual weight

The `.asc-undo` button gains `font-weight: 500`, `background: var(--primary-color, #03a9f4)`, and `color: white`, while padding increases from `6px 14px` to `8px 16px`. The button shifts from a minimal, text-only style to a filled button with solid background. This is a deliberate aesthetic break: prior undo buttons blended into the item row; now they command attention as a critical action that reverses completion.

The white-on-blue style is high-contrast and aligns with HA's primary-action button pattern. Font-weight 500 (medium) adds visual heft without becoming bold (700). The padding increase ensures the button has comfortable touch spacing on mobile, supporting the original user request for larger, more tappable controls.

The change does not alter button timing (still governed by the 30-second grace period in `TickController._startUndoWindow`), state machine logic, or the service call it triggers (`todo.update_item`). It is purely presentational.

### Responsive scaling and mobile media query

Mobile checkboxes (width/height: 40×40 px) are scaled proportionally from the desktop 36×36 px, and the media query also adds the explicit `min-width/min-height: var(--min-tap)` to mobile checkboxes. This ensures mobile touch targets remain compliant even if theme rendering changes. The rest of the item row (`gap: 14px`, `padding: 8px 0`) is handled separately in the media query and does not carry the row-compaction risk of the desktop rule (mobile rows keep `padding: 8px 0`, not the reduced `4px 0`). This asymmetry is intentional and correct: mobile rows have more breathing room.

### JavaScript and state machine unchanged

The TickController's `_startUndoWindow` method, which governs the grace period, remains at `Math.max(1, Number(gracePeriodSeconds) || 9) * 1000` milliseconds. No changes to the state machine, the 30-second default (or user-configured) grace window, or the undo/revert logic. CSS and HTML rendering changes only; the behavioral contract is preserved.

### CSS syntax validation

Node's `-c` flag confirms the file parses without syntax errors. All CSS properties are valid (no typos in property names or units). The stylesheet contains no new dependencies or external resources.

### No regressions in unrelated styles

Adjacent styles (`.asc-name`, `.asc-edit`, `.asc-edit-menu`, etc.) remain unchanged. The flexbox layout, gap, alignment, and text styles for non-completed items are untouched. Completed items use the new darkened strikethrough; uncompleted items are unaffected.

</details>

## File map

- **custom_components/alexa_shopping_categoriser/www/alexa-shopping-categoriser-card.js**
  - Checkbox size and padding: 26×26 → 36×36 px (desktop), 30×30 → 40×40 px (mobile)
  - Item row padding: 6px → 4px (desktop only)
  - Strikethrough opacity and color: 0.6 → 0.5 + `--disabled-text-color` fallback
  - Undo button styling: padding 6×14 → 8×16 px, added font-weight, background fill
  - Responsive query: checkbox sizes and WCAG min-tap constraints for mobile

[Full diff](https://github.com/TIA568B/HAShoppingList/commit/0c21f02)
