"""
Tool Tests (Python)

PATTERN: Test each tool in isolation.
AI Factory generates test cases for each tool automatically.

Uses pytest + pytest-asyncio for async tool testing.
"""

import pytest
import json


# {{TOOL_TEST_IMPORTS}} — AI factory adds per-tool imports
# from mcp_server_template.tools._example_tool import register_example_search_tool


class TestToolTemplate:
    """Template for AI Factory to generate tool tests."""

    def test_placeholder(self):
        """Replace with actual tool tests."""
        assert True

    # Example of what AI Factory generates:
    #
    # @pytest.mark.asyncio
    # async def test_example_search_valid_query(self):
    #     """Test that search returns results for valid query."""
    #     result = await example_search(query="test", limit=5)
    #     data = json.loads(result)
    #     assert "results" in data
    #     assert "totalCount" in data
    #     assert data["totalCount"] >= 0
    #
    # @pytest.mark.asyncio
    # async def test_example_search_empty_query(self):
    #     """Test behavior with empty query."""
    #     result = await example_search(query="", limit=10)
    #     data = json.loads(result)
    #     assert "results" in data


class TestValidation:
    """Test input validation utilities."""

    def test_validate_path_within_allowed(self, tmp_path):
        from mcp_server_template.utils.validation import validate_path
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        result = validate_path(str(test_file), [str(tmp_path)])
        assert result == test_file.resolve()

    def test_validate_path_traversal_blocked(self, tmp_path):
        from mcp_server_template.utils.validation import validate_path
        with pytest.raises(ValueError, match="Access denied"):
            validate_path("../../etc/passwd", [str(tmp_path)])

    def test_require_env_vars_missing(self):
        from mcp_server_template.utils.validation import require_env_vars
        with pytest.raises(EnvironmentError, match="Missing"):
            require_env_vars(["DEFINITELY_NOT_SET_12345"])
