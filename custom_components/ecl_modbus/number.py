from __future__ import annotations

"""Number platform for ECL Modbus.

Writable (RW) registers are exposed as NumberEntity so users can change setpoints.

Design:
- Hub + coordinator are created in __init__.py and stored in hass.data[DOMAIN][entry_id].
- Write uses hub.write_float / hub.write_int16 (no private attributes).
- After write, we update local coordinator cache (if available) and optionally refresh.
"""

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
from .registers import RegisterDef, RegisterType

_LOGGER = logging.getLogger(__name__)


def _coerce_step(value: float, step: float | None) -> float:
    if not step or step <= 0:
        return value
    snapped = round(value / step) * step
    return float(round(snapped, 6))


def _clamp(value: float, min_v: float | None, max_v: float | None) -> float:
    if min_v is not None and value < min_v:
        return min_v
    if max_v is not None and value > max_v:
        return max_v
    return value


def _entry_store(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(entry.entry_id)
    if not isinstance(store, dict):
        store = {}
        domain_data[entry.entry_id] = store
    return store


class EclModbusRegisterNumber(CoordinatorEntity, NumberEntity):
    """Number entity for one writable register."""

    _attr_mode = "box"

    def __init__(self, coordinator, entry_title: str, hub, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self._hub = hub
        self._reg = reg

        self._attr_name = f"{entry_title} {reg.name}"
        self._attr_unique_id = f"{DOMAIN}_{reg.key}"

        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = reg.device_class
        self._attr_icon = reg.icon

        self._attr_native_min_value = (
            float(reg.min_value) if getattr(reg, "min_value", None) is not None else None
        )
        self._attr_native_max_value = (
            float(reg.max_value) if getattr(reg, "max_value", None) is not None else None
        )
        self._attr_native_step = (
            float(reg.step) if getattr(reg, "step", None) is not None else None
        )

        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg.address,
            "ecl_modbus_type": reg.reg_type.value,
            "ecl_modbus_writable": True,
            "ecl_modbus_scale": getattr(reg, "scale", 1.0),
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
    def native_value(self) -> float | None:
        if not self.coordinator.data:
            return None

        raw = self.coordinator.data.get(self._reg.key)
        if raw is None:
            return None

        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None

        scale = float(getattr(self._reg, "scale", 1.0) or 1.0)
        value = val * scale

        # --- Presentation rounding ---
        step = getattr(self._reg, "step", None)
        if step:
            # Number of decimals derived from step (e.g. 0.1 -> 1, 0.01 -> 2)
            decimals = max(0, len(str(step).split(".")[-1]))
            return round(value, decimals)

        # Sensible defaults
        if self._reg.device_class == "temperature":
            return round(value, 1)

        return round(value, 2)

    async def async_set_native_value(self, value: float) -> None:
        if not getattr(self._reg, "writable", False):
            raise ValueError("Register is not writable")

        # Enforce HA-side min/max/step
        step = self._attr_native_step
        min_v = self._attr_native_min_value
        max_v = self._attr_native_max_value

        value = _coerce_step(float(value), float(step) if step else None)
        value = _clamp(
            value,
            float(min_v) if min_v is not None else None,
            float(max_v) if max_v is not None else None,
        )

        # Undo scaling for raw write
        scale = float(getattr(self._reg, "scale", 1.0) or 1.0)
        raw_to_write = value / scale if scale != 0 else value

        # Blocking write in executor
        await self.hass.async_add_executor_job(self._write_register_value, raw_to_write)

        # Update coordinator cache immediately if possible
        if self.coordinator.data is None:
            # Prevent NoneType issues during startup edge cases
            self.coordinator.data = {}

        self.coordinator.data[self._reg.key] = raw_to_write
        self.async_write_ha_state()

        # Optional but recommended: read-back validation
        # If RS485 gets noisy, you can comment this out.
        await self.coordinator.async_request_refresh()

    def _write_register_value(self, raw_value: float) -> None:
        """Blocking write (runs in executor)."""
        try:
            if self._reg.reg_type == RegisterType.FLOAT:
                self._hub.write_float(self._reg.address, float(raw_value))
            elif self._reg.reg_type == RegisterType.INT16:
                self._hub.write_int16(self._reg.address, int(round(raw_value)))
            else:
                raise ValueError(f"Unsupported writable type: {self._reg.reg_type}")
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: write failed for %s (addr=%s): %s",
                self._reg.key,
                self._reg.address,
                exc,
            )
            # Force reconnect next time
            try:
                self._hub.close()
            except Exception:  # noqa: BLE001
                pass
            raise


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    store = _entry_store(hass, entry)

    coordinator = store.get("coordinator")
    hub = store.get("hub")
    regs: list[RegisterDef] = store.get("registers", [])

    if coordinator is None or hub is None:
        _LOGGER.error("ECL Modbus: number platform missing coordinator/hub (setup order issue)")
        return

    entry_title = entry.data.get(CONF_NAME, DEFAULT_NAME)

    rw_regs = [
        r for r in regs
        if getattr(r, "writable", False)
        and r.reg_type in (RegisterType.FLOAT, RegisterType.INT16)
    ]

    async_add_entities(
        [EclModbusRegisterNumber(coordinator, entry_title, hub, r) for r in rw_regs],
        update_before_add=False,
    )