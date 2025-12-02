from __future__ import annotations

"""Sensor platform for the ECL Modbus integration."""

import logging
import struct
import threading
from datetime import timedelta
from typing import Any

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    UnitOfTemperature,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_BAUDRATE,
    DEFAULT_SLAVE_ID,
    CONF_BAUDRATE,
    CONF_SLAVE_ID,
    CONF_ENABLE_S1,
    CONF_ENABLE_S2,
    CONF_ENABLE_S3,
    CONF_ENABLE_S4,
    CONF_ENABLE_S5,
    CONF_ENABLE_S6,
    CONF_ENABLE_IP_ADDRESS,
    CONF_ENABLE_MAC_ADDRESS,
    CONF_ENABLE_VALVE_POSITION,
    CONF_ENABLE_HEAT_FLOW_REF,
    CONF_ENABLE_HEAT_RETURN_REF,
)

_LOGGER = logging.getLogger(__name__)

# Home Assistant will poll all entities in this platform using this interval
SCAN_INTERVAL = timedelta(seconds=30)

# Temperature sensor registers (manual addresses from the ECL documentation)
REG_S1_MANUAL = 4000
REG_S2_MANUAL = 4010
REG_S3_MANUAL = 4020
REG_S4_MANUAL = 4030
REG_S5_MANUAL = 4040
REG_S6_MANUAL = 4050

# Ethernet IP and MAC address registers (String16 / String32)
REG_ETH_IP_MANUAL = 2100   # String16
REG_ETH_MAC_MANUAL = 2110  # String32

# Valve position register (float, %)
REG_VALVE_POSITION_MANUAL = 21700

# Heat reference registers
REG_HEAT_FLOW_REF = 21200     # Float C (0–150°C)
REG_HEAT_RETURN_REF = 21210  # Float C (5 – 150°C)


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

    # ---------- LOW LEVEL READERS ----------

    def _read_registers(
        self,
        reg_address_manual: int,
        count: int,
    ):
        """Internal helper: read raw holding registers."""
        with self._lock:
            try:
                self._ensure_client()
                # Manual address is 1-based, Modbus PDU uses 0-based
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

        registers = getattr(result, "registers", None)
        if not registers:
            _LOGGER.warning(
                "ECL Modbus: empty register response for address %s: %s",
                reg_address_manual,
                result,
            )
            return None

        return registers

    def read_float(self, reg_address_manual: int) -> float | None:
        """Read a 32-bit float from two holding registers (4000+/6000+ area)."""
        registers = self._read_registers(reg_address_manual, count=2)
        if registers is None:
            return None

        try:
            return self._regs_to_float_be(registers)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: failed to convert registers %s at addr %s to float: %s",
                registers,
                reg_address_manual,
                exc,
            )
            return None

    def read_string(self, reg_address_manual: int, reg_count: int) -> str | None:
        """Read a string stored as ASCII across multiple registers."""
        registers = self._read_registers(reg_address_manual, count=reg_count)
        if registers is None:
            return None

        try:
            # Each register is 2 bytes (big endian)
            raw_bytes = bytearray()
            for reg in registers:
                raw_bytes.extend(reg.to_bytes(2, byteorder="big"))

            text = raw_bytes.decode("ascii", errors="ignore").strip("\x00").strip()
            if not text:
                return None
            return text
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: failed to decode string from addr %s (regs=%s): %s",
                reg_address_manual,
                registers,
                exc,
            )
            return None

    @staticmethod
    def _regs_to_float_be(registers: list[int]) -> float:
        """Convert two registers (big endian) to a Python float."""
        if len(registers) < 2:
            raise ValueError("Not enough registers for float")
        # High word first (big endian)
        raw = (registers[0] << 16) | registers[1]
        return struct.unpack(">f", raw.to_bytes(4, byteorder="big"))[0]


# ---------- SENSOR ENTITIES ----------


class EclModbusBaseEntity(SensorEntity):
    """Base class to share device_info between all ECL entities."""

    @property
    def device_info(self) -> dict:
        """Return device info so all sensors are grouped under one ECL device."""
        return {
            "identifiers": {(DOMAIN, "ecl_modbus")},
            "name": "ECL Modbus",
            "manufacturer": "Danfoss",
            "model": "ECL 120/220",
        }


class EclModbusTemperatureSensor(EclModbusBaseEntity):
    """Temperature sensor (S1–S6) read from the ECL controller."""

    _attr_state_class = "measurement"
    _attr_device_class = "temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        hub: EclModbusHub,
        name: str,
        reg_address_manual: int,
        unique_suffix: str,
    ) -> None:
        self._hub = hub
        self._reg_address_manual = reg_address_manual
        self._attr_name = name
        self._attr_unique_id = f"ecl_modbus_{unique_suffix}"
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg_address_manual
        }

    async def async_update(self) -> None:
        """Fetch a new temperature value from the ECL via Modbus."""
        _LOGGER.debug(
            "ECL Modbus: async_update started for %s (addr %s)",
            self.name,
            self._reg_address_manual,
        )

        value = await self.hass.async_add_executor_job(
            self._hub.read_float,
            self._reg_address_manual,
        )

        if value is None:
            _LOGGER.debug(
                "ECL Modbus: no new value for %s (addr %s) – keeping previous state",
                self.name,
                self._reg_address_manual,
            )
            return

        rounded = round(value, 1)
        _LOGGER.debug(
            "ECL Modbus: updating %s (addr %s) to %.1f °C",
            self.name,
            self._reg_address_manual,
            rounded,
        )
        self._attr_native_value = rounded


