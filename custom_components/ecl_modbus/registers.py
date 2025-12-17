from __future__ import annotations

"""Register definitions for the ECL Modbus integration.

Goal:
- Keep ALL register metadata in one place (address, type, unit, scaling, etc.)
- Make it easy to add new registers by adding a single entry to a list.

Notes:
- ECL Modbus "manual addresses" in Danfoss docs are typically 1-based (PNU-style).
- pymodbus read_holding_registers() uses 0-based addressing, so you usually read (address - 1).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final


class RegisterType(str, Enum):
    """How a register value should be decoded."""
    FLOAT = "float"          # 2 x 16-bit registers -> IEEE754 float (big-endian)
    INT16 = "int16"          # 1 x 16-bit register -> signed/unsigned int
    STRING16 = "string16"    # 16 chars (typically 8 registers) - adjust decoder later
    STRING32 = "string32"    # 32 chars (typically 16 registers) - adjust decoder later


@dataclass(frozen=True, slots=True)
class RegisterDef:
    """Definition of one readable register/point."""
    key: str                 # Stable internal key (also good for unique_id suffix)
    name: str                # Human friendly name shown in Home Assistant
    address: int             # Manual register address from Danfoss documentation
    reg_type: RegisterType

    # Optional presentation metadata
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    icon: str | None = None

    # Optional value handling
    scale: float = 1.0       # Apply after decoding (e.g., int16 * 0.1)
    signed: bool = True      # Only relevant for INT16


# -----------------------------------------------------------------------------
# Core temperature sensors (S1–S6)
# -----------------------------------------------------------------------------
REG_SENSORS: Final[list[RegisterDef]] = [
    RegisterDef(
        key="s1_temperature",
        name="S1 temperature",
        address=4000,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="s2_temperature",
        name="S2 temperature",
        address=4010,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="s3_temperature",
        name="S3 temperature",
        address=4020,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="s4_temperature",
        name="S4 temperature",
        address=4030,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="s5_temperature",
        name="S5 temperature",
        address=4040,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="s6_temperature",
        name="S6 temperature",
        address=4050,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
]

# -----------------------------------------------------------------------------
# Extra diagnostics / info
# -----------------------------------------------------------------------------
REG_DIAGNOSTICS: Final[list[RegisterDef]] = [
    RegisterDef(
        key="ethernet_ip_address",
        name="Ethernet IP address",
        address=2100,
        reg_type=RegisterType.STRING16,
        state_class=None,
        icon="mdi:ip-network",
    ),
    RegisterDef(
        key="ethernet_mac_address",
        name="Ethernet MAC address",
        address=2110,
        reg_type=RegisterType.STRING32,
        state_class=None,
        icon="mdi:lan",
    ),
]

# -----------------------------------------------------------------------------
# Extra calculated / control-related sensors
# -----------------------------------------------------------------------------
REG_EXTRAS: Final[list[RegisterDef]] = [
    RegisterDef(
        key="valve_position",
        name="Valve position",
        address=21700,
        reg_type=RegisterType.FLOAT,
        unit="%",
        device_class=None,
        state_class="measurement",
        icon="mdi:valve",
    ),
    RegisterDef(
        key="heat_flow_reference",
        name="Heat flow temperature reference",
        address=21200,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
    RegisterDef(
        key="heat_weather_comp_reference",
        name="Heat weather compensated reference",
        address=21206,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
    ),
]

# -----------------------------------------------------------------------------
# Single list of all registers we *can* expose.
# The integration can later decide which ones to enable via options.
# -----------------------------------------------------------------------------

ALL_REGISTERS: Final[list[RegisterDef]] = [
    *REG_SENSORS,
    *REG_DIAGNOSTICS,
    *REG_EXTRAS,
]


def option_key(reg_key: str) -> str:
    """Return the config entry options key used to enable/disable a register.

    We keep this in one place to ensure `config_flow.py` and `sensor.py`
    always agree on the exact options key naming.
    """
    return f"enable_{reg_key}"