from __future__ import annotations
import yaml
from pathlib import Path

DEFAULT: dict[str, dict[str, float]] = {
    "openai/gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "openai/gpt-4o": {"in": 2.50, "out": 10.00},
    "openai/gpt-3.5-turbo": {"in": 0.50, "out": 1.50},
    "anthropic/claude-3-haiku": {"in": 0.25, "out": 1.25},
    "local/tiny-llama": {"in": 0.00, "out": 0.00},
}


def load_costs(path: str | None) -> dict[str, dict[str, float]]:
    if path and Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            return loaded or DEFAULT
    return DEFAULT


def estimate(tokens_in: int, tokens_out: int, model: str, costs: dict[str, dict[str, float]]) -> float:
    c = costs.get(model) or {"in": 0.0, "out": 0.0}
    return (tokens_in / 1000) * c["in"] + (tokens_out / 1000) * c["out"]

