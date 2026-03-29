"""HTTP client for the local home automation FastAPI server."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class HomeApiClient:
    def __init__(
        self,
        base_url: str,
        session: requests.Session | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._session = session or requests.Session()

    def get_status(self) -> dict[str, Any]:
        response = self._session.get(f"{self._base}/status", timeout=30)
        response.raise_for_status()
        return response.json()

    def post_update_device(self, device_id: str, action: str) -> requests.Response:
        return self._session.post(
            f"{self._base}/update_device",
            json={"device_id": device_id, "action": action},
            timeout=30,
        )

    def log_initial_state(self) -> None:
        try:
            current_state = self.get_status()
            logger.info("Current Home State:")
            for device, state in current_state.items():
                logger.info("  - %s: %s", device, state)
        except Exception:
            logger.warning("Could not connect to server. Is main.py running?")
