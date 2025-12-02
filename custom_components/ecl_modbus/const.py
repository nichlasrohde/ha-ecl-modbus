from __future__ import annotations

"""Constants for the ECL Modbus integration."""

# Domain used by Home Assistant
DOMAIN = "ecl_modbus"

# This integration exposes only the sensor platform
PLATFORMS: list[str] = ["sensor"]

# Configuration keys (for config flow)
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"

# Default values
DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5

# Options: enable/disable temperature sensors S1–S6
CONF_ENABLE_S1 = "enable_s1"
CONF_ENABLE_S2 = "enable_s2"
CONF_ENABLE_S3 = "enable_s3"
CONF_ENABLE_S4 = "enable_s4"
CONF_ENABLE_S5 = "enable_s5"
CONF_ENABLE_S6 = "enable_s6"