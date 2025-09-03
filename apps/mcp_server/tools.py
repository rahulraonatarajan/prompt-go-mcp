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
from packages.core.learning.adaptive_router import get_adaptive_suggestion, record_team_feedback
from packages.core.policy.budget_manager import get_team_budget_status, enforce_budget_policy
from datetime import datetime, timedelta
import os
import yaml
from pathlib import Path


COSTS = load_costs(os.getenv("PG_COSTS", "config/cost_models.yaml"))
ENGINE, SESSION = make_engine(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db"))
_SCHEMA_READY = False
_TEAM_WEIGHTS_CACHE = {}


async def _ensure_db() -> None:
    global _SCHEMA_READY
    if not _SCHEMA_READY:
        await _ensure_schema(ENGINE)
        _SCHEMA_READY = True


async def t_suggest_route(body: SuggestRequest) -> SuggestResponse:
    # Load team-specific routing weights if available
    org = body.context.org if body.context else "default"
    user = body.context.user if body.context else None
    
    # Use adaptive learning if enabled
    if os.getenv("PG_ENABLE_LEARNING", "false").lower() == "true":
        adaptive_result = await get_adaptive_suggestion(org, body.prompt, user)
        scores = adaptive_result["scores"]
        top = adaptive_result["top_route"]
    else:
        weights = await _load_team_weights(org)
        scores = score(body.prompt, weights)
        top = max(scores.items(), key=lambda x: x[1])[0]
    
    ranking = [
        ScoreItem(route=k, score=round(v, 4)) for k, v in sorted(scores.items(), key=lambda x: x[1], reverse=True)
    ]
    
    # Add UX enhancements for Cursor teams
    ux_hints = _generate_cursor_ux_hints(body.prompt, top, scores)
    suggestions = suggestion_pack(body.prompt)
    
    # Add team-specific suggestions
    suggestions["team_context"] = await _get_team_context(org, top)
    
    # Add learning indicators
    if os.getenv("PG_ENABLE_LEARNING", "false").lower() == "true":
        ux_hints["learning_enabled"] = True
        ux_hints["personalized"] = user is not None
    
    return SuggestResponse(
        top_route=top, 
        ranking=ranking, 
        reasons=explain(body.prompt), 
        suggestions=suggestions,
        ux_hints=ux_hints  # New field for Cursor UI integration
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


async def _load_team_weights(org: str) -> dict[str, float]:
    """Load team-specific routing weights from config"""
    if org in _TEAM_WEIGHTS_CACHE:
        return _TEAM_WEIGHTS_CACHE[org]
    
    # Default weights
    weights = {"web": 1.0, "agent": 1.0, "ask": 1.0, "direct": 1.0}
    
    # Try to load team-specific config
    config_file = Path(f"config/{org.lower().replace(' ', '_')}_policy.yaml")
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
                if 'routing_weights' in config:
                    weights.update(config['routing_weights'])
        except Exception:
            pass  # Use defaults if config is invalid
    
    _TEAM_WEIGHTS_CACHE[org] = weights
    return weights


def _generate_cursor_ux_hints(prompt: str, top_route: str, scores: dict[str, float]) -> dict[str, Any]:
    """Generate UX hints for Cursor interface integration"""
    hints = {
        "primary_indicator": {
            "route": top_route,
            "confidence": max(scores.values()),
            "icon": _get_route_icon(top_route),
            "color": _get_route_color(top_route),
            "tooltip": _get_route_tooltip(top_route)
        },
        "alternatives": []
    }
    
    # Add alternative routes if they're close in score
    top_score = max(scores.values())
    for route, score in scores.items():
        if route != top_route and score > top_score * 0.7:  # Within 30% of top score
            hints["alternatives"].append({
                "route": route,
                "score": score,
                "icon": _get_route_icon(route),
                "suggestion": f"Consider {route} mode for this type of request"
            })
    
    return hints


def _get_route_icon(route: str) -> str:
    """Get emoji icon for route type"""
    icons = {
        "web": "🌐",
        "agent": "🤖", 
        "ask": "💬",
        "direct": "⚡"
    }
    return icons.get(route, "❓")


def _get_route_color(route: str) -> str:
    """Get color code for route type"""
    colors = {
        "web": "#4CAF50",      # Green - fresh info
        "agent": "#2196F3",    # Blue - complex tasks
        "ask": "#FF9800",      # Orange - needs clarification
        "direct": "#9C27B0"    # Purple - quick answers
    }
    return colors.get(route, "#757575")


def _get_route_tooltip(route: str) -> str:
    """Get tooltip text for route type"""
    tooltips = {
        "web": "Best for fresh information and current data",
        "agent": "Best for complex, multi-step tasks",
        "ask": "Prompt needs clarification for better results", 
        "direct": "Quick, straightforward answer"
    }
    return tooltips.get(route, "Recommended routing option")


async def _get_team_context(org: str, route: str) -> dict[str, Any]:
    """Get team-specific context and suggestions"""
    # Check recent team usage patterns
    await _ensure_db()
    async with SESSION() as s:
        recent_usage = await get_usage_between(
            s, org, datetime.utcnow() - timedelta(days=7), datetime.utcnow()
        )
    
    # Calculate team patterns
    route_usage = {}
    total_cost = 0.0
    for req in recent_usage:
        route_usage[req.route] = route_usage.get(req.route, 0) + 1
        total_cost += req.cost_usd
    
    context = {
        "weekly_spend": round(total_cost, 2),
        "popular_routes": sorted(route_usage.items(), key=lambda x: x[1], reverse=True)[:3],
        "suggestion": _get_team_suggestion(org, route, route_usage, total_cost)
    }
    
    return context


def _get_team_suggestion(org: str, route: str, route_usage: dict, total_cost: float) -> str:
    """Generate team-specific suggestions based on usage patterns"""
    if total_cost > 100:  # High spend team
        if route == "agent" and route_usage.get("agent", 0) > 20:
            return "💡 Your team uses agent mode frequently. Consider breaking complex prompts into smaller steps to optimize costs."
        elif route == "web":
            return "🌐 Web search is cost-effective for your high-usage team. Good choice!"
    
    if route == "ask":
        return "💬 Taking time to clarify prompts upfront saves time and costs later."
    
    return f"✨ {route.title()} mode is a good fit for this request."


async def t_budget_status(org: str) -> dict[str, Any]:
    """Get comprehensive budget status for a team"""
    if not org:
        return {"error": "Organization name is required"}
    
    try:
        budget_status = await get_team_budget_status(org)
        return budget_status.dict()
    except Exception as e:
        return {"error": f"Failed to get budget status: {str(e)}"}
