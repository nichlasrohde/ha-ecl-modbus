from __future__ import annotations

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
    CONF_ENABLE_TR1,
    CONF_ENABLE_TR2,
    CONF_ENABLE_R1,
    CONF_ENABLE_R2,
    CONF_ENABLE_P1_DUTY,
    CONF_ENABLE_P1_FREQ,
    CONF_ENABLE_STEPPER1,
    CONF_ENABLE_STEPPER2,
)


class EclModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow til ECL Modbus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Første trin i opsætningen."""
        if user_input is not None:
            # Kun én ECL-instans giver mening → brug fast unique_id
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, DEFAULT_NAME),
                data=user_input,
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_PORT): str,  # fx /dev/ttyUSB1 eller /dev/ttyUSB0
                vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
                vol.Optional(CONF_SLAVE_ID, default=DEFAULT_SLAVE_ID): int,
            }
        )

        return self.async_show_form(step_id="user", data_schema=data_schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "EclModbusOptionsFlow":
        """Returnér options flow handler."""
        return EclModbusOptionsFlow(config_entry)


class EclModbusOptionsFlow(config_entries.OptionsFlow):
    """Håndterer indstillinger (Options) for en eksisterende ECL Modbus entry."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Standard entry point – sender videre til options step."""
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict | None = None) -> FlowResult:
        """Form med hvilke sensorer der skal aktiveres."""
        if user_input is not None:
            # Gemmer options som entry.options
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options

        def opt(key: str, default: bool) -> bool:
            return bool(options.get(key, default))

        # Defaults: vi antager at S3 og S4 er vigtigst; outputs er off som udgangspunkt
        data_schema = vol.Schema(
            {
                # Temperatur sensorer
                vol.Optional(CONF_ENABLE_S1, default=opt(CONF_ENABLE_S1, False)): bool,
                vol.Optional(CONF_ENABLE_S2, default=opt(CONF_ENABLE_S2, False)): bool,
                vol.Optional(CONF_ENABLE_S3, default=opt(CONF_ENABLE_S3, True)): bool,
                vol.Optional(CONF_ENABLE_S4, default=opt(CONF_ENABLE_S4, True)): bool,
                vol.Optional(CONF_ENABLE_S5, default=opt(CONF_ENABLE_S5, False)): bool,
                vol.Optional(CONF_ENABLE_S6, default=opt(CONF_ENABLE_S6, False)): bool,

                # Outputs
                vol.Optional(CONF_ENABLE_TR1, default=opt(CONF_ENABLE_TR1, False)): bool,
                vol.Optional(CONF_ENABLE_TR2, default=opt(CONF_ENABLE_TR2, False)): bool,
                vol.Optional(CONF_ENABLE_R1, default=opt(CONF_ENABLE_R1, False)): bool,
                vol.Optional(CONF_ENABLE_R2, default=opt(CONF_ENABLE_R2, False)): bool,
                vol.Optional(
                    CONF_ENABLE_P1_DUTY,
                    default=opt(CONF_ENABLE_P1_DUTY, False),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_P1_FREQ,
                    default=opt(CONF_ENABLE_P1_FREQ, False),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_STEPPER1,
                    default=opt(CONF_ENABLE_STEPPER1, False),
                ): bool,
                vol.Optional(
                    CONF_ENABLE_STEPPER2,
                    default=opt(CONF_ENABLE_STEPPER2, False),
                ): bool,
            }
        )

        return self.async_show_form(step_id="options", data_schema=data_schema)