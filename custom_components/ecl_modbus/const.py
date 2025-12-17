from __future__ import annotations

"""
Constants for the ECL Modbus integration.

This file must contain ONLY static constants and configuration keys.
No runtime logic, no register definitions, no enable flags.
"""

# -----------------------------------------------------------------------------
# Integration basics
# -----------------------------------------------------------------------------

DOMAIN = "ecl_modbus"

# Platforms provided by this integration
PLATFORMS: list[str] = [
    "sensor",   # Read-only registers
    "number",   # Writable numeric registers (RW)
    # "select", # Future: token-based RW registers (Comfort/Night/etc.)
]

# -----------------------------------------------------------------------------
# Config flow base options
# -----------------------------------------------------------------------------

CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5
DEFAULT_SCAN_INTERVAL = 30