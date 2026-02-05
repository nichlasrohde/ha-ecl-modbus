from __future__ import annotations

"""Register definitions for the ECL Modbus integration.

Goal:
- Keep ALL register metadata in one place (address, type, unit, scaling, etc.)
- Make it easy to add new registers by adding a single entry to a list
- Support both read-only (R) and read/write (RW) registers

Notes:
- ECL Modbus "manual addresses" in Danfoss documentation are typically 1-based
  (PNU-style addresses).
- pymodbus read_holding_registers() uses 0-based addressing, so the integration
  will internally read (address - 1).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Final, Mapping


class RegisterType(str, Enum):
    """How a register value should be decoded."""
    FLOAT = "float"          # 2 x 16-bit registers -> IEEE754 float (big-endian)
    INT16 = "int16"          # 1 x 16-bit register -> signed/unsigned int
    UINT32 = "uint32"        # 2 x 16-bit registers -> unsigned 32-bit int (big-endian)
    STRING16 = "string16"    # 16 chars (typically 8 registers)
    STRING32 = "string32"    # 32 chars (typically 16 registers)


@dataclass(frozen=True, slots=True)
class RegisterDef:
    """Definition of one Modbus register/point.

    A register can be read-only (R) or read/write (RW).
    RW registers can later be exposed as Number or Select entities in Home Assistant.
    """

    # Identity
    key: str                 # Stable internal key (also used for unique_id suffix)
    name: str                # Human-friendly name shown in Home Assistant
    address: int             # Manual register address from Danfoss documentation
    reg_type: RegisterType   # How the value is decoded

    # Presentation metadata (Home Assistant)
    unit: str | None = None
    device_class: str | None = None
    state_class: str | None = "measurement"
    icon: str | None = None

    # Value handling
    scale: float = 1.0       # Apply after decoding (e.g. int16 * 0.1)
    signed: bool = True      # Only relevant for INT16

    # Write support
    writable: bool = False   # True if the register supports writing (RW)

    # Optional limits for writable numeric registers
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None

    # Optional mapping for mode/token registers
    # Example: {1: "Comfort", 2: "Night", 3: "Frost"}
    value_map: Mapping[int, str] | None = None


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
    RegisterDef(
        key="heat_return_temperature_reference",
        name="Heat return temperature reference",
        address=21210,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        state_class="measurement",
        icon="mdi:thermometer-water",
        writable=True,
        min_value=5,
        max_value=150,
        step=0.1,
    ),
    RegisterDef(
        key="operation_mode",
        name="Operation mode",
        address=21000,
        reg_type=RegisterType.INT16,
        signed=False,
        writable=True,
        value_map={
            0: "Automatic",
            1: "Comfort",
            2: "Saving",
            3: "Frost protection",
        },
    ),
    RegisterDef(
        key="operation_status",
        name="Operation status",
        address=21001,
        reg_type=RegisterType.INT16,
        signed=False,
        writable=False,
        value_map={
            0: "Comfort",
            1: "Saving",
            2: "Frost protection",
        },
    ),
]

# -----------------------------------------------------------------------------
# Circuit 1 – Supply temperature (flow temperature / heating curve)
# DK: Fremløbstemperatur for kreds 1
# -----------------------------------------------------------------------------
REG_CIRCUIT1_SUPPLY: Final[list[RegisterDef]] = [
    # DK: Min. fremløbstemperatur for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_min",
        name="Circuit 1 minimum supply temperature",
        address=21202,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=True,
        min_value=5,
        max_value=150,
        step=1.0,
    ),
    # DK: Max. fremløbstemperatur for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_max",
        name="Circuit 1 maximum supply temperature",
        address=21204,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=True,
        min_value=5,
        max_value=150,
        step=1.0,
    ),
    # DK: Fremløbstemperatur ved -30°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_minus30",
        name="Circuit 1 supply temperature at -30 °C",
        address=21232,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
    # DK: Fremløbstemperatur ved -15°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_minus15",
        name="Circuit 1 supply temperature at -15 °C",
        address=21234,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
    # DK: Fremløbstemperatur ved -5°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_minus5",
        name="Circuit 1 supply temperature at -5 °C",
        address=21236,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
    # DK: Fremløbstemperatur ved 0°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_0",
        name="Circuit 1 supply temperature at 0 °C",
        address=21238,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
    # DK: Fremløbstemperatur ved 5°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_5",
        name="Circuit 1 supply temperature at 5 °C",
        address=21240,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
    # DK: Fremløbstemperatur ved 15°C for kreds 1
    RegisterDef(
        key="circuit1_supply_temp_at_15",
        name="Circuit 1 supply temperature at 15 °C",
        address=21242,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=False,
    ),
]


# -----------------------------------------------------------------------------
# Circuit 1 – PID tuning / regulation parameters
# DK: Reguleringsparametre for kreds 1
# -----------------------------------------------------------------------------
REG_CIRCUIT1_PID_TUNING: Final[list[RegisterDef]] = [
    RegisterDef(
        key="circuit1_pid_xp_low",
        name="Circuit 1 PID Xp (low)",
        address=21446,
        reg_type=RegisterType.INT16,   # UInt16 in docs -> use INT16 with signed=False
        signed=False,
        unit="K",
        writable=True,
        min_value=0,
        max_value=250,
        step=1,
        icon="mdi:tune",
    ),
    RegisterDef(
        key="circuit1_pid_xp_high",
        name="Circuit 1 PID Xp (high)",
        address=21447,
        reg_type=RegisterType.INT16,   # UInt16 in docs -> use INT16 with signed=False
        signed=False,
        unit="K",
        writable=True,
        min_value=0,
        max_value=250,
        step=1,
        icon="mdi:tune",
    ),
    RegisterDef(
        key="circuit1_pid_tn",
        name="Circuit 1 PID Tn (adaptation time)",
        address=21448,
        reg_type=RegisterType.INT16,   # UInt16 in docs -> use INT16 with signed=False
        signed=False,
        unit="s",
        device_class="duration",
        writable=True,
        min_value=0,
        max_value=999,
        step=1,
        icon="mdi:timer-outline",
    ),
    RegisterDef(
        key="circuit1_pid_deadband",
        name="Circuit 1 PID deadband (Nz)",
        address=21458,
        reg_type=RegisterType.FLOAT,
        unit="K",
        writable=True,
        min_value=0.0,
        max_value=20.0,
        step=1.0,
        scale=2.0,  # scale=2.0 due to 0.5 K resolution in ECL (Modbus value * 2 = UI value)
        icon="mdi:arrow-expand-horizontal",
    ),
]


# -----------------------------------------------------------------------------
# Comfort / Saving / Boost (room limiter + boost)
# -----------------------------------------------------------------------------
REG_COMFORT_SAVING_BOOST: Final[list[RegisterDef]] = [
    # DK: Komforttemperatur references
    RegisterDef(
        key="heat_room_comfort_relative_reference",
        name="Heat room comfort relative reference",
        address=21212,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=True,
        min_value=0.5,
        max_value=5.0,
        step=0.5,
        icon="mdi:home-thermometer",
    ),
    # DK: Sparetemperatur references
    RegisterDef(
        key="heat_room_saving_relative_reference",
        name="Heat room saving relative reference",
        address=21214,
        reg_type=RegisterType.FLOAT,
        unit="°C",
        device_class="temperature",
        writable=True,
        min_value=0.5,
        max_value=5.0,
        step=0.5,
        icon="mdi:home-thermometer-outline",
    ),

    # Boost
    RegisterDef(
        key="boost_active",
        name="Boost active",
        address=21003,
        reg_type=RegisterType.INT16,   # UInt16 in docs -> use INT16 with signed=False
        signed=False,
        writable=True,
        value_map={
            0: "Off",
            1: "On",
        },
        icon="mdi:rocket-launch",
    ),
    RegisterDef(
        key="boost_remaining_time",
        name="Boost remaining time",
        address=21004,
        reg_type=RegisterType.FLOAT,
        unit="s",
        writable=False,
        icon="mdi:timer-outline",
    ),
    RegisterDef(
        key="boost_period",
        name="Boost period",
        address=21438,
        reg_type=RegisterType.UINT32,
        unit="s",
        writable=True,
        min_value=0,
        max_value=86400,
        step=60,
        icon="mdi:timer-cog-outline",
    ),
    RegisterDef(
        key="boost_added_temperature",
        name="Boost added temperature",
        address=21440,
        reg_type=RegisterType.FLOAT,
        unit="K",
        writable=True,
        min_value=0.0,
        max_value=25.0,
        step=1.0,
        icon="mdi:thermometer-plus",
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
    *REG_CIRCUIT1_SUPPLY,
    *REG_CIRCUIT1_PID_TUNING,
    *REG_COMFORT_SAVING_BOOST,
]


def option_key(reg_key: str) -> str:
    """Return the config entry options key used to enable/disable a register.

    We keep this in one place to ensure `config_flow.py` and `sensor.py`
    always agree on the exact options key naming.
    """
    return f"enable_{reg_key}"