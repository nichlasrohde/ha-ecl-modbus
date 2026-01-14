from __future__ import annotations

"""
Constants for the ECL Modbus integration.

Keep ONLY constants and config keys here.
No runtime logic.
"""

DOMAIN = "ecl_modbus"

# Platforms we expose
PLATFORMS: list[str] = ["sensor", "number", "select"]

# Config entry (setup)
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5
DEFAULT_SCAN_INTERVAL = 30

# Transport (serial vs tcp)
CONF_TRANSPORT = "transport"
CONF_HOST = "host"
CONF_TCP_PORT = "tcp_port"

TRANSPORT_SERIAL = "serial"
TRANSPORT_TCP = "tcp"

DEFAULT_TRANSPORT = TRANSPORT_SERIAL
DEFAULT_TCP_PORT = 502