from __future__ import annotations

from app.models.requirements import ExtractedRequirements, RequirementGap
from app.models.messages import WSFrame, WSMessageType, OptionItem


def has_high_priority_gaps(requirements: ExtractedRequirements) -> bool:
    """Check if there are unresolved high-priority gaps."""
    return any(
        g.priority == "high" and not g.resolved
        for g in requirements.gaps
    )


def should_proceed_to_design(requirements: ExtractedRequirements, threshold: float = 0.7) -> bool:
    """Determine if we have enough info to design the architecture."""
    if has_high_priority_gaps(requirements):
        return False
    if not requirements.intent or requirements.intent_confidence < 0.5:
        return False
    if not requirements.tools_requested:
        return False
    if requirements.completeness_score < threshold:
        return False
    return True


def build_options_frame(session_id: str, gap: RequirementGap) -> WSFrame:
    """Build a WSFrame with clickable options for a requirement gap."""
    options = []
    if gap.options:
        for i, opt in enumerate(gap.options):
            options.append(OptionItem(id=f"{gap.category}_{i}", label=opt))

    return WSFrame(
        type=WSMessageType.OPTIONS_PROMPT,
        session_id=session_id,
        payload={
            "question_id": f"q-{gap.category}",
            "question": gap.question,
            "options": [o.model_dump() for o in options],
            "allow_multiple": False,
            "allow_freeform": True,
        },
    )


def get_next_gap(requirements: ExtractedRequirements) -> RequirementGap | None:
    """Get the highest priority unresolved gap."""
    unresolved = [g for g in requirements.gaps if not g.resolved]
    if not unresolved:
        return None
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unresolved.sort(key=lambda g: priority_order.get(g.priority, 3))
    return unresolved[0]
