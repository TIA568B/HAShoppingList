"""Config, options, and reconfigure flows.

Selects the source `todo` entity (preferring one on the `alexa_devices` platform),
enforces one entry per source entity, and lets the user tune display options. Changing
the source entity is a reconfigure operation (not an option) because the entry unique_id
is the source entity id.
"""

from __future__ import annotations

from typing import Any

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
            self._abort_if_unique_id_mismatch(reason="already_configured")
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


class AlexaShoppingOptionsFlow(OptionsFlow):
    """Handle the options flow (display tuning only; not the source entity)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
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
        return self.async_show_form(step_id="init", data_schema=schema)
