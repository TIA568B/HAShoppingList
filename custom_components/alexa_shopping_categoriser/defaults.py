"""Default vegan taxonomy and default shops, loaded from the shipped ``default_map.json``.

The seed data lives in ``default_map.json`` (data, not code) so it can be updated in a
release without touching Python, and re-applied via the upgrade migration and the
``reload_defaults`` service (see docs/plans/feature-map-management/). This module is a thin,
defensive loader: the JSON is read+parsed once at import (off the event loop) and cached; a
missing or malformed file degrades to a minimal safe fallback rather than crashing setup.

No Home Assistant import — kept pure so it is unit-testable standalone.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .models import Category, Shop

_LOGGER = logging.getLogger(__name__)

_DEFAULT_MAP_PATH = Path(__file__).parent / "default_map.json"

# Minimal, vegan-safe fallback used only if the shipped JSON is missing/unreadable. It must
# never block setup; the real seed is the JSON. Kept intentionally small.
_FALLBACK: dict[str, Any] = {
    "seed_version": 0,
    "categories": [
        {"name": "Fruit & Veg", "keywords": ["apple", "banana", "carrot"]},
        {"name": "Milk", "keywords": ["milk", "oat milk"]},
        {"name": "Chilled", "keywords": ["cheese", "yogurt", "butter", "tofu"]},
        {"name": "Fake Meat", "keywords": ["sausages", "bacon", "mince"]},
        {"name": "Household", "keywords": ["toilet roll"]},
    ],
    "shops": [
        {"name": "Aldi", "keywords": ["milk"]},
        {"name": "Asda", "keywords": ["clothes"]},
        {"name": "Tesco", "keywords": []},
    ],
}


def _load_raw() -> dict[str, Any]:
    """Read and parse the shipped default map, falling back safely on any error."""
    try:
        with _DEFAULT_MAP_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as err:
        _LOGGER.warning(
            "Could not read %s (%s); using the built-in fallback default map.",
            _DEFAULT_MAP_PATH.name,
            err,
        )
        return _FALLBACK

    if not isinstance(data, dict):
        _LOGGER.warning("%s is not a JSON object; using fallback.", _DEFAULT_MAP_PATH.name)
        return _FALLBACK
    return data


# Parse once at import time (import runs off the event loop in HA), then hand out copies.
_RAW: dict[str, Any] = _load_raw()


def _coerce_categories(raw: Any) -> list[Category]:
    if not isinstance(raw, list):
        return [
            Category(name=c["name"], keywords=list(c["keywords"])) for c in _FALLBACK["categories"]
        ]
    result: list[Category] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        keywords = entry.get("keywords", [])
        kw = [k for k in keywords if isinstance(k, str)] if isinstance(keywords, list) else []
        result.append(Category(name=name, keywords=list(kw)))
    return result


def _coerce_shops(raw: Any) -> list[Shop]:
    if not isinstance(raw, list):
        return [Shop(name=s["name"], keywords=list(s["keywords"])) for s in _FALLBACK["shops"]]
    result: list[Shop] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        keywords = entry.get("keywords", [])
        kw = [k for k in keywords if isinstance(k, str)] if isinstance(keywords, list) else []
        result.append(Shop(name=name, keywords=list(kw)))
    return result


def default_seed_version() -> int:
    """Return the shipped seed version (for migration/diagnostics)."""
    version = _RAW.get("seed_version", 0)
    return version if isinstance(version, int) else 0


def default_categories() -> list[Category]:
    """Return a fresh list of the default categories from the shipped map."""
    return _coerce_categories(_RAW.get("categories"))


def default_shops() -> list[Shop]:
    """Return a fresh list of the default shops (excludes 'No Preference')."""
    return _coerce_shops(_RAW.get("shops"))
