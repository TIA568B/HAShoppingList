"""Build the shop-primary, category-secondary projection (pure).

The projection is the derived, non-authoritative view the sensor exposes and the card
renders (contract canonical in docs/plans/06). It is rebuildable at any time from the
source items plus the category/shop maps -- no item state is stored here.
"""

from __future__ import annotations

from typing import Any, TypedDict

from .categoriser import categorise_item
from .const import (
    ATTR_ATTRIBUTES_VERSION,
    ATTRIBUTES_VERSION,
    NO_PREFERENCE,
    UNCATEGORISED,
)
from .models import Category, CategoryMap, Shop, SourceItem


class ProjectionOptions(TypedDict):
    """Options echoed into the projection for the card."""

    grace_period_seconds: int
    show_completed: bool
    collapse_empty_categories: bool


class Projection(TypedDict):
    """The full sensor attribute payload (attributes_version 3)."""

    attributes_version: int
    source_entity_id: str
    last_synced: str | None
    total_unchecked: int
    uncategorised_count: int
    options: ProjectionOptions
    category_definitions: list[dict[str, Any]]
    shop_definitions: list[dict[str, Any]]
    shop_groups: list[dict[str, Any]]


def _shop_order_key(shops: list[Shop]) -> dict[str, int]:
    """Map shop name -> display order; No Preference sorts last."""
    order = {shop.name: index for index, shop in enumerate(shops)}
    order[NO_PREFERENCE] = len(shops)
    return order


def _category_order_key(categories: list[Category]) -> dict[str, int]:
    """Map category name -> display order; Uncategorised sorts last."""
    order = {category.name: index for index, category in enumerate(categories)}
    order[UNCATEGORISED] = len(categories)
    return order


def build_projection(
    items: list[SourceItem],
    category_map: CategoryMap,
    source_entity_id: str,
    *,
    grace_period_seconds: int,
    show_completed: bool,
    collapse_empty_categories: bool,
    last_synced: str | None,
) -> Projection:
    """Build the shop-primary projection from source items and the maps."""
    categorised = [
        categorise_item(
            item,
            category_map.categories,
            category_map.overrides,
            category_map.shops,
            category_map.shop_overrides,
        )
        for item in items
    ]

    shop_order = _shop_order_key(category_map.shops)
    category_order = _category_order_key(category_map.categories)

    # Group: shop -> category -> items.
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
    unchecked_by_shop_cat: dict[tuple[str, str], int] = {}
    total_unchecked = 0
    uncategorised_count = 0

    for ci in categorised:
        if ci.checked and not show_completed:
            # Still counts toward "done" auto-collapse but is not listed.
            pass
        shop_bucket = grouped.setdefault(ci.shop, {})
        cat_bucket = shop_bucket.setdefault(ci.category, [])

        if not ci.checked:
            total_unchecked += 1
            unchecked_by_shop_cat[(ci.shop, ci.category)] = (
                unchecked_by_shop_cat.get((ci.shop, ci.category), 0) + 1
            )
            if ci.category == UNCATEGORISED:
                uncategorised_count += 1

        if ci.checked and not show_completed:
            continue

        cat_bucket.append(
            {
                "uid": ci.uid,
                "name": ci.name,
                "checked": ci.checked,
                "shop": ci.shop,
                "category": ci.category,
            }
        )

    # Emit ordered structure.
    shop_groups: list[dict[str, Any]] = []
    for shop_name in sorted(grouped, key=lambda s: shop_order.get(s, len(shop_order))):
        cat_map = grouped[shop_name]
        categories_out: list[dict[str, Any]] = []
        shop_unchecked = 0
        for cat_name in sorted(cat_map, key=lambda c: category_order.get(c, len(category_order))):
            cat_items = cat_map[cat_name]
            cat_unchecked = unchecked_by_shop_cat.get((shop_name, cat_name), 0)
            shop_unchecked += cat_unchecked
            categories_out.append(
                {
                    "name": cat_name,
                    "collapsed": collapse_empty_categories and cat_unchecked == 0,
                    "items": cat_items,
                }
            )
        shop_groups.append(
            {
                "name": shop_name,
                "collapsed": collapse_empty_categories and shop_unchecked == 0,
                "categories": categories_out,
            }
        )

    projection: Projection = {
        ATTR_ATTRIBUTES_VERSION: ATTRIBUTES_VERSION,
        "source_entity_id": source_entity_id,
        "last_synced": last_synced,
        "total_unchecked": total_unchecked,
        "uncategorised_count": uncategorised_count,
        "options": {
            "grace_period_seconds": grace_period_seconds,
            "show_completed": show_completed,
            "collapse_empty_categories": collapse_empty_categories,
        },
        "category_definitions": [
            {"name": c.name, "keywords": list(c.keywords)} for c in category_map.categories
        ],
        "shop_definitions": [
            {"name": s.name, "keywords": list(s.keywords)} for s in category_map.shops
        ],
        "shop_groups": shop_groups,
    }
    return projection
