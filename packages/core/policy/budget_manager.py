"""
Proactive Budget Management with Smart Suggestions
Monitors spending, provides alerts, and suggests cost optimizations for Cursor teams
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
import yaml
from pathlib import Path
from packages.storage.repo import get_usage_between
from packages.storage.db import make_engine
from packages.core.roi.cost_models import load_costs


class BudgetAlert(BaseModel):
    level: str  # "info", "warning", "critical"
    message: str
    suggestion: Optional[str] = None
    action_required: bool = False


class BudgetStatus(BaseModel):
    org: str
    period: str  # "monthly", "weekly", "daily"
    current_spend: float
    budget_limit: float
    percentage_used: float
    days_remaining: int
    projected_spend: float
    alerts: List[BudgetAlert]
    suggestions: List[str]


class SmartBudgetManager:
    """
    Intelligent budget management with proactive suggestions
    """
    
    def __init__(self):
        self.costs = load_costs(os.getenv("PG_COSTS", "config/cost_models.yaml"))
        self.ENGINE, self.SESSION = make_engine(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db"))
    
    async def get_budget_status(self, org: str) -> BudgetStatus:
        """Get comprehensive budget status for a team"""
        # Load team budget configuration
        budget_config = self._load_team_budget_config(org)
        
        # Get current month's spending
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async with self.SESSION() as s:
            usage_data = await get_usage_between(s, org, month_start, now)
        
        current_spend = sum(req.cost_usd for req in usage_data)
        monthly_budget = budget_config.get("monthly_limit_usd", 500)
        
        # Calculate projections
        days_elapsed = (now - month_start).days + 1
        days_in_month = self._get_days_in_month(now)
        days_remaining = days_in_month - days_elapsed
        
        if days_elapsed > 0:
            daily_avg = current_spend / days_elapsed
            projected_spend = daily_avg * days_in_month
        else:
            projected_spend = current_spend
        
        percentage_used = (current_spend / monthly_budget) * 100
        
        # Generate alerts and suggestions
        alerts = self._generate_budget_alerts(current_spend, monthly_budget, projected_spend, percentage_used)
        suggestions = await self._generate_smart_suggestions(org, usage_data, budget_config)
        
        return BudgetStatus(
            org=org,
            period="monthly",
            current_spend=round(current_spend, 2),
            budget_limit=monthly_budget,
            percentage_used=round(percentage_used, 1),
            days_remaining=days_remaining,
            projected_spend=round(projected_spend, 2),
            alerts=alerts,
            suggestions=suggestions
        )
    
    def _load_team_budget_config(self, org: str) -> Dict[str, Any]:
        """Load team-specific budget configuration"""
        config_file = Path(f"config/{org.lower().replace(' ', '_')}_policy.yaml")
        default_config = {
            "monthly_limit_usd": 500,
            "alert_threshold": 0.8,
            "mode": "soft",
            "budget_fallbacks": {
                "gpt-4": "gpt-3.5-turbo",
                "claude-3-opus": "claude-3-haiku"
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    return config.get("budget", default_config)
            except Exception:
                pass
        
        return default_config
    
    def _get_days_in_month(self, date: datetime) -> int:
        """Get number of days in the current month"""
        if date.month == 12:
            next_month = date.replace(year=date.year + 1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month + 1, day=1)
        
        return (next_month - date.replace(day=1)).days
    
    def _generate_budget_alerts(self, current: float, budget: float, 
                              projected: float, percentage: float) -> List[BudgetAlert]:
        """Generate budget alerts based on current status"""
        alerts = []
        
        if percentage >= 100:
            alerts.append(BudgetAlert(
                level="critical",
                message=f"Budget exceeded! Current spend: ${current:.2f} / ${budget:.2f}",
                suggestion="Consider enabling hard budget limits or upgrading your plan",
                action_required=True
            ))
        elif percentage >= 90:
            alerts.append(BudgetAlert(
                level="critical",
                message=f"Budget nearly exhausted: {percentage:.1f}% used",
                suggestion="Enable cost-saving measures immediately",
                action_required=True
            ))
        elif percentage >= 80:
            alerts.append(BudgetAlert(
                level="warning",
                message=f"Budget alert: {percentage:.1f}% of monthly limit used",
                suggestion="Consider reviewing routing patterns to optimize costs"
            ))
        elif projected > budget * 1.1:  # Projected to exceed by 10%
            alerts.append(BudgetAlert(
                level="warning",
                message=f"Projected to exceed budget: ${projected:.2f} estimated for month",
                suggestion="Current usage patterns may lead to budget overrun"
            ))
        
        if percentage < 50 and datetime.utcnow().day > 15:
            alerts.append(BudgetAlert(
                level="info",
                message="Budget usage is lower than expected - good cost management!",
                suggestion="Consider investing saved budget in advanced features"
            ))
        
        return alerts
    
    async def _generate_smart_suggestions(self, org: str, usage_data: List, 
                                        budget_config: Dict[str, Any]) -> List[str]:
        """Generate smart cost optimization suggestions"""
        suggestions = []
        
        if not usage_data:
            return ["Start using Prompt Go to get personalized cost optimization suggestions"]
        
        # Analyze route distribution
        route_costs = {}
        route_counts = {}
        model_costs = {}
        
        for req in usage_data:
            route = req.route
            model = req.model
            
            route_costs[route] = route_costs.get(route, 0) + req.cost_usd
            route_counts[route] = route_counts.get(route, 0) + 1
            model_costs[model] = model_costs.get(model, 0) + req.cost_usd
        
        total_cost = sum(route_costs.values())
        total_requests = sum(route_counts.values())
        
        # Route-based suggestions
        if route_costs.get("agent", 0) / total_cost > 0.5:
            suggestions.append(
                "🤖 Agent mode accounts for >50% of costs. Try breaking complex tasks into smaller prompts."
            )
        
        if route_costs.get("direct", 0) / total_cost > 0.4 and route_counts.get("direct", 0) > 20:
            suggestions.append(
                "⚡ Consider using smaller/local models for simple direct questions to reduce costs by ~60%."
            )
        
        if route_counts.get("web", 0) < total_requests * 0.1:
            suggestions.append(
                "🌐 Web search is underused. Route fresh info queries to web to avoid expensive LLM calls."
            )
        
        # Model-based suggestions
        expensive_models = ["gpt-4", "claude-3-opus", "gpt-4-turbo"]
        expensive_cost = sum(cost for model, cost in model_costs.items() if model in expensive_models)
        
        if expensive_cost / total_cost > 0.7:
            fallbacks = budget_config.get("budget_fallbacks", {})
            if fallbacks:
                suggestions.append(
                    f"💰 Premium models account for {expensive_cost/total_cost:.1%} of costs. "
                    f"Enable automatic fallbacks to save ~40% on routine tasks."
                )
        
        # Usage pattern suggestions
        if total_requests > 100:
            avg_cost_per_request = total_cost / total_requests
            if avg_cost_per_request > 0.05:  # High cost per request
                suggestions.append(
                    f"📊 Average cost per request (${avg_cost_per_request:.3f}) is high. "
                    f"Consider more specific prompts and better routing."
                )
        
        # Time-based suggestions
        now = datetime.utcnow()
        if now.day > 20 and total_cost > budget_config.get("monthly_limit_usd", 500) * 0.8:
            suggestions.append(
                "⏰ High usage in late month detected. Consider batching non-urgent requests for next month."
            )
        
        return suggestions
    
    async def apply_budget_enforcement(self, org: str, route: str, model: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Apply budget enforcement policies and return modified route/model
        Returns: (new_route, new_model, enforcement_info)
        """
        budget_status = await self.get_budget_status(org)
        budget_config = self._load_team_budget_config(org)
        enforcement_mode = budget_config.get("mode", "observe")
        
        enforcement_info = {
            "enforced": False,
            "original_route": route,
            "original_model": model,
            "reason": None
        }
        
        # No enforcement in observe mode
        if enforcement_mode == "observe":
            return route, model, enforcement_info
        
        # Check if budget enforcement should kick in
        should_enforce = (
            budget_status.percentage_used > 90 or  # Over 90% of budget
            budget_status.projected_spend > budget_status.budget_limit * 1.2  # Projected 20% overage
        )
        
        if not should_enforce:
            return route, model, enforcement_info
        
        # Apply soft enforcement (downgrades)
        if enforcement_mode == "soft":
            fallbacks = budget_config.get("budget_fallbacks", {})
            
            # Model downgrade
            if model in fallbacks:
                new_model = fallbacks[model]
                enforcement_info.update({
                    "enforced": True,
                    "reason": f"Budget enforcement: downgraded {model} → {new_model}",
                    "savings_estimated": "~40%"
                })
                model = new_model
            
            # Route optimization for high-cost scenarios
            if route == "agent" and budget_status.percentage_used > 95:
                route = "ask"  # Force clarification instead of expensive agent mode
                enforcement_info.update({
                    "enforced": True,
                    "reason": "Budget critical: routing to 'ask' for clarification instead of agent mode",
                    "savings_estimated": "~70%"
                })
        
        # Hard enforcement (blocking)
        elif enforcement_mode == "hard" and budget_status.percentage_used >= 100:
            # Block expensive operations
            expensive_routes = ["agent"]
            expensive_models = ["gpt-4", "claude-3-opus", "gpt-4-turbo"]
            
            if route in expensive_routes or model in expensive_models:
                route = "ask"
                model = "gpt-3.5-turbo"  # Fallback to cheapest option
                enforcement_info.update({
                    "enforced": True,
                    "reason": "Hard budget limit reached: forcing cost-effective alternatives",
                    "savings_estimated": "~80%"
                })
        
        return route, model, enforcement_info
    
    async def get_cost_optimization_report(self, org: str) -> Dict[str, Any]:
        """Generate comprehensive cost optimization report"""
        budget_status = await self.get_budget_status(org)
        
        # Get detailed usage breakdown
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        async with self.SESSION() as s:
            usage_data = await get_usage_between(s, org, month_start, now)
        
        # Calculate potential savings
        savings_opportunities = await self._calculate_savings_opportunities(usage_data)
        
        report = {
            "org": org,
            "period": "current_month",
            "budget_status": budget_status.dict(),
            "savings_opportunities": savings_opportunities,
            "recommendations": {
                "immediate": [],
                "medium_term": [],
                "long_term": []
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
        # Generate tiered recommendations
        if budget_status.percentage_used > 80:
            report["recommendations"]["immediate"].extend([
                "Enable soft budget enforcement to automatically downgrade models",
                "Review and optimize agent-mode prompts for efficiency",
                "Batch non-urgent requests to spread costs"
            ])
        
        report["recommendations"]["medium_term"].extend([
            "Set up team routing preferences based on usage patterns",
            "Implement prompt templates for common use cases",
            "Enable adaptive learning to improve routing efficiency"
        ])
        
        report["recommendations"]["long_term"].extend([
            "Consider local/on-premise models for routine tasks",
            "Establish team guidelines for cost-effective prompting",
            "Regular budget reviews and optimization sessions"
        ])
        
        return report
    
    async def _calculate_savings_opportunities(self, usage_data: List) -> Dict[str, Any]:
        """Calculate potential cost savings from optimization"""
        if not usage_data:
            return {"total_potential_savings": 0, "opportunities": []}
        
        opportunities = []
        total_current_cost = sum(req.cost_usd for req in usage_data)
        
        # Model downgrade savings
        expensive_model_cost = sum(
            req.cost_usd for req in usage_data 
            if req.model in ["gpt-4", "claude-3-opus", "gpt-4-turbo"]
        )
        if expensive_model_cost > 0:
            potential_savings = expensive_model_cost * 0.6  # 60% savings from downgrades
            opportunities.append({
                "category": "Model Optimization",
                "description": "Downgrade premium models for routine tasks",
                "current_cost": expensive_model_cost,
                "potential_savings": potential_savings,
                "impact": "High"
            })
        
        # Route optimization savings
        agent_cost = sum(req.cost_usd for req in usage_data if req.route == "agent")
        if agent_cost > total_current_cost * 0.4:  # Agent mode >40% of costs
            potential_savings = agent_cost * 0.3  # 30% savings from better routing
            opportunities.append({
                "category": "Route Optimization", 
                "description": "Optimize agent-mode usage with better prompt structuring",
                "current_cost": agent_cost,
                "potential_savings": potential_savings,
                "impact": "Medium"
            })
        
        total_potential_savings = sum(opp["potential_savings"] for opp in opportunities)
        
        return {
            "total_potential_savings": round(total_potential_savings, 2),
            "opportunities": opportunities,
            "optimization_percentage": round((total_potential_savings / total_current_cost) * 100, 1) if total_current_cost > 0 else 0
        }


# Global budget manager instance
budget_manager = SmartBudgetManager()


async def get_team_budget_status(org: str) -> BudgetStatus:
    """Convenience function to get budget status"""
    return await budget_manager.get_budget_status(org)


async def enforce_budget_policy(org: str, route: str, model: str) -> Tuple[str, str, Dict[str, Any]]:
    """Convenience function to apply budget enforcement"""
    return await budget_manager.apply_budget_enforcement(org, route, model)
