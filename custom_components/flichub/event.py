"""Event platform for Flic Hub."""
from __future__ import annotations

from homeassistant.components.event import EventEntity, EventDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import FlicHubEntryData
from .const import (
    DOMAIN,
    DATA_BUTTONS,
    SIGNAL_BUTTON_EVENT,
    EVENT_DATA_SERIAL_NUMBER,
    EVENT_DATA_CLICK_TYPE,
    EVENT_DATA_NAME,
)

EVENT_TYPES = ["single_press", "double_press", "hold"]
CLICK_MAP = {"single": "single_press", "double": "double_press", "hold": "hold"}

async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    data_entry: FlicHubEntryData = hass.data[DOMAIN][entry.entry_id]
    buttons = data_entry.coordinator.data[DATA_BUTTONS]

    entities: list[FlicHubButtonEventEntity] = []
    for serial, button in buttons.items():
        entities.append(FlicHubButtonEventEntity(entry, serial, button.name))

    async_add_entities(entities, update_before_add=False)


class FlicHubButtonEventEntity(EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = EVENT_TYPES
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, serial_number: str, name: str) -> None:
        self._entry = entry
        self._serial_number = serial_number
        self._attr_unique_id = f"{serial_number}_event"
        self._attr_name = name
        self._unsub = None

    async def async_added_to_hass(self) -> None:
        signal = f"{SIGNAL_BUTTON_EVENT}_{self._entry.entry_id}"

        @callback
        def _handle(data: dict) -> None:
            if data.get(EVENT_DATA_SERIAL_NUMBER) != self._serial_number:
                return

            raw = data.get(EVENT_DATA_CLICK_TYPE)
            event_type = CLICK_MAP.get(raw)
            if not event_type:
                return

            # Optional: include the original payload for templating
            extra = {
                "name": data.get(EVENT_DATA_NAME),
                "click_type_raw": raw,
            }

            self._trigger_event(event_type, extra)
            self.async_write_ha_state()

        self._unsub = async_dispatcher_connect(self.hass, signal, _handle)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
