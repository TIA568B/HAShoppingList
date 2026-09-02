# Contributing

## Repository layout: Bitbucket primary, GitHub mirror

This project is **developed on Bitbucket** and **mirrored to GitHub** so it can be
distributed through HACS (HACS only resolves GitHub repositories).

| Purpose | Remote | URL |
| --- | --- | --- |
| Primary development (fetch + push) | `origin` (Bitbucket) | `git@bitbucket.org:tia568b/hashoppinglist.git` |
| HACS-facing mirror (push only) | `origin` (GitHub) + `github` | `git@github.com:TIA568B/HAShoppingList.git` |

`origin` is configured as a **dual-push** remote: it fetches from Bitbucket and pushes to
**both** Bitbucket and GitHub. A single `git push` keeps them in sync.

```
# One-time setup (already done on the maintainer's machine):
git remote set-url --add --push origin git@bitbucket.org:tia568b/hashoppinglist.git
git remote set-url --add --push origin git@github.com:TIA568B/HAShoppingList.git
```

Verify with `git remote -v` — `origin` should list one fetch URL (Bitbucket) and two push
URLs (Bitbucket + GitHub).

### Day-to-day sync

```
git push            # or: git push origin main — updates Bitbucket + GitHub together
```

Notes and caveats:

- **Fetch/pull is Bitbucket only.** The mirror is one-way; never commit directly on GitHub.
- **If a push is rejected on one side**, git may update the other and leave them briefly
  diverged. Re-push once resolved.
- **Tags and GitHub Releases do not auto-sync from Bitbucket.** Use the release script below.

## Cutting a HACS release

HACS reads **GitHub Releases**, and the release tag must match the `version` field in
`custom_components/alexa_shopping_categoriser/manifest.json`.

Use the helper script — it derives the tag from the manifest, guards against a dirty tree /
wrong branch / duplicate tag, pushes to both remotes, and publishes the GitHub release:

```
# 1. Bump "version" in custom_components/alexa_shopping_categoriser/manifest.json
# 2. Commit and push the bump
git commit -am "Bump version to X.Y.Z"
git push

# 3. Preview, then release
DRY_RUN=1 ./scripts/release.sh   # prints what it would do, changes nothing
./scripts/release.sh             # tags, pushes to both remotes, publishes the release
```

Prerequisites: the [`gh` CLI](https://cli.github.com/) installed and authenticated
(`gh auth login`).

To publish a release manually instead: create the tag, push it, then on github.com go to
**Releases → Draft a new release**, pick the tag, and publish.

## Local development

Match the checks that CI (`.github/workflows/ci.yml`) runs.

### Backend (Python 3.13)

```
pip install homeassistant pytest-homeassistant-custom-component ruff mypy pytest-cov

ruff check custom_components tests
ruff format --check custom_components tests
mypy custom_components/alexa_shopping_categoriser
pytest tests/ --cov=custom_components.alexa_shopping_categoriser --cov-fail-under=90
```

The pure `categoriser` module has a **100% coverage gate**:

```
pytest tests/test_categoriser.py \
  --cov=custom_components.alexa_shopping_categoriser.categoriser \
  --cov-fail-under=100
```

### Frontend card (Node 22)

```
cd frontend/alexa-shopping-categoriser-card
npm ci
npm test
npm run build
```

## Before opening a pull request

- Run the backend and frontend checks above; they must pass (CI enforces them).
- Update docs in the **same change set** as the code when you touch a documented contract:
  the sensor attribute schema or service signatures (`docs/plans/06`), config/options fields
  (README), or the category taxonomy / vegan rules (`product` steering + README).
- Add a `CHANGELOG.md` entry. Any config-entry or stored-data schema change also needs an
  `async_migrate_entry` note and a migration test.
