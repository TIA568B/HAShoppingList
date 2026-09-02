"""Config-entry-scoped services for category/shop maintenance and learning.

These operate on the shared persisted map, targeted by an optional ``entry_id`` -- they
are NOT entity services. All input is validated with voluptuous. Every mutating service
persists the store then requests a coordinator recompute.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .categoriser import normalize
from .const import (
    ATTR_APPLY_TO_UID,
    ATTR_CATEGORY,
    ATTR_ENTRY_ID,
    ATTR_ITEM_TEXT,
    ATTR_KEYWORDS,
    ATTR_NAME,
    ATTR_NEW_NAME,
    ATTR_SHOP,
    DOMAIN,
    MAX_KEYWORD_LENGTH,
    MAX_NAME_LENGTH,
    NO_PREFERENCE,
    SERVICE_ADD_CATEGORY,
    SERVICE_ADD_SHOP,
    SERVICE_ASSIGN_SHOP,
    SERVICE_DELETE_CATEGORY,
    SERVICE_DELETE_SHOP,
    SERVICE_EDIT_CATEGORY,
    SERVICE_EDIT_SHOP,
    SERVICE_RECATEGORISE_ITEM,
    SERVICE_RELOAD_MAPS,
    UNCATEGORISED,
)
from .models import Category, CategoryMap, Shop

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .coordinator import AlexaShoppingCoordinator
    from .runtime import AlexaShoppingRuntimeData
    from .store import CategoryStore

_LOGGER = logging.getLogger(__name__)

_COMMON_ENGLISH_WORDS = frozenset(
    {
        "fresh",
        "local",
        "shop",
        "store",
        "market",
        "corner",
        "food",
        "the",
        "and",
    }
)

_KEYWORDS_SCHEMA = vol.All(
    cv.ensure_list,
    [vol.All(cv.string, vol.Length(min=1, max=MAX_KEYWORD_LENGTH))],
)

_ENTRY_ID = vol.Optional(ATTR_ENTRY_ID)

RECATEGORISE_ITEM_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_ITEM_TEXT): cv.string,
        vol.Required(ATTR_CATEGORY): cv.string,
        vol.Optional(ATTR_APPLY_TO_UID): cv.string,
    }
)

ADD_CATEGORY_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_KEYWORDS): _KEYWORDS_SCHEMA,
    }
)

EDIT_CATEGORY_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_NEW_NAME): cv.string,
        vol.Optional(ATTR_KEYWORDS): _KEYWORDS_SCHEMA,
    }
)

DELETE_CATEGORY_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
    }
)

ASSIGN_SHOP_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_ITEM_TEXT): cv.string,
        vol.Required(ATTR_SHOP): cv.string,
        vol.Optional(ATTR_APPLY_TO_UID): cv.string,
    }
)

ADD_SHOP_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_KEYWORDS): _KEYWORDS_SCHEMA,
    }
)

EDIT_SHOP_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
        vol.Optional(ATTR_NEW_NAME): cv.string,
        vol.Optional(ATTR_KEYWORDS): _KEYWORDS_SCHEMA,
    }
)

DELETE_SHOP_SCHEMA = vol.Schema(
    {
        _ENTRY_ID: cv.string,
        vol.Required(ATTR_NAME): cv.string,
    }
)

RELOAD_MAPS_SCHEMA = vol.Schema({_ENTRY_ID: cv.string})


def _validate_name(raw: str) -> str:
    """Validate + normalize a user-supplied category/shop display name."""
    name = raw.strip()
    if not name:
        raise ServiceValidationError("Name must not be empty")
    if len(name) > MAX_NAME_LENGTH:
        raise ServiceValidationError(f"Name exceeds {MAX_NAME_LENGTH} characters")
    if any(ord(ch) < 32 for ch in name):
        raise ServiceValidationError("Name must not contain control characters")
    return name


def _clean_keywords(raw: list[str]) -> list[str]:
    """Strip and drop empties from a keyword list."""
    cleaned: list[str] = []
    for kw in raw:
        stripped = kw.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _coordinator_of(entry: ConfigEntry) -> AlexaShoppingCoordinator:
    """Return the coordinator from an entry's runtime data."""
    runtime: AlexaShoppingRuntimeData = entry.runtime_data
    return runtime.coordinator


def _resolve_coordinator(hass: HomeAssistant, call: ServiceCall) -> AlexaShoppingCoordinator:
    """Find the target coordinator, using entry_id if given else the sole entry."""
    entries = [
        e
        for e in hass.config_entries.async_entries(DOMAIN)
        if getattr(e, "runtime_data", None) is not None
    ]
    entry_id = call.data.get(ATTR_ENTRY_ID)
    if entry_id is not None:
        for e in entries:
            if e.entry_id == entry_id:
                return _coordinator_of(e)
        raise ServiceValidationError(f"No loaded config entry with id {entry_id}")

    if len(entries) == 1:
        return _coordinator_of(entries[0])
    if not entries:
        raise ServiceValidationError("No loaded config entries for this integration")
    raise ServiceValidationError(
        "Multiple config entries exist; specify entry_id in the service call"
    )


