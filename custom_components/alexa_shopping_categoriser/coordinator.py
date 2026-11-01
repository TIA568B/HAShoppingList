"""DataUpdateCoordinator that reads the source list and builds the projection.

Event-driven: the primary trigger is a state-change listener on the source todo entity;
``update_interval`` is a slow safety-net poll. All recomputation lives here -- entities
and services never categorise themselves.
"""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_COLLAPSE_EMPTY_CATEGORIES,
    CONF_GRACE_PERIOD_SECONDS,
    CONF_SHOW_COMPLETED,
    CONF_SOURCE_ENTITY_ID,
    DEBOUNCE_SECONDS,
    DEFAULT_COLLAPSE_EMPTY_CATEGORIES,
    DEFAULT_GRACE_PERIOD_SECONDS,
    DEFAULT_SHOW_COMPLETED,
    DOMAIN,
    SAFETY_POLL_MINUTES,
    TODO_DOMAIN,
)
from .models import SourceItem
from .projection import Projection, build_projection
from .repairs import async_clear_source_missing, async_raise_source_missing

if TYPE_CHECKING:
    from .store import CategoryStore

_LOGGER = logging.getLogger(__name__)

_GET_ITEMS_SERVICE = "get_items"


class AlexaShoppingCoordinator(DataUpdateCoordinator[Projection]):
    """Coordinator owning the categorised projection."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: CategoryStore,
    ) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.store = store
        self.source_entity_id: str = entry.data[CONF_SOURCE_ENTITY_ID]
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(minutes=SAFETY_POLL_MINUTES),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=DEBOUNCE_SECONDS,
                immediate=False,
            ),
        )

    @callback
    def async_subscribe_source_changes(self) -> Any:
        """Subscribe to source entity state changes; return the unsubscribe callback."""

        @callback
        def _handle_state_change(event: Event[EventStateChangedData]) -> None:
            self.hass.async_create_task(self.async_request_refresh())

        return async_track_state_change_event(
            self.hass, [self.source_entity_id], _handle_state_change
        )

    async def _async_update_data(self) -> Projection:
        """Read source items and build the projection."""
        source_state = self.hass.states.get(self.source_entity_id)

        if source_state is None or source_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            async_raise_source_missing(self.hass, self.entry.entry_id, self.source_entity_id)
            # At first refresh this becomes ConfigEntryNotReady (see below); at runtime
            # it is a transient failure.
            if self.data is None:
                raise ConfigEntryNotReady(
                    f"Source entity {self.source_entity_id} is not available yet"
                )
            raise UpdateFailed(f"Source entity {self.source_entity_id} is unavailable")

        try:
            items = await self._async_read_source_items()
        except ConfigEntryNotReady:
            raise
        except Exception as err:
            raise UpdateFailed(f"Error reading {self.source_entity_id}: {err}") from err

        # Source is healthy: clear any prior repair issue.
        async_clear_source_missing(self.hass, self.entry.entry_id)

        options = self.entry.options
        grace = int(options.get(CONF_GRACE_PERIOD_SECONDS, DEFAULT_GRACE_PERIOD_SECONDS))
        show_completed = bool(options.get(CONF_SHOW_COMPLETED, DEFAULT_SHOW_COMPLETED))
        collapse = bool(
            options.get(CONF_COLLAPSE_EMPTY_CATEGORIES, DEFAULT_COLLAPSE_EMPTY_CATEGORIES)
        )

        projection = build_projection(
            items,
            self.store.category_map,
            self.source_entity_id,
            grace_period_seconds=grace,
            show_completed=show_completed,
            collapse_empty_categories=collapse,
            last_synced=dt_util.now().isoformat(),
        )
        return projection

    async def _async_read_source_items(self) -> list[SourceItem]:
        """Call ``todo.get_items`` and map the response into SourceItems."""
        response = await self.hass.services.async_call(
            TODO_DOMAIN,
            _GET_ITEMS_SERVICE,
            {"status": ["needs_action", "completed"]},
            target={"entity_id": self.source_entity_id},
            blocking=True,
            return_response=True,
        )

        if not isinstance(response, dict):
            raise UpdateFailed("Unexpected get_items response shape")

        entity_payload = response.get(self.source_entity_id)
        if not isinstance(entity_payload, dict):
            raise UpdateFailed("get_items response missing payload for source entity")

        raw_items = entity_payload.get("items")
        if not isinstance(raw_items, list):
            raise UpdateFailed("get_items response missing items for source entity")

        items: list[SourceItem] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                _LOGGER.debug("Skipping malformed source item: %r", raw)
                continue
            uid = raw.get("uid")
            summary = raw.get("summary")
            if not isinstance(uid, str) or not isinstance(summary, str):
                _LOGGER.debug("Skipping source item with missing uid/summary: %r", raw)
                continue
            items.append(
                SourceItem(
                    uid=uid,
                    name=summary,
                    completed=raw.get("status") == "completed",
                )
            )
        return items

    async def async_recompute(self) -> None:
        """Rebuild the projection immediately after a map change."""
        await self.async_refresh()
