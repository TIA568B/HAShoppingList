"""Config, options, and reconfigure flows.

Selects the source `todo` entity (preferring one on the `alexa_devices` platform),
enforces one entry per source entity, and lets the user tune display options. Changing
the source entity is a reconfigure operation (not an option) because the entry unique_id
is the source entity id.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from . import map_ops
from .const import (
    ALEXA_DEVICES_PLATFORM,
    CONF_COLLAPSE_EMPTY_CATEGORIES,
    CONF_GRACE_PERIOD_SECONDS,
    CONF_REDACT_ITEMS_IN_DIAGNOSTICS,
    CONF_SHOW_COMPLETED,
    CONF_SOURCE_ENTITY_ID,
    CONFIG_ENTRY_VERSION,
    DEFAULT_COLLAPSE_EMPTY_CATEGORIES,
    DEFAULT_GRACE_PERIOD_SECONDS,
    DEFAULT_REDACT_ITEMS_IN_DIAGNOSTICS,
    DEFAULT_SHOW_COMPLETED,
    DOMAIN,
    GRACE_PERIOD_MAX,
    GRACE_PERIOD_MIN,
    TODO_DOMAIN,
)
from .map_ops import MapValidationError

if TYPE_CHECKING:
    from .coordinator import AlexaShoppingCoordinator
    from .models import CategoryMap


def _todo_entities_by_platform(hass: Any) -> list[tuple[str, str]]:
    """Return (entity_id, friendly_name) for todo entities on the alexa_devices platform."""
    registry = er.async_get(hass)
    result: list[tuple[str, str]] = []
    for entry in registry.entities.values():
        if entry.domain != TODO_DOMAIN:
            continue
        if entry.platform != ALEXA_DEVICES_PLATFORM:
            continue
        state = hass.states.get(entry.entity_id)
        friendly = (
            state.attributes.get("friendly_name", entry.entity_id)
            if state is not None
            else entry.entity_id
        )
        result.append((entry.entity_id, friendly))
    return result


def _default_source_choice(candidates: list[tuple[str, str]]) -> str | None:
    """Prefer a todo entity whose id contains 'shopping'."""
    for entity_id, _friendly in candidates:
        if "shopping" in entity_id:
            return entity_id
    if candidates:
        return candidates[0][0]
    return None


class AlexaShoppingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = CONFIG_ENTRY_VERSION

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step: pick the source entity."""
        candidates = _todo_entities_by_platform(self.hass)

        if user_input is not None:
            source_entity_id = user_input[CONF_SOURCE_ENTITY_ID]
            await self.async_set_unique_id(source_entity_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Alexa Shopping List Categoriser",
                data={CONF_SOURCE_ENTITY_ID: source_entity_id},
            )

        if not candidates:
            return self.async_abort(reason="no_alexa_lists")

        default = _default_source_choice(candidates)
        schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE_ENTITY_ID, default=default): vol.In(
                    {entity_id: f"{friendly} ({entity_id})" for entity_id, friendly in candidates}
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the source entity, updating data and unique_id atomically."""
        entry = self._get_reconfigure_entry()
        candidates = _todo_entities_by_platform(self.hass)

        if user_input is not None:
            source_entity_id = user_input[CONF_SOURCE_ENTITY_ID]
            await self.async_set_unique_id(source_entity_id)
            # Abort only if a *different* entry already uses this source; the current
            # reconfigure entry is ignored by _abort_if_unique_id_configured.
            self._abort_if_unique_id_configured()
            return self.async_update_reload_and_abort(
                entry,
                unique_id=source_entity_id,
                data={CONF_SOURCE_ENTITY_ID: source_entity_id},
                reason="reconfigure_successful",
            )

        current = entry.data.get(CONF_SOURCE_ENTITY_ID)
        choices = {entity_id: f"{friendly} ({entity_id})" for entity_id, friendly in candidates}
        # Ensure the current source remains selectable even if not in candidates.
        if current and current not in choices:
            choices[current] = current
        schema = vol.Schema({vol.Required(CONF_SOURCE_ENTITY_ID, default=current): vol.In(choices)})
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return AlexaShoppingOptionsFlow()


_ADD_NEW = "__add_new__"


class AlexaShoppingOptionsFlow(OptionsFlow):
    """Menu-style options flow: display tuning + native taxonomy management.

    Category/shop edits are applied through the shared ``map_ops`` (the same code path the
    services use) against the integration's store, then the coordinator recomputes — so the
    view updates live. Taxonomy edits do **not** go through ``entry.options``.
    """

    def __init__(self) -> None:
        """Initialise transient per-flow state."""
        self._selected: str | None = None

    # --- helpers ----------------------------------------------------------

    def _coordinator(self) -> AlexaShoppingCoordinator | None:
        runtime = getattr(self.config_entry, "runtime_data", None)
        return runtime.coordinator if runtime is not None else None

    async def _apply(self, mutate: Callable[[CategoryMap], None]) -> None:
        """Run a map_ops mutation against the store, persist, and recompute."""
        coordinator = self._coordinator()
        if coordinator is None:
            raise MapValidationError("Integration is not loaded; try again after setup")
        category_map = coordinator.store.category_map
        mutate(category_map)
        await coordinator.store.async_replace(category_map)
        await coordinator.async_recompute()

    # --- menu -------------------------------------------------------------

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Top-level menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=[
                "display_options",
                "manage_categories",
                "manage_shops",
                "reload_defaults",
            ],
        )

    # --- display options (the original form) ------------------------------

    async def async_step_display_options(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Tune display options (grace window, toggles). Persists to entry.options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_GRACE_PERIOD_SECONDS,
                    default=options.get(CONF_GRACE_PERIOD_SECONDS, DEFAULT_GRACE_PERIOD_SECONDS),
                ): vol.All(
                    cv.positive_int,
                    vol.Range(min=GRACE_PERIOD_MIN, max=GRACE_PERIOD_MAX),
                ),
                vol.Required(
                    CONF_SHOW_COMPLETED,
                    default=options.get(CONF_SHOW_COMPLETED, DEFAULT_SHOW_COMPLETED),
                ): cv.boolean,
                vol.Required(
                    CONF_COLLAPSE_EMPTY_CATEGORIES,
                    default=options.get(
                        CONF_COLLAPSE_EMPTY_CATEGORIES, DEFAULT_COLLAPSE_EMPTY_CATEGORIES
                    ),
                ): cv.boolean,
                vol.Required(
                    CONF_REDACT_ITEMS_IN_DIAGNOSTICS,
                    default=options.get(
                        CONF_REDACT_ITEMS_IN_DIAGNOSTICS,
                        DEFAULT_REDACT_ITEMS_IN_DIAGNOSTICS,
                    ),
                ): cv.boolean,
            }
        )
        return self.async_show_form(step_id="display_options", data_schema=schema)

    # --- categories -------------------------------------------------------

    async def async_step_manage_categories(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a category to edit, or add a new one."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="not_loaded")

        if user_input is not None:
            self._selected = user_input["selection"]
            return await self.async_step_edit_category()

        names = sorted(
            (c.name for c in coordinator.store.category_map.categories), key=str.casefold
        )
        choices = {name: name for name in names}
        choices[_ADD_NEW] = "(Add new category)"
        schema = vol.Schema({vol.Required("selection"): vol.In(choices)})
        return self.async_show_form(step_id="manage_categories", data_schema=schema)

    async def async_step_edit_category(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add / rename / edit-keywords / delete a single category."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="not_loaded")
        adding = self._selected == _ADD_NEW
        current = None if adding else self._selected

        if user_input is not None:
            name = user_input.get("name", "").strip()
            keywords = _split_keywords(user_input.get("keywords", ""))
            delete = user_input.get("delete", False)
            existing = current or ""
            try:
                if adding:
                    await self._apply(lambda m: map_ops.add_category(m, name, keywords))
                elif delete:
                    await self._apply(lambda m: map_ops.delete_category(m, existing))
                else:
                    await self._apply(
                        lambda m: map_ops.edit_category(
                            m, existing, new_name=name, keywords=keywords
                        )
                    )
            except MapValidationError as err:
                return self.async_show_form(
                    step_id="edit_category",
                    data_schema=self._category_schema(current, coordinator),
                    errors={"base": "invalid"},
                    description_placeholders={"error": str(err)},
                )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="edit_category",
            data_schema=self._category_schema(current, coordinator),
        )

    def _category_schema(
        self, current: str | None, coordinator: AlexaShoppingCoordinator
    ) -> vol.Schema:
        keywords = ""
        name = ""
        if current is not None:
            cat = next(
                (c for c in coordinator.store.category_map.categories if c.name == current),
                None,
            )
            if cat is not None:
                name = cat.name
                keywords = ", ".join(cat.keywords)
        fields: dict[Any, Any] = {
            vol.Required("name", default=name): cv.string,
            vol.Optional("keywords", default=keywords): cv.string,
        }
        if current is not None:
            fields[vol.Optional("delete", default=False)] = cv.boolean
        return vol.Schema(fields)

    # --- shops ------------------------------------------------------------

    async def async_step_manage_shops(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick a shop to edit, or add a new one."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="not_loaded")

        if user_input is not None:
            self._selected = user_input["selection"]
            return await self.async_step_edit_shop()

        names = sorted((s.name for s in coordinator.store.category_map.shops), key=str.casefold)
        choices = {name: name for name in names}
        choices[_ADD_NEW] = "(Add new shop)"
        schema = vol.Schema({vol.Required("selection"): vol.In(choices)})
        return self.async_show_form(step_id="manage_shops", data_schema=schema)

    async def async_step_edit_shop(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add / rename / edit-keyword-rules / delete a single shop."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="not_loaded")
        adding = self._selected == _ADD_NEW
        current = None if adding else self._selected

        if user_input is not None:
            name = user_input.get("name", "").strip()
            keywords = _split_keywords(user_input.get("keywords", ""))
            delete = user_input.get("delete", False)
            existing = current or ""
            try:
                if adding:
                    await self._apply(lambda m: map_ops.add_shop(m, name, keywords))
                elif delete:
                    await self._apply(lambda m: map_ops.delete_shop(m, existing))
                else:
                    await self._apply(
                        lambda m: map_ops.edit_shop(m, existing, new_name=name, keywords=keywords)
                    )
            except MapValidationError as err:
                return self.async_show_form(
                    step_id="edit_shop",
                    data_schema=self._shop_schema(current, coordinator),
                    errors={"base": "invalid"},
                    description_placeholders={"error": str(err)},
                )
            return await self.async_step_init()

        return self.async_show_form(
            step_id="edit_shop",
            data_schema=self._shop_schema(current, coordinator),
        )

    def _shop_schema(
        self, current: str | None, coordinator: AlexaShoppingCoordinator
    ) -> vol.Schema:
        keywords = ""
        name = ""
        if current is not None:
            shop = next(
                (s for s in coordinator.store.category_map.shops if s.name == current),
                None,
            )
            if shop is not None:
                name = shop.name
                keywords = ", ".join(shop.keywords)
        fields: dict[Any, Any] = {
            vol.Required("name", default=name): cv.string,
            vol.Optional("keywords", default=keywords): cv.string,
        }
        if current is not None:
            fields[vol.Optional("delete", default=False)] = cv.boolean
        return vol.Schema(fields)

    # --- reload defaults --------------------------------------------------

    async def async_step_reload_defaults(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm, then replace categories/shops from the shipped defaults (keep learning)."""
        coordinator = self._coordinator()
        if coordinator is None:
            return self.async_abort(reason="not_loaded")

        if user_input is not None:
            if user_input.get("confirm"):
                await coordinator.store.async_reload_defaults()
                await coordinator.async_recompute()
            return await self.async_step_init()

        schema = vol.Schema({vol.Required("confirm", default=False): cv.boolean})
        return self.async_show_form(step_id="reload_defaults", data_schema=schema)


def _split_keywords(raw: str) -> list[str]:
    """Split a comma/newline-separated keyword string into a list."""
    parts: list[str] = []
    for chunk in raw.replace("\n", ",").split(","):
        stripped = chunk.strip()
        if stripped:
            parts.append(stripped)
    return parts
