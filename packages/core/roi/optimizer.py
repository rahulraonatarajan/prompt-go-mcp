from __future__ import annotations
from typing import List, Tuple


def downshift_savings(samples: List[Tuple[int, int, float]], cheaper_ratio: float = 0.2) -> float:
    """
    samples: list of (tok_in, tok_out, cost_usd) for candidate requests.
    cheaper_ratio: assumed fraction of requests safely downshiftable.
    returns estimated savings in USD.
    """
    if not samples:
        return 0.0
    subtotal = sum(c for _, _, c in samples)
    return subtotal * cheaper_ratio

