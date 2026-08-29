"""Persistence for the category/shop maps and learned overrides.

Wraps the Home Assistant ``Store`` helper. One store per config entry. Loads
defensively: any missing top-level key is filled from defaults (finding F4-1), so an
older or partial store loads without a KeyError. Storage holds no item state and no copy
of the list -- only the maps -- keeping the projection rebuildable and drift-free (NFR3).
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_PREFIX, STORAGE_VERSION, STORE_SCHEMA_VERSION
from .defaults import default_categories, default_shops
from .models import Category, CategoryMap, Shop

_LOGGER = logging.getLogger(__name__)


class CategoryStore:
    """Load/save/migrate the :class:`CategoryMap` for one config entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store for the given config entry."""
        self._store: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}.{entry_id}",
        )
        self._map: CategoryMap | None = None

    @property
    def category_map(self) -> CategoryMap:
        """Return the loaded map (must call ``async_load`` first)."""
        if self._map is None:
            raise RuntimeError("CategoryStore.async_load must be called before access")
        return self._map

    async def async_load(self) -> CategoryMap:
        """Load the map, seeding defaults on first run and healing partial stores."""
        raw = await self._store.async_load()
        if raw is None:
            self._map = self._default_map()
            await self.async_save()
            return self._map

        category_map, migrated = self._deserialize(raw)
        self._map = category_map
        if migrated:
            await self.async_save()
        return category_map

    async def async_save(self) -> None:
        """Persist the current map."""
        if self._map is None:
            raise RuntimeError("Nothing to save; call async_load first")
        await self._store.async_save(self._serialize(self._map))

    async def async_replace(self, category_map: CategoryMap) -> None:
        """Replace the in-memory map and persist it."""
        self._map = category_map
        await self.async_save()

    # --- (de)serialization ------------------------------------------------

    @staticmethod
    def _default_map() -> CategoryMap:
        return CategoryMap(
            schema_version=STORE_SCHEMA_VERSION,
            categories=default_categories(),
            overrides={},
            shops=default_shops(),
            shop_overrides={},
        )

    @staticmethod
    def _deserialize(raw: dict[str, Any]) -> tuple[CategoryMap, bool]:
        """Convert raw storage dict into a CategoryMap.

        Returns (map, migrated) where ``migrated`` is True if defaults were injected or
        the schema version was upgraded, meaning the store should be re-persisted.
        Uses ``.get`` with defaults for every top-level key so a partial store is safe.
        """
        migrated = False

        stored_version = raw.get("schema_version", STORE_SCHEMA_VERSION)

        categories_raw = raw.get("categories")
        if categories_raw is None:
            categories = default_categories()
            migrated = True
        else:
            categories = [
                Category(name=c["name"], keywords=list(c.get("keywords", [])))
                for c in categories_raw
            ]

        shops_raw = raw.get("shops")
        if shops_raw is None:
            shops = default_shops()
            migrated = True
        else:
            shops = [Shop(name=s["name"], keywords=list(s.get("keywords", []))) for s in shops_raw]

        overrides_raw = raw.get("overrides")
        if overrides_raw is None:
            overrides: dict[str, str] = {}
            migrated = True
        else:
            overrides = dict(overrides_raw)

        shop_overrides_raw = raw.get("shop_overrides")
        if shop_overrides_raw is None:
            shop_overrides: dict[str, str] = {}
            migrated = True
        else:
            shop_overrides = dict(shop_overrides_raw)

        if stored_version < STORE_SCHEMA_VERSION:
            # Future ordered migrators run here; for now bump and persist.
            migrated = True

        category_map = CategoryMap(
            schema_version=STORE_SCHEMA_VERSION,
            categories=categories,
            overrides=overrides,
            shops=shops,
            shop_overrides=shop_overrides,
        )
        return category_map, migrated

    @staticmethod
    def _serialize(category_map: CategoryMap) -> dict[str, Any]:
        return {
            "schema_version": category_map.schema_version,
            "categories": [
                {"name": c.name, "keywords": list(c.keywords)} for c in category_map.categories
            ],
            "overrides": dict(category_map.overrides),
            "shops": [{"name": s.name, "keywords": list(s.keywords)} for s in category_map.shops],
            "shop_overrides": dict(category_map.shop_overrides),
        }
