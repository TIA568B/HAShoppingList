# Tasks: Categorized Alexa Shopping List

## Wave 1 — No dependencies

- [ ] 1.1 Confirm historical data source: check `recorder` retention for `todo.shopping_list`
      and decide between recorder history query vs. manual export. (Design §6)
- [ ] 1.2 Define starter category taxonomy (Produce, Milk, Chilled, Fake Meat, Bakery, Frozen,
      Drinks, Pantry, Household, Uncategorized) with egg and other animal-derived categories
      excluded, milk kept as its own category, other dairy-style items (cheese/yogurt/butter)
      grouped under "Chilled", and meat-keyword items routed to "Fake Meat" instead of excluded.
      (Req 1.2, 1.3, 1.4, 1.5)
- [ ] 1.3 Set up `pyscript` (or `python_script`) integration in HA if not already installed.
- [ ] 1.4 Create `category_map.json` schema and initial empty/default file. (Design §3)

## Wave 2 — Depends on Wave 1

- [ ] 2.1 Build historical bootstrap script: pull item history, normalize text, cluster into
      candidate categories, exclude egg and other animal-derived terms, route milk items to
      "Milk", other dairy-style items to "Chilled", meat-keyword items to "Fake Meat".
      (Req 1.1–1.5)
- [ ] 2.2 Build review step (simple YAML/JSON output the user edits, or a minimal UI form) for
      approving the draft category map before it goes live. (Req 1.4)
- [ ] 2.3 Build the Categorization Engine: event listener on `todo.shopping_list` state change,
      normalize + match against `category_map`, write to
      `sensor.shopping_list_categorized`. (Req 2.1, 2.2, 2.3)
- [ ] 2.4 Add fallback default category set for the case where no historical data exists.
      (Req 1.5)

## Wave 3 — Depends on Wave 2

- [ ] 3.1 Add manual re-categorization service (e.g.
      `pyscript.categorize_recategorize_item`) that updates `category_map` and re-runs
      categorization. (Req 2.4, 6.2)
- [ ] 3.2 Build custom Lovelace card: render categories from
      `sensor.shopping_list_categorized`, subscribe via websocket for live updates. (Req 3.1)
- [ ] 3.3 Implement category auto-collapse when all items in a category are checked. (Req 3.3)
- [ ] 3.4 Implement add-item flow in the card calling `todo.add_item` directly. (Req 5.2)

## Wave 4 — Depends on Wave 3

- [ ] 4.1 Implement optimistic tick-off with local "pending" state. (Req 3.2, 4.1)
- [ ] 4.2 Implement per-item undo countdown + Undo control, independent per item. (Req 4.2, 4.5)
- [ ] 4.3 Implement undo logic: revert local state, cancel pending backend call. (Req 4.3)
- [ ] 4.4 Implement grace-period expiry → `todo.update_item` call to finalize completion.
      (Req 4.4, 5.1)
- [ ] 4.5 Implement error handling/retry + user-visible warning on failed sync. (Req 5.4)

## Wave 5 — Depends on Wave 4

- [ ] 5.1 Implement category settings UI: view/add/edit/remove categories and keywords.
      (Req 6.1, 6.2)
- [ ] 5.2 Implement category-deletion behavior: reassign orphaned items to "Uncategorized"
      rather than deleting them. (Req 6.3)
- [ ] 5.3 End-to-end test: add item via Alexa voice → confirm it appears categorized in card
      within a few seconds. (Req 2.1, 3.1)
- [ ] 5.4 End-to-end test: tick item in card → undo within grace period → confirm no change
      propagated to Alexa list. (Req 4.1–4.4)
- [ ] 5.5 End-to-end test: tick item in card → let grace period expire → confirm item marked
      complete on the real Alexa app. (Req 5.1)
- [ ] 5.6 End-to-end test: run bootstrap against real historical data → confirm milk items land
      in "Milk", cheese/yogurt/butter land in "Chilled", meat-keyword items land in "Fake Meat",
      and no egg or other animal-derived categories/keywords appear elsewhere in the generated
      map. (Req 1.2–1.5)
