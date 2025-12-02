from __future__ import annotations

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
    UnitOfFrequency,
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
    CONF_ENABLE_TR1,
    CONF_ENABLE_TR2,
    CONF_ENABLE_R1,
    CONF_ENABLE_R2,
    CONF_ENABLE_P1_DUTY,
    CONF_ENABLE_P1_FREQ,
    CONF_ENABLE_STEPPER1,
    CONF_ENABLE_STEPPER2,
)

_LOGGER = logging.getLogger(__name__)

# Ekstra config felter
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5

# Poll-interval
SCAN_INTERVAL = timedelta(seconds=30)

# Temperatur-sensor registre (manual adresser)
REG_S1_MANUAL = 4000
REG_S2_MANUAL = 4010
REG_S3_MANUAL = 4020
REG_S4_MANUAL = 4030
REG_S5_MANUAL = 4040
REG_S6_MANUAL = 4050

# Output / override registre (manual adresser 6000+)
REG_TR1_OVERRIDE = 6200
REG_TR2_OVERRIDE = 6201
REG_R1_OVERRIDE = 6210
REG_R2_OVERRIDE = 6211
REG_P1_PWM_DUTY = 6220
REG_P1_PWM_FREQ = 6222
REG_STEPPER1_POS = 6230
REG_STEPPER2_POS = 6232


