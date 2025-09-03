from __future__ import annotations
import math
from .signals import has, FRESH_WORDS, COMPLEX_VERBS, AMBIGUOUS


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def score(prompt: str, weights: dict[str, float]) -> dict[str, float]:
    p = prompt.lower()
    s: dict[str, float] = dict(web=0.0, agent=0.0, ask=0.0, direct=0.0)
    if has(FRESH_WORDS, p):
        s["web"] += 1.2
    if "how much" in p or "compare" in p:
        s["web"] += 0.4
    if has(COMPLEX_VERBS, p) or "step-by-step" in p or p.count("\n- ") >= 2:
        s["agent"] += 1.1
    if has(AMBIGUOUS, p) or "not sure" in p or ("recommend" in p and "budget" not in p):
        s["ask"] += 0.9
    if len(p) < 280 and p.count("?") == 1 and not has(FRESH_WORDS, p) and not has(COMPLEX_VERBS, p):
        s["direct"] += 0.9
    return {k: _sigmoid(v) * weights.get(k, 1.0) for k, v in s.items()}


def explain(prompt: str) -> list[str]:
    p = prompt.lower()
    r: list[str] = []
    if has(FRESH_WORDS, p):
        r.append("Fresh/volatile info → web")
    if has(COMPLEX_VERBS, p) or "step-by-step" in p:
        r.append("Multi-step/tooling → agent")
    if has(AMBIGUOUS, p):
        r.append("Underspecified → ask")
    if len(p) < 280 and p.count("?") == 1 and not has(FRESH_WORDS, p):
        r.append("Short Q → direct")
    if not r:
        r.append("No strong signals; direct or ask are safe defaults")
    return r


def suggestion_pack(prompt: str) -> dict:
    q = prompt.strip().rstrip("?")
    return {
        "ask": [
            "Goal & success metric?",
            "Constraints (budget, deadline, platform)?",
            "Inputs available (files, URLs, APIs)?",
        ],
        "web": f"{q} site:docs official after:2024-01-01",
        "agent": [
            "Plan:\n1) Subtasks\n2) Tools\n3) Execute\n4) Verify\n5) Summarize",
            "Tools: web.search → parse → write.md / commit PR",
        ],
        "direct": "Answer concisely with 3 bullets and a short example.",
    }

