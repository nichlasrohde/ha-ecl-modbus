from __future__ import annotations

"""Config flow and options flow for the ECL Modbus integration."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigEntry

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
)


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
    """Handle options (which sensors are enabled) for an existing entry."""

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

        def opt(key: str, default: bool) -> bool:
            """Helper to read a boolean option with a default."""
            return bool(options.get(key, default))

        # Defaults: S3 & S4 on, others off; extra sensors off by default
        data_schema = vol.Schema(
            {
                # Temperature sensors S1–S6
                vol.Optional(CONF_ENABLE_S1, default=opt(CONF_ENABLE_S1, False)): bool,
                vol.Optional(CONF_ENABLE_S2, default=opt(CONF_ENABLE_S2, False)): bool,
                vol.Optional(CONF_ENABLE_S3, default=opt(CONF_ENABLE_S3, True)): bool,
                vol.Optional(CONF_ENABLE_S4, default=opt(CONF_ENABLE_S4, True)): bool,
                vol.Optional(CONF_ENABLE_S5, default=opt(CONF_ENABLE_S5, False)): bool,
                vol.Optional(CONF_ENABLE_S6, default=opt(CONF_ENABLE_S6, False)): bool,
                # Extra sensors: IP, MAC, valve position
                vol.Optional(
                    CONF_ENABLE_IP_ADDRESS,
                    default=opt(CONF_ENABLE_IP_ADDRESS, False),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_MAC_ADDRESS,
                    default=opt(CONF_ENABLE_MAC_ADDRESS, False),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_VALVE_POSITION,
                    default=opt(CONF_ENABLE_VALVE_POSITION, False),
                ): bool,
            }
        )

        return self.async_show_form(step_id="options", data_schema=data_schema)