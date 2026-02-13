from __future__ import annotations

import logging
from pathlib import Path

from app.models.architecture import MCPArchitecture

log = logging.getLogger("mcp.codegen.tests")


def generate_test_file(project_dir: Path, arch: MCPArchitecture) -> None:
    """Generate actual test stubs that import and verify each tool registers."""
    if arch.language == "python":
        _generate_python_tests(project_dir, arch)
    else:
        _generate_typescript_tests(project_dir, arch)


def _generate_python_tests(project_dir: Path, arch: MCPArchitecture) -> None:
    pkg_name = f"mcp_server_{arch.server_name.replace('-', '_')}"

    imports = [
        '"""',
        f"Auto-generated tests for mcp-server-{arch.server_name}",
        "",
        "Each test verifies that a tool/resource/prompt registers correctly",
        "with a FastMCP instance. Extend these with your own test cases.",
        '"""',
        "",
        "import pytest",
        "from unittest.mock import MagicMock",
        "",
    ]

    test_classes = []

    # Tool tests
    for tool in arch.tools:
        module = tool.file_name.replace(".py", "")
        snake = tool.name.replace(".", "_").replace("-", "_")
        func = f"register_{snake}_tool"
        class_name = "".join(w.capitalize() for w in snake.split("_"))

        imports.append(f"from {pkg_name}.tools.{module} import {func}")

        test_classes.append(f"""

class Test{class_name}:
    \\"\\"\\"Tests for the {tool.name} tool.\\"\\"\\"

    @pytest.fixture
    def mcp(self):
        return MagicMock()

    def test_registers_without_error(self, mcp):
        \\"\\"\\"Verify {tool.name} registers with FastMCP.\\"\\"\\"
        {func}(mcp)
        assert mcp.tool.called
""")

    # Resource tests
    if arch.enable_resources:
        for res in arch.resources:
            module = res.file_name.replace(".py", "")
            snake = res.name.lower().replace(" ", "_").replace(".", "_").replace("-", "_")
            func = f"register_{snake}_resource"
            class_name = "".join(w.capitalize() for w in snake.split("_"))

            imports.append(f"from {pkg_name}.resources.{module} import {func}")

            test_classes.append(f"""

class TestResource{class_name}:
    \\"\\"\\"Tests for the {res.name} resource.\\"\\"\\"

    @pytest.fixture
    def mcp(self):
        return MagicMock()

    def test_registers_without_error(self, mcp):
        \\"\\"\\"Verify {res.name} resource registers.\\"\\"\\"
        {func}(mcp)
        assert mcp.resource.called
""")

    # Prompt tests
    if arch.enable_prompts:
        for prompt in arch.prompts:
            module = prompt.file_name.replace(".py", "")
            snake = prompt.name.replace(".", "_").replace("-", "_")
            func = f"register_{snake}_prompt"
            class_name = "".join(w.capitalize() for w in snake.split("_"))

            imports.append(f"from {pkg_name}.prompts.{module} import {func}")

            test_classes.append(f"""

class TestPrompt{class_name}:
    \\"\\"\\"Tests for the {prompt.name} prompt.\\"\\"\\"

    @pytest.fixture
    def mcp(self):
        return MagicMock()

    def test_registers_without_error(self, mcp):
        \\"\\"\\"Verify {prompt.name} prompt registers.\\"\\"\\"
        {func}(mcp)
        assert mcp.prompt.called
""")

    content = "\n".join(imports) + "\n" + "\n".join(test_classes)
    test_file = project_dir / "tests" / "test_tools.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(content, encoding="utf-8")
    log.info("Generated test file with %d tool + %d resource + %d prompt tests",
             len(arch.tools),
             len(arch.resources) if arch.enable_resources else 0,
             len(arch.prompts) if arch.enable_prompts else 0)


def _generate_typescript_tests(project_dir: Path, arch: MCPArchitecture) -> None:
    imports = [
        f'// Auto-generated tests for mcp-server-{arch.server_name}',
        f'import {{ describe, it, expect, vi }} from "vitest";',
        "",
    ]

    test_blocks = []

    for tool in arch.tools:
        module = tool.file_name.replace(".ts", "")
        parts = tool.name.replace("-", ".").split(".")
        func = "register" + "".join(p.capitalize() for p in parts) + "Tool"

        imports.append(f'import {{ {func} }} from "../tools/{module}.js";')

        test_blocks.append(f"""
describe("{tool.name}", () => {{
  it("registers without error", () => {{
    const server = {{ tool: vi.fn() }};
    {func}(server as any);
    expect(server.tool).toHaveBeenCalled();
  }});
}});
""")

    if arch.enable_resources:
        for res in arch.resources:
            module = res.file_name.replace(".ts", "")
            parts = res.name.lower().replace(" ", "_").replace("-", "_").split("_")
            func = "register" + "".join(p.capitalize() for p in parts) + "Resource"

            imports.append(f'import {{ {func} }} from "../resources/{module}.js";')

            test_blocks.append(f"""
describe("resource: {res.name}", () => {{
  it("registers without error", () => {{
    const server = {{ resource: vi.fn() }};
    {func}(server as any);
    expect(server.resource).toHaveBeenCalled();
  }});
}});
""")

    if arch.enable_prompts:
        for prompt in arch.prompts:
            module = prompt.file_name.replace(".ts", "")
            parts = prompt.name.replace("-", "_").split("_")
            func = "register" + "".join(p.capitalize() for p in parts) + "Prompt"

            imports.append(f'import {{ {func} }} from "../prompts/{module}.js";')

            test_blocks.append(f"""
describe("prompt: {prompt.name}", () => {{
  it("registers without error", () => {{
    const server = {{ prompt: vi.fn() }};
    {func}(server as any);
    expect(server.prompt).toHaveBeenCalled();
  }});
}});
""")

    content = "\n".join(imports) + "\n" + "\n".join(test_blocks)
    test_file = project_dir / "src" / "__tests__" / "tools.test.ts"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(content, encoding="utf-8")
    log.info("Generated TypeScript test file")
