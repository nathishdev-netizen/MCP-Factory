from __future__ import annotations

import json
import logging
import re

log = logging.getLogger("mcp.json_parser")


def extract_json(text: str) -> dict:
    """Extract JSON from LLM output, handling markdown fences and extra text."""

    # Try 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        log.debug("Direct parse failed: %s", e)

    # Try 2: Extract from ```json ... ``` fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError as e:
            log.debug("Fence parse failed: %s", e)

    # Try 3: Find the first { ... } block (greedy to get the outermost braces)
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        candidate = brace_match.group(0)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            log.warning("Brace extraction found %d chars but parse failed: %s", len(candidate), e)
            log.warning("  Last 200 chars: ...%s", candidate[-200:])
            # Check if it looks truncated (no closing brace at proper nesting)
            open_count = candidate.count("{")
            close_count = candidate.count("}")
            if open_count > close_count:
                log.warning("  Likely TRUNCATED: %d open braces vs %d close braces", open_count, close_count)

    log.error("All JSON extraction methods failed. Text length=%d, last 100 chars: ...%s",
              len(text), text[-100:])
    raise ValueError(f"Could not extract JSON from LLM response: {text[:200]}...")


def split_text_and_json(text: str) -> tuple[str, dict | None]:
    """Split LLM response into natural text and JSON parts.

    The LLM is prompted to use ---JSON--- as a separator.
    Returns (display_text, parsed_json_or_None).
    """
    separator = "---JSON---"
    if separator in text:
        parts = text.split(separator, 1)
        display_text = parts[0].strip()
        try:
            parsed = extract_json(parts[1])
            return display_text, parsed
        except ValueError:
            return display_text, None

    # No separator — try to find JSON at the end
    try:
        parsed = extract_json(text)
        # If the whole thing is valid JSON, there's no display text
        return "", parsed
    except ValueError:
        return text.strip(), None
