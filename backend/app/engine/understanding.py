from __future__ import annotations

import logging

from app.models.requirements import (
    ExtractedRequirements,
    APIReference,
    ToolSketch,
    RequirementGap,
)

log = logging.getLogger("mcp.understanding")


def _normalize_string_list(items: list) -> list[str]:
    """LLM sometimes returns dicts instead of strings — flatten them."""
    result = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            result.append(str(item))
        else:
            result.append(str(item))
    return result


def _safe_parse_list(raw: list, model_cls, label: str) -> list:
    """Parse a list of dicts into pydantic models, skipping bad entries."""
    parsed = []
    for i, entry in enumerate(raw):
        try:
            if isinstance(entry, dict):
                parsed.append(model_cls(**entry))
            elif isinstance(entry, model_cls):
                parsed.append(entry)
        except Exception as e:
            log.warning("[%s] Skipping entry %d: %s", label, i, e)
    return parsed


def parse_understanding_response(data: dict) -> ExtractedRequirements:
    """Parse the JSON output from the understanding phase into ExtractedRequirements."""
    log.info("[parse] Raw keys from LLM: %s", list(data.keys()))

    reqs = ExtractedRequirements(
        intent=data.get("intent"),
        intent_confidence=data.get("intent_confidence", 0.0),
        apis_mentioned=_safe_parse_list(data.get("apis_mentioned", []), APIReference, "apis"),
        tools_requested=_safe_parse_list(data.get("tools_requested", []), ToolSketch, "tools"),
        features_requested=data.get("features_requested", []),
        gaps=_safe_parse_list(data.get("gaps", []), RequirementGap, "gaps"),
        preferred_language=data.get("preferred_language"),
        auth_requirements=_normalize_string_list(data.get("auth_requirements", [])),
        env_vars_known=_normalize_string_list(data.get("env_vars_known", [])),
        completeness_score=data.get("completeness_score", 0.0),
    )

    log.info("[parse] Intent: %s (confidence: %.2f, completeness: %.2f)",
             reqs.intent, reqs.intent_confidence, reqs.completeness_score)
    log.info("[parse] Tools: %d, APIs: %d, Gaps: %d",
             len(reqs.tools_requested), len(reqs.apis_mentioned), len(reqs.gaps))
    return reqs


def merge_requirements(
    existing: ExtractedRequirements,
    update: dict,
) -> ExtractedRequirements:
    """Merge clarification update into existing requirements."""
    log.info("[merge] Merging clarification data, keys: %s", list(update.keys()))

    merged = ExtractedRequirements(
        intent=update.get("intent", existing.intent),
        intent_confidence=update.get("intent_confidence", existing.intent_confidence),
        apis_mentioned=_safe_parse_list(update.get("apis_mentioned", []), APIReference, "apis")
            if "apis_mentioned" in update else existing.apis_mentioned,
        tools_requested=_safe_parse_list(update.get("tools_requested", []), ToolSketch, "tools")
            if "tools_requested" in update else existing.tools_requested,
        features_requested=update.get("features_requested", existing.features_requested),
        gaps=_safe_parse_list(update.get("gaps", []), RequirementGap, "gaps")
            if "gaps" in update else existing.gaps,
        preferred_language=update.get("preferred_language", existing.preferred_language),
        auth_requirements=_normalize_string_list(update.get("auth_requirements", existing.auth_requirements)),
        env_vars_known=_normalize_string_list(update.get("env_vars_known", existing.env_vars_known)),
        completeness_score=update.get("completeness_score", existing.completeness_score),
    )

    log.info("[merge] Result — completeness: %.2f, gaps: %d, tools: %d",
             merged.completeness_score, len(merged.gaps), len(merged.tools_requested))
    return merged
