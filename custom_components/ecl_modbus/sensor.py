from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .registers import RegisterDef, RegisterType

_LOGGER = logging.getLogger(__name__)


class EclModbusRegisterSensor(CoordinatorEntity, SensorEntity):
    """Generic sensor exposing one read-only register."""

    def __init__(self, coordinator, entry_title: str, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self._reg = reg
        self._attr_name = f"{entry_title} {reg.name}"
        self._attr_unique_id = f"{DOMAIN}_{reg.key}"
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = reg.device_class
        self._attr_state_class = reg.state_class
        self._attr_icon = reg.icon
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg.address,
            "ecl_modbus_type": reg.reg_type.value,
            "ecl_modbus_writable": getattr(reg, "writable", False),
        }

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, "ecl_modbus")},
            "name": "ECL Modbus",
            "manufacturer": "Danfoss",
            "model": "ECL 120/220",
        }

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if not data:
            return None

        raw = data.get(self._reg.key)
        if raw is None:
            return None

        # Strings
        if self._reg.reg_type in (RegisterType.STRING16, RegisterType.STRING32):
            return raw

        # Enum/token mapping (status/tilstande)
        enum_map = getattr(self._reg, "enum", None)
        if enum_map and isinstance(raw, (int, float)):
            return enum_map.get(int(raw), str(int(raw)))

        # Numeric types
        try:
            value = float(raw) * float(getattr(self._reg, "scale", 1.0) or 1.0)
        except (TypeError, ValueError):
            return None

        # Pretty rounding
        if self._reg.device_class == "temperature":
            return round(value, 1)
        if self._reg.unit == "%":
            return round(value, 1)

        # Avoid ugly float representation (e.g. 30.100000381...)
        step = getattr(self._reg, "step", None)
        if step:
            try:
                step_f = float(step)
                if step_f > 0:
                    decimals = max(0, len(str(step_f).split(".")[1]) if "." in str(step_f) else 0)
                    return round(value, decimals)
            except Exception:
                pass

        # Default numeric output
        return round(value, 6)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = hass.data[DOMAIN][entry.entry_id]
    coordinator = store["coordinator"]
    entry_title: str = store["entry_title"]
    regs: list[RegisterDef] = store["registers"]

    ro_regs = [r for r in regs if not getattr(r, "writable", False)]
    async_add_entities(
        [EclModbusRegisterSensor(coordinator, entry_title, r) for r in ro_regs],
        update_before_add=False,
    )