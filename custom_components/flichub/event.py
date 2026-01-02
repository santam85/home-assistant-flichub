"""Event platform for Flic Hub."""
from __future__ import annotations

from homeassistant.components.event import EventEntity, EventDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo, format_mac
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pyflichub.button import FlicButton
from pyflichub.flichub import FlicHubInfo

from . import FlicHubEntryData
from .const import (
    DOMAIN,
    SIGNAL_BUTTON_EVENT,
    EVENT_DATA_SERIAL_NUMBER,
    EVENT_DATA_CLICK_TYPE,
    EVENT_DATA_NAME,
)

EVENT_TYPES = ["single_press", "double_press", "hold"]
CLICK_MAP = {"single": "single_press", "double": "double_press", "hold": "hold"}

class FlicHubButtonEventEntity(EventEntity):
    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = EVENT_TYPES
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, coordinator, config_entry, button: FlicButton, flic_hub: FlicHubInfo):
        super().__init__(coordinator, config_entry, button.serial_number, flic_hub)
        self._attr_unique_id = f"{self.serial_number}-event"
        self._serial_number = button.serial_number
        self._attr_name = button.name
        self._button = button
        self._flic_hub = flic_hub
        self._click_type = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
            manufacturer="Flic",
            model="Flic Button",
            name=self._attr_name,
            via_device=(DOMAIN, self.mac_address),
        )

    @property
    def mac_address(self):
        """Return a unique ID to use for this entity."""
        if self.flic_hub.has_ethernet() and self._ip_address == self.flic_hub.ethernet.ip:
            return format_mac(self.flic_hub.ethernet.mac)
        if self.flic_hub.has_wifi() and self._ip_address == self.flic_hub.wifi.ip:
            return format_mac(self.flic_hub.wifi.mac)

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
