from __future__ import annotations


def roi_markdown(savings_usd: float, notes: list[str]) -> str:
    bullets = "\n".join([f"- {n}" for n in notes])
    return f"""# Prompt Go – ROI Report

**Estimated monthly savings:** ${savings_usd:,.2f}

Recommendations:
{bullets}
"""

