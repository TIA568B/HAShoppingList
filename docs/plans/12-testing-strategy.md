# 12 — Testing Strategy

Tooling: `pytest` + `pytest-homeassistant-custom-component`, `ruff`, `mypy --strict`. No
network; no live Alexa. Coverage gates: categorizer 100%; integration ≥90% (see testing
steering).

## Test types

- **Unit (pure):** `categorizer.py` — normalization, matching, vegan rules, override
  precedence, fallback.
- **Config flow / options flow:** step behavior, aborts, validation, single-instance.
- **Coordinator:** projection build from mocked `get_items`, recompute on state change,
  debounce, unavailable source, safety poll.
- **Sensor:** attribute schema == contract (snapshot), state value, availability.
- **Services:** each service's persistence + recompute + validation + error raising.
- **Sync/error paths:** completion/undo/add service payloads, retry/backoff, revert-on-failure.
- **Diagnostics:** redaction.
- **Frontend (light):** card timer/undo/collapse state machine as JS unit tests.

## Test matrix

| Area | Case | Expected | Req |
|------|------|----------|-----|
| categorizer | "2x oat milk" | Milk | 1.3, 7 |
| categorizer | "cheddar cheese" | Chilled | 1.4 |
| categorizer | "smoky bacon" | Fake Meat | 1.5 |
| categorizer | "free range eggs" | Uncategorized | 1.2 |
| categorizer | "honey" | Uncategorized | 1.2 |
| categorizer | "birthday candles" (no kw) | Uncategorized | 1.6, 2.3 |
| categorizer | override "birthday candles"→Household | Household (beats keyword/fallback) | 2.4 |
| categorizer | override→deleted category | falls through to keyword/Uncategorized | 6.3 |
| config flow | alexa_devices todo present | creates entry, unique_id=source | C1 |
| config flow | no alexa_devices todo | abort `no_alexa_lists` (or manual entry warn) | 1.8 |
| config flow | same source twice | abort already_configured | — |
| options flow | set grace=12 | persisted, echoed in attributes | 4.1 |
| options flow | grace<8 or >30 | rejected (range 8–30) | L-7 |
| reconfigure flow | change source entity | entry.data + unique_id updated atomically; store survives | M-3 |
| coordinator | get_items returns active+completed | projection has both; completed feed learning corpus | C2 |
| coordinator | source state_changed | recompute called (debounced) | 3.1 |
| coordinator | source unavailable | sensor unavailable, cached projection kept | 9 |
| coordinator | get_items raises | UpdateFailed, last_update_success False | 9 |
| sensor | attributes | match contract v2 exactly (snapshot, incl. category_definitions) | 6, M-2 |
| sensor | category_definitions | mirrors stored map name+keywords, ordered | 6.1, M-2 |
| coordinator | get_items envelope | reads response[source]["items"]; summary→name, status→completed | REVIEW2-001 |
| sensor | state | == total_unchecked | 5 |
| services | recategorize_item | overrides updated + recompute | 2.4 |
| services | delete_category | category gone, items→Uncategorized, items not deleted | 6.3 |
| services | add_category duplicate name | HomeAssistantError | 6.2 |
| services | edit_category rename | overrides pointing at old name migrated to new name | REVIEW2-003 |
| sync | tick sends completion on tap | todo.update_item(uid,status=completed) called immediately | 4.4, 5.1, H-1 |
| sync | undo within window | todo.update_item(uid,status=needs_action) | 4.3 |
| sync | add item | todo.add_item(item=text); placeholder adopts inbound uid by normalized summary | 5.2, REVIEW2-002 |
| sync | completion fails 3x | optimistic revert + error surfaced, not dropped | 5.4 |
| sync | card gone during undo window | completion already synced; nothing dropped (mis-tap becomes a real completion — accepted) | 5.4, H-1 |
| sync | inbound delete of item in undo window | local undo affordance cancelled (source wins) | M-7 |
| diagnostics | default | item text redacted; counts present | 10 |
| card (js) | tap | update_item(completed) sent immediately; undo shown | 4.1, H-1 |
| card (js) | tap then undo <N | reversing update_item(needs_action) sent, item unchecked | 4.3 |
| card (js) | tap, window expires | no further call; undo affordance removed | 4.4 |
| card (js) | two items in undo window | independent timers/undo | 4.5 |
| card (js) | category all checked | collapsed/de-emphasized | 3.3 |
| card (js) | first setup | "Review your categories" banner + prominent Uncategorized surfaced | 1.7, M-1 |
| migration | store schema_version v0→v1 | migrates + persists | 4 |

> Note (followup02 FO-2): the store **`schema_version`** (persistence, currently 1) and the sensor
> **`attributes_version`** (frontend contract, currently 2) version **independently** — they are
> unrelated counters. The migration test targets the store schema; the snapshot test targets the
> attribute contract. See doc 06.

## Mocking

- `MockConfigEntry`; patch `hass.services.async_call` for `todo.get_items` (return the response
  shape) and assert exact payloads for writes; freeze time for debounce/grace tests; snapshot
  the sensor attributes.

## Regression

- Failing-first test per bug fix. Permanent regression test that source selection targets an
  entity on the **`alexa_devices` platform** (not a hard-coded entity id) and never silently
  picks an entity on the `shopping_list` platform. (Finding M-8 / S-03.)
