# Security Review — Alexa Shopping List Categoriser

**Reviewer:** Security Review Agent (adversarial audit)
**Date:** 2026-09-02
**Scope:** Entire repository — the `alexa_shopping_categoriser` custom Home Assistant
integration, its bundled Lovelace card, steering/planning docs, configuration, CI, and
dependencies.
**Target environment:** Single-household Home Assistant OS install (HA 2026.8.3), with the
core `alexa_devices` integration already configured. Distributed via HACS.

---

## Executive Summary

The **shipped integration and card are, on their own merits, well-built and low-risk.** The
code holds no credentials, makes no outbound network calls, validates all service and
flow input with voluptuous, renders all user-supplied text through safe DOM APIs
(`textContent`/`setText` — never `innerHTML` with user text, never `eval`), redacts personal
data in diagnostics by default (with a passing test proving it), pins its one build
dependency chain, and ships an empty `requirements` list (stdlib only). The projection is a
derived, rebuildable view — there is no second source of truth to poison, and no
Amazon/Alexa API is ever called directly. Measured against its own steering, the
integration meets its stated security posture.

**However, the review is of the entire codebase and its configuration, and there it fails.**
A **live, currently-valid Home Assistant long-lived access token is stored in plaintext** in
`.kiro/settings/mcp.json`, granting full authenticated API access to the production Home
Assistant instance at `http://homeassistant.local:8123`. I confirmed the token is live and
privileged via a read-only API status call (returned HA 2026.8.3, real location "Home", 270
loaded components). This token has an approximately **ten-year lifetime** (issued 2026-08-26,
expires 2036) and is transmitted over **plaintext HTTP**. This is a real, exploitable
credential exposure that directly contradicts the project's own security steering ("stores
**no** Amazon/Alexa credentials … never in files under the integration folder").

Mitigating context (which lowers blast radius but does **not** clear the finding): the file
is **not** committed to git and never was — `.kiro/settings/` is in `.gitignore` and the token
does not appear anywhere in git history. The exposure is therefore a **local workstation /
developer-config exposure**, not a public source-control leak. It is still a full-access
credential sitting in cleartext on disk with an excessive lifetime, and it must be rotated.

### Findings by severity

| Severity | Count |
| --- | --- |
| CRITICAL | 1 |
| HIGH | 0 |
| MEDIUM | 1 |
| LOW | 4 |
| INFORMATIONAL | 3 |

### Major risks

1. **Full-access HA token in plaintext workspace config** (SEC-001) — confirmed live, 10-year
   lifetime, plaintext-HTTP endpoint. Anyone with read access to this workstation/backup owns
   the whole Home Assistant instance.
2. Everything else is defence-in-depth or informational. No injection, no XSS, no SSRF, no
   broken authorization, no unsafe deserialization, and no vulnerable dependency was found in
   the integration or card.

### Is it safe to proceed?

The **integration code** is safe to proceed to release. The **repository as it currently
sits on disk is not**, because of the exposed credential. The blocking issue (SEC-001) is an
operational/configuration problem that is fixed by rotating the token and keeping it out of a
plaintext file — it requires **no application code change**. Once SEC-001 is remediated, the
project is GO.

---

## Security Decision

# NO-GO

**Reason:** One CRITICAL finding is open — a confirmed, live, full-access Home Assistant
long-lived access token stored in plaintext in the workspace (`.kiro/settings/mcp.json`),
over a plaintext-HTTP endpoint, with a ~10-year lifetime. A fundamental control (secret
protection at rest / least-privilege credential lifetime) is missing for that credential.

This is a **configuration/operational** blocker, not a defect in the shipped integration.
The integration and card themselves would be **GO**. Rotate the token and remove it from the
plaintext config (see P0 below); after that, this review flips to GO.

---

## Findings Summary

