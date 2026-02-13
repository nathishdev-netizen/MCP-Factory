from __future__ import annotations

from pydantic import BaseModel, Field


class APIReference(BaseModel):
    name: str
    purpose: str
    auth_type: str | None = None
    base_url: str | None = None


class ToolSketch(BaseModel):
    name: str
    description: str
    input_params: list[str] = Field(default_factory=list)
    source: str = "user"  # "user" or "inferred"


class RequirementGap(BaseModel):
    category: str  # api_details, tool_behavior, auth, scope, language_preference
    question: str
    priority: str  # high, medium, low
    options: list[str] | None = None
    resolved: bool = False


class ExtractedRequirements(BaseModel):
    intent: str | None = None
    intent_confidence: float = 0.0

    apis_mentioned: list[APIReference] = Field(default_factory=list)
    tools_requested: list[ToolSketch] = Field(default_factory=list)
    features_requested: list[str] = Field(default_factory=list)

    gaps: list[RequirementGap] = Field(default_factory=list)

    preferred_language: str | None = None
    auth_requirements: list[str] = Field(default_factory=list)
    env_vars_known: list[str] = Field(default_factory=list)

    completeness_score: float = 0.0
