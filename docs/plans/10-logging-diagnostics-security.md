# 10 — Logging, Diagnostics & Security

## Logging strategy

- Module logger: `_LOGGER = logging.getLogger(__name__)`.

| Level | Used for |
|-------|----------|
| debug | Per-item categorization decisions, sync payloads, coordinator refresh detail, item text |
| info | Setup/unload milestones (sparingly) |
| warning | Recoverable sync failures, retries, source entity temporarily unavailable |
| error | Exhausted retries, corrupt store, unexpected exceptions |

- **Item text may appear only at `debug`.** Never log the full list contents at info+.
- Never log credentials/tokens/account ids (we hold none, but the rule stands for any borrowed
  context).

## Diagnostics

- `async_get_config_entry_diagnostics` returns a redacted structure:
  - `entry`: data + options, passed through `async_redact_data` (no secrets exist, but future-proof).
  - `source_entity_id`, `last_update_success`, `last_synced`.
  - `category_count`, per-category **counts only** (not contents) by default.
  - `override_count`.
  - `shop_count`, per-shop **counts only**, and `shop_override_count` (Req 7 dimension — finding
    F4-4). Counts only by default; redaction unchanged.
  - Item text included **only if** `redact_items_in_diagnostics` option is false.
- Goal: a diagnostics download is safe to paste into a bug report by default.

## Security review

| Area | Assessment / mitigation |
|------|-------------------------|
| Authentication | None owned. Alexa auth lives in `alexa_devices`. No new auth surface. |
| Credential storage | None. Do not add credential fields (see security steering). |
| Secret handling | No secrets. Store holds only categories/keywords/overrides. |
| Authorisation | Card acts as the logged-in HA user; writes go through HA services honoring HA auth. No bypass/elevation. |
| Input validation | voluptuous on all services + config/options; category names/keywords stripped, length-limited, control-char rejected. |
| Output encoding | Card must render user-supplied category/keyword/item text via safe DOM APIs (no raw `innerHTML`), preventing stored-XSS via item names. |
| SSRF / unsafe URLs | No outbound calls, no user URLs, no webhooks. Nothing to exploit. |
| Dependencies | stdlib only for v1; any addition pinned + reviewed for typosquatting/vulns. |
| Logging exposure | Item text at debug only; diagnostics redacted by default. |
| Data locality | All processing local; personal list contents never sent off-device. |
| API key rotation | N/A (no keys held). |

## Residual risks

- Best-effort vegan filtering can mis-handle hidden animal ingredients (accepted, NFR4;
  mitigated by routing ambiguous items to `Uncategorized`).
- If the user enables item text in diagnostics, that download contains personal data — clearly
  labelled; default is redacted.
