from __future__ import annotations
from typing import Any
from packages.core.schemas import (
    SuggestRequest,
    SuggestResponse,
    ScoreItem,
    UsageSummaryRequest,
    LogRequest,
    Context,
)
from packages.core.routing.router import score, explain, suggestion_pack
from packages.core.roi.cost_models import load_costs, estimate
from packages.core.analytics.aggregator import summarize
from packages.core.analytics.reports import roi_markdown
from packages.core.recs.cursor_rules import weekly_rule_recommendations
from packages.storage.models import Request
from packages.storage.repo import insert_request, get_usage_between
from packages.storage.db import make_engine, ensure_schema as _ensure_schema
from packages.core.utils.hashing import sha256_hex
from datetime import datetime, timedelta
import os


COSTS = load_costs(os.getenv("PG_COSTS", "config/cost_models.yaml"))
ENGINE, SESSION = make_engine(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db"))
_SCHEMA_READY = False


async def _ensure_db() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        await _ensure_schema(ENGINE)
        _SCHEMA_READY = True


async def t_suggest_route(body: SuggestRequest) -> SuggestResponse:
    weights = {"web": 1, "agent": 1, "ask": 1, "direct": 1}
    scores = score(body.prompt, weights)
    ranking = [
        ScoreItem(route=k, score=round(v, 4)) for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
    top = ranking[0].route
    return SuggestResponse(
        top_route=top, ranking=ranking, reasons=explain(body.prompt), suggestions=suggestion_pack(body.prompt)
    )


async def t_log_and_estimate(
    body: SuggestRequest,
    route: str,
    model: str,
    user: str,
    org: str,
    feature: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: int = 0,
) -> dict[str, Any]:
    await _ensure_db()
    async with SESSION() as s:
        cost = estimate(tokens_in, tokens_out, model, COSTS)
        row = Request(
            org=org,
            user=user,
            feature=feature,
            source_app=body.context.sourceApp if body.context else "cursor",
            prompt_hash=sha256_hex(body.prompt),
            route=route,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency_ms,
        )
        await insert_request(s, row)
        return {"ok": True, "cost_usd": cost}


async def t_usage_summary(body: UsageSummaryRequest) -> dict[str, Any]:
    await _ensure_db()
    async with SESSION() as s:
        rows = await get_usage_between(
            s, body.org, datetime.fromisoformat(body.since), datetime.fromisoformat(body.until)
        )
        items = summarize(rows, by=body.by)
        return {
            "items": [
                {
                    "key": k,
                    "requests": r,
                    "tokens_in": ti,
                    "tokens_out": to,
                    "cost_usd": c,
                    "latency_ms_p95": p95,
                }
                for k, r, ti, to, c, p95 in items
            ]
        }


async def t_optimize_report(org: str) -> dict[str, str]:
    # naive synthetic estimation; can be replaced with actual analysis
    await _ensure_db()
    async with SESSION() as s:
        rows = await get_usage_between(s, org, datetime.utcnow() - timedelta(days=7), datetime.utcnow())
        samples = [(r.tokens_in, r.tokens_out, r.cost_usd) for r in rows]
    est = sum(x[2] for x in samples) * 0.25
    md = roi_markdown(
        est,
        [
            "Downshift short Q&A to cheaper/local models",
            "Prefer web for freshness keywords",
            "Set agent threshold requiring action verbs",
        ],
    )
    return {"markdown": md}


async def t_weekly_cursor_rules(org: str) -> dict[str, Any]:
    # stub stats; later compute from DB
    stats = {"simple_qa_ratio": 0.35, "freshness_hits": 72, "agent_overuse": 0.24}
    return weekly_rule_recommendations(stats)


async def t_log_request(body: LogRequest) -> dict[str, Any]:
    """Persist a single request's usage/cost/latency into storage.
    Returns computed cost so the client can display/aggregate locally.
    """
    # Build a minimal SuggestRequest for logging context/source_app
    ctx = Context(sourceApp=body.source_app)
    sr = SuggestRequest(prompt=body.prompt, context=ctx)
    org = body.org or "unknown"
    user = body.user or "unknown"
    feature = body.feature or "default"
    return await t_log_and_estimate(
        sr,
        route=body.route,
        model=body.model,
        user=user,
        org=org,
        feature=feature,
        tokens_in=body.tokens_in,
        tokens_out=body.tokens_out,
        latency_ms=body.latency_ms,
    )
