"""Default vegan taxonomy and default shops (seed data).

Pure data + factory helpers, no Home Assistant import. Canonical values mirror
docs/plans/06 and the product steering vegan rules.
"""

from __future__ import annotations

from .models import Category, Shop

# Default category taxonomy (order is significant: more specific categories earlier;
# whole-word matching, first match wins). Vegan rules: milk -> Milk, dairy-style ->
# Chilled, meat-style -> Fake Meat.
_DEFAULT_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Fruit & Veg",
        (
            "apple",
            "banana",
            "carrot",
            "carrots",
            "lettuce",
            "onion",
            "onions",
            "cucumber",
            "garlic",
            "tomato",
            "tomatoes",
            "potato",
            "potatoes",
            "pepper",
            "peppers",
            "mushroom",
            "mushrooms",
            "spinach",
            "broccoli",
        ),
    ),
    ("Milk", ("milk", "oat milk", "soy milk", "soya milk", "almond milk", "oat drink")),
    # Sauces before Chilled so multi-word sauces (e.g. "salad cream") win over Chilled's
    # bare "cream" keyword (whole-word, first-match-wins ordering).
    (
        "Sauces",
        (
            "sauce",
            "teriyaki",
            "teriyaki sauce",
            "soy sauce",
            "soya sauce",
            "ketchup",
            "mayo",
            "mayonnaise",
            "mango chutney",
            "chutney",
            "salad cream",
            "pesto",
        ),
    ),
    (
        "Chilled",
        ("cheese", "yogurt", "yogurts", "yoghurt", "yoghurts", "butter", "cream", "tofu"),
    ),
    # Fake Meat before Pantry so meat-substitute terms win first.
    (
        "Fake Meat",
        (
            "sausages",
            "bacon",
            "mince",
            "chicken",
            "chicken pieces",
            "burgers",
            "ham",
        ),
    ),
    ("Baby", ("nappies", "nappy", "wipes", "baby wipes", "baby food", "formula")),
    ("Bakery", ("bread", "bagel", "roll", "sourdough")),
    ("Frozen", ("frozen peas", "vegan ice cream", "chips", "pizza")),
    ("Drinks", ("juice", "squash", "coffee", "tea", "ice tea", "iced tea")),
    (
        "Pantry",
        (
            "pasta",
            "rice",
            "lentils",
            "beans",
            "chickpeas",
            "olives",
            "tinned",
        ),
    ),
    ("Household", ("toilet roll", "washing up liquid", "bin bags")),
)

# Default shops (excluding the implicit, non-removable "No Preference").
# Order is significant for keyword-rule resolution.
_DEFAULT_SHOPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Aldi", ("nappies", "milk", "teriyaki", "teriyaki sauce", "veggie pasta")),
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
    ("Waitrose", ("pizza",)),
    ("Morrisons", ()),
    ("Lidl", ()),
    ("Sainsburys", ()),
)


def default_categories() -> list[Category]:
    """Return a fresh list of the default categories."""
    return [Category(name=name, keywords=list(keywords)) for name, keywords in _DEFAULT_CATEGORIES]


def default_shops() -> list[Shop]:
    """Return a fresh list of the default shops (excludes 'No Preference')."""
    return [Shop(name=name, keywords=list(keywords)) for name, keywords in _DEFAULT_SHOPS]
