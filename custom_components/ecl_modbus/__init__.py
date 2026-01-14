from __future__ import annotations

"""Home Assistant entry points for the ECL Modbus integration."""

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_BAUDRATE,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SLAVE_ID,
    DEFAULT_TCP_PORT,
    DEFAULT_TRANSPORT,
    CONF_BAUDRATE,
    CONF_SCAN_INTERVAL,
    CONF_SLAVE_ID,
    CONF_TRANSPORT,
    CONF_HOST,
    CONF_TCP_PORT,
    TRANSPORT_TCP,
)
from .modbus import EclModbusCoordinator, EclModbusHub
from .registers import ALL_REGISTERS, option_key


def _clamp_scan_interval(value: Any) -> int:
    try:
        sec = int(value)
    except (TypeError, ValueError):
        sec = DEFAULT_SCAN_INTERVAL
    return max(5, min(3600, sec))


def _default_enabled_key(reg_key: str) -> bool:
    return reg_key in {"s3_temperature", "s4_temperature"}


def _entry_store(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    store = domain_data.get(entry.entry_id)
    if not isinstance(store, dict):
        store = {}
        domain_data[entry.entry_id] = store
    return store


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Create hub+coordinator and forward to platforms."""
    store = _entry_store(hass, entry)

    # Build enabled register list from options
    enabled_regs = []
    for reg in ALL_REGISTERS:
        enabled = bool(
            entry.options.get(option_key(reg.key), _default_enabled_key(reg.key))
        )
        if enabled:
            enabled_regs.append(reg)

    # Reuse hub if it already exists (prevents serial port lock issues on reload)
    hub = store.get("hub")
    if not isinstance(hub, EclModbusHub):
        transport = entry.data.get(CONF_TRANSPORT, DEFAULT_TRANSPORT)
        slave_id = entry.data.get(CONF_SLAVE_ID, DEFAULT_SLAVE_ID)

        if transport == TRANSPORT_TCP:
            hub = EclModbusHub(
                transport=transport,
                slave_id=slave_id,
                host=entry.data.get(CONF_HOST),
                tcp_port=entry.data.get(CONF_TCP_PORT, DEFAULT_TCP_PORT),
            )
        else:
            hub = EclModbusHub(
                transport=transport,
                slave_id=slave_id,
                port=entry.data[CONF_PORT],
                baudrate=entry.data.get(CONF_BAUDRATE, DEFAULT_BAUDRATE),
            )

        store["hub"] = hub

    # Create a fresh coordinator every setup (uses current enabled_regs + scan_interval)
    scan_interval_sec = _clamp_scan_interval(entry.options.get(CONF_SCAN_INTERVAL))
    coordinator = EclModbusCoordinator(hass, hub, enabled_regs, scan_interval_sec)

    # First refresh BEFORE platforms set up (prevents coordinator.data=None issues)
    await coordinator.async_config_entry_first_refresh()

    store["coordinator"] = coordinator
    store["registers"] = enabled_regs
    store["entry_title"] = entry.data.get(CONF_NAME, DEFAULT_NAME)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    hub = store.get("hub")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Close hub AFTER platforms are unloaded (safer)
    if hub is not None:
        try:
            hub.close()
        except Exception:  # noqa: BLE001
            pass

    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)