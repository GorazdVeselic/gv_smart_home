"""Skupna naprava in osnovni razred entitet."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SmartEvCoordinator, Snapshot


class SmartEvEntity(CoordinatorEntity[SmartEvCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartEvCoordinator, key: str, domain: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_translation_key = key
        # id ne sme biti odvisen od jezika prevedenega imena (plošča in avtomatizacije ga uporabljajo)
        self.entity_id = f"{domain}.ev_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="EV",
            manufacturer="gv_smart_home",
            model="Smart EV Charging",
        )

    @property
    def snap(self) -> Snapshot | None:
        return self.coordinator.data
