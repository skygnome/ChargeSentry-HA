from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN
from .coordinator import ChargeSentryDataUpdateCoordinator  # <- match coordinator name

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ChargeSentryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    device = DeviceInfo(
        identifiers={(DOMAIN, coordinator.serial)},  # stable device id per charger
        name="ChargeSentry",
        manufacturer="ChargeSentry",
        model="OCPP via REST",
        sw_version="server-2025.10",
    )

    async_add_entities(
        [
            ChargerPowerSensor(coordinator, device),
            ChargerStatusSensor(coordinator, device),
            ChargerEnergySensor(coordinator, device),
        ]
    )

class BaseCS(CoordinatorEntity[ChargeSentryDataUpdateCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ChargeSentryDataUpdateCoordinator, device: DeviceInfo):
        super().__init__(coordinator)
        self._attr_device_info = device

    @property
    def available(self) -> bool:
        # Be conservative: only available if the update succeeded and we have data
        return bool(self.coordinator.last_update_success and self.coordinator.data)

    @property
    def _live(self) -> dict | None:
        data = self.coordinator.data or {}
        return data.get("live")

    @property
    def _energy(self) -> dict | None:
        data = self.coordinator.data or {}
        return data.get("energy")

class ChargerPowerSensor(BaseCS):
    _attr_name = "Power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_power"

    @property
    def native_value(self):
        live = self._live
        return None if not live else live.get("power_w")

class ChargerStatusSensor(BaseCS):
    _attr_name = "Status"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_status"

    @property
    def native_value(self):
        live = self._live
        return None if not live else live.get("status")

class ChargerEnergySensor(BaseCS):
    _attr_name = "Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_energy"

    @property
    def native_value(self):
        # Use lifetime kWh from your energy endpoint (as per your API sketch)
        energy = self._energy
        return None if not energy else energy.get("lifetime_kwh")