| ID | Severity | Area | Finding | Exploitability | Status |
| -- | -------- | ---- | ------- | -------------- | ------ |
| SEC-001 | CRITICAL | Secrets / Config | Live full-access HA long-lived token in plaintext `.kiro/settings/mcp.json` | Confirmed (token validated live via read-only API call) | Open |
| SEC-002 | MEDIUM | Transport / Config | HA MCP endpoint uses plaintext `http://` (token sent in clear) | Requires local-network position | Open |
| SEC-003 | LOW | Authorization | Integration services are admin/service-level with no finer authZ | Requires an authenticated HA user with service access | Accepted risk |
| SEC-004 | LOW | DoS / Resource | Unbounded count of categories/shops/keywords and override-map growth | Requires an authenticated user; local-only impact | Open |
| SEC-005 | LOW | Data protection | Item text (personal data) written to store and sensor attributes unredacted at rest | Requires filesystem/attribute read access | Accepted risk |
| SEC-006 | LOW | Frontend robustness | Card trusts sensor attribute shape; malformed projection could throw (availability) | Requires compromise of the sensor/attribute path | Open |
| SEC-007 | INFO | Supply chain | Bundled `www/` card is hand-copied from `dist/` (no build-time integrity link) | N/A | Open |
| SEC-008 | INFO | CI/CD | CI installs floating `homeassistant`/tooling; no pinned lockfile for the Python job | N/A | Open |
| SEC-009 | INFO | Prior review | TDA "Security Gate: PASS" did not consider the workspace credential | N/A | Open |

---

## Detailed Findings

### [SEC-001] Live full-access Home Assistant token stored in plaintext workspace config

**Severity:** CRITICAL
**Confidence:** Confirmed
**Affected Components:** `.kiro/settings/mcp.json`
**Attack Surface:** Local filesystem / any copy of the workspace (backups, sync, screen-share,
support bundle, another process on the host)

**Description**

`.kiro/settings/mcp.json` contains a Home Assistant **long-lived access token** in cleartext
inside the MCP server `env` block, alongside `HA_URL: http://homeassistant.local:8123`. The
JWT payload decodes to `iat` 2026-08-26 and `exp` 2036-08-23 — an approximately **ten-year**
validity window — and it is currently valid. HA long-lived access tokens are **not**
scoped: they act as the user who created them, so this token grants full read/write access to
the entire Home Assistant API (call any service, read any entity/state, modify config,
control every device).

I verified exploitability directly with a **read-only** status call through the configured
credential: it succeeded, returning `API running`, `Version: 2026.8.3`, `Location: Home`,
`Timezone: Europe/London`, and 270 loaded components. This is a real, privileged, live
credential — not a placeholder.

**Security Impact**

Anyone who can read this file gains complete control of the household's Home Assistant:
unlocking smart locks, disabling alarms/cameras, reading presence and location data,
manipulating the very Alexa shopping list this project targets, and pivoting to any other
integration on the instance (270 components). Because the endpoint is `http://` (see
SEC-002), the same token is also exposed to passive interception on the local network.

**Attack Scenario**

1. **Attacker capability:** read access to the workspace directory — e.g. a synced backup, a
   cloud-drive copy, a shared/temp directory, a malicious dependency or process running under
   the same user, or an over-shared support/diagnostic bundle.
2. **Entry point:** `.kiro/settings/mcp.json`, plaintext.
3. **Required conditions:** the token is unexpired (it is, until 2036) and the HA instance is
   reachable (it is, on the LAN / via the same hostname).
4. **Exploitation path:** read the token → issue authenticated calls to
   `http://homeassistant.local:8123/api/...` as the token owner.
5. **Control that should prevent it:** secrets kept out of plaintext files, short-lived and
   least-privilege credentials, TLS transport. Project steering explicitly forbids storing
   credentials in files.
6. **Why it fails:** the token is committed to a working config file in cleartext with a
   decade-long lifetime, contradicting the steering's own rule.
7. **Impact:** full compromise of the Home Assistant instance and everything it controls.
8. **Remediation:** see below.

**Evidence**

- `.kiro/settings/mcp.json` → `mcpServers.homeassistant.env.HA_TOKEN` (a JWT beginning
  `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9…`) and `HA_URL: http://homeassistant.local:8123`.