def _store_of(coordinator: AlexaShoppingCoordinator) -> CategoryStore:
    return coordinator.store


async def _persist_and_recompute(
    coordinator: AlexaShoppingCoordinator, category_map: CategoryMap
) -> None:
    await _store_of(coordinator).async_replace(category_map)
    await coordinator.async_recompute()


# --- Category handlers ----------------------------------------------------


async def _handle_recategorise_item(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    category = call.data[ATTR_CATEGORY].strip()

    valid = {c.name for c in category_map.categories} | {UNCATEGORISED}
    if category not in valid:
        raise ServiceValidationError(f"Unknown category: {category}")

    key = normalize(call.data[ATTR_ITEM_TEXT])
    if not key:
        raise ServiceValidationError("item_text normalizes to empty")

    if category == UNCATEGORISED:
        category_map.overrides.pop(key, None)
    else:
        category_map.overrides[key] = category
    # `apply_to_uid` is accepted for API-contract compatibility. It is intentionally a
    # no-op beyond the recompute below: the coordinator rebuilds the whole projection from
    # the source list + maps on every change, so the matching item (by uid or by any other
    # item sharing the normalized text) already moves immediately. There is no per-uid
    # mutation to perform because the projection is fully derived (NFR3).
    await _persist_and_recompute(coordinator, category_map)


async def _handle_add_category(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = _validate_name(call.data[ATTR_NAME])

    if name.casefold() == UNCATEGORISED.casefold():
        raise ServiceValidationError(f"{UNCATEGORISED} is reserved")
    if any(c.name.casefold() == name.casefold() for c in category_map.categories):
        raise ServiceValidationError(f"Category '{name}' already exists")

    keywords = _clean_keywords(call.data.get(ATTR_KEYWORDS, []))
    category_map.categories.append(Category(name=name, keywords=keywords))
    await _persist_and_recompute(coordinator, category_map)


async def _handle_edit_category(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = call.data[ATTR_NAME].strip()

    target = next(
        (c for c in category_map.categories if c.name.casefold() == name.casefold()), None
    )
    if target is None:
        raise ServiceValidationError(f"Category '{name}' not found")

    if ATTR_NEW_NAME in call.data:
        new_name = _validate_name(call.data[ATTR_NEW_NAME])
        if new_name.casefold() == UNCATEGORISED.casefold():
            raise ServiceValidationError(f"{UNCATEGORISED} is reserved")
        if new_name.casefold() != target.name.casefold() and any(
            c.name.casefold() == new_name.casefold() for c in category_map.categories
        ):
            raise ServiceValidationError(f"Category '{new_name}' already exists")
        old_name = target.name
        target.name = new_name
        # Migrate learned overrides pointing at the old name.
        for key, value in list(category_map.overrides.items()):
            if value == old_name:
                category_map.overrides[key] = new_name

    if ATTR_KEYWORDS in call.data:
        target.keywords = _clean_keywords(call.data[ATTR_KEYWORDS])

    await _persist_and_recompute(coordinator, category_map)


async def _handle_delete_category(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = call.data[ATTR_NAME].strip()

    target = next(
        (c for c in category_map.categories if c.name.casefold() == name.casefold()), None
    )
    if target is None:
        raise ServiceValidationError(f"Category '{name}' not found")

    category_map.categories.remove(target)
    # Overrides pointing at the deleted category self-heal on recompute; drop them so
    # they do not resurrect if the name is re-added later with a different intent.
    for key, value in list(category_map.overrides.items()):
        if value == target.name:
            del category_map.overrides[key]
    await _persist_and_recompute(coordinator, category_map)


# --- Shop handlers --------------------------------------------------------


async def _handle_assign_shop(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    shop = call.data[ATTR_SHOP].strip()

    key = normalize(call.data[ATTR_ITEM_TEXT])
    if not key:
        raise ServiceValidationError("item_text normalizes to empty")

    if shop.casefold() == NO_PREFERENCE.casefold():
        category_map.shop_overrides.pop(key, None)
    else:
        if not any(s.name.casefold() == shop.casefold() for s in category_map.shops):
            raise ServiceValidationError(f"Unknown shop: {shop}")
        # Store the canonical shop name.
        canonical = next(s.name for s in category_map.shops if s.name.casefold() == shop.casefold())
        category_map.shop_overrides[key] = canonical
    await _persist_and_recompute(coordinator, category_map)


async def _handle_add_shop(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = _validate_name(call.data[ATTR_NAME])

    if name.casefold() == NO_PREFERENCE.casefold():
        raise ServiceValidationError(f"{NO_PREFERENCE} is reserved")
    if any(s.name.casefold() == name.casefold() for s in category_map.shops):
        raise ServiceValidationError(f"Shop '{name}' already exists")

    keywords = _clean_keywords(call.data.get(ATTR_KEYWORDS, []))
    category_map.shops.append(Shop(name=name, keywords=keywords))

    if name.casefold() in _COMMON_ENGLISH_WORDS:
        _LOGGER.warning(
            "Shop name '%s' is a common word; it may match ordinary item text (tier-1 "
            "shop-name-in-text resolution). Consider a more distinctive name.",
            name,
        )
    await _persist_and_recompute(coordinator, category_map)


async def _handle_edit_shop(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = call.data[ATTR_NAME].strip()

    target = next((s for s in category_map.shops if s.name.casefold() == name.casefold()), None)
    if target is None:
        raise ServiceValidationError(f"Shop '{name}' not found")

    if ATTR_NEW_NAME in call.data:
        new_name = _validate_name(call.data[ATTR_NEW_NAME])
        if new_name.casefold() == NO_PREFERENCE.casefold():
            raise ServiceValidationError(f"{NO_PREFERENCE} is reserved")
        if new_name.casefold() != target.name.casefold() and any(
            s.name.casefold() == new_name.casefold() for s in category_map.shops
        ):
            raise ServiceValidationError(f"Shop '{new_name}' already exists")
        old_name = target.name
        target.name = new_name
        for key, value in list(category_map.shop_overrides.items()):
            if value == old_name:
                category_map.shop_overrides[key] = new_name
        if new_name.casefold() in _COMMON_ENGLISH_WORDS:
            _LOGGER.warning(
                "Shop name '%s' is a common word; it may match ordinary item text.",
                new_name,
            )

    if ATTR_KEYWORDS in call.data:
        target.keywords = _clean_keywords(call.data[ATTR_KEYWORDS])

    await _persist_and_recompute(coordinator, category_map)


async def _handle_delete_shop(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    category_map = _store_of(coordinator).category_map
    name = call.data[ATTR_NAME].strip()

    if name.casefold() == NO_PREFERENCE.casefold():
        raise ServiceValidationError(f"{NO_PREFERENCE} cannot be deleted")

    target = next((s for s in category_map.shops if s.name.casefold() == name.casefold()), None)
    if target is None:
        raise ServiceValidationError(f"Shop '{name}' not found")

    category_map.shops.remove(target)
    for key, value in list(category_map.shop_overrides.items()):
        if value == target.name:
            del category_map.shop_overrides[key]
    await _persist_and_recompute(coordinator, category_map)


async def _handle_reload_maps(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator = _resolve_coordinator(hass, call)
    await _store_of(coordinator).async_load()
    await coordinator.async_recompute()


_ServiceHandler = Callable[[HomeAssistant, ServiceCall], Awaitable[None]]

_SERVICE_TABLE: tuple[tuple[str, vol.Schema, _ServiceHandler], ...] = (
    (SERVICE_RECATEGORISE_ITEM, RECATEGORISE_ITEM_SCHEMA, _handle_recategorise_item),
    (SERVICE_ADD_CATEGORY, ADD_CATEGORY_SCHEMA, _handle_add_category),
    (SERVICE_EDIT_CATEGORY, EDIT_CATEGORY_SCHEMA, _handle_edit_category),
    (SERVICE_DELETE_CATEGORY, DELETE_CATEGORY_SCHEMA, _handle_delete_category),
    (SERVICE_ASSIGN_SHOP, ASSIGN_SHOP_SCHEMA, _handle_assign_shop),
    (SERVICE_ADD_SHOP, ADD_SHOP_SCHEMA, _handle_add_shop),
    (SERVICE_EDIT_SHOP, EDIT_SHOP_SCHEMA, _handle_edit_shop),
    (SERVICE_DELETE_SHOP, DELETE_SHOP_SCHEMA, _handle_delete_shop),
    (SERVICE_RELOAD_MAPS, RELOAD_MAPS_SCHEMA, _handle_reload_maps),
)


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register all integration services once (idempotent)."""

    def _make(handler: _ServiceHandler) -> Callable[[ServiceCall], Coroutine[Any, Any, None]]:
        async def _service(call: ServiceCall) -> None:
            try:
                await handler(hass, call)
            except (ServiceValidationError, HomeAssistantError):
                raise
            except Exception as err:
                raise HomeAssistantError(str(err)) from err

        return _service

    for name, schema, handler in _SERVICE_TABLE:
        if hass.services.has_service(DOMAIN, name):
            continue
        hass.services.async_register(DOMAIN, name, _make(handler), schema=schema)


@callback
def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove all integration services."""
    for name, _schema, _handler in _SERVICE_TABLE:
        if hass.services.has_service(DOMAIN, name):
            hass.services.async_remove(DOMAIN, name)
