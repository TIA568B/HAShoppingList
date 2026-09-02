"""Shared category/shop map operations — the single source of truth for mutations.

Both the services (`services.py`) and the options flow (`config_flow.py`) call these, so
validation and semantics live in exactly one place. Functions mutate the given
:class:`CategoryMap` in place and raise :class:`MapValidationError` on invalid input; they
do not persist or recompute (the caller owns store + coordinator).
"""

from __future__ import annotations

from homeassistant.exceptions import ServiceValidationError

from .categoriser import normalize
from .const import MAX_KEYWORD_LENGTH, MAX_NAME_LENGTH, NO_PREFERENCE, UNCATEGORISED
from .models import Category, CategoryMap, Shop


class MapValidationError(ServiceValidationError):
    """Raised when a category/shop edit is invalid (bad name, duplicate, reserved, …).

    Subclasses ``ServiceValidationError`` so services raise the same public error type as
    before, and the options flow can surface it natively too.
    """


def _find_category(cmap: CategoryMap, name: str) -> Category | None:
    folded = name.strip().casefold()
    return next((c for c in cmap.categories if c.name.casefold() == folded), None)


def _find_shop(cmap: CategoryMap, name: str) -> Shop | None:
    folded = name.strip().casefold()
    return next((s for s in cmap.shops if s.name.casefold() == folded), None)


# --- validation helpers ---------------------------------------------------


def validate_name(raw: str) -> str:
    """Validate + normalise a user-supplied category/shop display name."""
    name = raw.strip()
    if not name:
        raise MapValidationError("Name must not be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise MapValidationError(f"Name exceeds {MAX_NAME_LENGTH} characters")
    if any(ord(ch) < 32 for ch in name):
        raise MapValidationError("Name must not contain control characters")
    return name


def clean_keywords(raw: list[str] | None) -> list[str]:
    """Strip, length-limit, and drop empty/non-string entries from a keyword list."""
    cleaned: list[str] = []
    for kw in raw or []:
        if not isinstance(kw, str):
            continue
        stripped = kw.strip()
        if stripped:
            cleaned.append(stripped[:MAX_KEYWORD_LENGTH])
    return cleaned


# --- category operations --------------------------------------------------


def add_category(cmap: CategoryMap, name: str, keywords: list[str] | None) -> None:
    """Add a new category. Raises on empty/duplicate/reserved name."""
    valid = validate_name(name)
    if valid.casefold() == UNCATEGORISED.casefold():
        raise MapValidationError(f"{UNCATEGORISED} is reserved")
    if any(c.name.casefold() == valid.casefold() for c in cmap.categories):
        raise MapValidationError(f"Category '{valid}' already exists")
    cmap.categories.append(Category(name=valid, keywords=clean_keywords(keywords)))


def edit_category(
    cmap: CategoryMap,
    name: str,
    new_name: str | None = None,
    keywords: list[str] | None = None,
) -> None:
    """Rename a category and/or replace its keywords; migrates learned overrides on rename."""
    target = _find_category(cmap, name)
    if target is None:
        raise MapValidationError(f"Category '{name}' not found")

    if new_name is not None:
        valid = validate_name(new_name)
        if valid.casefold() == UNCATEGORISED.casefold():
            raise MapValidationError(f"{UNCATEGORISED} is reserved")
        if valid.casefold() != target.name.casefold() and any(
            c.name.casefold() == valid.casefold() for c in cmap.categories
        ):
            raise MapValidationError(f"Category '{valid}' already exists")
        old = target.name
        target.name = valid
        for key, value in list(cmap.overrides.items()):
            if value == old:
                cmap.overrides[key] = valid

    if keywords is not None:
        target.keywords = clean_keywords(keywords)


def delete_category(cmap: CategoryMap, name: str) -> None:
    """Delete a category; its items fall to Uncategorised. Overrides at it are dropped."""
    target = _find_category(cmap, name)
    if target is None:
        raise MapValidationError(f"Category '{name}' not found")
    cmap.categories.remove(target)
    for key, value in list(cmap.overrides.items()):
        if value == target.name:
            del cmap.overrides[key]


def set_category_override(cmap: CategoryMap, item_text: str, category: str) -> None:
    """Learn a category for an item's normalised text (Uncategorised clears it)."""
    key = normalize(item_text)
    if not key:
        raise MapValidationError("item_text normalises to empty")
    if category == UNCATEGORISED:
        cmap.overrides.pop(key, None)
        return
    if not any(c.name == category for c in cmap.categories):
        raise MapValidationError(f"Unknown category: {category}")
    cmap.overrides[key] = category


# --- shop operations ------------------------------------------------------


def add_shop(cmap: CategoryMap, name: str, keywords: list[str] | None) -> None:
    """Add a new shop. Raises on empty/duplicate/reserved name."""
    valid = validate_name(name)
    if valid.casefold() == NO_PREFERENCE.casefold():
        raise MapValidationError(f"{NO_PREFERENCE} is reserved")
    if any(s.name.casefold() == valid.casefold() for s in cmap.shops):
        raise MapValidationError(f"Shop '{valid}' already exists")
    cmap.shops.append(Shop(name=valid, keywords=clean_keywords(keywords)))


def edit_shop(
    cmap: CategoryMap,
    name: str,
    new_name: str | None = None,
    keywords: list[str] | None = None,
) -> None:
    """Rename a shop and/or replace its keyword rules; migrates learned shop overrides."""
    target = _find_shop(cmap, name)
    if target is None:
        raise MapValidationError(f"Shop '{name}' not found")

    if new_name is not None:
        valid = validate_name(new_name)
        if valid.casefold() == NO_PREFERENCE.casefold():
            raise MapValidationError(f"{NO_PREFERENCE} is reserved")
        if valid.casefold() != target.name.casefold() and any(
            s.name.casefold() == valid.casefold() for s in cmap.shops
        ):
            raise MapValidationError(f"Shop '{valid}' already exists")
        old = target.name
        target.name = valid
        for key, value in list(cmap.shop_overrides.items()):
            if value == old:
                cmap.shop_overrides[key] = valid

    if keywords is not None:
        target.keywords = clean_keywords(keywords)


def delete_shop(cmap: CategoryMap, name: str) -> None:
    """Delete a shop; its items fall to No Preference. Overrides at it are dropped."""
    if name.strip().casefold() == NO_PREFERENCE.casefold():
        raise MapValidationError(f"{NO_PREFERENCE} cannot be deleted")
    target = _find_shop(cmap, name)
    if target is None:
        raise MapValidationError(f"Shop '{name}' not found")
    cmap.shops.remove(target)
    for key, value in list(cmap.shop_overrides.items()):
        if value == target.name:
            del cmap.shop_overrides[key]


def set_shop_override(cmap: CategoryMap, item_text: str, shop: str) -> None:
    """Learn a shop for an item's normalised text (No Preference clears it)."""
    key = normalize(item_text)
    if not key:
        raise MapValidationError("item_text normalises to empty")
    if shop.casefold() == NO_PREFERENCE.casefold():
        cmap.shop_overrides.pop(key, None)
        return
    canonical = next((s.name for s in cmap.shops if s.name.casefold() == shop.casefold()), None)
    if canonical is None:
        raise MapValidationError(f"Unknown shop: {shop}")
    cmap.shop_overrides[key] = canonical


def is_common_word(name: str, common_words: frozenset[str]) -> bool:
    """True if a shop name is a common English word (tier-1 hijack warning, R7-L2)."""
    return name.strip().casefold() in common_words
