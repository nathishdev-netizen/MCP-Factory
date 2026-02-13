from __future__ import annotations

import json
import logging
import py_compile
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.models.architecture import MCPArchitecture

log = logging.getLogger("mcp.codegen.validator")

# Env vars that are standard/system — don't flag as "discovered"
SYSTEM_ENV_VARS = {
    "HOME", "PATH", "USER", "SHELL", "TERM", "LANG", "PWD", "TMPDIR",
    "LOG_LEVEL", "NODE_ENV", "DEBUG", "CI", "PYTHONPATH", "VIRTUAL_ENV",
    "COMPLETION_TIME",
}


@dataclass
class ValidationResult:
    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    discovered_env_vars: list[str] = field(default_factory=list)


def validate_project(project_dir: Path, arch: MCPArchitecture) -> ValidationResult:
    """Run fast validation checks on the generated project."""
    result = ValidationResult()

    if arch.language == "python":
        _validate_python_syntax(project_dir, result)
        _check_file_consistency(project_dir, arch, result)
        _discover_env_vars_python(project_dir, arch, result)
        _validate_pyproject(project_dir, result)
    else:
        _check_file_consistency(project_dir, arch, result)
        _discover_env_vars_typescript(project_dir, arch, result)
        _validate_package_json(project_dir, result)

    result.passed = len(result.errors) == 0

    if result.errors:
        log.warning("Validation found %d errors", len(result.errors))
    if result.warnings:
        log.info("Validation found %d warnings", len(result.warnings))
    if result.discovered_env_vars:
        log.info("Discovered undocumented env vars: %s", result.discovered_env_vars)

    return result


# ── Python syntax ────────────────────────────────────────────────────────


def _validate_python_syntax(project_dir: Path, result: ValidationResult) -> None:
    """Run py_compile on all .py files to catch syntax errors."""
    for py_file in project_dir.rglob("*.py"):
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            result.warnings.append(f"Syntax error in {py_file.name}: {e.msg}")
            log.warning("Syntax error in %s: %s", py_file.name, e.msg)


# ── File consistency ─────────────────────────────────────────────────────


def _check_file_consistency(
    project_dir: Path, arch: MCPArchitecture, result: ValidationResult
) -> None:
    """Check that every tool/resource/prompt file referenced in architecture exists."""
    if arch.language == "python":
        pkg_name = f"mcp_server_{arch.server_name.replace('-', '_')}"
        base = project_dir / "src" / pkg_name
        tools_dir = base / "tools"
        resources_dir = base / "resources"
        prompts_dir = base / "prompts"
    else:
        tools_dir = project_dir / "src" / "tools"
        resources_dir = project_dir / "src" / "resources"
        prompts_dir = project_dir / "src" / "prompts"

    for tool in arch.tools:
        expected = tools_dir / tool.file_name
        if not expected.exists():
            result.errors.append(f"Missing tool file: {tool.file_name}")

    if arch.enable_resources:
        for res in arch.resources:
            expected = resources_dir / res.file_name
            if not expected.exists():
                result.errors.append(f"Missing resource file: {res.file_name}")

    if arch.enable_prompts:
        for prompt in arch.prompts:
            expected = prompts_dir / prompt.file_name
            if not expected.exists():
                result.errors.append(f"Missing prompt file: {prompt.file_name}")


# ── Env var discovery ────────────────────────────────────────────────────


def _discover_env_vars_python(
    project_dir: Path, arch: MCPArchitecture, result: ValidationResult
) -> None:
    """Find env vars used in Python code but not documented in architecture."""
    known = {v.name for v in arch.env_vars} | SYSTEM_ENV_VARS
    discovered = set()

    for py_file in project_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # os.environ.get("VAR") or os.environ["VAR"]
        for match in re.finditer(r'os\.environ(?:\.get)?\s*[\[\(]\s*["\'](\w+)["\']', content):
            var_name = match.group(1)
            if var_name not in known:
                discovered.add(var_name)

    result.discovered_env_vars = sorted(discovered)


def _discover_env_vars_typescript(
    project_dir: Path, arch: MCPArchitecture, result: ValidationResult
) -> None:
    """Find env vars used in TypeScript code but not documented."""
    known = {v.name for v in arch.env_vars} | SYSTEM_ENV_VARS
    discovered = set()

    for ts_file in project_dir.rglob("*.ts"):
        try:
            content = ts_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue

        # process.env.VAR_NAME
        for match in re.finditer(r'process\.env\.(\w+)', content):
            var_name = match.group(1)
            if var_name not in known:
                discovered.add(var_name)

    result.discovered_env_vars = sorted(discovered)


# ── Manifest validation ──────────────────────────────────────────────────


def _validate_pyproject(project_dir: Path, result: ValidationResult) -> None:
    """Check that pyproject.toml is valid."""
    pyproject = project_dir / "pyproject.toml"
    if not pyproject.exists():
        result.errors.append("Missing pyproject.toml")
        return

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            result.warnings.append("Cannot validate pyproject.toml (no tomllib/tomli)")
            return

    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception as e:
        result.errors.append(f"Invalid pyproject.toml: {e}")
        return

    project = data.get("project", {})
    if not project.get("name"):
        result.warnings.append("pyproject.toml missing project.name")
    if not project.get("dependencies"):
        result.warnings.append("pyproject.toml missing dependencies")


def _validate_package_json(project_dir: Path, result: ValidationResult) -> None:
    """Check that package.json is valid."""
    pkg_json = project_dir / "package.json"
    if not pkg_json.exists():
        result.errors.append("Missing package.json")
        return

    try:
        data = json.loads(pkg_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        result.errors.append(f"Invalid package.json: {e}")
        return

    if not data.get("name"):
        result.warnings.append("package.json missing name")
    if not data.get("dependencies"):
        result.warnings.append("package.json missing dependencies")


# ── Env example regeneration ─────────────────────────────────────────────


def regenerate_env_example(
    project_dir: Path, arch: MCPArchitecture, discovered: list[str]
) -> None:
    """Rewrite .env.example with architecture env vars + discovered ones."""
    lines = [
        f"# Environment Variables for mcp-server-{arch.server_name}",
        "# Copy this file to .env and fill in your values",
        "# NEVER commit .env to version control!",
        "",
        "LOG_LEVEL=INFO",
        "",
    ]

    if arch.env_vars:
        for var in arch.env_vars:
            req = "REQUIRED" if var.required else "optional"
            lines.append(f"# {var.description} ({req})")
            lines.append(f"{var.name}={var.example}")
            lines.append("")

    if discovered:
        lines.append("# --- Discovered in generated code ---")
        for var_name in discovered:
            lines.append(f"# Set your value below")
            lines.append(f"{var_name}=")
            lines.append("")

    env_file = project_dir / ".env.example"
    env_file.write_text("\n".join(lines), encoding="utf-8")
    log.info("Regenerated .env.example with %d arch vars + %d discovered",
             len(arch.env_vars), len(discovered))
