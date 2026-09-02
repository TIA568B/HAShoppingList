"""Tests for the shared category/shop map operations (single source of truth)."""

from __future__ import annotations

import pytest

from custom_components.alexa_shopping_categoriser import map_ops
from custom_components.alexa_shopping_categoriser.const import NO_PREFERENCE, UNCATEGORISED
from custom_components.alexa_shopping_categoriser.map_ops import MapValidationError
from custom_components.alexa_shopping_categoriser.models import Category, CategoryMap, Shop


def _map() -> CategoryMap:
    return CategoryMap(
        schema_version=2,
        categories=[Category(name="Milk", keywords=["milk"])],
        overrides={"birthday candles": "Milk"},
        shops=[Shop(name="Aldi", keywords=["nappies"])],
        shop_overrides={"oat milk": "Aldi"},
    )


def test_validate_name_rejects_bad() -> None:
    for bad in ["", "   ", "x" * 100, "bad\x01name"]:
        with pytest.raises(MapValidationError):
            map_ops.validate_name(bad)
    assert map_ops.validate_name("  Snacks  ") == "Snacks"


def test_clean_keywords() -> None:
    assert map_ops.clean_keywords([" a ", "", "b", None]) == ["a", "b"]  # type: ignore[list-item]
    assert map_ops.clean_keywords(None) == []


def test_add_category_dupe_and_reserved() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.add_category(m, "milk", [])  # case-insensitive dup
    with pytest.raises(MapValidationError):
        map_ops.add_category(m, UNCATEGORISED, [])
    map_ops.add_category(m, "Snacks", ["crisps"])
    assert any(c.name == "Snacks" for c in m.categories)


def test_edit_category_rename_migrates_overrides() -> None:
    m = _map()
    map_ops.edit_category(m, "Milk", new_name="Dairy-free")
    assert any(c.name == "Dairy-free" for c in m.categories)
    assert m.overrides["birthday candles"] == "Dairy-free"


def test_delete_category_drops_overrides() -> None:
    m = _map()
    map_ops.delete_category(m, "Milk")
    assert not any(c.name == "Milk" for c in m.categories)
    assert "birthday candles" not in m.overrides


def test_set_category_override_unknown_and_clear() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.set_category_override(m, "x", "Ghost")
    map_ops.set_category_override(m, "candles", "Milk")
    assert m.overrides["candles"] == "Milk"
    map_ops.set_category_override(m, "candles", UNCATEGORISED)  # clears
    assert "candles" not in m.overrides


def test_shop_add_edit_delete_and_reserved() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.add_shop(m, NO_PREFERENCE, [])
    with pytest.raises(MapValidationError):
        map_ops.add_shop(m, "aldi", [])
    map_ops.add_shop(m, "Lidl", ["bratwurst"])
    map_ops.edit_shop(m, "Aldi", new_name="Aldi UK")
    assert m.shop_overrides["oat milk"] == "Aldi UK"  # migrated
    with pytest.raises(MapValidationError):
        map_ops.delete_shop(m, NO_PREFERENCE)
    map_ops.delete_shop(m, "Lidl")
    assert not any(s.name == "Lidl" for s in m.shops)


def test_set_shop_override_unknown_and_clear() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.set_shop_override(m, "x", "Nowhere")
    map_ops.set_shop_override(m, "widget", "Aldi")
    assert m.shop_overrides["widget"] == "Aldi"
    map_ops.set_shop_override(m, "widget", NO_PREFERENCE)  # clears
    assert "widget" not in m.shop_overrides


def test_is_common_word() -> None:
    words = frozenset({"fresh", "local"})
    assert map_ops.is_common_word("Fresh", words) is True
    assert map_ops.is_common_word("Aldi", words) is False


def test_empty_item_text_rejected() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.set_category_override(m, "   ", "Milk")
    with pytest.raises(MapValidationError):
        map_ops.set_shop_override(m, "   ", "Aldi")


def test_not_found_errors() -> None:
    m = _map()
    with pytest.raises(MapValidationError):
        map_ops.edit_category(m, "Ghost", new_name="X")
    with pytest.raises(MapValidationError):
        map_ops.delete_category(m, "Ghost")
    with pytest.raises(MapValidationError):
        map_ops.edit_shop(m, "Ghost", new_name="X")
    with pytest.raises(MapValidationError):
        map_ops.delete_shop(m, "Ghost")


def test_rename_to_existing_and_reserved_rejected() -> None:
    m = _map()
    map_ops.add_category(m, "Bakery", ["bread"])
    with pytest.raises(MapValidationError):
        map_ops.edit_category(m, "Milk", new_name="Bakery")  # dup
    with pytest.raises(MapValidationError):
        map_ops.edit_category(m, "Milk", new_name=UNCATEGORISED)  # reserved
    map_ops.add_shop(m, "Tesco", [])
    with pytest.raises(MapValidationError):
        map_ops.edit_shop(m, "Aldi", new_name="Tesco")  # dup
    with pytest.raises(MapValidationError):
        map_ops.edit_shop(m, "Aldi", new_name=NO_PREFERENCE)  # reserved


def test_edit_keywords_only() -> None:
    m = _map()
    map_ops.edit_category(m, "Milk", keywords=["milk", "kefir"])
    assert next(c for c in m.categories if c.name == "Milk").keywords == ["milk", "kefir"]
    map_ops.edit_shop(m, "Aldi", keywords=["wipes"])
    assert next(s for s in m.shops if s.name == "Aldi").keywords == ["wipes"]
