"""In-memory home device state backed by JSON (replaces global HOME_DB)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_HOME: dict[str, str] = {
    "light": "off",
    "tv": "off",
    "curtain": "closed",
    "door_lock": "locked",
    "thermostat_mode": "off",
    "main_water_valve": "closed",
}


class HomeStatusStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._data: dict[str, Any] = {}

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            self._data = dict(_DEFAULT_HOME)
            logger.warning("Home status file not found at %s; using defaults.", self._path)
            return self._data
        try:
            with open(self._path, encoding="utf-8") as f:
                self._data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not read home status from %s: %s; using defaults.", self._path, e)
            self._data = dict(_DEFAULT_HOME)
        return self._data

    def update_device(self, device_id: str, value: str) -> None:
        if device_id in self._data:
            self._data[device_id] = value
        else:
            if "thermostat" in device_id:
                self._data["thermostat_mode"] = value
            if "door" in device_id:
                self._data["door_lock"] = value

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f)
        logger.info("Database synced to %s", self._path)
