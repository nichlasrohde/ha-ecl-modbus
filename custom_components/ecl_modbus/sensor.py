from __future__ import annotations

"""Sensor platform for the ECL Modbus integration.

This module is intentionally built around a single register definition list
(`registers.py`). That makes it easy to add new registers without copy/paste
of entity classes and setup logic.

The integration uses a DataUpdateCoordinator to poll all enabled registers at
one global interval. This avoids serial port locking issues and improves RS485
stability compared to per-entity polling.
"""

import logging
import struct
import threading
from datetime import timedelta
from typing import Any

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    CONF_BAUDRATE,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
)
from .registers import ALL_REGISTERS, RegisterDef, RegisterType, option_key

_LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Modbus hub (serial client + low level readers)
# -----------------------------------------------------------------------------

class EclModbusHub:
    """Handle Modbus communication with the ECL controller."""

    def __init__(self, port: str, baudrate: int, slave_id: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._slave_id = slave_id
        self._client: ModbusSerialClient | None = None
        self._lock = threading.Lock()

    def _ensure_client(self) -> None:
        """Ensure that the Modbus client is initialized and connected."""
        if self._client is not None and self._client.connected:
            return

        _LOGGER.info(
            "ECL Modbus: creating ModbusSerialClient on %s @ %s baud",
            self._port,
            self._baudrate,
        )

        # Close any previous client
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

        self._client = ModbusSerialClient(
            port=self._port,
            baudrate=self._baudrate,
            parity="E",  # ECL default: Even parity
            stopbits=1,
            bytesize=8,
            timeout=2,
        )

        if not self._client.connect():
            raise ModbusIOException(f"Could not connect to {self._port}")

    def close(self) -> None:
        """Explicitly close the Modbus client."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    def _read_registers(self, reg_address_manual: int, count: int) -> list[int] | None:
        """Read raw holding registers.

        ECL documentation uses 1-based manual addresses.
        pymodbus expects 0-based PDU addresses.
        """
        with self._lock:
            try:
                self._ensure_client()
                pdu_address = reg_address_manual - 1
                result = self._client.read_holding_registers(
                    address=pdu_address,
                    count=count,
                    device_id=self._slave_id,
                )
            except ModbusIOException as exc:
                _LOGGER.error(
                    "ECL Modbus: ModbusIOException reading %s: %s",
                    reg_address_manual,
                    exc,
                )
                # Force reconnect next time
                self.close()
                return None
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "ECL Modbus: unexpected error reading %s: %s",
                    reg_address_manual,
                    exc,
                )
                self.close()
                return None

        if not result or getattr(result, "isError", lambda: True)():
            _LOGGER.warning(
                "ECL Modbus: Modbus error or no response for address %s: %s",
                reg_address_manual,
                result,
            )
            return None

        regs = getattr(result, "registers", None)
        if not regs:
            _LOGGER.warning(
                "ECL Modbus: empty register response for address %s: %s",
                reg_address_manual,
                result,
            )
            return None

        return list(regs)

    def read_float(self, reg_address_manual: int) -> float | None:
        """Read a 32-bit float from two holding registers."""
        regs = self._read_registers(reg_address_manual, count=2)
        if regs is None:
            return None
        try:
            return self._regs_to_float_be(regs)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: failed to convert regs %s at addr %s to float: %s",
                regs,
                reg_address_manual,
                exc,
            )
            return None

    def read_int16(self, reg_address_manual: int, signed: bool = True) -> int | None:
        """Read a single 16-bit register as int."""
        regs = self._read_registers(reg_address_manual, count=1)
        if regs is None:
            return None
        raw = regs[0]
        if signed and raw > 0x7FFF:
            raw -= 0x10000
        return raw

    def read_string(self, reg_address_manual: int, reg_count: int) -> str | None:
        """Read an ASCII string stored across multiple registers."""
        regs = self._read_registers(reg_address_manual, count=reg_count)
        if regs is None:
            return None
        try:
            raw_bytes = bytearray()
            for reg in regs:
                raw_bytes.extend(reg.to_bytes(2, byteorder="big"))
            text = raw_bytes.decode("ascii", errors="ignore").strip("\x00").strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: failed to decode string at addr %s (regs=%s): %s",
                reg_address_manual,
                regs,
                exc,
            )
            return None

    @staticmethod
    def _regs_to_float_be(registers: list[int]) -> float:
        """Convert two registers (big endian) to a Python float."""
        if len(registers) < 2:
            raise ValueError("Not enough registers for float")
        raw = (registers[0] << 16) | registers[1]
        return struct.unpack(">f", raw.to_bytes(4, byteorder="big"))[0]


# -----------------------------------------------------------------------------
# Coordinator (one global poll loop for all enabled registers)
# -----------------------------------------------------------------------------

class EclModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll all enabled registers at a single global interval."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub: EclModbusHub,
        registers: list[RegisterDef],
        scan_interval_sec: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="ECL Modbus Coordinator",
            update_interval=timedelta(seconds=scan_interval_sec),
        )
        self._hub = hub
        self._registers = registers

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all enabled register values."""
        def _read_all() -> dict[str, Any]:
            data: dict[str, Any] = {}
            for reg in self._registers:
                if reg.reg_type == RegisterType.FLOAT:
                    data[reg.key] = self._hub.read_float(reg.address)
                elif reg.reg_type == RegisterType.INT16:
                    data[reg.key] = self._hub.read_int16(reg.address, signed=reg.signed)
                elif reg.reg_type == RegisterType.STRING16:
                    # String16 is typically 16 chars -> 8 registers
                    data[reg.key] = self._hub.read_string(reg.address, reg_count=8)
                elif reg.reg_type == RegisterType.STRING32:
                    # String32 is typically 32 chars -> 16 registers
                    data[reg.key] = self._hub.read_string(reg.address, reg_count=16)
                else:
                    data[reg.key] = None
            return data

        try:
            return await self.hass.async_add_executor_job(_read_all)
        except Exception as exc:  # noqa: BLE001
            raise UpdateFailed(f"ECL Modbus update failed: {exc}") from exc


# -----------------------------------------------------------------------------
# Entities
# -----------------------------------------------------------------------------

class EclModbusRegisterSensor(CoordinatorEntity[EclModbusCoordinator], SensorEntity):
    """Generic sensor that exposes one register from the coordinator."""

    def __init__(
        self,
        coordinator: EclModbusCoordinator,
        entry_title: str,
        reg: RegisterDef,
    ) -> None:
        super().__init__(coordinator)
        self._reg = reg

        # Entity identity
        self._attr_name = f"{entry_title} {reg.name}"
        self._attr_unique_id = f"{DOMAIN}_{reg.key}"

        # Presentation
        self._attr_native_unit_of_measurement = reg.unit
        self._attr_device_class = reg.device_class
        self._attr_state_class = reg.state_class
        self._attr_icon = reg.icon

        # Useful debugging metadata
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg.address,
            "ecl_modbus_type": reg.reg_type.value,
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
    def native_value(self) -> Any:
        """Return the latest value from the coordinator."""
        raw = self.coordinator.data.get(self._reg.key)
        if raw is None:
            return None

        # Apply scaling for numeric types (if configured)
        if self._reg.reg_type in (RegisterType.FLOAT, RegisterType.INT16):
            try:
                value = float(raw) * float(self._reg.scale)
            except (TypeError, ValueError):
                return None

            # Common nicety: round temperatures and percentages a bit
            if self._reg.device_class == "temperature":
                return round(value, 1)
            if self._reg.unit == "%":
                return round(value, 1)

            # Default numeric output
            # If integer scaling isn't used, keep int-ish values readable
            return value

        # Strings, etc.
        return raw


# -----------------------------------------------------------------------------
# Platform setup
# -----------------------------------------------------------------------------

def _clamp_scan_interval(value: Any) -> int:
    """Clamp scan interval to a safe range for RS485 polling."""
    try:
        sec = int(value)
    except (TypeError, ValueError):
        sec = DEFAULT_SCAN_INTERVAL
    if sec < 5:
        return 5
    if sec > 3600:
        return 3600
    return sec


def _default_enabled(reg: RegisterDef) -> bool:
    """Return whether a register should be enabled by default."""
    # Keep defaults conservative. Most users typically want S3/S4 first.
    if reg.key in ("s3_temperature", "s4_temperature"):
        return True
    return False


def get_hub_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> EclModbusHub:
    """Get (or create) the EclModbusHub for this config entry."""
    data = hass.data.setdefault(DOMAIN, {})
    hub: EclModbusHub | None = data.get(entry.entry_id)

    if hub is None:
        port = entry.data[CONF_PORT]
        baudrate = entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
        slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

        hub = EclModbusHub(port=port, baudrate=baudrate, slave_id=slave_id)
        data[entry.entry_id] = hub

    return hub


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors based on a config entry (UI configuration)."""
    entry_title = entry.data.get(CONF_NAME, DEFAULT_NAME)
    hub = get_hub_for_entry(hass, entry)

    # Global polling interval (one coordinator for everything)
    scan_interval_sec = _clamp_scan_interval(entry.options.get(CONF_SCAN_INTERVAL))

    # Build enabled register list from options
    enabled_regs: list[RegisterDef] = []
    for reg in ALL_REGISTERS:
        enabled = bool(entry.options.get(option_key(reg.key), _default_enabled(reg)))
        if enabled:
            enabled_regs.append(reg)

    coordinator = EclModbusCoordinator(
        hass=hass,
        hub=hub,
        registers=enabled_regs,
        scan_interval_sec=scan_interval_sec,
    )

    # Do a first refresh before adding entities (better UX)
    await coordinator.async_config_entry_first_refresh()

    entities: list[SensorEntity] = [
        EclModbusRegisterSensor(coordinator, entry_title, reg) for reg in enabled_regs
    ]

    async_add_entities(entities, update_before_add=False)

    async def _async_close_hub(event: Any) -> None:
        """Close the Modbus client when Home Assistant stops."""
        hub.close()

    hass.bus.async_listen_once("homeassistant_stop", _async_close_hub)