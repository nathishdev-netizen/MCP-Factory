from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TemplateLoader:
    def __init__(self) -> None:
        self._manifest: dict[str, Any] = {}
        self._loaded = False

    def load(self, manifest_path: str) -> None:
        path = Path(manifest_path).resolve()
        if not path.exists():
            print(f"[template_loader] WARNING: Manifest not found at {path}")
            return
        with open(path) as f:
            self._manifest = json.load(f)
        self._loaded = True
        print(f"[template_loader] Loaded manifest from {path}")

    @property
    def manifest(self) -> dict[str, Any]:
        return self._manifest

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def get_placeholders(self) -> dict[str, Any]:
        return self._manifest.get("placeholders", {})

    def get_generation_rules(self) -> dict[str, Any]:
        return self._manifest.get("ai_generation_rules", {})

    def get_template_info(self, language: str) -> dict[str, Any]:
        return self._manifest.get("templates", {}).get(language, {})

    def get_constraints_text(self) -> str:
        """Return a formatted text summary of template constraints for LLM prompts."""
        rules = self.get_generation_rules()
        placeholders = self.get_placeholders()

        lines = [
            "TEMPLATE CONSTRAINTS:",
            f"- Server name: must match {placeholders.get('{{SERVER_NAME}}', {}).get('validation', 'N/A')}",
            f"- Tool naming: {rules.get('tool_name_convention', 'snake_case')}",
            f"- Tool file naming (TS): {rules.get('tool_file_naming', {}).get('typescript', 'kebab-case.ts')}",
            f"- Tool file naming (Python): {rules.get('tool_file_naming', {}).get('python', 'snake_case.py')}",
            f"- One tool per file: {rules.get('one_tool_per_file', True)}",
            f"- Max tools per server: {rules.get('max_tools_per_server', 25)}",
            "",
            "Always include in generated tools:",
        ]
        for item in rules.get("always_include", []):
            lines.append(f"  - {item}")

        lines.append("")
        lines.append("Never include in generated tools:")
        for item in rules.get("never_include", []):
            lines.append(f"  - {item}")

        ts_info = self.get_template_info("typescript")
        py_info = self.get_template_info("python")
        lines.extend([
            "",
            "Available languages:",
            f"  TypeScript: {', '.join(ts_info.get('best_for', []))}",
            f"  Python: {', '.join(py_info.get('best_for', []))}",
        ])

        return "\n".join(lines)


template_loader = TemplateLoader()
