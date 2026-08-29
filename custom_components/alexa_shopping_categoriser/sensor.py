"""The categorised shopping list sensor entity.

Exposes the derived projection as attributes for the card. State is the count of
unchecked items. It is coordinator-driven (``should_poll = False``) and attaches to a
service device -- never the Alexa device.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AlexaShoppingCoordinator

if TYPE_CHECKING:
    from . import AlexaShoppingConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlexaShoppingConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the categorised sensor from a config entry."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([CategorisedShoppingListSensor(coordinator, entry)])


class CategorisedShoppingListSensor(CoordinatorEntity[AlexaShoppingCoordinator], SensorEntity):
    """A sensor exposing the shop-primary categorised projection."""

    _attr_has_entity_name = True
    _attr_name = "Categorised Shopping List"
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: AlexaShoppingCoordinator,
        entry: AlexaShoppingConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_categorised"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Alexa Shopping List Categoriser",
            manufacturer="alexa_shopping_categoriser",
            model="Shopping List Categoriser",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> int | None:
        """Return the count of unchecked items."""
        if self.coordinator.data is None:
            return None
        return int(self.coordinator.data["total_unchecked"])

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the projection payload (the frontend contract)."""
        data = self.coordinator.data
        if data is None:
            return None
        # The projection TypedDict is already the attribute contract.
        return dict(data)

    @property
    def available(self) -> bool:
        """Availability follows coordinator success and source entity state."""
        if not self.coordinator.last_update_success:
            return False
        source_state = self.hass.states.get(self.coordinator.source_entity_id)
        return source_state is not None and source_state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
