"""Type definitions for the SOMweb integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from somweb import SomwebClient

type SomwebConfigEntry = ConfigEntry[SomwebClient]
