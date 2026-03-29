"""User memory text file persistence."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class UserMemoryStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def read(self) -> str:
        memory = ""
        try:
            if self._path.exists():
                with open(self._path, encoding="utf-8") as f:
                    memory = f.read()
                logger.info("Loaded existing memory from '%s'.", self._path)
            else:
                logger.info("'%s' file not found. Initializing memory as empty.", self._path)
        except OSError as e:
            logger.warning("File read error: %s. Initializing memory as empty.", e)
        except Exception as e:
            logger.warning("An unexpected error occurred (reading): %s. Initializing memory as empty.", e)
        return memory

    def write(self, content: str) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            f.write(content)
