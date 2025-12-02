from __future__ import annotations

"""Home Assistant entry points for the ECL Modbus integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Basic setup from YAML (not used, but required by Home Assistant)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ECL Modbus from a config entry created via the UI."""
    hass.data.setdefault(DOMAIN, {})

    # Forward the config entry to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload integration automatically when the entry is updated (options changed)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and close the Modbus client."""
    # Close the Modbus hub (if any) to free the serial port
    hub = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if hub is not None:
        try:
            hub.close()
        except Exception:  # noqa: BLE001
            # Do not let errors in close() break unloading
            pass

    # Unload all platforms (sensors)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle config entry updates (e.g. options changed) by reloading."""
    await hass.config_entries.async_reload(entry.entry_id)