from __future__ import annotations

"""Config flow (UI setup) and options flow for the ECL Modbus integration.

Register-driven design:
- All register metadata lives in registers.py
- Options are generated dynamically from ALL_REGISTERS
- Platforms (sensor/number/select) read the same options keys via option_key()
"""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    CONF_BAUDRATE,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_TRANSPORT,
    CONF_HOST,
    CONF_TCP_PORT,
    TRANSPORT_SERIAL,
    TRANSPORT_TCP,
    DEFAULT_TRANSPORT,
    DEFAULT_TCP_PORT,
)
from .registers import ALL_REGISTERS, option_key


class EclModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for setting up ECL Modbus."""

    VERSION = 1

    def __init__(self) -> None:
        self._base: dict = {}

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """First step when a user adds the integration."""
        if user_input is not None:
            self._base = user_input
            transport = user_input.get(CONF_TRANSPORT, DEFAULT_TRANSPORT)

            if transport == TRANSPORT_TCP:
                return await self.async_step_tcp()

            return await self.async_step_serial()

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TRANSPORT, default=DEFAULT_TRANSPORT): vol.In(
                    [TRANSPORT_SERIAL, TRANSPORT_TCP]
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_serial(self, user_input: dict | None = None) -> FlowResult:
        """Serial (RTU) settings."""
        if user_input is not None:
            data = {**self._base, **user_input}

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=data.get(CONF_NAME, DEFAULT_NAME),
                data=data,
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_PORT): str,  # e.g. /dev/ttyUSB0
                vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
                vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
            }
        )

        return self.async_show_form(step_id="serial", data_schema=data_schema)

    async def async_step_tcp(self, user_input: dict | None = None) -> FlowResult:
        """TCP settings."""
        if user_input is not None:
            data = {**self._base, **user_input}

            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=data.get(CONF_NAME, DEFAULT_NAME),
                data=data,
            )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,  # e.g. 10.10.100.50
                vol.Optional(CONF_TCP_PORT, default=DEFAULT_TCP_PORT): int,
                vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
            }
        )

        return self.async_show_form(step_id="tcp", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "EclModbusOptionsFlow":
        """Return the options flow handler for an existing entry."""
        return EclModbusOptionsFlow(config_entry)


class EclModbusOptionsFlow(config_entries.OptionsFlow):
    """Options flow for an existing entry.

    Options:
    - Enable/disable registers (checkbox per register)
    - Global polling interval (scan_interval)
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Entry point for the options flow."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict | None = None) -> FlowResult:
        """Show the form where the user chooses which registers to enable."""
        options = dict(self._entry.options)

        if user_input is not None:
            # Merge with existing options to avoid losing keys
            new_options = {**options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        def opt_bool(key: str, default: bool) -> bool:
            """Read a boolean option with a default."""
            return bool(options.get(key, default))

        # Default enable behaviour (conservative)
        default_enabled_keys = {"s3_temperature", "s4_temperature"}

        schema_dict: dict[vol.Marker, object] = {}

        # One checkbox per register (both RO + RW are enabled here;
        # platforms decide how to expose them: sensors vs numbers/selects)
        for reg in ALL_REGISTERS:
            k = option_key(reg.key)
            default_value = opt_bool(k, reg.key in default_enabled_keys)

            label = f"{reg.name} ({reg.address})"

            schema_dict[
                vol.Optional(
                    k,
                    default=default_value,
                    description={"name": label},
                )
            ] = bool

        # Global polling interval (seconds)
        schema_dict[
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        ] = vol.All(int, vol.Clamp(min=5, max=3600))

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(schema_dict),
        )