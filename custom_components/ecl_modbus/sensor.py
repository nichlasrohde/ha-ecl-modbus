from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .registers import RegisterDef, RegisterType

_LOGGER = logging.getLogger(__name__)


def _decimals_from_step(step: float | None) -> int | None:
    """Return number of decimals implied by step (e.g. 0.1 -> 1, 0.01 -> 2)."""
    if step is None:
        return None
    try:
        d = Decimal(str(step)).normalize()
    except (InvalidOperation, ValueError):
        return None
    exp = d.as_tuple().exponent
    return abs(exp) if exp < 0 else 0


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

        # If we show mapped text, don't let HA treat it as a measurement/statistics sensor
        if getattr(reg, "value_map", None):
            self._attr_state_class = None

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
        if data is None:
            return None

        raw = data.get(self._reg.key)
        if raw is None:
            return None

        # Strings
        if self._reg.reg_type in (RegisterType.STRING16, RegisterType.STRING32):
            return raw

        # Enum/token mapping (show text instead of number)
        value_map = getattr(self._reg, "value_map", None)
        if value_map:
            try:
                code = int(float(raw))
            except (TypeError, ValueError):
                return None
            return value_map.get(code, str(code))

        scale = float(getattr(self._reg, "scale", 1.0) or 1.0)

        # Integer-ish types: keep integers as integers (avoid 1234.0)
        if self._reg.reg_type in (RegisterType.INT16, RegisterType.UINT32):
            try:
                n = int(raw)
            except (TypeError, ValueError):
                try:
                    n = int(float(raw))
                except (TypeError, ValueError):
                    return None

            if scale == 1.0:
                return n

            # If scaling is used for an int-type, return scaled value with sensible rounding
            value = n * scale
            decimals = _decimals_from_step(getattr(self._reg, "step", None))
            if decimals is not None:
                return round(value, decimals)
            return round(value, 6)

        # Float types (and any other numeric we treat as float)
        try:
            value = float(raw) * scale
        except (TypeError, ValueError):
            return None

        # Pretty rounding for common types
        if self._reg.device_class == "temperature":
            return round(value, 1)
        if self._reg.unit == "%":
            return round(value, 1)

        # Avoid ugly float representation (e.g. 30.100000381...)
        decimals = _decimals_from_step(getattr(self._reg, "step", None))
        if decimals is not None:
            return round(value, decimals)

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