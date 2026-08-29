# 01 — Specification Analysis

## Specification files reviewed

All files in `docs/specs/` were read in full and treated as the primary source of truth for
*requirements* (where they don't conflict with verified HA reality):

| File | Role |
|------|------|
| `docs/specs/requirements.md` | 6 EARS-style requirements with acceptance criteria |
| `docs/specs/design.md` | Proposed architecture (pyscript + sensor + card), data model, sequences, open questions |
| `docs/specs/tasks.md` | 5 dependency-ordered task waves |

## Consolidated requirements

### Functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| FR1 | Seed an initial item→category mapping from available data | Req 1 |
| FR2 | Exclude egg/animal-derived categories; milk→Milk; dairy-style→Chilled; meat→Fake Meat | Req 1.2–1.5, 3, 4 |
| FR3 | Unmappable items → `Uncategorized` (never guess) | Req 1.6, 2.3 |
| FR4 | Present generated mapping for user review before going live | Req 1.7 |
| FR5 | Fall back to a default vegan taxonomy if no data; never block setup | Req 1.8 |
| FR6 | Categorize new items automatically within a few seconds | Req 2.1, 2.2 |
| FR7 | Manual category assignment persists and applies to future identical items (learning) | Req 2.4, 6.2 |
| FR8 | Categorized view updates live on any source change (incl. Alexa-direct) without refresh | Req 3.1 |
| FR9 | Optimistic UI on tick-off | Req 3.2, 4.1 |
| FR10 | Collapse/de-emphasize categories with zero remaining unchecked items | Req 3.3 |
| FR11 | Per-item undo during an 8–10s grace period, tracked independently per item | Req 4.1–4.5 |
| FR12 | On grace-period expiry, finalize completion and sync to source | Req 4.4, 5.1 |
| FR13 | Undo within grace period reverses UI and any sent change | Req 4.3 |
| FR14 | Add item via view → native `todo.add_item` on source | Req 5.2 |
| FR15 | Failed sync retries and surfaces a visible error; never silently drops | Req 5.4 |
| FR16 | View/add/edit/remove categories and keywords; apply immediately | Req 6.1, 6.2 |
| FR17 | Deleting a category reassigns its items to `Uncategorized`, never deletes items | Req 6.3 |

### Non-functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| NFR1 | Reactive delay ≤ "a few seconds" for new-item categorization and live display | Req 2.1, 3.1 |
| NFR2 | Undo grace period target 8–10s | Req 4.1 |
| NFR3 | No drift: projection always rebuildable from source + map | design §2.3 |
| NFR4 | Best-effort vegan filtering; ambiguous → Uncategorized (not a guarantee) | design §6 |
| NFR5 | Runs fully local; personal data (list contents) stays on-device | derived (security) |

### Technical constraints

- Runs inside Home Assistant 2026.8.3.
- Depends on the core `todo` building block and the `alexa_devices`-provided list entity.
- The source entity supports only CREATE/UPDATE/DELETE (no reorder, no due dates).

### Dependencies between specs

- `tasks.md` waves map onto `requirements.md` IDs and `design.md` components; Wave 1 (data
  source + taxonomy + pyscript setup) gates everything.
- `design.md` §6 open questions feed directly into `tasks.md` 1.1 (confirm history source).

### Integration requirements

- Must interoperate with the existing `alexa_devices` todo entity purely through public HA
  APIs (state machine + `todo.*` services).

### Security requirements

- No new credential storage (auth lives in `alexa_devices`). List contents are personal data;
  keep local; redact diagnostics.

### Performance requirements

- Categorization over a shopping-list-sized corpus (tens to low hundreds of items) must be
  effectively instant; recompute is debounced.

### Operational requirements

- Survives HA restarts (persisted map + rebuildable projection). Surfaces failures visibly.

## Conflicts (spec vs. verified HA reality — reality wins)

| # | Conflict | Resolution |
|---|----------|------------|
| C1 | Spec targets `todo.shopping_list` as the Alexa list. Reality: that is the empty native list; the Alexa list is `todo.david_carson_amazon_gmail_com_shopping_list` (platform `alexa_devices`). | Target the `alexa_devices` entity. Make the source entity **configurable** in the config flow, defaulting to an auto-detected `alexa_devices` todo list. |
| C2 | Req 1 assumes queryable historical shopping data (recorder/logbook). Reality: no recorder history for the todo entity; state is only an item count. | Drop history mining. Seed from the **live list including completed items** (retained and exposed by `alexa_devices`) + default taxonomy, and learn over time. Confirmed with user. |
| C3 | `design.md` sample "sensor attributes" JSON shows a `Dairy` category, contradicting the requirements (no Dairy; milk→Milk, dairy-style→Chilled). | Follow the requirements. `Dairy` is a spec typo. No `Dairy` category exists. |
| C4 | Spec implementation vehicle is pyscript/`python_script`. pyscript is not installed and is a weaker fit. | Implement as a custom integration + card (documented override; user approved choosing the best approach). |

## Ambiguities (documented, not silently resolved)

| # | Ambiguity | Recommended approach |
|---|-----------|----------------------|
| A1 | Grace period "8–10s": fixed or configurable? | Configurable via options flow, default 9s. |
| A2 | "Collapse or de-emphasize" empty categories: which? | Collapse by default, user-toggle to de-emphasize; card option. |
| A3 | Where do users edit categories — YAML, a form, or the card? | Primary: card settings panel calling services. Services are the API; card is one client. |
| A4 | Add-item flow: does a new item get an immediate category before the source round-trips? | Yes — optimistic categorization in the card, reconciled when the inbound flow returns the real item. |
| A5 | Should completed (already-ticked) items appear in the categorized view? | Show unchecked by default; provide a card toggle to reveal completed. Completed items still feed learning. |

## Missing requirements / gaps (recorded as open questions — see doc 15)

- G1: Multiple Alexa lists exist (`shopping_list` and `to_do_list`). Scope confirmed to
  shopping list only; to-do list explicitly out of scope for v1.
- G2: No requirement covers what happens to `Uncategorized` learning when the same raw text
  later gets a manual category — precedence rule needed (defined in doc 07).
- G3: No requirement defines behavior for duplicate item names on the source list — handled by
  operating on stable `uid`, defined in doc 08.
