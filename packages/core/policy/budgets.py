from __future__ import annotations


def enforce(budget_mode: str, over_budget: bool) -> str:
    if budget_mode == "hard" and over_budget:
        return "deny"
    if budget_mode == "soft" and over_budget:
        return "degrade"  # auto downshift routes/models
    return "allow"

