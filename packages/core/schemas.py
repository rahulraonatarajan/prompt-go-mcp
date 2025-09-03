from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal, List, Dict, Optional

Route = Literal["web", "agent", "ask", "direct"]


class Context(BaseModel):
    repoDetected: Optional[bool] = None
    filesTouched: Optional[List[str]] = None
    hasInternet: Optional[bool] = True
    org: Optional[str] = None
    user: Optional[str] = None
    featureTag: Optional[str] = None
    sourceApp: Optional[str] = None  # cursor, vscode, slack, etc.


class SuggestRequest(BaseModel):
    prompt: str
    context: Optional[Context] = None


class ScoreItem(BaseModel):
    route: Route
    score: float


class SuggestResponse(BaseModel):
    top_route: Route
    ranking: List[ScoreItem]
    reasons: List[str]
    suggestions: Dict[str, Any]


class OutcomeRequest(BaseModel):
    prompt: str
    selected_route: Route
    outcome: Literal["good", "neutral", "bad"]
    notes: Optional[str] = None
    org: Optional[str] = None
    user: Optional[str] = None


class UsageSummaryRequest(BaseModel):
    org: str
    since: str
    until: str
    by: Literal["user", "feature", "model"] = "user"


class UsageSummaryItem(BaseModel):
    key: str
    requests: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms_p95: float


class UsageSummaryResponse(BaseModel):
    items: List[UsageSummaryItem]


class OptimizeReportResponse(BaseModel):
    markdown: str


class Policy(BaseModel):
    weights: Dict[str, float] = Field(default_factory=lambda: {"web": 1, "agent": 1, "ask": 1, "direct": 1})
    freshness_domains: List[str] = Field(default_factory=list)
    budgets: Dict[str, float] = Field(default_factory=dict)  # month->usd_limit


class EstimateCostRequest(BaseModel):
    prompt: str
    candidate_models: List[str]


class EstimateCostItem(BaseModel):
    model: str
    est_tokens_in: int
    est_tokens_out: int
    est_cost_usd: float
    est_latency_ms: int


class EstimateCostResponse(BaseModel):
    items: List[EstimateCostItem]


class LogRequest(BaseModel):
    prompt: str
    route: Route
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    org: Optional[str] = None
    user: Optional[str] = None
    feature: Optional[str] = None
    source_app: Optional[str] = "cursor"
