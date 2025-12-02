from __future__ import annotations

from homeassistant.const import Platform  # 👈 NY import

DOMAIN = "ecl_modbus"

# Hvilke platforme integrationen bruger (lige nu kun sensor)
PLATFORMS: list[Platform] = [Platform.SENSOR]  # 👈 NY konstant

# Konfiguration (setup via config_flow)
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"

DEFAULT_NAME = "ECL Modbus"
DEFAULT_BAUDRATE = 38400
DEFAULT_SLAVE_ID = 5

# Poll interval (sekunder)
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 30

# Options: enable/disable temperatur-sensorer
CONF_ENABLE_S1 = "enable_s1"
CONF_ENABLE_S2 = "enable_s2"
CONF_ENABLE_S3 = "enable_s3"
CONF_ENABLE_S4 = "enable_s4"
CONF_ENABLE_S5 = "enable_s5"
CONF_ENABLE_S6 = "enable_s6"

# Options: enable/disable outputs (6200+)
CONF_ENABLE_TR1 = "enable_tr1"
CONF_ENABLE_TR2 = "enable_tr2"
CONF_ENABLE_R1 = "enable_r1"
CONF_ENABLE_R2 = "enable_r2"
CONF_ENABLE_P1_DUTY = "enable_p1_duty"
CONF_ENABLE_P1_FREQ = "enable_p1_freq"
CONF_ENABLE_STEPPER1 = "enable_stepper1"
CONF_ENABLE_STEPPER2 = "enable_stepper2"
