from __future__ import annotations

"""
Constants for the ECL Modbus integration.

Keep ONLY constants and config keys here.
No runtime logic.
"""

DOMAIN = "ecl_modbus"

# Platforms we expose
PLATFORMS: list[str] = ["sensor", "number"]

# Config entry (setup)
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5
DEFAULT_SCAN_INTERVAL = 30