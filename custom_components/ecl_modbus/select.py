from __future__ import annotations

"""Select platform for ECL Modbus.

Token/enum registers (e.g. 0=Auto, 1=Comfort, 2=Saving...) should be exposed
as SelectEntity so users can choose a mode from a dropdown.

Design:
- Reuse hub + coordinator created in __init__.py (stored in hass.data[DOMAIN][entry_id]).
- Write to Modbus, then update coordinator cache so UI updates immediately.
"""

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, DEFAULT_NAME
from .registers import RegisterDef, RegisterType

_LOGGER = logging.getLogger(__name__)


def _entry_store(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(entry.entry_id)
    if not isinstance(store, dict):
        store = {}
        domain_data[entry.entry_id] = store
    return store


class ModbusWriteError(Exception):
    """Raised when a Modbus write fails."""


class EclModbusRegisterSelect(CoordinatorEntity, SelectEntity):
    """Select entity for one token/enum register."""

    def __init__(self, coordinator, entry_title: str, hub, reg: RegisterDef) -> None:
        super().__init__(coordinator)
        self._hub = hub
        self._reg = reg

        self._attr_name = f"{entry_title} {reg.name}"
        self._attr_unique_id = f"{DOMAIN}_{reg.key}"

        self._attr_icon = reg.icon

        # Expect reg.value_map: Mapping[int, str]
        self._options_map: dict[int, str] = dict(getattr(reg, "value_map", {}) or {})
        self._reverse_map: dict[str, int] = {label: code for code, label in self._options_map.items()}

        # HA expects list[str]
        self._attr_options = [self._options_map[k] for k in sorted(self._options_map)]

        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg.address,
            "ecl_modbus_type": reg.reg_type.value,
            "ecl_modbus_writable": True,
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
    def current_option(self) -> str | None:
        """Return current option label from coordinator cache."""
        if not self.coordinator.data:
            return None

        raw = self.coordinator.data.get(self._reg.key)
        if raw is None:
            return None

        try:
            code = int(raw)
        except (TypeError, ValueError):
            return None

        return self._options_map.get(code)

    async def async_select_option(self, option: str) -> None:
        """Write selected option to Modbus and update local cache."""
        if option not in self._reverse_map:
            raise ValueError(f"Unknown option: {option}")

        if not getattr(self._reg, "writable", False):
            raise ValueError("Register is not writable")

        code = int(self._reverse_map[option])

        await self.hass.async_add_executor_job(self._write_register_value, code)

        # Update coordinator cache immediately (store RAW like reader does)
        if self.coordinator.data is not None:
            self.coordinator.data[self._reg.key] = code

        self.async_write_ha_state()
        # Optional validation refresh:
        # await self.coordinator.async_request_refresh()

    def _write_register_value(self, code: int) -> None:
        """Blocking Modbus write (runs in executor)."""
        pdu_address = self._reg.address - 1

        # Ensure hub has a connected client
        self._hub._ensure_client()  # noqa: SLF001

        try:
            # Token registers are typically one 16-bit value
            # Use write_register for INT16/UINT16 style registers
            if self._reg.reg_type not in (RegisterType.INT16,):
                # If you later add RegisterType.UINT16, include it here.
                _LOGGER.warning(
                    "ECL Modbus: select write on non-INT16 reg_type (%s) for %s",
                    self._reg.reg_type,
                    self._reg.key,
                )

            result = self._hub._client.write_register(  # noqa: SLF001
                address=pdu_address,
                value=int(code) & 0xFFFF,
                device_id=self._hub._slave_id,  # noqa: SLF001
            )

            if not result or getattr(result, "isError", lambda: True)():
                raise ModbusWriteError(f"Modbus write failed: {result}")

        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: write failed for %s (addr=%s): %s",
                self._reg.key,
                self._reg.address,
                exc,
            )
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
    """Set up Select entities for token/enum registers."""
    store = _entry_store(hass, entry)

    coordinator = store.get("coordinator")
    hub = store.get("hub")
    regs: list[RegisterDef] = store.get("registers", [])

    if coordinator is None or hub is None:
        _LOGGER.error("ECL Modbus: select platform missing coordinator/hub (setup order issue)")
        return

    entry_title = entry.data.get(CONF_NAME, DEFAULT_NAME)

    select_regs = [
        r for r in regs
        if getattr(r, "writable", False)
        and getattr(r, "value_map", None)  # must have token map
    ]

    entities: list[SelectEntity] = [
        EclModbusRegisterSelect(coordinator, entry_title, hub, reg) for reg in select_regs
    ]

    async_add_entities(entities, update_before_add=False)