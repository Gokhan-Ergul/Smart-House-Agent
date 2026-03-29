"""Rules and operations JSON (replaces inline rules_operations.json access)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RulesStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def ensure_default_file(self) -> None:
        if self._path.exists():
            return
        logger.info("rules_operations.json file not found. Using empty rules.")
        default_data = {"rules": [], "operations": []}
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("Home Agent Warning: Could not create rules file: %s", e)

    def get_operations_json_for_prompt(self) -> str:
        rules_content = "{}"
        try:
            if self._path.exists():
                with open(self._path, encoding="utf-8") as f:
                    data = json.load(f)
                    operations_list = data.get("operations", [])
                    formatted_modes: dict[str, Any] = {}
                    for item in operations_list:
                        name = item.get("operation_name")
                        actions = item.get("home_operations", [])
                        if name and actions:
                            formatted_modes[name] = actions
                    if formatted_modes:
                        rules_content = json.dumps(formatted_modes, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Home Agent Warning: Could not read rules file: %s", e)
        return rules_content

    def get_formatted_rules_and_operations(self) -> str:
        if not self._path.exists():
            return "Rules Agent: Dosya bulunamadı, henüz kural veya operasyon yok."

        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)

            output_lines: list[str] = []

            output_lines.append("RULES:")
            rules = data.get("rules", [])
            if rules:
                for rule in rules:
                    output_lines.append(f"- {rule}")
            else:
                output_lines.append("- (Kayıtlı kural yok)")

            output_lines.append("")

            output_lines.append("OPERATIONS:")
            operations = data.get("operations", [])
            if operations:
                for op in operations:
                    name = op.get("operation_name", "Bilinmeyen Operasyon")
                    actions_list = op.get("home_operations", [])
                    actions_str = ", ".join(actions_list)
                    output_lines.append(f"- {name} : {actions_str}")
            else:
                output_lines.append("- (Kayıtlı operasyon yok)")

            return "\n".join(output_lines)

        except json.JSONDecodeError:
            return "Rules Agent: Dosya formatı bozuk (JSON Hatası)."
        except Exception as e:
            return f"Rules Agent: Bir hata oluştu: {e}"
