from __future__ import annotations
from pydantic import BaseModel
from typing import Dict, List


class OrgPolicy(BaseModel):
    org: str
    weights: Dict[str, float] = {"web": 1, "agent": 1, "ask": 1, "direct": 1}
    freshness_domains: List[str] = []
    budget_mode: str = "observe"  # observe | soft | hard

