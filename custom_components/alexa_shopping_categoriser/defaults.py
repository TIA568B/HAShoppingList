"""Default vegan taxonomy and default shops (seed data).

Pure data + factory helpers, no Home Assistant import. Canonical values mirror
docs/plans/06 and the product steering vegan rules.
"""

from __future__ import annotations

from .models import Category, Shop

# Default category taxonomy (order is significant: more specific categories earlier).
# Vegan rules: milk -> Milk, dairy-style -> Chilled, meat-style -> Fake Meat.
_DEFAULT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Produce", ("apple", "banana", "carrot", "carrots", "lettuce", "onion", "onions")),
    ("Milk", ("milk", "oat milk", "soy milk", "soya milk", "almond milk", "oat drink")),
    ("Chilled", ("cheese", "yogurt", "yoghurt", "butter", "cream", "tofu")),
    (
        "Fake Meat",
        ("sausages", "bacon", "mince", "chicken pieces", "burgers", "ham"),
    ),
    ("Bakery", ("bread", "bagel", "roll", "sourdough")),
    ("Frozen", ("frozen peas", "vegan ice cream", "chips")),
    ("Drinks", ("juice", "squash", "coffee", "tea")),
    ("Pantry", ("pasta", "rice", "lentils", "beans", "tinned")),
    ("Household", ("toilet roll", "washing up liquid", "bin bags")),
)

# Default shops (excluding the implicit, non-removable "No Preference").
# Order is significant for keyword-rule resolution.
_DEFAULT_SHOPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Aldi", ("nappies", "milk")),
    (
        "Asda",
        (
            "clothes",
            "clothing",
            "t-shirt",
            "tshirt",
            "shirt",
            "jumper",
            "hoodie",
            "socks",
            "underwear",
            "pants",
            "knickers",
            "boxers",
            "vest",
            "jeans",
            "trousers",
            "shorts",
            "leggings",
            "joggers",
            "pyjamas",
            "jammies",
            "pjs",
            "dress",
            "skirt",
            "coat",
            "jacket",
            "shoes",
            "trainers",
            "slippers",
            "hat",
            "gloves",
            "scarf",
        ),
    ),
    ("Tesco", ()),
)


def default_categories() -> list[Category]:
    """Return a fresh list of the default categories."""
    return [Category(name=name, keywords=list(keywords)) for name, keywords in _DEFAULT_CATEGORIES]


def default_shops() -> list[Shop]:
    """Return a fresh list of the default shops (excludes 'No Preference')."""
    return [Shop(name=name, keywords=list(keywords)) for name, keywords in _DEFAULT_SHOPS]
