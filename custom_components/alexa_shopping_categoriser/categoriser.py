"""Pure categorisation + shop-resolution engine.

No Home Assistant import and no I/O, so every function here is a plain ``def`` and is
unit-testable standalone (docs/plans/07). Matching is **whole-word / whole-phrase,
case-insensitive** for both the category and shop resolvers -- never substring, which
would break the vegan boundary (e.g. ``ham`` inside "graham crackers"). This is a
correctness rule (finding F4-2).
"""

from __future__ import annotations

import re

from .const import NO_PREFERENCE, UNCATEGORISED
from .models import CategorisedItem, Category, Shop, SourceItem

# Leading quantity/unit prefixes to strip, e.g. "2x", "500g", "1 litre", "a dozen".
_UNIT_WORDS = (
    "x",
    "g",
    "kg",
    "mg",
    "ml",
    "l",
    "litre",
    "litres",
    "liter",
    "liters",
    "pack",
    "packs",
    "dozen",
    "bunch",
    "tin",
    "tins",
    "can",
    "cans",
    "bottle",
    "bottles",
    "box",
    "boxes",
    "bag",
    "bags",
)

# A leading numeric quantity token, optionally with a trailing unit, e.g. "2x", "500g", "1".
_QTY_RE = re.compile(
    r"^\s*(?:a\s+)?\d+\s*(?:[a-z]+)?\b|^\s*a\s+(?=dozen\b)",
    re.IGNORECASE,
)

# Characters kept during normalization: word chars, spaces, intra-word hyphen/apostrophe.
_STRIP_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Normalize raw item text into the key used for matching and overrides.

    Lowercase, trim, strip a leading quantity/unit, drop punctuation (keeping
    intra-word hyphens/apostrophes), and collapse whitespace.
    """
    lowered = text.strip().lower()

    # Strip a single leading quantity/unit token if present.
    stripped = _strip_leading_quantity(lowered)

    # Remove punctuation except intra-word hyphen/apostrophe.
    cleaned = _STRIP_PUNCT_RE.sub(" ", stripped)
    collapsed = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return collapsed


def _strip_leading_quantity(text: str) -> str:
    """Remove a leading quantity token such as '2x', '500g', '1 litre', 'a dozen'."""
    match = _QTY_RE.match(text)
    if not match:
        return text
    remainder = text[match.end() :].strip()
    # Guard against consuming a bare unit word that is actually the item (rare); if the
    # remainder is empty, keep the original text.
    if not remainder:
        return text
    # If a unit word survived as the first token (e.g. "1 litre milk" -> "litre milk"),
    # drop it too.
    parts = remainder.split(" ", 1)
    if len(parts) == 2 and parts[0] in _UNIT_WORDS:
        return parts[1].strip()
    return remainder


def _tokens(normalized: str) -> list[str]:
    """Split a normalized string into word tokens."""
    return normalized.split(" ") if normalized else []


def _phrase_matches(normalized_tokens: list[str], keyword: str) -> bool:
    """Return True if ``keyword`` matches ``normalized_tokens`` as a contiguous phrase.

    Whole-word / whole-phrase, case-insensitive. A multi-word keyword like "oat milk"
    matches only as a contiguous token sequence.
    """
    kw_tokens = keyword.strip().lower().split()
    if not kw_tokens:
        return False
    n = len(kw_tokens)
    if n > len(normalized_tokens):
        return False
    for i in range(len(normalized_tokens) - n + 1):
        if normalized_tokens[i : i + n] == kw_tokens:
            return True
    return False


def categorise(
    normalized: str,
    categories: list[Category],
    overrides: dict[str, str],
) -> str:
    """Resolve a normalized item text to a category name.

    Precedence: learned override (if its target still exists) > keyword match (whole-word,
    category order significant) > Uncategorised. Never guesses.
    """
    category_names = {c.name for c in categories}

    # 1. Learned override (highest precedence). Self-heals if target was deleted.
    override = overrides.get(normalized)
    if override is not None and override in category_names:
        return override

    # 2. Keyword match, in category order (first match wins).
    tokens = _tokens(normalized)
    for category in categories:
        for keyword in category.keywords:
            if _phrase_matches(tokens, keyword):
                return category.name

    # 3. Fallback.
    return UNCATEGORISED


def resolve_shop(
    normalized: str,
    shops: list[Shop],
    shop_overrides: dict[str, str],
) -> str:
    """Resolve a normalized item text to a shop name.

    Precedence (highest to lowest):
      1. Explicit shop name present in the item text (whole word) -- beats a learned override.
      2. Learned override (if its target shop still exists).
      3. Shop keyword rule (shop order significant).
      4. No Preference (never guessed).
    """
    shop_names = {s.name for s in shops}
    tokens = _tokens(normalized)

    # 1. Explicit shop name in the item text (whole word, case-insensitive).
    for shop in shops:
        if _phrase_matches(tokens, shop.name):
            return shop.name

    # 2. Learned override, if the target shop still exists (self-heal otherwise).
    override = shop_overrides.get(normalized)
    if override is not None and override in shop_names:
        return override

    # 3. Shop keyword rule, in shop order.
    for shop in shops:
        for keyword in shop.keywords:
            if _phrase_matches(tokens, keyword):
                return shop.name

    # 4. Fallback.
    return NO_PREFERENCE


def categorise_item(
    item: SourceItem,
    categories: list[Category],
    overrides: dict[str, str],
    shops: list[Shop],
    shop_overrides: dict[str, str],
) -> CategorisedItem:
    """Resolve a source item's category and shop (independently)."""
    normalized = normalize(item.name)
    category = categorise(normalized, categories, overrides)
    shop = resolve_shop(normalized, shops, shop_overrides)
    return CategorisedItem(
        uid=item.uid,
        name=item.name,
        checked=item.completed,
        category=category,
        shop=shop,
    )
