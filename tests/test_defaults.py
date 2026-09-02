"""Tests for the JSON-backed default map loader (M1)."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import custom_components.alexa_shopping_categoriser.defaults as defaults_mod
from custom_components.alexa_shopping_categoriser.defaults import (
    default_categories,
    default_seed_version,
    default_shops,
)


def test_default_map_json_is_valid_and_shaped() -> None:
    path = Path(defaults_mod.__file__).parent / "default_map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(data["seed_version"], int)
    assert isinstance(data["categories"], list) and data["categories"]
    assert isinstance(data["shops"], list) and data["shops"]


def test_loads_expected_taxonomy() -> None:
    cat_names = [c.name for c in default_categories()]
    # Order matters and is significant (first-match-wins). Specific, marker-driven
    # categories are evaluated before broad bare-word ones:
    #  - Canned Food is first: an explicit "tinned"/"canned" marker is the strongest
    #    signal and must win over the food inside (e.g. "tinned tomatoes" is Canned
    #    Food, not Fruit & Veg via "tomatoes").
    #  - Sauces must precede Chilled (salad cream vs bare "cream").
    #  - Sauces/Drinks/Frozen must precede Fruit & Veg so multi-word items like
    #    "tomato ketchup", "apple juice" and "vanilla ice cream" win over bare
    #    produce/fruit keywords ("tomato", "apple", "strawberry").
    assert cat_names.index("Sauces") < cat_names.index("Chilled")
    for specific in ("Canned Food", "Sauces", "Drinks", "Frozen"):
        assert cat_names.index(specific) < cat_names.index("Fruit & Veg")
    assert cat_names.index("Canned Food") < cat_names.index("Pantry")
    assert cat_names[0] == "Canned Food"
    for expected in ("Canned Food", "Sauces", "Baby", "Frozen", "Fake Meat"):
        assert expected in cat_names
    # No stale "Produce".
    assert "Produce" not in cat_names


def test_loads_expected_shops() -> None:
    shop_names = [s.name for s in default_shops()]
    assert shop_names == [
        "Aldi",
        "Asda",
        "Tesco",
        "Waitrose",
        "Morrisons",
        "Lidl",
        "Sainsburys",
        "Co-op",
        "Marks & Spencer",
        "Home Bargains",
    ]
    aldi = next(s for s in default_shops() if s.name == "Aldi")
    assert "teriyaki" in aldi.keywords and "veggie pasta" in aldi.keywords
    waitrose = next(s for s in default_shops() if s.name == "Waitrose")
    assert waitrose.keywords == ["pizza"]


def test_seed_version_is_positive() -> None:
    assert default_seed_version() >= 1


def test_key_keyword_placements() -> None:
    cats = {c.name: c.keywords for c in default_categories()}
    assert "pizza" in cats["Frozen"]
    assert "salad cream" in cats["Sauces"]
    assert "nappies" in cats["Baby"]
    assert "chickpeas" in cats["Pantry"] and "olives" in cats["Pantry"]


def test_malformed_file_falls_back_safely(tmp_path: Path, monkeypatch) -> None:
    # Point the loader at a malformed file and re-run the raw loader.
    bad = tmp_path / "default_map.json"
    bad.write_text("{ not valid json ", encoding="utf-8")
    monkeypatch.setattr(defaults_mod, "_DEFAULT_MAP_PATH", bad)
    raw = defaults_mod._load_raw()
    # Falls back to the built-in minimal map (never raises).
    assert raw["seed_version"] == 0
    assert any(c["name"] == "Milk" for c in raw["categories"])


def test_module_reimport_still_works() -> None:
    # Re-importing must not crash (module-level parse is cached but re-runnable).
    importlib.reload(defaults_mod)
    assert defaults_mod.default_categories()


def test_coerce_categories_fallback_and_filtering() -> None:
    # Non-list -> fallback set.
    fb = defaults_mod._coerce_categories("nope")
    assert any(c.name == "Milk" for c in fb)
    # List with junk entries -> only valid dicts with non-blank names survive; bad keywords
    # coerce to empty.
    coerced = defaults_mod._coerce_categories(
        [
            {"name": "Good", "keywords": ["a", 1, "b"]},
            {"name": "  "},  # blank name dropped
            "not a dict",  # dropped
            {"keywords": ["x"]},  # missing name dropped
            {"name": "NoKw", "keywords": "not-a-list"},  # keywords coerce to []
        ]
    )
    names = [c.name for c in coerced]
    assert names == ["Good", "NoKw"]
    good = next(c for c in coerced if c.name == "Good")
    assert good.keywords == ["a", "b"]  # non-strings filtered
    assert next(c for c in coerced if c.name == "NoKw").keywords == []


def test_coerce_shops_fallback_and_filtering() -> None:
    fb = defaults_mod._coerce_shops(None)
    assert any(s.name == "Aldi" for s in fb)
    coerced = defaults_mod._coerce_shops([{"name": "Shop1", "keywords": ["k"]}, 42])
    assert [s.name for s in coerced] == ["Shop1"]


def test_load_raw_non_object_json_falls_back(tmp_path: Path, monkeypatch) -> None:
    bad = tmp_path / "default_map.json"
    bad.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON but not an object
    monkeypatch.setattr(defaults_mod, "_DEFAULT_MAP_PATH", bad)
    raw = defaults_mod._load_raw()
    assert raw["seed_version"] == 0  # fallback


def test_seed_version_non_int_coerces_to_zero(monkeypatch) -> None:
    monkeypatch.setattr(defaults_mod, "_RAW", {"seed_version": "oops"})
    assert defaults_mod.default_seed_version() == 0
