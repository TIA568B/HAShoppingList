---
inclusion: always
---

# Release & Deployment Steering

How code in this repo actually reaches a running Home Assistant instance. This is a
**canonical** rule; other steering files reference it rather than restating it.

## Ground truth (do not re-assume)

- The developer machine is **not** the Home Assistant box. The workspace lives at
  `/Users/dc/hashoppinglist`; the running HA instance is remote (HA OS) and serves the
  integration from `/config/custom_components/alexa_shopping_categoriser/`. Editing files in
  the workspace does **not** change what HA runs.
- This integration is distributed via **HACS**. HACS installs a repository integration from
  its **GitHub releases (git tags)** — not from the `main` branch (branch tracking is a
  non-default per-install setting we do not rely on). No new release => HACS keeps serving
  the old code, even on "redownload".
- The GitHub mirror HACS resolves is `TIA568B/HAShoppingList`. The repo dual-pushes to
  Bitbucket (`origin`) and GitHub.

## The only supported way to ship a change

A change is not "done" until it is released. Never tell the user a runtime-visible change is
live after only editing the workspace — it is not on their HA box yet.

For every user-visible change (new panel, service, card behaviour, bug fix that affects
runtime):

1. Bump the version in **`custom_components/alexa_shopping_categoriser/manifest.json`**
   (the single source of truth HA/HACS reads). Follow semver:
   - patch (`0.2.0 -> 0.2.1`) for fixes,
   - minor (`0.2.0 -> 0.3.0`) for new features,
   - major for breaking contract changes.
2. Keep the version in step across **`pyproject.toml`** and add a dated entry to
   **`CHANGELOG.md`** (Keep a Changelog format) in the same change set.
3. Commit (do not release from a dirty tree — `scripts/release.sh` refuses).
4. Run **`./scripts/release.sh`**. It reads the manifest version, pushes `main`, creates and
   pushes the matching `vX.Y.Z` tag, and publishes the GitHub release so HACS can see it.
5. Tell the user to update via HACS (Redownload/Update → pick the new version), restart HA,
   and hard-refresh the browser.

`manifest.json` version, the git tag (`vX.Y.Z`), and the GitHub release must always agree.
A change that does not increase `manifest.json` version will **not** be recognised as an
update, even if a new tag is cut.

## What the agent may and may not do

- The agent **cannot** deploy: there is no `/config` on this machine, and the Home Assistant
  MCP manages entities/automations only, not the HA filesystem. Do not claim to have deployed.
- Cutting a release **publishes to GitHub**. Treat `./scripts/release.sh` (and any
  `git push` / tag / `gh release` step) as a higher-risk action: prepare the version bump,
  changelog, and commit, then get explicit user confirmation before running the release.
- The agent may edit files, bump versions, update the changelog, run tests/lint/mypy, and
  stage a commit locally without special permission.

## Verifying a deployed change (use the HA MCP)

The workspace and the running instance drift, so verify against reality:

- Turn on debug logging for the integration and look for the specific log line the new code
  emits (e.g. panel registration logs `Registered sidebar panel at /...`). Absence of *any*
  expected log line usually means the deployed copy is stale — the release/redownload did not
  land, not that the code is wrong.
- Use the HA MCP (`ha_status`, `ha_get_entity`, `ha_search_entities`, logbook/history) to
  confirm entities, attributes, and state on the live box.
- Distinguish **absent** (panel/entity not registered => deploy or registration problem) from
  **blank/broken** (registered but errors at runtime => check the browser console for frontend
  issues). They point at different root causes.

## Cross-references

- Changelog/migration mechanics and doc-update triggers: `documentation.md`.
- Manifest field requirements (`version` mandatory for custom components, dependency rules):
  `home-assistant.md`.
