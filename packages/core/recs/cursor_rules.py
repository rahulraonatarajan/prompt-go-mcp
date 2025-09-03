from __future__ import annotations
from typing import Any


def weekly_rule_recommendations(stats: dict[str, Any]) -> dict[str, Any]:
    """
    Input: aggregated weekly stats per team/feature/model.
    Output: JSON with concise rule recommendations for Cursor Teams.
    """
    rules: list[dict[str, str]] = []

    # Example recommendations
    if stats.get("simple_qa_ratio", 0) > 0.3:
        rules.append({"rule": "downshift_simple_qa", "action": "use gpt-3.5 or local tiny-llama for short single-question prompts"})
    if stats.get("freshness_hits", 0) > 50:
        rules.append({"rule": "prefer_web_for_freshness", "action": "route 'latest/pricing/update/version' prompts to web first"})
    if stats.get("agent_overuse", 0) > 0.2:
        rules.append({"rule": "agent_threshold", "action": "require 'plan/implement/deploy' verbs before agent route"})

    summary = "Use smaller models for short Q&A, prefer web for freshness, and require action verbs for agents."
    return {"summary": summary, "rules": rules}

