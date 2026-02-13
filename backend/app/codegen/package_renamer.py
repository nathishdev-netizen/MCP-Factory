from __future__ import annotations

import logging
from pathlib import Path

from app.models.architecture import MCPArchitecture

log = logging.getLogger("mcp.codegen.renamer")

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz",
    ".pyc", ".pyo",
}


def rename_if_python(dest_dir: Path, arch: MCPArchitecture) -> None:
    """Rename the Python package directory and update all internal references.

    Renames src/mcp_server_template/ → src/mcp_server_{server_name}/
    and replaces all occurrences of the old name in text files.
    """
    if arch.language != "python":
        return

    old_name = "mcp_server_template"
    # Replace hyphens with underscores for valid Python package name
    new_name = f"mcp_server_{arch.server_name.replace('-', '_')}"

    if old_name == new_name:
        return

    # Rename the directory
    old_dir = dest_dir / "src" / old_name
    new_dir = dest_dir / "src" / new_name

    if old_dir.exists():
        old_dir.rename(new_dir)
        log.info("Renamed %s → %s", old_name, new_name)

    # Walk all text files and replace references
    replaced_count = 0
    for file_path in dest_dir.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        if old_name in content:
            file_path.write_text(content.replace(old_name, new_name), encoding="utf-8")
            replaced_count += 1

    log.info("Updated %d files with new package name: %s", replaced_count, new_name)
