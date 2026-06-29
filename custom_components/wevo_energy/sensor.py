from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WevoStateSensor(coordinator, entry),
            WevoChargingRateSensor(coordinator, entry),
            WevoSessionEnergySensor(coordinator, entry),
            WevoMonthlyEnergySensor(coordinator, entry),
        ],
        True,
    )


class WevoBaseSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry: ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"


class WevoStateSensor(WevoBaseSensor):
    _attr_name = "Wevo Charging State"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "charging_state")

    @property
    def native_value(self):
        return self.coordinator.data.get("state")


class WevoChargingRateSensor(WevoBaseSensor):
    _attr_name = "Wevo Charging Speed"
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "charging_speed_kw")

    @property
    def native_value(self):
        value = self.coordinator.data.get("rate_kw")
        return round(float(value), 3) if value is not None else None


class WevoSessionEnergySensor(WevoBaseSensor):
    _attr_name = "Wevo Session Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "session_energy_kwh")

    @property
    def native_value(self):
        value = self.coordinator.data.get("total_energy_kwh")
        return round(float(value), 3) if value is not None else None


class WevoMonthlyEnergySensor(WevoBaseSensor):
    _attr_name = "Wevo Monthly Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "monthly_energy_kwh")

    @property
    def native_value(self):
        value = self.coordinator.data.get("monthly_energy_kwh")
        return round(float(value), 3) if value is not None else None

    @property
    def extra_state_attributes(self):
        return {
            "session_count": self.coordinator.data.get("monthly_session_count"),
        }
