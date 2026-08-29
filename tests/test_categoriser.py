"""Unit tests for the pure categoriser + shop resolver.

Target: 100% coverage of categoriser.py. No Home Assistant dependency here.
"""

from __future__ import annotations

import pytest

from custom_components.alexa_shopping_categoriser.categoriser import (
    categorise,
    categorise_item,
    normalize,
    resolve_shop,
)
from custom_components.alexa_shopping_categoriser.const import NO_PREFERENCE, UNCATEGORISED
from custom_components.alexa_shopping_categoriser.defaults import (
    default_categories,
    default_shops,
)
from custom_components.alexa_shopping_categoriser.models import (
    Category,
    Shop,
    SourceItem,
)

CATS = default_categories()
SHOPS = default_shops()


# --- normalization --------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Oat Milk  ", "oat milk"),
        ("2x oat milk", "oat milk"),
        ("500g pasta", "pasta"),
        ("1 litre milk", "milk"),
        ("a dozen eggs", "eggs"),
        ("Free-Range Eggs!", "free-range eggs"),
        ("Ben's cookies", "ben's cookies"),
        ("MILK", "milk"),
        ("", ""),
        ("   ", ""),
        ("3", "3"),
    ],
)
def test_normalize(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


def test_normalize_bare_quantity_kept() -> None:
    # A leading number with nothing after it keeps the original.
    assert normalize("12") == "12"


# --- category matching (vegan rules) --------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2x oat milk", "Milk"),
        ("oat milk", "Milk"),
        ("cheddar cheese", "Chilled"),
        ("smoky bacon", "Fake Meat"),
        ("sausages", "Fake Meat"),
        ("free range eggs", UNCATEGORISED),
        ("honey", UNCATEGORISED),
        ("birthday candles", UNCATEGORISED),
        # whole-word protection
        ("graham crackers", UNCATEGORISED),  # not Fake Meat via "ham"
        ("steak", UNCATEGORISED),  # not Drinks via "tea"
        ("rollmop", UNCATEGORISED),  # not Bakery via "roll"
        ("bread", "Bakery"),
        ("carrots", "Produce"),
    ],
)
def test_categorise_keyword(raw: str, expected: str) -> None:
    assert categorise(normalize(raw), CATS, {}) == expected


def test_categorise_override_wins() -> None:
    overrides = {"birthday candles": "Household"}
    assert categorise(normalize("birthday candles"), CATS, overrides) == "Household"


def test_categorise_override_beats_keyword() -> None:
    overrides = {"oat milk": "Pantry"}
    assert categorise(normalize("oat milk"), CATS, overrides) == "Pantry"


def test_categorise_override_to_deleted_category_self_heals() -> None:
    # Override points at a category not present -> fall through to keyword match.
    overrides = {"oat milk": "GhostCategory"}
    assert categorise(normalize("oat milk"), CATS, overrides) == "Milk"


def test_categorise_no_keywords_category() -> None:
    cats = [Category(name="Empty", keywords=[]), *default_categories()]
    assert categorise(normalize("mystery item"), cats, {}) == UNCATEGORISED


# --- shop resolution precedence -------------------------------------------


def test_shop_keyword_rule() -> None:
    assert resolve_shop(normalize("nappies"), SHOPS, {}) == "Aldi"


def test_shop_name_in_text_beats_keyword_rule() -> None:
    # "tesco nappies" -> Tesco (name in text) not Aldi (keyword rule).
    assert resolve_shop(normalize("tesco nappies"), SHOPS, {}) == "Tesco"


def test_shop_name_in_text_beats_learned_override() -> None:
    overrides = {"tesco nappies": "Aldi"}
    assert resolve_shop(normalize("tesco nappies"), SHOPS, overrides) == "Tesco"


def test_shop_learned_override_beats_keyword_rule() -> None:
    overrides = {"oat milk": "Asda"}
    # "oat milk" has an Aldi keyword ("milk"); override to Asda wins.
    assert resolve_shop(normalize("oat milk"), SHOPS, overrides) == "Asda"


def test_shop_no_signal_is_no_preference() -> None:
    assert resolve_shop(normalize("mystery widget"), SHOPS, {}) == NO_PREFERENCE


def test_shop_override_to_deleted_shop_self_heals() -> None:
    overrides = {"mystery widget": "GhostShop"}
    assert resolve_shop(normalize("mystery widget"), SHOPS, overrides) == NO_PREFERENCE


def test_shop_override_to_deleted_shop_falls_to_keyword() -> None:
    overrides = {"nappies": "GhostShop"}
    # Override target gone -> fall through to keyword rule (Aldi).
    assert resolve_shop(normalize("nappies"), SHOPS, overrides) == "Aldi"


def test_shop_clothing_keyword() -> None:
    assert resolve_shop(normalize("jeans"), SHOPS, {}) == "Asda"


# --- combined item resolution (independence) ------------------------------


def test_categorise_item_independent_dimensions() -> None:
    item = SourceItem(uid="u1", name="oat milk", completed=False)
    result = categorise_item(item, CATS, {}, SHOPS, {})
    assert result.category == "Milk"
    assert result.shop == "Aldi"
    assert result.uid == "u1"
    assert result.checked is False


def test_categorise_item_tesco_milk() -> None:
    item = SourceItem(uid="u2", name="tesco milk", completed=True)
    result = categorise_item(item, CATS, {}, SHOPS, {})
    assert result.category == "Milk"
    assert result.shop == "Tesco"
    assert result.checked is True


def test_resolve_shop_empty_keyword_ignored() -> None:
    shops = [Shop(name="Weird", keywords=[""])]
    assert resolve_shop(normalize("anything"), shops, {}) == NO_PREFERENCE
