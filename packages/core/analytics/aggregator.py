
from __future__ import annotations
from typing import Literal, Any


def summarize(rows: list[Any], by: Literal["user", "feature", "model"]) -> list[tuple[str, int, int, int, float, int]]:
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = getattr(r, by)
        bucket = out.setdefault(key, {"requests": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "latencies": []})
        bucket["requests"] += 1
        bucket["tokens_in"] += getattr(r, "tokens_in")
        bucket["tokens_out"] += getattr(r, "tokens_out")
        bucket["cost_usd"] += getattr(r, "cost_usd")
        bucket["latencies"].append(getattr(r, "latency_ms") or 0)
    # p95 latency
    items: list[tuple[str, int, int, int, float, int]] = []
    for k, v in out.items():
        lat = sorted(v["latencies"])  # type: ignore[arg-type]
        p95 = lat[int(0.95 * len(lat)) - 1] if lat else 0
        items.append((k, v["requests"], v["tokens_in"], v["tokens_out"], round(v["cost_usd"], 2), p95))
    return items

