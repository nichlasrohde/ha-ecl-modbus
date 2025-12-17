from __future__ import annotations

"""Config flow (UI setup) and options flow for the ECL Modbus integration.

This implementation is register-driven:
- The list of available registers lives in `registers.py`
- Options are generated dynamically from that list
- Sensor platform reads the same options keys (enable_<register_key>)
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
)
from .registers import ALL_REGISTERS, option_key


class EclModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for setting up ECL Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """First step when a user adds the integration."""
        if user_input is not None:
            # Only one ECL instance makes sense → fixed unique_id
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_PORT): str,  # e.g. /dev/ttyUSB0 or /dev/ttyUSB1
                vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
                vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "EclModbusOptionsFlow":
        """Return the options flow handler for an existing entry."""
        return EclModbusOptionsFlow(config_entry)


class EclModbusOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing entry.

    Options include:
    - Which registers should be enabled (checkbox per register)
    - Global poll interval (scan_interval)
    """

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Entry point for the options flow."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict | None = None) -> FlowResult:
        """Show the form where the user chooses which sensors to enable."""
        if user_input is not None:
            # Save options as entry.options
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options

        def opt_bool(key: str, default: bool) -> bool:
            """Helper to read a boolean option with a default."""
            return bool(options.get(key, default))

        # Default enable behaviour:
        # - Keep defaults conservative
        # - S3/S4 are commonly used, so enable them by default (if no options exist)
        default_enabled_keys = {"s3_temperature", "s4_temperature"}

        schema_dict: dict[vol.Marker, object] = {}

        # One checkbox per register
        for reg in ALL_REGISTERS:
            k = option_key(reg.key)
            default_value = opt_bool(k, reg.key in default_enabled_keys)
            schema_dict[vol.Optional(k, default=default_value)] = bool

        # Global polling interval (seconds)
        schema_dict[
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            )
        ] = vol.All(int, vol.Clamp(min=5, max=3600))

        return self.async_show_form(step_id="options", data_schema=vol.Schema(schema_dict))