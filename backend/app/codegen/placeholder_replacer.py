from __future__ import annotations

import logging
import re
from pathlib import Path

from app.models.architecture import MCPArchitecture

log = logging.getLogger("mcp.codegen.replacer")

# Binary file extensions to skip
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz",
    ".pyc", ".pyo",
}


def _build_substitution_map(arch: MCPArchitecture) -> dict[str, str]:
    """Build a map of {{PLACEHOLDER}} → value from architecture fields."""
    return {
        "{{SERVER_NAME}}": arch.server_name,
        "{{SERVER_DESCRIPTION}}": arch.server_description,
        "{{SERVER_VERSION}}": arch.server_version,
        "{{SERVER_INSTRUCTIONS}}": arch.server_instructions or "",
    }


def _replace_capability_line(line: str, placeholder: str, value: bool) -> str:
    """Replace the boolean in a capability line that contains the placeholder comment.

    Example:
        Input:  '  tools: true,           // {{ENABLE_TOOLS}}'
        Output: '  tools: true,'  (if value is True)
        Output: '  tools: false,' (if value is False)
    """
    if placeholder not in line:
        return line
    # Replace the first true/false with the correct value, then strip the comment
    replaced = re.sub(r"(true|false)", str(value).lower(), line, count=1)
    # Remove the placeholder comment
    replaced = replaced.split(f"// {placeholder}")[0].rstrip()
    if not replaced.endswith(","):
        replaced += ","
    return replaced


def replace_all(dest_dir: Path, arch: MCPArchitecture) -> None:
    """Walk all files in dest_dir and substitute placeholders."""
    sub_map = _build_substitution_map(arch)
    file_count = 0

    for file_path in dest_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        original = content

        # Simple placeholder substitution
        for placeholder, value in sub_map.items():
            content = content.replace(placeholder, value)

        # Special handling for capability booleans (TypeScript template)
        content_lines = content.split("\n")
        new_lines = []
        for line in content_lines:
            line = _replace_capability_line(line, "{{ENABLE_TOOLS}}", arch.enable_tools)
            line = _replace_capability_line(line, "{{ENABLE_RESOURCES}}", arch.enable_resources)
            line = _replace_capability_line(line, "{{ENABLE_PROMPTS}}", arch.enable_prompts)
            new_lines.append(line)
        content = "\n".join(new_lines)

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            file_count += 1

    log.info("Replaced placeholders in %d files", file_count)
