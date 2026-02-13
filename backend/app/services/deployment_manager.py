from __future__ import annotations

import asyncio
import logging
import shutil
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger("mcp.deployment")

# Port range for deployed MCP servers
_PORT_START = 3001
_PORT_END = 3099

# Base directory for persistent deployments
_DEPLOYMENTS_DIR = Path.home() / ".mcp-factory" / "deployments"


@dataclass
class DeploymentInfo:
    """Tracks a running MCP server deployment."""
    session_id: str
    server_name: str
    language: str
    port: int
    project_dir: str
    process: subprocess.Popen | None = None
    status: str = "pending"  # pending | installing | starting | running | failed | stopped
    error: str | None = None
    server_url: str = ""
    sse_url: str = ""


class DeploymentManager:
    """Manages deployed MCP server processes."""

    def __init__(self) -> None:
        self._deployments: dict[str, DeploymentInfo] = {}  # session_id -> info
        self._used_ports: set[int] = set()
        _DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)

    def _find_available_port(self) -> int:
        """Find an available port in the deployment range."""
        for port in range(_PORT_START, _PORT_END + 1):
            if port in self._used_ports:
                continue
            # Check if port is actually free
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        raise RuntimeError("No available ports for MCP server deployment")

    async def deploy(
        self,
        session_id: str,
        server_name: str,
        language: str,
        project_dir: Path,
        env_vars: dict[str, str] | None = None,
        progress_callback=None,
    ) -> DeploymentInfo:
        """Deploy a generated MCP server.

        1. Copy project to persistent directory
        2. Install dependencies (uv sync / npm install)
        3. Start server with HTTP transport on a dynamic port
        """
        port = self._find_available_port()
        self._used_ports.add(port)

        # Copy to persistent deployment dir
        deploy_dir = _DEPLOYMENTS_DIR / f"mcp-server-{server_name}"
        if deploy_dir.exists():
            shutil.rmtree(deploy_dir)
        shutil.copytree(project_dir, deploy_dir)

        info = DeploymentInfo(
            session_id=session_id,
            server_name=server_name,
            language=language,
            port=port,
            project_dir=str(deploy_dir),
        )
        self._deployments[session_id] = info

        try:
            # Step 1: Install dependencies
            info.status = "installing"
            if progress_callback:
                await progress_callback("Installing dependencies...", 1, 3)

            await self._install_deps(deploy_dir, language)

            # Step 2: Start server
            info.status = "starting"
            if progress_callback:
                await progress_callback("Starting MCP server...", 2, 3)

            process = await self._start_server(deploy_dir, server_name, language, port, env_vars)
            info.process = process

            # Step 3: Wait for server to be ready
            await self._wait_for_ready(port, process)

            info.status = "running"
            info.server_url = f"http://localhost:{port}"
            info.sse_url = f"http://localhost:{port}/mcp"

            if progress_callback:
                await progress_callback("MCP server is running!", 3, 3)

            log.info("Deployment ready: %s on port %d", server_name, port)
            return info

        except Exception as e:
            info.status = "failed"
            info.error = str(e)
            self._used_ports.discard(port)
            log.error("Deployment failed for %s: %s", server_name, e)
            # Don't re-raise — caller handles via info.status
            if progress_callback:
                await progress_callback(f"Deployment failed: {e}", 3, 3)
            return info

    async def _install_deps(self, deploy_dir: Path, language: str) -> None:
        """Install project dependencies."""
        if language == "python":
            cmd = ["uv", "sync"]
        else:
            cmd = ["npm", "install"]

        log.info("Installing deps: %s in %s", " ".join(cmd), deploy_dir)

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(deploy_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace").strip()
            log.error("Dependency install failed: %s", error_msg)
            raise RuntimeError(f"Dependency install failed: {error_msg[:500]}")

        log.info("Dependencies installed successfully")

    async def _start_server(
        self,
        deploy_dir: Path,
        server_name: str,
        language: str,
        port: int,
        env_vars: dict[str, str] | None = None,
    ) -> subprocess.Popen:
        """Start the MCP server process with HTTP transport."""
        import os

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        pkg_name = f"mcp-server-{server_name}"

        if language == "python":
            cmd = [
                "uv", "run",
                pkg_name, "--transport", "http", "--port", str(port),
            ]
        else:
            cmd = [
                "node", "dist/index.js",
                "--transport", "http", "--port", str(port),
            ]

        log.info("Starting server: %s (port %d)", " ".join(cmd), port)

        process = subprocess.Popen(
            cmd,
            cwd=str(deploy_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return process

    async def _wait_for_ready(self, port: int, process: subprocess.Popen, timeout: float = 30.0) -> None:
        """Wait for the server to accept connections."""
        import time

        start = time.monotonic()
        while time.monotonic() - start < timeout:
            # Check if process crashed
            if process.poll() is not None:
                stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
                stdout = process.stdout.read().decode("utf-8", errors="replace") if process.stdout else ""
                output = (stderr or stdout).strip()
                log.error("Server process exited with code %d: %s", process.returncode, output[-1000:])
                raise RuntimeError(f"Server crashed (exit code {process.returncode}): {output[-500:]}")

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1.0)
                    s.connect(("127.0.0.1", port))
                    log.info("Server is accepting connections on port %d", port)
                    return
            except (ConnectionRefusedError, OSError):
                await asyncio.sleep(0.5)

        raise RuntimeError(f"Server did not start within {timeout}s on port {port}")

    def get_deployment(self, session_id: str) -> DeploymentInfo | None:
        """Get deployment info for a session."""
        return self._deployments.get(session_id)

    def stop_deployment(self, session_id: str) -> bool:
        """Stop a running deployment."""
        info = self._deployments.get(session_id)
        if not info:
            return False

        if info.process and info.process.poll() is None:
            info.process.terminate()
            try:
                info.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                info.process.kill()

        info.status = "stopped"
        self._used_ports.discard(info.port)
        log.info("Stopped deployment: %s (port %d)", info.server_name, info.port)
        return True

    def stop_all(self) -> None:
        """Stop all running deployments (for shutdown)."""
        for session_id in list(self._deployments.keys()):
            self.stop_deployment(session_id)

    def get_client_config(self, info: DeploymentInfo) -> dict:
        """Generate per-client MCP configs for a running deployment."""
        url = info.sse_url  # e.g. http://localhost:3001/mcp

        return {
            "claude_desktop": {
                "mcpServers": {
                    info.server_name: {
                        "command": "npx",
                        "args": ["@pyroprompts/mcp-stdio-to-streamable-http-adapter"],
                        "env": {
                            "URI": url,
                        },
                    }
                }
            },
            "cursor": {
                "mcpServers": {
                    info.server_name: {
                        "url": url,
                    }
                }
            },
            "generic": {
                "mcpServers": {
                    info.server_name: {
                        "url": url,
                    }
                }
            },
        }

    def list_deployments(self) -> list[DeploymentInfo]:
        return list(self._deployments.values())


deployment_manager = DeploymentManager()
