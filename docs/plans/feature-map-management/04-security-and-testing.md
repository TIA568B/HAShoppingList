# 04 — Security & Testing (this feature)

References the canonical rules in `security.md` and `testing.md`; only the deltas for this
feature are listed here.

## Security

- **Input validation stays server-side.** The panels are convenience; the services remain the
  enforcement point (non-empty, unique case-insensitive, length-limited, control-char-free,
  reserved-name `Uncategorised`/`No Preference` rejected). No new validation surface is created
  that could be bypassed.
- **XSS:** category/shop names and keywords are user data and are rendered via safe DOM APIs
  (textContent / `setText`) only. No `innerHTML` with raw text; no `eval`. New panel code must
  follow the card's existing pattern.
- **`default_map.json` is trusted, shipped data**, not user input — but it is still parsed
  defensively (tolerate missing keys, validate types) so a malformed file degrades to a safe
  default rather than crashing setup. It contains **no** secrets and **no** item text (only
  taxonomy/shops), so no redaction concerns.
- **Reload is a destructive action** → must be confirmed in the UI and logged at `info`
  (without item text). Item text stays out of `info`/`warning`/`error` logs (canonical logging
  rule).
- No new outbound calls, webhooks, or URLs. No credentials involved. SSRF surface unchanged
  (still none).

## Testing additions

Backend:
- **Default JSON loader:** loads `default_map.json`, parses categories/shops; tolerates a
  missing/partial/malformed file (falls back safely); parity test that the JSON seed matches
  the intended taxonomy (guards accidental edits).
- **Upgrade migration:** a store at the pre-feature `schema_version` re-seeds categories/shops
  from the JSON on load, persists, bumps `schema_version`; learned overrides preserved (or
  wiped — per OQ-A); migration is idempotent (running twice is a no-op).
- **`reload_defaults` service:** replaces categories/shops from the JSON + recomputes; keeps
  overrides; self-heals overrides pointing at removed categories/shops; distinct from
  `reload_maps`; validates entry targeting; raises cleanly if the JSON is missing.
- **Recompute-on-edit (regression):** each panel-driven service still triggers a recompute so
  the projection changes without a manual reload (guards the "instant update" requirement).

Frontend (card):
- Category panel: add/rename/delete/edit-keywords render and dispatch the correct service with
  the correct payload; inline error surfaced on `ServiceValidationError`.
- Shop panel: same, plus common-word add warning surfaced.
- Reload button: shows a confirm dialog and only calls `reload_defaults` on confirm.
- XSS: a category/shop name containing `<img onerror>` is rendered as text, not parsed.

Coverage gates unchanged (categoriser 100%; integration ≥90%). New service/migration branches
must be exercised.
