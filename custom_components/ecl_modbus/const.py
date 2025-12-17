from __future__ import annotations

"""
Constants for the ECL Modbus integration.

This file contains only static constants and configuration keys.
No runtime logic must be placed here.
"""

# -----------------------------------------------------------------------------
# Integration basics
# -----------------------------------------------------------------------------

DOMAIN = "ecl_modbus"
PLATFORMS: list[str] = ["sensor"]

# -----------------------------------------------------------------------------
# Config flow base options
# -----------------------------------------------------------------------------

CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5

# -----------------------------------------------------------------------------
# Sensor enable options – physical temperature sensors
# -----------------------------------------------------------------------------

CONF_ENABLE_S1 = "enable_s1"
CONF_ENABLE_S2 = "enable_s2"
CONF_ENABLE_S3 = "enable_s3"
CONF_ENABLE_S4 = "enable_s4"
CONF_ENABLE_S5 = "enable_s5"
CONF_ENABLE_S6 = "enable_s6"

# -----------------------------------------------------------------------------
# Sensor enable options – system / network information
# -----------------------------------------------------------------------------

CONF_ENABLE_IP_ADDRESS = "enable_ip_address"
CONF_ENABLE_MAC_ADDRESS = "enable_mac_address"

# -----------------------------------------------------------------------------
# Sensor enable options – application / heating values
# -----------------------------------------------------------------------------

# Circuit heat references (read-only)
CONF_ENABLE_HEAT_FLOW_REF = "enable_heat_flow_ref"
CONF_ENABLE_HEAT_WEATHER_REF = "enable_heat_weather_ref"

# Circuit outputs (read-only)
CONF_ENABLE_VALVE_POSITION = "enable_valve_position"

# -----------------------------------------------------------------------------
# Polling
# -----------------------------------------------------------------------------

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30