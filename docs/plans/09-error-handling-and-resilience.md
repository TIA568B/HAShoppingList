# 09 — Error Handling & Resilience

## Principles

- Never drop a user change silently (Req 5.4).
- Degrade gracefully: an unmatched or problematic item becomes `Uncategorized`; the coordinator
  never crashes on one bad item.
- Fail loud in logs, visible to the user only when action is needed.

## Failure modes and responses

| Failure | Detection | Response |
|---------|-----------|----------|
| Source entity missing/unavailable at **first refresh** | `hass.states.get(source)` None or state `unavailable`/`unknown` | Raise `ConfigEntryNotReady` (HA retries setup); create a repair issue guiding to `alexa_devices`. Distinct from a read error with the entity present, which is `UpdateFailed` (finding L-3) |
| Source entity `unavailable`/`unknown` at runtime | state listener / poll | Sensor becomes unavailable; keep last projection cached; repair issue if prolonged |
| `todo.get_items` read fails | exception from service call | `UpdateFailed`; coordinator marks `last_update_success=False`; retry on next event/poll |
| Invalid/empty response | schema/shape check | Treat as read failure (`UpdateFailed`); do not corrupt the cached projection |
| Completion sync (`todo.update_item`) fails | exception from call | Retry with backoff (below); on exhaustion revert optimistic UI + surface error |
| Add sync (`todo.add_item`) fails | exception | Same retry/backoff; remove the optimistic item + surface error |
| Store load corrupt | JSON/schema error | Log error, back up the corrupt file, fall back to default taxonomy, raise repair issue |
| Category name collision on edit/add | validation | Raise `HomeAssistantError` (service) / show inline error (card) |

## Retry & backoff (writes)

- The card performs the write **immediately on the user action** (complete-on-tap, reversing
  undo, or add — see doc 08); on failure it retries up to **3** attempts with exponential backoff
  (e.g. 0.5s, 1.5s, 4s + jitter).
- On exhaustion: revert the optimistic change and show a persistent, dismissible error toast
  naming the item and action (Req 5.4). The item returns to its prior (unchecked/absent) state
  so nothing is silently lost.
- **Why no deferred client-only finalize (finding H-1):** completion is not held behind a
  client-side grace timer. Because the write is sent on tap, a closed/backgrounded/crashed card
  cannot silently drop a completion — the change is already synced. The grace window governs undo
  only. This is the design's resolution of the "never silently drops" guarantee (Req 5.4) and the
  architecture rule "no business logic in the card the backend cannot also enforce."
- Reads (coordinator) simply wait for the next event/poll — no aggressive retry loop against
  Amazon (respect the upstream integration's rate posture).

## Rate limiting

- We add negligible load: reads are event-driven + a slow poll; writes are user-initiated and
  low frequency. We rely on `alexa_devices`/`aioamazondevices` to enforce upstream limits and
  surface `CannotRetrieveData`, which we treat as a transient read failure.

## Partial failures

- Batch operations (e.g. multiple quick tick-offs) are per-item and independent; one item's
  sync failure does not affect others (mirrors the source integration's per-item delete/refresh
  approach).

## Home Assistant restart / card closed

- Category map + overrides persist in the Store. The projection is rebuilt on first refresh.
- With complete-on-tap (doc 08), there are **no** in-flight server-side finalize timers to lose.
  A tapped item's completion is already synced to the source; a card close/restart during the
  undo window only removes the ability to undo — nothing is dropped (safe direction, Req 5.4).

## External outage (Amazon/Alexa down)

- Reads fail → sensor unavailable/stale with a banner. Writes fail → retried then surfaced.
  When connectivity returns, the next event/poll reconciles automatically. No data loss because
  the source list remains the single source of truth.

## Guardrails

- All awaited I/O has timeouts.
- One malformed item never aborts the whole projection (per-item try/normalize).
- Concurrency around grace-period/in-flight writes guarded by locks where server-side state is
  involved.
