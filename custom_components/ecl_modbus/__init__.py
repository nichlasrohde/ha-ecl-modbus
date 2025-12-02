from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, PLATFORMS


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up ECL Modbus from YAML (ikke brugt, men kræves)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Sæt ECL Modbus op ud fra en config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Forward setup til platforme (sensor.py)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Når data/options ændres, reload entry automatisk
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Fjern en config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok and DOMAIN in hass.data:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Håndter opdatering af entry (options ændret)."""
    await hass.config_entries.async_reload(entry.entry_id)
