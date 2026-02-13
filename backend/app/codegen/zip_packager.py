from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path

log = logging.getLogger("mcp.codegen.zip")


def create_zip(project_dir: Path, server_name: str) -> Path:
    """Create a ZIP file from the generated project directory.

    The ZIP root directory is mcp-server-{server_name}/ so it extracts cleanly.
    Returns the path to the created ZIP file.
    """
    zip_filename = f"mcp-server-{server_name}.zip"
    zip_path = Path(tempfile.gettempdir()) / zip_filename
    root_name = f"mcp-server-{server_name}"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(project_dir.rglob("*")):
            if file_path.is_file():
                arcname = f"{root_name}/{file_path.relative_to(project_dir)}"
                zf.write(file_path, arcname)

    size_kb = zip_path.stat().st_size / 1024
    log.info("Created ZIP: %s (%.1f KB)", zip_path, size_kb)
    return zip_path
