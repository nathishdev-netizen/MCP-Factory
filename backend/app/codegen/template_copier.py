from __future__ import annotations

import logging
import shutil
from pathlib import Path

from app.config import settings

log = logging.getLogger("mcp.codegen.copier")


def get_template_dir(language: str) -> Path:
    """Resolve the template directory for the given language."""
    manifest = Path(settings.template_manifest_path).resolve()
    return manifest.parent / language


def copy_template(language: str, dest_dir: Path) -> None:
    """Copy the base template for the given language into dest_dir."""
    template_dir = get_template_dir(language)
    if not template_dir.exists():
        raise FileNotFoundError(f"Template directory not found: {template_dir}")

    shutil.copytree(template_dir, dest_dir, dirs_exist_ok=True)
    log.info("Copied %s template to %s", language, dest_dir)