class EclModbusHub:
    """Håndterer Modbus-kommunikationen til ECL."""

    def __init__(self, port: str, baudrate: int, slave_id: int) -> None:
        self._port = port
        self._baudrate = baudrate
        self._slave_id = slave_id
        self._client: ModbusSerialClient | None = None
        self._lock = threading.Lock()

    def _ensure_client(self) -> None:
        """Sørg for at klienten er initialiseret og forbundet."""
        if self._client is not None and self._client.connected:
            return

        _LOGGER.info(
            "ECL Modbus: Opretter ModbusSerialClient på %s @ %s baud",
            self._port,
            self._baudrate,
        )

        # Luk evt. gammel klient
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
            raise ModbusIOException(
                f"Kunne ikke forbinde til {self._port}"
            )

    def close(self) -> None:
        """Luk klienten eksplicit."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # noqa: BLE001
                pass
        self._client = None

    # ---------- LÆSERE ----------

    def read_float(self, reg_address_manual: int) -> float | None:
        """Læs en float (2 registre) fra 4000+/6000+ området."""
        with self._lock:
            try:
                self._ensure_client()
                pdu_address = reg_address_manual - 1

                result = self._client.read_holding_registers(
                    address=pdu_address,
                    count=2,
                    device_id=self._slave_id,
                )
            except ModbusIOException as exc:
                _LOGGER.error(
                    "ECL Modbus: ModbusIOException ved læsning af %s: %s",
                    reg_address_manual,
                    exc,
                )
                # Tving reconnect næste gang
                self.close()
                return None
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "ECL Modbus: Uventet fejl ved læsning af %s: %s",
                    reg_address_manual,
                    exc,
                )
                self.close()
                return None

        if not result or getattr(result, "isError", lambda: True)():
            _LOGGER.warning(
                "ECL Modbus: Modbus-fejl eller intet svar for adresse %s: %s",
                reg_address_manual,
                result,
            )
            return None

        registers = getattr(result, "registers", None)
        if not registers:
            _LOGGER.warning(
                "ECL Modbus: Tomt register-svar for adresse %s: %s",
                reg_address_manual,
                result,
            )
            return None

        try:
            return self._regs_to_float_be(registers)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error(
                "ECL Modbus: Kunne ikke konvertere registre %s fra adr %s til float: %s",
                registers,
                reg_address_manual,
                exc,
            )
            return None

    def read_int16(self, reg_address_manual: int, signed: bool = True) -> int | None:
        """Læs et Int16-register (1 register)."""
        with self._lock:
            try:
                self._ensure_client()
                pdu_address = reg_address_manual - 1

                result = self._client.read_holding_registers(
                    address=pdu_address,
                    count=1,
                    device_id=self._slave_id,
                )
            except ModbusIOException as exc:
                _LOGGER.error(
                    "ECL Modbus: ModbusIOException ved læsning af %s: %s",
                    reg_address_manual,
                    exc,
                )
                self.close()
                return None
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "ECL Modbus: Uventet fejl ved læsning af %s: %s",
                    reg_address_manual,
                    exc,
                )
                self.close()
                return None

        if not result or getattr(result, "isError", lambda: True)():
            _LOGGER.warning(
                "ECL Modbus: Modbus-fejl eller intet svar for adresse %s: %s",
                reg_address_manual,
                result,
            )
            return None

        regs = getattr(result, "registers", None)
        if not regs:
            _LOGGER.warning(
                "ECL Modbus: Tomt register-svar for adresse %s: %s",
                reg_address_manual,
                result,
            )
            return None

        raw = regs[0]
        if signed and raw > 0x7FFF:
            raw -= 0x10000
        return raw

    @staticmethod
    def _regs_to_float_be(registers: list[int]) -> float:
        """Konverter 2 registre (Big Endian) til float."""
        if len(registers) < 2:
            raise ValueError("For få registre til float")
        # Højeste register først (big endian)
        raw = (registers[0] << 16) | registers[1]
        return struct.unpack(">f", raw.to_bytes(4, byteorder="big"))[0]


# ---------- SENSOR-KLASSER ----------


class EclModbusTemperatureSensor(SensorEntity):
    """Temperatur-sensor (S1-S6) fra ECL."""

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
        """Hent ny temperatur fra ECL via Modbus."""
        _LOGGER.debug(
            "ECL Modbus: async_update startet for %s (adr %s)",
            self.name,
            self._reg_address_manual,
        )

        value = await self.hass.async_add_executor_job(
            self._hub.read_float,
            self._reg_address_manual,
        )

        if value is None:
            _LOGGER.debug(
                "ECL Modbus: ingen ny værdi for %s (adr %s) – beholder gammel værdi",
                self.name,
                self._reg_address_manual,
            )
            return

        rounded = round(value, 1)
        _LOGGER.debug(
            "ECL Modbus: opdaterer %s (adr %s) til %.1f °C",
            self.name,
            self._reg_address_manual,
            rounded,
        )
        self._attr_native_value = rounded


class EclModbusOutputSensor(SensorEntity):
    """Sensor for override/outputs (triac, relay, pumpe, stepper)."""

    _attr_state_class = "measurement"

    def __init__(
        self,
        hub: EclModbusHub,
        name: str,
        reg_address_manual: int,
        unique_suffix: str,
        value_type: str = "int16",  # "int16" eller "float"
        scale: float = 1.0,
        unit: str | None = None,
        device_class: str | None = None,
        signed: bool = True,
    ) -> None:
        self._hub = hub
        self._reg_address_manual = reg_address_manual
        self._value_type = value_type
        self._scale = scale
        self._signed = signed

        self._attr_name = name
        self._attr_unique_id = f"ecl_modbus_{unique_suffix}"
        self._attr_extra_state_attributes = {
            "ecl_modbus_register": reg_address_manual
        }

        if unit is not None:
            self._attr_native_unit_of_measurement = unit
        if device_class is not None:
            self._attr_device_class = device_class

    async def async_update(self) -> None:
        """Hent ny outputværdi fra ECL via Modbus."""
        _LOGGER.debug(
            "ECL Modbus: async_update (output) startet for %s (adr %s)",
            self.name,
            self._reg_address_manual,
        )

        if self._value_type == "float":
            value = await self.hass.async_add_executor_job(
                self._hub.read_float,
                self._reg_address_manual,
            )
        else:
            value = await self.hass.async_add_executor_job(
                self._hub.read_int16,
                self._reg_address_manual,
                self._signed,
            )

        if value is None:
            _LOGGER.debug(
                "ECL Modbus: ingen ny output-værdi for %s (adr %s) – beholder gammel",
                self.name,
                self._reg_address_manual,
            )
            return

        scaled = value * self._scale
        _LOGGER.debug(
            "ECL Modbus: opdaterer output %s (adr %s) til %s",
            self.name,
            self._reg_address_manual,
            scaled,
        )
        self._attr_native_value = scaled


# ---------- PLATFORM SETUP ----------

def get_hub_for_entry(hass: HomeAssistant, entry: ConfigEntry) -> "EclModbusHub":
    from .const import DOMAIN  # for at undgå cirkulær import i typechecking

    data = hass.data.setdefault(DOMAIN, {})
    hub: EclModbusHub | None = data.get(entry.entry_id)

    if hub is None:
        port = entry.data[CONF_PORT]
        baudrate = entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)
        slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

        hub = EclModbusHub(port=port, baudrate=baudrate, slave_id=slave_id)
        data[entry.entry_id] = hub

    return hub


# ---------- CONFIG ENTRY SETUP ----------

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sæt sensorer op ud fra en config entry (UI-opsætning)."""
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)

    hub = get_hub_for_entry(hass, entry)

    entities: list[SensorEntity] = []

    # Temperatur-sensorer S1-S6
    entities.extend(
        [
            EclModbusTemperatureSensor(
                hub, f"{name} S1 temperatur", REG_S1_MANUAL, "s1_temp"
            ),
            EclModbusTemperatureSensor(
                hub, f"{name} S2 temperatur", REG_S2_MANUAL, "s2_temp"
            ),
            EclModbusTemperatureSensor(
                hub, f"{name} S3 temperatur", REG_S3_MANUAL, "s3_temp"
            ),
            EclModbusTemperatureSensor(
                hub, f"{name} S4 temperatur", REG_S4_MANUAL, "s4_temp"
            ),
            EclModbusTemperatureSensor(
                hub, f"{name} S5 temperatur", REG_S5_MANUAL, "s5_temp"
            ),
            EclModbusTemperatureSensor(
                hub, f"{name} S6 temperatur", REG_S6_MANUAL, "s6_temp"
            ),
        ]
    )

    # Override outputs 6200+ (triac, relæ, pumpe, stepper)
    entities.extend(
        [
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} TR1 triac override",
                reg_address_manual=REG_TR1_OVERRIDE,
                unique_suffix="tr1_override",
                value_type="int16",
                scale=0.1,  # -150.0 .. 150.0 %
                unit=PERCENTAGE,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} TR2 triac override",
                reg_address_manual=REG_TR2_OVERRIDE,
                unique_suffix="tr2_override",
                value_type="int16",
                scale=0.1,
                unit=PERCENTAGE,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} R1 relay override",
                reg_address_manual=REG_R1_OVERRIDE,
                unique_suffix="r1_override",
                value_type="int16",
                scale=1.0,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} R2 relay override",
                reg_address_manual=REG_R2_OVERRIDE,
                unique_suffix="r2_override",
                value_type="int16",
                scale=1.0,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} Pump P1 dutycycle",
                reg_address_manual=REG_P1_PWM_DUTY,
                unique_suffix="p1_duty",
                value_type="float",
                scale=1.0,
                unit=PERCENTAGE,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} Pump P1 frequency",
                reg_address_manual=REG_P1_PWM_FREQ,
                unique_suffix="p1_freq",
                value_type="float",
                scale=1.0,
                unit=UnitOfFrequency.HERTZ,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} Stepper 1 position",
                reg_address_manual=REG_STEPPER1_POS,
                unique_suffix="stepper1_pos",
                value_type="float",
                scale=1.0,
                unit=PERCENTAGE,
            ),
            EclModbusOutputSensor(
                hub=hub,
                name=f"{name} Stepper 2 position",
                reg_address_manual=REG_STEPPER2_POS,
                unique_suffix="stepper2_pos",
                value_type="float",
                scale=1.0,
                unit=PERCENTAGE,
            ),
        ]
    )

    async_add_entities(entities, update_before_add=True)

    async def _async_close_hub(event: Any) -> None:
        """Luk Modbus-klienten når HA stopper."""
        hub.close()

    hass.bus.async_listen_once("homeassistant_stop", _async_close_hub)
