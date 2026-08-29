---
inclusion: always
---

# Security Steering

## Credential handling

- This integration stores **no** Amazon/Alexa credentials. All authentication is owned by the
  core `alexa_devices` integration. Do not add username/password/token fields to the config
  or options flow.
- If a future need for secrets arises, store them only in the config entry (encrypted at
  rest by HA), never in the category-map store, never in files under the integration folder,
  never in the frontend.

## Secret and sensitive-data handling

- Treat the shopping list contents as **personal data**. Do not transmit item text to any
  external endpoint. All processing is local to Home Assistant.
- Diagnostics output must use `homeassistant.components.diagnostics.async_redact_data` for
  any field that could carry secrets. Provide an option to redact item text in diagnostics.

## Logging restrictions (canonical)

This is the **canonical** logging-restriction rule for the project; `python.md` and
`home-assistant.md` reference it rather than restating it (finding L-9 / S-11).

- Never log: credentials, tokens, Amazon account identifiers, or the full list contents at
  `info`/`warning`/`error`.
- Item names may appear only in `debug` logs, and only when debug logging is explicitly
  enabled.

## Input validation

- Validate every service call and config/options-flow input with voluptuous.
- Category names and keywords are user-supplied strings: strip, length-limit, and reject
  control characters. Treat them as untrusted when rendering in the card (the card must
  escape them — no `innerHTML` with raw user text).
- The frontend must not `eval` or inject unsanitized attribute data into the DOM.

## External calls / SSRF

- The integration makes **no outbound network calls** of its own. It only calls local HA
  services. Do not introduce webhooks, URL fetches, or user-supplied URLs. If any future
  feature needs a URL, it must be validated against SSRF (no internal IP ranges, https only)
  and explicitly reviewed.

## Dependencies

- Minimize dependencies; prefer stdlib. Pin exact versions in `manifest.json`. Reject
  unfamiliar or typosquat-looking package names. Run dependency vulnerability review before
  adding anything.

## Frontend

- The custom card runs in the HA frontend context. It must only call documented HA services
  and websocket APIs available to the logged-in user, honoring HA's existing auth. It must
  not embed API keys or bypass HA authentication.