- Decoded JWT payload: `{"iss":"…","iat":1787779728,"exp":2103139728}` → issued
  2026-08-26, expires 2036-08-23.
- Live read-only verification: HA status API returned version 2026.8.3, location "Home", 270
  components.
- Contradicts `.kiro/steering/security.md`: "stores **no** Amazon/Alexa credentials … never
  in files under the integration folder, never in the frontend" and "store them only in the
  config entry (encrypted at rest by HA)".
- **Not** in source control: `git ls-files` does not track `.kiro/settings/mcp.json`
  (`.gitignore` excludes `.kiro/settings/`), and a history search for the token string
  returned nothing. Blast radius is local, not public.

**Root Cause**

An operational MCP configuration convenience (embedding a static long-lived token so the HA
MCP server can talk to the live instance) placed a full-privilege, long-lived secret into a
plaintext workspace file. Compounded by an excessive token lifetime and a non-TLS endpoint.

**Recommended Remediation** (P0)

1. **Rotate/revoke the token immediately** in Home Assistant (Profile → Long-Lived Access
   Tokens → delete the exposed one). Assume it is compromised.
2. Do **not** store the replacement in a plaintext file. Prefer an environment variable
   injected at runtime, an OS keychain/secret manager, or a machine-local secrets store that
   the MCP launcher reads — never a file that travels with the workspace or backups.
3. Issue the replacement with the **shortest practical lifetime** and rotate on a schedule;
   avoid decade-long tokens.
4. Confirm `.kiro/settings/` remains git-ignored (it is) and audit any backups/sync targets
   that may already hold the old token; treat those copies as compromised until the token is
   revoked.
5. Move the MCP endpoint to HTTPS (SEC-002).

**Regression Test**

- Add a repository hygiene check (pre-commit hook or CI secret-scan such as `gitleaks`/
  `detect-secrets`) that fails on JWT-shaped strings and on `HA_TOKEN=` assignments anywhere
  in the tree, including ignored-but-present config paths that get bundled into support
  archives. Verify `.kiro/settings/` is never added to git.
- Manually verify the old token returns HTTP 401 after rotation.

**Status:** Open (blocking)

---

### [SEC-002] HA MCP endpoint configured over plaintext HTTP

**Severity:** MEDIUM
**Confidence:** Confirmed
**Affected Components:** `.kiro/settings/mcp.json` (`HA_URL: http://homeassistant.local:8123`)
**Attack Surface:** Local network (LAN)

**Description**

The MCP server is pointed at `http://homeassistant.local:8123`. Every request carries the
long-lived bearer token from SEC-001 in the clear. A local-network adversary (ARP spoofing,
rogue AP, compromised router, shared Wi-Fi) can passively capture the token or tamper with
responses.

**Security Impact**

Token disclosure to a network eavesdropper → same full-compromise impact as SEC-001, plus
response tampering (feeding false state to the MCP client).

**Attack Scenario**

LAN-positioned attacker sniffs the plaintext `Authorization: Bearer …` header on any MCP call
and replays it against the API.

**Evidence**

`HA_URL` scheme is `http://` in `.kiro/settings/mcp.json`.

**Root Cause**

Development convenience over an unencrypted local endpoint.

**Recommended Remediation** (P1)

Use HTTPS for the HA endpoint (HA supports TLS; or reach it via a trusted reverse proxy).
Combine with SEC-001's short-lived token so any intercepted credential expires quickly.

**Regression Test**

Config-lint check that rejects `http://` for `HA_URL` (allow only `https://` or a documented
loopback exception).

**Status:** Open

---

### [SEC-003] Integration services have no authorization granularity beyond HA's own gate

**Severity:** LOW
**Confidence:** Confirmed
**Affected Components:** `services.py` (all nine services), `config_flow.py`

**Description**

The integration registers services (`recategorise_item`, `add_category`, `edit_category`,
`delete_category`, `assign_shop`, `add_shop`, `edit_shop`, `delete_shop`, `reload_maps`) that
mutate the shared category/shop map. They rely entirely on Home Assistant's own
authentication/authorization for who may call services — there is no per-user scoping,
ownership, or extra check inside the integration.

