from __future__ import annotations
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN
from .coordinator import ChargeSentryCoordinator

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: ChargeSentryCoordinator = hass.data[DOMAIN][entry.entry_id]

    device = DeviceInfo(
        identifiers={(DOMAIN, coordinator.serial)},
        name=f"ChargeSentry {coordinator.serial}",
        manufacturer="ChargeSentry",
        model="OCPP via REST",
        sw_version="server-2025.10",
    )

    async_add_entities([
        ChargerPowerSensor(coordinator, device),
        ChargerStatusSensor(coordinator, device),
        ChargerEnergySensor(coordinator, device),
    ])

class BaseCS(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator: ChargeSentryCoordinator, device: DeviceInfo):
        super().__init__(coordinator)
        self._attr_device_info = device

    @property
    def available(self) -> bool:
        # consider offline if coordinator data missing
        return bool(self.coordinator.data)

class ChargerPowerSensor(BaseCS):
    _attr_name = "Power"
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = "measurement"
    _attr_unique_id = None  # set in __init__

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_power"

    @property
    def native_value(self):
        return self.coordinator.data.get("power_w") if self.coordinator.data else None

class ChargerStatusSensor(BaseCS):
    _attr_name = "Status"
    _attr_unique_id = None

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_status"
        self._attr_icon = "mdi:ev-station"

    @property
    def native_value(self):
        return self.coordinator.data.get("status") if self.coordinator.data else None

class ChargerEnergySensor(BaseCS):
    _attr_name = "Energy"
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = "total_increasing"
    _attr_unique_id = None

    def __init__(self, coordinator, device):
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.serial}_energy"

    @property
    def native_value(self):
        return self.coordinator.data.get("lifetime_kwh") if self.coordinator.data else None
