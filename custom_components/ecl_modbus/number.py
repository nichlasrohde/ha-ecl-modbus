from __future__ import annotations

"""Number platform for ECL Modbus.

RW registers (writable=True) should NOT be sensors.
They are exposed as NumberEntity so users can change setpoints/overrides.

Design:
- Reuse hub + coordinator created in sensor.py (stored in hass.data[DOMAIN][entry_id]).
- Write to Modbus, then update coordinator cache to reflect the new value immediately.
- Optional: request a refresh after write (commented) if you want "read-back" validation.
"""

import logging
import struct
from dataclasses import dataclass
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


# -----------------------------------------------------------------------------
# Helpers: encode values for Modbus writes
# -----------------------------------------------------------------------------

def _float_to_regs_be(value: float) -> list[int]:
    """Encode float -> 2x16-bit registers (big endian)."""
    raw = struct.pack(">f", float(value))
    hi = int.from_bytes(raw[0:2], byteorder="big", signed=False)
    lo = int.from_bytes(raw[2:4], byteorder="big", signed=False)
    return [hi, lo]


def _coerce_step(value: float, step: float | None) -> float:
    """Snap to step if provided."""
    if not step:
        return value
    if step <= 0:
        return value
    # Snap to nearest step (avoid float noise)
    snapped = round(value / step) * step
    # Keep reasonable precision
    return float(round(snapped, 6))


def _clamp(value: float, min_v: float | None, max_v: float | None) -> float:
    if min_v is not None and value < min_v:
        return min_v
    if max_v is not None and value > max_v:
        return max_v
    return value


# -----------------------------------------------------------------------------
# Modbus hub "interface" we expect (provided by sensor.py)
# -----------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _HubWriteAPI:
    """Document the expected hub API (duck-typed)."""
    # This is only for readability; we don't instantiate this.
    pass


# -----------------------------------------------------------------------------
# Entity
# -----------------------------------------------------------------------------

class EclModbusRegisterNumber(CoordinatorEntity, NumberEntity):
    """Number entity for one writable register."""

    _attr_mode = "box"  # nice UX (also supports slider if you prefer)

    def __init__(self, coordinator, entry_title: str, hub, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self._hub = hub
        self._reg = reg

        self._attr_name = f"{entry_title} {reg.name}"
        self._attr_unique_id = f"{DOMAIN}_{reg.key}"

        # Presentation
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = reg.device_class
        self._attr_icon = reg.icon

        # Limits (from RegisterDef)
        self._attr_native_min_value = float(reg.min_value) if getattr(reg, "min_value", None) is not None else None
        self._attr_native_max_value = float(reg.max_value) if getattr(reg, "max_value", None) is not None else None
        self._attr_native_step = float(reg.step) if getattr(reg, "step", None) is not None else None

        # Extra attrs for debugging
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg.address,
            "ecl_modbus_type": reg.reg_type.value,
            "ecl_modbus_writable": True,
            "ecl_modbus_scale": getattr(reg, "scale", 1.0),
        }

    @property
    def device_info(self) -> dict:
        """Group all entities under a single ECL device."""
        return {
            "identifiers": {(DOMAIN, "ecl_modbus")},
            "name": "ECL Modbus",
            "manufacturer": "Danfoss",
            "model": "ECL 120/220",
        }

    @property
    def native_value(self) -> float | None:
        """Expose the latest value from the coordinator cache."""
        raw = self.coordinator.data.get(self._reg.key)
        if raw is None:
            return None

        try:
            # coordinator stores decoded numeric (float/int) already.
            val = float(raw)
        except (TypeError, ValueError):
            return None

        # Apply scaling for display (same as sensors)
        scale = float(getattr(self._reg, "scale", 1.0) or 1.0)
        return val * scale

    async def async_set_native_value(self, value: float) -> None:
        """Write new value to Modbus and update local cache."""
        if not getattr(self._reg, "writable", False):
            raise ValueError("Register is not writable")

        # Enforce min/max/step in HA side (controller might enforce too)
        step = self._attr_native_step
        min_v = self._attr_native_min_value
        max_v = self._attr_native_max_value

        value = _coerce_step(float(value), float(step) if step else None)
        value = _clamp(value, float(min_v) if min_v is not None else None, float(max_v) if max_v is not None else None)

        # Convert from displayed unit -> raw register value (undo scaling)
        scale = float(getattr(self._reg, "scale", 1.0) or 1.0)
        raw_to_write = value / scale if scale != 0 else value

        # Perform write in executor (pymodbus is blocking)
        await self.hass.async_add_executor_job(self._write_register_value, raw_to_write)

        # Update coordinator cache immediately so UI updates instantly
        self.coordinator.data[self._reg.key] = raw_to_write  # store RAW (unscaled) like reader does
        self.async_write_ha_state()

        # Optional: request a refresh to validate read-back (can be noisy on RS485)
        # await self.coordinator.async_request_refresh()

    def _write_register_value(self, raw_value: float) -> None:
        """Blocking write to Modbus (runs in executor)."""
        # Access manual address in docs (1-based)
        pdu_address = self._reg.address - 1

        # Ensure hub has a connected client
        self._hub._ensure_client()  # noqa: SLF001 (we control hub; keeps code simple)

        try:
            if self._reg.reg_type == RegisterType.FLOAT:
                regs = _float_to_regs_be(float(raw_value))
                result = self._hub._client.write_registers(  # noqa: SLF001
                    address=pdu_address,
                    values=regs,
                    device_id=self._hub._slave_id,  # noqa: SLF001
                )
            elif self._reg.reg_type == RegisterType.INT16:
                # INT16 write: if signed and negative -> two's complement
                val = int(round(raw_value))
                if getattr(self._reg, "signed", True) and val < 0:
                    val = (val + 0x10000) & 0xFFFF

                result = self._hub._client.write_register(  # noqa: SLF001
                    address=pdu_address,
                    value=val,
                    device_id=self._hub._slave_id,  # noqa: SLF001
                )
            else:
                raise ValueError(f"Unsupported writable type: {self._reg.reg_type}")

            if not result or getattr(result, "isError", lambda: True)():
                raise ModbusWriteError(f"Modbus write failed: {result}")

        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: write failed for %s (addr=%s): %s",
                self._reg.key,
                self._reg.address,
                exc,
            )
            # Force reconnect next time if serial is upset
            try:
                self._hub.close()
            except Exception:  # noqa: BLE001
                pass
            raise


class ModbusWriteError(Exception):
    """Raised when a Modbus write fails."""


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------

def _entry_store(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(entry.entry_id)
    if not isinstance(store, dict):
        store = {}
        domain_data[entry.entry_id] = store
    return store


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Number entities for writable registers."""
    store = _entry_store(hass, entry)

    coordinator = store.get("coordinator")
    hub = store.get("hub")
    regs: list[RegisterDef] = store.get("registers", [])

    if coordinator is None or hub is None:
        _LOGGER.error("ECL Modbus: number platform missing coordinator/hub (setup order issue)")
        return

    entry_title = entry.data.get(CONF_NAME, DEFAULT_NAME)

    # Only RW regs that are numeric
    rw_regs = [
        r for r in regs
        if getattr(r, "writable", False)
        and r.reg_type in (RegisterType.FLOAT, RegisterType.INT16)
    ]

    entities: list[NumberEntity] = [
        EclModbusRegisterNumber(coordinator, entry_title, hub, reg) for reg in rw_regs
    ]

    async_add_entities(entities, update_before_add=False)