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
| coordinator | get_items returns active+completed | projection has both; completed feed learning corpus | C2 |
| coordinator | source state_changed | recompute called (debounced) | 3.1 |
| coordinator | source unavailable | sensor unavailable, cached projection kept | 9 |
| coordinator | get_items raises | UpdateFailed, last_update_success False | 9 |
| sensor | attributes | match contract v1 exactly (snapshot) | 6 |
| sensor | state | == total_unchecked | 5 |
| services | recategorize_item | overrides updated + recompute | 2.4 |
| services | delete_category | category gone, items→Uncategorized, items not deleted | 6.3 |
| services | add_category duplicate name | HomeAssistantError | 6.2 |
| sync | finalize tick | todo.update_item(uid,status=completed) called once | 4.4, 5.1 |
| sync | undo completed | todo.update_item(uid,status=needs_action) | 4.3 |
| sync | add item | todo.add_item(item=text) | 5.2 |
| sync | update_item fails 3x | optimistic revert + error surfaced, not dropped | 5.4 |
| diagnostics | default | item text redacted; counts present | 10 |
| card (js) | tap then undo <N | no service call, item unchecked | 4.3 |
| card (js) | tap, timer expires | update_item(completed) called | 4.4 |
| card (js) | two items pending | independent timers/undo | 4.5 |
| card (js) | category all checked | collapsed/de-emphasized | 3.3 |
| migration | store v0→v1 | migrates + persists | 4 |

## Mocking

- `MockConfigEntry`; patch `hass.services.async_call` for `todo.get_items` (return the response
  shape) and assert exact payloads for writes; freeze time for debounce/grace tests; snapshot
  the sensor attributes.

## Regression

- Failing-first test per bug fix. Permanent regression test that source selection targets the
  `alexa_devices` todo entity and never silently picks `todo.shopping_list`.
