from __future__ import annotations

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "ecl_modbus"
PLATFORMS: list[Platform] = [Platform.SENSOR]

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

CONF_SLAVE_ID = "slave_id"
CONF_BAUDRATE = "baudrate"