Adversarial framing (no creds / low-priv account / other-user resources): a caller with **no**
HA session cannot reach these at all (HA gates the service and websocket APIs). A caller who
**is** an authenticated HA user with service-call ability can invoke them. For a
single-household power-user product (the stated primary user), this is the intended and
idiomatic HA trust model — services are the standard admin surface and are not object-scoped
resources. There is no IDOR/BOLA here because there are no per-user objects; the map is a
single shared config-entry-scoped resource.

**Security Impact**

Minimal in the intended single-household deployment. In a multi-user HA install, any user
permitted to call services could reshape another household member's categorisation. Non-
destructive by design (`delete_category`/`delete_shop` reassign, never delete items).

**Evidence**

`services.py` `_resolve_coordinator` selects the entry by optional `entry_id` or the sole
entry; handlers mutate `category_map` with no caller-identity check. This is consistent with
the steering ("config-entry-scoped services … not entity services") and is the documented
design.

**Root Cause**

By design — HA services inherit HA's auth model; the product is single-user.

**Recommended Remediation** (P3, defence-in-depth)

Document that these services inherit HA's service-call authorization and are intended for the
account owner. No code change needed for the stated deployment. If a multi-user variant is
ever shipped, revisit.

**Status:** Accepted risk (documented)

---

### [SEC-004] Unbounded growth of categories, shops, keywords, and learned overrides

**Severity:** LOW
**Confidence:** Confirmed
**Affected Components:** `services.py`, `store.py`, `categoriser.py`

**Description**

Individual names and keywords are length-limited (`MAX_NAME_LENGTH`/`MAX_KEYWORD_LENGTH` =
64) and control characters are rejected — good. But there is **no cap on the number** of
categories, shops, keywords per entity, or entries in the learned `overrides` /
`shop_overrides` maps. `categorise`/`resolve_shop` iterate every category × keyword and every
shop × keyword per item (O(items × categories × keywords)); the store rewrites the whole map
on every mutation. An authenticated user (or a runaway automation) repeatedly calling
`add_category`/`add_shop`/`assign_shop`/`recategorise_item` could inflate the map and slow
per-item categorisation and store writes.

**Security Impact**

Local, self-inflicted denial-of-service / performance degradation only; requires an
authenticated caller. No remote or cross-tenant impact. Bounded further by the debounce and
15-minute safety poll.

**Attack Scenario**

Authenticated user scripts thousands of `add_category` + distinct `assign_shop` calls →
projection recompute and store serialization grow linearly, degrading coordinator refresh.

**Evidence**

- `services.py`: `_handle_add_category`/`_handle_add_shop` append without a count ceiling;
  `_handle_assign_shop`/`_handle_recategorise_item` insert override keys without a cap.
- `categoriser.py`: nested loops over categories/shops × keywords per item.
- `store.py`: `_serialize` rewrites the entire map each save.

**Root Cause**

No aggregate-size limits; acceptable for a household but not hardened.

**Recommended Remediation** (P2)

Add generous ceilings (e.g. max categories/shops, max keywords each, max override entries)
raising `ServiceValidationError` past the limit; consider pruning override keys that no
longer resolve. Keeps the household case unaffected while bounding worst case.

**Regression Test**

Service test asserting the (N+1)th add/override beyond the ceiling raises
`ServiceValidationError`.

**Status:** Open

---

### [SEC-005] Personal data (item text) stored unredacted at rest and in sensor attributes

**Severity:** LOW
**Confidence:** Confirmed
**Affected Components:** `sensor.py` (`extra_state_attributes`), coordinator/projection,
learned-override keys in `store.py`

**Description**

The steering treats shopping-list item text as personal data. Diagnostics redaction is
correctly implemented and gated by `redact_items_in_diagnostics` (default true), and a test
proves the literal item text does not leak into a default diagnostics dump. However, item
text legitimately appears **unredacted** in (a) the sensor's `extra_state_attributes`
(`shop_groups[...].items[...].name`) — necessary for the card to render — and (b) the
`overrides`/`shop_overrides` keys in the Store (normalized item text as map keys). These are
protected only by HA's own auth (attributes) and filesystem permissions (store).

