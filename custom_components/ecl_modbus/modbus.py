from __future__ import annotations

"""Shared Modbus hub + coordinator for ECL Modbus.

This module contains:
- EclModbusHub: handles serial connection + low-level read/write
- EclModbusCoordinator: polls enabled registers on a global interval

Keeping this separate avoids platform import order issues (sensor/number).
"""

import logging
import struct
import threading
from datetime import timedelta
from typing import Any

from pymodbus.client import ModbusSerialClient
from pymodbus.exceptions import ModbusIOException

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .registers import RegisterDef, RegisterType

_LOGGER = logging.getLogger(__name__)


class EclModbusHub:
    """Handle Modbus RTU communication with the ECL controller."""

    def __init__(self, port: str, baudrate: int, slave_id: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._slave_id = slave_id
        self._client: ModbusSerialClient | None = None
        self._lock = threading.Lock()

    def _ensure_client(self) -> None:
        if self._client is not None and self._client.connected:
            return

        _LOGGER.info(
            "ECL Modbus: creating ModbusSerialClient on %s @ %s baud",
            self._port,
            self._baudrate,
        )

        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass

        self._client = ModbusSerialClient(
            port=self._port,
            baudrate=self._baudrate,
            parity="E",
            stopbits=1,
            bytesize=8,
            timeout=2,
        )

        if not self._client.connect():
            raise ModbusIOException(f"Could not connect to {self._port}")

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    def _read_registers(self, reg_address_manual: int, count: int) -> list[int] | None:
        """Read holding registers (manual addresses are 1-based in Danfoss docs)."""
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
                _LOGGER.error("ECL Modbus: ModbusIOException reading %s: %s", reg_address_manual, exc)
                self.close()
                return None
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error("ECL Modbus: unexpected error reading %s: %s", reg_address_manual, exc)
                self.close()
                return None

        if not result or getattr(result, "isError", lambda: True)():
            _LOGGER.warning("ECL Modbus: Modbus error/no response at %s: %s", reg_address_manual, result)
            return None

        regs = getattr(result, "registers", None)
        if not regs:
            _LOGGER.warning("ECL Modbus: empty register response at %s: %s", reg_address_manual, result)
            return None

        return list(regs)

    def read_float(self, reg_address_manual: int) -> float | None:
        regs = self._read_registers(reg_address_manual, count=2)
        if regs is None:
            return None
        raw = (regs[0] << 16) | regs[1]
        return struct.unpack(">f", raw.to_bytes(4, byteorder="big"))[0]

    def read_int16(self, reg_address_manual: int, signed: bool = True) -> int | None:
        regs = self._read_registers(reg_address_manual, count=1)
        if regs is None:
            return None
        raw = regs[0]
        if signed and raw > 0x7FFF:
            raw -= 0x10000
        return raw

    def read_string(self, reg_address_manual: int, reg_count: int) -> str | None:
        regs = self._read_registers(reg_address_manual, count=reg_count)
        if regs is None:
            return None
        raw_bytes = bytearray()
        for reg in regs:
            raw_bytes.extend(reg.to_bytes(2, byteorder="big"))
        text = raw_bytes.decode("ascii", errors="ignore").strip("\x00").strip()
        return text or None

    # -----------------
    # Write operations
    # -----------------

    def write_int16(self, reg_address_manual: int, value: int) -> None:
        """Write a single 16-bit holding register (manual addr is 1-based)."""
        with self._lock:
            self._ensure_client()
            pdu_address = reg_address_manual - 1
            result = self._client.write_register(
                address=pdu_address,
                value=int(value) & 0xFFFF,
                device_id=self._slave_id,
            )
            if not result or getattr(result, "isError", lambda: True)():
                raise ModbusIOException(f"Write int16 failed at {reg_address_manual}: {result}")

    def write_float(self, reg_address_manual: int, value: float) -> None:
        """Write a 32-bit float into two holding registers (big-endian)."""
        b = struct.pack(">f", float(value))
        hi = int.from_bytes(b[0:2], byteorder="big")
        lo = int.from_bytes(b[2:4], byteorder="big")

        with self._lock:
            self._ensure_client()
            pdu_address = reg_address_manual - 1
            result = self._client.write_registers(
                address=pdu_address,
                values=[hi, lo],
                device_id=self._slave_id,
            )
            if not result or getattr(result, "isError", lambda: True)():
                raise ModbusIOException(f"Write float failed at {reg_address_manual}: {result}")


class EclModbusCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll enabled registers at a single global interval."""

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
        self.hub = hub
        self.registers = registers

    async def _async_update_data(self) -> dict[str, Any]:
        def _read_all() -> dict[str, Any]:
            data: dict[str, Any] = {}
            for reg in self.registers:
                if reg.reg_type == RegisterType.FLOAT:
                    data[reg.key] = self.hub.read_float(reg.address)
                elif reg.reg_type == RegisterType.INT16:
                    data[reg.key] = self.hub.read_int16(reg.address, signed=reg.signed)
                elif reg.reg_type == RegisterType.STRING16:
                    data[reg.key] = self.hub.read_string(reg.address, reg_count=8)
                elif reg.reg_type == RegisterType.STRING32:
                    data[reg.key] = self.hub.read_string(reg.address, reg_count=16)
                else:
                    data[reg.key] = None
            return data

        try:
            return await self.hass.async_add_executor_job(_read_all)
        except Exception as exc:  # noqa: BLE001
            raise UpdateFailed(f"ECL Modbus update failed: {exc}") from exc