class EclModbusStringSensor(EclModbusBaseEntity):
    """String-based sensor (e.g. IP address, MAC address) from ECL."""

    _attr_state_class = None  # no numeric state

    def __init__(
        self,
        hub: EclModbusHub,
        name: str,
        reg_address_manual: int,
        reg_count: int,
        unique_suffix: str,
    ) -> None:
        self._hub = hub
        self._reg_address_manual = reg_address_manual
        self._reg_count = reg_count
        self._attr_name = name
        self._attr_unique_id = f"ecl_modbus_{unique_suffix}"
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg_address_manual,
            "ecl_modbus_reg_count": reg_count,
        }

    async def async_update(self) -> None:
        """Fetch the latest string value from ECL via Modbus."""
        _LOGGER.debug(
            "ECL Modbus: async_update (string) started for %s (addr %s, count %s)",
            self.name,
            self._reg_address_manual,
            self._reg_count,
        )

        value = await self.hass.async_add_executor_job(
            self._hub.read_string,
            self._reg_address_manual,
            self._reg_count,
        )

        if value is None:
            _LOGGER.debug(
                "ECL Modbus: no new string value for %s (addr %s) – keeping previous",
                self.name,
                self._reg_address_manual,
            )
            return

        _LOGGER.debug(
            "ECL Modbus: updating %s (addr %s) to '%s'",
            self.name,
            self._reg_address_manual,
            value,
        )
        self._attr_native_value = value


class EclModbusValvePositionSensor(EclModbusBaseEntity):
    """Valve position sensor (float, percentage) from ECL."""

    _attr_state_class = "measurement"
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        hub: EclModbusHub,
        name: str,
        reg_address_manual: int,
        unique_suffix: str,
    ) -> None:
        self._hub = hub
        self._reg_address_manual = reg_address_manual
        self._attr_name = name
        self._attr_unique_id = f"ecl_modbus_{unique_suffix}"
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg_address_manual
        }

    async def async_update(self) -> None:
        """Fetch a new valve position value from ECL via Modbus."""
        _LOGGER.debug(
            "ECL Modbus: async_update (valve position) started for %s (addr %s)",
            self.name,
            self._reg_address_manual,
        )

        value = await self.hass.async_add_executor_job(
            self._hub.read_float,
            self._reg_address_manual,
        )

        if value is None:
            _LOGGER.debug(
                "ECL Modbus: no new valve position for %s (addr %s) – keeping previous",
                self.name,
                self._reg_address_manual,
            )
            return

        rounded = round(value, 1)
        _LOGGER.debug(
            "ECL Modbus: updating valve position %s (addr %s) to %.1f %%",
            self.name,
            self._reg_address_manual,
            rounded,
        )
        self._attr_native_value = rounded


# ---------- PLATFORM SETUP ----------


def get_hub_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> "EclModbusHub":
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
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    hub = get_hub_for_entry(hass, entry)

    options = entry.options

    def opt(key: str, default: bool) -> bool:
        """Helper to read boolean options with a default."""
        return bool(options.get(key, default))

    entities: list[SensorEntity] = []

    # ---------- Temperature sensors S1–S6 ----------

    if opt(CONF_ENABLE_S1, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S1 temperature", REG_S1_MANUAL, "s1_temp"
            )
        )
    if opt(CONF_ENABLE_S2, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S2 temperature", REG_S2_MANUAL, "s2_temp"
            )
        )
    if opt(CONF_ENABLE_S3, True):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S3 temperature", REG_S3_MANUAL, "s3_temp"
            )
        )
    if opt(CONF_ENABLE_S4, True):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S4 temperature", REG_S4_MANUAL, "s4_temp"
            )
        )
    if opt(CONF_ENABLE_S5, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S5 temperature", REG_S5_MANUAL, "s5_temp"
            )
        )
    if opt(CONF_ENABLE_S6, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub, f"{name} S6 temperature", REG_S6_MANUAL, "s6_temp"
            )
        )

    # ---------- Extra sensors: IP, MAC, valve position ----------

    if opt(CONF_ENABLE_IP_ADDRESS, False):
        # String16 → 16 characters → 8 registers (2 bytes per register)
        entities.append(
            EclModbusStringSensor(
                hub=hub,
                name=f"{name} Ethernet IP address",
                reg_address_manual=REG_ETH_IP_MANUAL,
                reg_count=8,
                unique_suffix="eth_ip",
            )
        )

    if opt(CONF_ENABLE_MAC_ADDRESS, False):
        # String32 → 32 characters → 16 registers
        entities.append(
            EclModbusStringSensor(
                hub=hub,
                name=f"{name} Ethernet MAC address",
                reg_address_manual=REG_ETH_MAC_MANUAL,
                reg_count=16,
                unique_suffix="eth_mac",
            )
        )

    if opt(CONF_ENABLE_VALVE_POSITION, False):
        entities.append(
            EclModbusValvePositionSensor(
                hub=hub,
                name=f"{name} valve position",
                reg_address_manual=REG_VALVE_POSITION_MANUAL,
                unique_suffix="valve_position",
            )
        )

    # Heat Flow Reference (float °C 0–150)
    if opt(CONF_ENABLE_HEAT_FLOW_REF, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub,
                f"{name} heat flow reference",
                REG_HEAT_FLOW_REF,
                "heat_flow_ref",
            )
        )

    # Heat Return Compensated Reference (float °C 5–150)
    if opt(CONF_ENABLE_HEAT_RETURN_REF, False):
        entities.append(
            EclModbusTemperatureSensor(
                hub,
                f"{name} heat return reference",
                REG_HEAT_RETURN_REF,
                "heat_return_ref",
            )
        )

    async_add_entities(entities, update_before_add=True)

    async def _async_close_hub(event: Any) -> None:
        """Close the Modbus client when Home Assistant stops."""
        hub.close()

    hass.bus.async_listen_once("homeassistant_stop", _async_close_hub)