**Security Impact**

Item text is low-sensitivity personal data (a vegan household's grocery list). Exposure
requires an authenticated HA user (to read attributes) or filesystem access (to read the
store) — both of which already imply broader access. The recorder-exclusion guidance further
limits long-term retention. Impact is limited.

**Evidence**

- `sensor.py` returns `dict(self.coordinator.data)` including item names.
- `store.py` `_serialize` persists `overrides`/`shop_overrides` whose **keys** are normalized
  item text.
- Contrast with diagnostics, which is properly redacted (`diagnostics.py`, `_ITEM_TEXT_KEYS`).

**Root Cause**

Inherent to the feature: the card needs names to render, and learning is keyed by item text.
This is acceptable and matches the "all processing local" data-locality principle.

**Recommended Remediation** (P3)

Confirm the sensor is excluded from the recorder as the steering directs (prevents long-term
history retention of item names). Document that the Store contains item-text keys so operators
protect `.storage/` with normal HA filesystem hygiene. No functional change required.

**Status:** Accepted risk (documented)

---

### [SEC-006] Card trusts the sensor attribute shape; malformed projection can throw

**Severity:** LOW
**Confidence:** Potential / Requires validation
**Affected Components:** `www/alexa-shopping-categoriser-card.js` (`set hass`, `_render`,
`_renderShop`/`_renderCategory`/`_renderItem`)

**Description**

The card iterates `state.attributes.shop_groups`, `.categories`, `.items` with sensible
`|| []` guards and reads `item.uid`/`item.name`/`item.checked`. It honours
`attributes_version` and degrades gracefully when the version is higher than supported. If the
sensor ever emitted a structurally malformed projection (wrong types, non-array where an array
is expected in a spot without a guard), the render could throw. Since the backend is the sole
producer of these attributes and it builds them from a typed `TypedDict` projection, this is
not currently reachable by an external attacker — it is a robustness/defence-in-depth note,
not an injection vector. Critically, all text is written via `setText`/`textContent`, so even
hostile strings cannot cause XSS.

**Security Impact**

At worst a card render error (UI availability), not code execution or data exposure. No XSS
(safe DOM writes throughout).

**Evidence**

`_render`/`_renderShop`/`_renderCategory` use `|| []` fallbacks; `_renderItem` reads item
fields directly. `setText` is used for every user-derived string.

**Root Cause**

The card assumes a well-formed contract from a trusted backend (reasonable), without total
defensive type-checking.

**Recommended Remediation** (P3)

Optionally wrap the top of `_render` in a try/catch that surfaces a friendly "could not
render" message, and type-guard array reads. Low priority given the backend is the only
producer and output encoding is already safe.

**Status:** Requires validation (no exploit path found; robustness only)

---

### [SEC-007] Bundled `www/` card is hand-copied from the build output (no integrity link)

**Severity:** INFORMATIONAL
**Confidence:** Confirmed
**Affected Components:** `custom_components/.../www/alexa-shopping-categoriser-card.js`,
`frontend/alexa-shopping-categoriser-card/dist/…`

**Description**

The integration serves `www/alexa-shopping-categoriser-card.js`. I confirmed it is currently
**byte-identical** to the Rollup `dist/` output, which is good. But the copy is manual —
there is no CI step asserting `www/` equals a fresh build of `src/`. Drift could ship a stale
or divergent asset, and a tampered `www/` file would be served to the browser with the user's
session.

**Security Impact**

Supply-chain/integrity hygiene. No current issue (files match). Risk is future drift or
undetected tampering of the served asset.

**Evidence**

`diff` of `www/…js` vs `dist/…js` → identical. `frontend.py` serves the `www/` copy with a
fixed filename (`StaticPathConfig` on `/{DOMAIN}/{CARD_FILENAME}` — no path traversal, good).

**Root Cause**

Manual copy step between build output and the served asset.

**Recommended Remediation** (P2)

Add a CI check that rebuilds the card and fails if `www/…js` differs from `dist/…js` (or serve
`dist/` directly). This binds the served bytes to reviewed source.

**Status:** Open

---

### [SEC-008] CI installs floating Home Assistant and tooling versions

**Severity:** INFORMATIONAL
**Confidence:** Confirmed
**Affected Components:** `.github/workflows/ci.yml`

**Description**

The backend CI job runs `pip install homeassistant pytest-homeassistant-custom-component ruff
mypy pytest-cov` with no version pins and no lockfile. GitHub Actions are pinned to major tags
(`actions/checkout@v4`, `setup-python@v5`, `setup-node@v4`) rather than commit SHAs. The
frontend job uses `npm ci` against a committed `package-lock.json` (good) with pinned
dev-dependencies (`rollup 4.63.1`, `eslint 9.39.5`, `@rollup/plugin-node-resolve 16.0.0`).

**Security Impact**

Build reproducibility / supply-chain surface. A malicious or broken upstream release of an
unpinned Python tool could affect CI. Impact is limited to the CI runner (no deploy step, no
secrets in the workflow). No production runtime dependency is affected — the shipped
integration has `requirements: []`.

**Evidence**

`ci.yml` backend `Install dependencies` step; action tags are floating majors.

**Root Cause**

Convenience; acceptable for a hobby integration but not hardened.

**Recommended Remediation** (P3)

Pin the Python CI toolchain (constraints file or explicit versions) and consider pinning
Actions to commit SHAs. Keep using `npm ci` with the committed lockfile.

**Status:** Open

---

### [SEC-009] Prior "Security Gate: PASS" did not consider the workspace credential

**Severity:** INFORMATIONAL
**Confidence:** Confirmed
**Affected Components:** `docs/plans/reviews/go-no-go/tda-review.md`

**Description**

The earlier TDA review records "Security Gate: **PASS**", reasoning that the integration owns
no credentials and stores no secrets. That assessment is accurate **for the shipped
integration's design and code**, and my review independently confirms those specific claims
(no secrets in code, no outbound calls, safe rendering, redacted diagnostics, input
validation). It is **incomplete** because it scoped out the workspace configuration, where the
live HA token actually lives (SEC-001). This is a scope gap, not an incorrect code claim.

**Security Impact**

None directly; noted so the security decision reflects the full repository, not just the
integration.

**Recommended Remediation**

Treat the workspace `.kiro/settings/mcp.json` credential as in-scope for security going
forward; resolve SEC-001. The integration-level PASS claims stand.

**Status:** Open (challenge recorded)

---

## Validation of Existing Security Claims (challenged)

Each claim from `docs/plans/10-...md` and the TDA review, checked against the implementation:

- **"No credentials / no secrets in the integration."** VALID for shipped code — confirmed by
  a repo-wide secret scan (only `.kiro/settings/mcp.json` contains a real secret, which is
  MCP tooling config, not integration code). The steering rule is nonetheless **violated at
  the workspace level** (SEC-001).
- **"No outbound network calls / no SSRF / no webhooks."** VALID. The integration only calls
  local `todo.*` services and `homeassistant.*`; `frontend.py` registers a static path and one
  `add_extra_js_url`. No `requests`/`aiohttp`/URL fetch anywhere.
- **"Input validated with voluptuous; names stripped, length-limited, control chars
  rejected."** VALID. `services.py` `_validate_name` rejects empty, >64 chars, and any
  `ord < 32`; keyword schema enforces per-item length; flows use `vol.Range`/`cv.boolean`.
- **"Card renders user text safely (no innerHTML with user text, no eval)."** VALID. Every
  user-derived string goes through `setText`/`textContent`. `innerHTML` is used once to reset
  the shadow root to `""` (constant, safe). No `eval`, no `Function`, no template injection.
- **"Diagnostics redacted by default."** VALID and **tested** (`test_diagnostics.py` asserts
  the literal item text is absent by default and present when the option is disabled).
- **"Static asset serving is safe."** VALID. Fixed URL prefix and fixed filename — no user
  input reaches the path, so no path traversal.
- **"Dependencies stdlib-only / pinned."** VALID. `manifest.json` `requirements: []`; frontend
  dev-deps pinned with a committed lockfile.

---

## Threat-Boundary Review

- **Frontend → HA services:** card calls only documented `todo.*` and the integration's own
  services as the logged-in user; HA enforces auth. No bespoke endpoints. OK.
- **Integration → source `todo` entity:** all reads/writes via public `todo.get_items` /
  `todo.update_item` / `todo.add_item`, by `uid`. No direct Amazon/Alexa API. Matches
  architecture steering. OK.
- **Integration → filesystem (Store):** uses the HA `Store` helper (no raw file writes);
  stores only maps + overrides (item-text keys — SEC-005). OK.
- **MCP client → HA API:** **this is the weak boundary** — plaintext token over HTTP
  (SEC-001/SEC-002). This is tooling, not the shipped product, but it is the real exposure.
- **CI → environment:** no deploy, no secrets in the workflow; floating tool versions
  (SEC-008). Low risk.

---

## Remediation Priorities

### P0 — Immediate (blocks GO)

- **SEC-001:** Revoke/rotate the exposed HA long-lived token now; stop storing it in a
  plaintext workspace file; reissue short-lived and least-privilege; audit backups/sync copies.

### P1 — High priority (before production/daily use)

- **SEC-002:** Move the MCP HA endpoint to HTTPS so the bearer token is not sent in clear.

### P2 — Medium priority (normal hardening)

- **SEC-004:** Add aggregate ceilings for categories/shops/keywords/override entries.
- **SEC-007:** CI check that the served `www/` card matches a fresh build of `src/`.

### P3 — Defence in depth

- **SEC-003:** Document the service authZ model (owner-intended, HA-gated).
- **SEC-005:** Confirm recorder exclusion; document that the Store holds item-text keys.
- **SEC-006:** Wrap card render in a friendly try/catch and type-guard array reads.
- **SEC-008:** Pin the Python CI toolchain (and optionally Actions to SHAs).

---

## Security Coverage Matrix

| Security Area | Reviewed | Issues Found | Confidence | Notes |
| ------------- | -------- | ------------ | ---------- | ----- |
| Authentication | Yes | No | High | Integration owns none; relies on HA + `alexa_devices`. SEC-001 is a token-handling issue, not an auth-logic flaw. |
| Authorisation | Yes | Low (SEC-003) | High | HA-gated services; no per-user objects, so no IDOR/BOLA. Single-household model. |
| Session management | Yes | No | High | No sessions owned; card uses HA session. |
| Input validation | Yes | No | High | voluptuous everywhere; names stripped/length-limited/control-char-rejected. |
| Injection (SQL/NoSQL/OS/cmd/template/log) | Yes | No | High | No SQL/DB, no shell/`os.system`/`subprocess`, no template eval, no user-controlled log format strings. |
| File handling | Yes | No | High | HA `Store` helper only; static serve uses a fixed filename (no traversal). |
| SSRF | Yes | No | High | No outbound calls, no user URLs, no webhooks. |
| CSRF | Yes | No | Medium | Actions go through HA's authenticated service/WS APIs; no custom state-changing HTTP endpoint. |
| XSS | Yes | No | High | `setText`/`textContent` for all user text; no `innerHTML` with user data; no `eval`. |
| Secrets | Yes | **CRITICAL (SEC-001)** | Confirmed | Live full-access HA token in plaintext `.kiro/settings/mcp.json`. Not in git, but present on disk. |
| Cryptography | Yes | No | Medium | No custom crypto; token is HA-issued. SEC-002 is transport (plaintext HTTP). |
| Dependencies | Yes | No | High | Runtime `requirements: []`; frontend dev-deps pinned + lockfile. |
| Supply chain | Yes | Info (SEC-007/008) | Medium | `www/`↔`dist/` currently identical but no CI integrity link; floating Python CI tools. |
| API security | Yes | No | High | No bespoke API; only documented HA services. |
| Infrastructure | Yes | Medium (SEC-002) | High | Plaintext HTTP endpoint for the MCP/HA link. |
| Containers | N/A | — | — | No container/Dockerfile in scope. |
| CI/CD | Yes | Info (SEC-008) | High | No deploy step, no workflow secrets; unpinned Python toolchain. |
| Logging | Yes | No | High | Item text at `debug` only per canonical rule; no credentials logged (none held). |
| Privacy / data protection | Yes | Low (SEC-005) | High | Item text is local personal data; diagnostics redacted by default (tested). |
| Error handling | Yes | No | High | Narrow excepts; low-level errors wrapped as `HomeAssistantError`/`UpdateFailed`; degrades to `Uncategorised`. |
| DoS / resource exhaustion | Yes | Low (SEC-004) | Medium | Unbounded map/keyword/override growth; local, authenticated-only impact. |
| Business logic | Yes | No | High | Derived projection, rebuildable; deletes reassign (never drop items); vegan boundary enforced by whole-word matching. |
| Configuration | Yes | **CRITICAL (SEC-001)** + Medium (SEC-002) | Confirmed | Workspace MCP config is where the real risk lives. |
| Monitoring | Yes | No | Medium | Repair issue on missing source entity; standard HA logbook/history for actions. |

---

## Final Review Checklist

1. **All steering files reviewed** — Yes: `security.md`, `product.md`, `architecture.md`,
   `home-assistant.md`, `frontend.md`, `python.md`, `testing.md`, `documentation.md`.
2. **Relevant documentation/plans reviewed** — Yes: `docs/plans/10` (logging/diagnostics/
   security), the go-no-go `tda-review.md` and `implementation-deviations.md`; the rest of
   `docs/plans/` was indexed and spot-read where security-relevant. The `docs/plans/` set is
   large; I read the security-bearing documents in full and sampled the others — see
   limitations below.
3. **Entire source tree considered** — Yes: every Python module under
   `custom_components/alexa_shopping_categoriser/`, the bundled `www/` card, and the
   `frontend/…/src/` + `dist/` sources.
4. **Configuration and deployment files reviewed** — Yes: `manifest.json`, `hacs.json`,
   `.gitignore`, `pyproject.toml`, `.github/workflows/ci.yml`, `.kiro/settings/mcp.json`,
   `services.yaml`.
5. **Dependencies reviewed** — Yes: runtime (`requirements: []`), frontend `package.json` +
   lockfile, CI-installed tooling.
6. **Existing controls validated, not assumed** — Yes: diagnostics redaction confirmed by
   reading the code **and** the passing test; token liveness confirmed by a read-only API
   call; `www/`↔`dist/` equality confirmed by `diff`; secret scan run repo-wide; git tracking/
   history checked for the token.
7. **False positives checked** — Yes: SEC-006 explicitly downgraded to "requires validation"
   (no reachable exploit); SEC-003/005 marked accepted risk with rationale; XSS ruled out by
   confirming safe DOM writes rather than assuming.
8. **Every CRITICAL/HIGH has clear remediation** — Yes: SEC-001 has a concrete P0 plan (no
   HIGH findings).
9. **Explicit decision provided** — Yes: **NO-GO** (until SEC-001 is remediated; the shipped
   integration alone would be GO).
10. **No unreviewed items claimed as reviewed** — See limitations.

### Limitations / not exhaustively reviewed

- The `docs/plans/` directory is extensive (00–15 plus multiple review sub-folders). I read
  the security-relevant documents in full and sampled the remainder; a line-by-line read of
  every planning document was not performed as it does not affect the security posture.
- The Python backend tests were reviewed for **security coverage** (diagnostics redaction was
  read in full); I did not execute the full test suite as part of this review.
- I intentionally performed only a **read-only** HA API call to validate SEC-001; I did not
  exercise any state-changing capability of the exposed token.
