"""
Adaptive Learning System for Team Routing Patterns
Learns from team feedback and usage patterns to improve routing decisions over time
"""
from __future__ import annotations
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from packages.core.routing.router import score as base_score
from packages.storage.models import Request
from packages.storage.repo import get_usage_between
from packages.storage.db import make_engine
import asyncio


class AdaptiveRouter:
    """
    Learns from team patterns to improve routing decisions
    """
    
    def __init__(self, org: str):
        self.org = org
        self.learning_data_path = Path(f"data/learning/{org.lower().replace(' ', '_')}_patterns.json")
        self.learning_data_path.parent.mkdir(parents=True, exist_ok=True)
        self.patterns = self._load_patterns()
        self.ENGINE, self.SESSION = make_engine(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db"))
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load learned patterns from disk"""
        if self.learning_data_path.exists():
            try:
                with open(self.learning_data_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {
            "route_weights": {"web": 1.0, "agent": 1.0, "ask": 1.0, "direct": 1.0},
            "keyword_preferences": {},
            "user_preferences": {},
            "successful_patterns": [],
            "failed_patterns": [],
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _save_patterns(self):
        """Save learned patterns to disk"""
        self.patterns["last_updated"] = datetime.utcnow().isoformat()
        with open(self.learning_data_path, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    async def learn_from_usage(self, days_back: int = 7):
        """
        Analyze recent usage patterns to improve routing
        """
        async with self.SESSION() as s:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days_back)
            usage_data = await get_usage_between(s, self.org, start_date, end_date)
        
        if not usage_data:
            return
        
        # Analyze route success patterns
        route_performance = {}
        keyword_route_mapping = {}
        user_preferences = {}
        
        for req in usage_data:
            route = req.route
            
            # Track route performance (lower latency and cost = better)
            if route not in route_performance:
                route_performance[route] = {"total_cost": 0, "total_latency": 0, "count": 0}
            
            route_performance[route]["total_cost"] += req.cost_usd
            route_performance[route]["total_latency"] += req.latency_ms or 0
            route_performance[route]["count"] += 1
            
            # Learn user preferences
            if req.user:
                if req.user not in user_preferences:
                    user_preferences[req.user] = {}
                if route not in user_preferences[req.user]:
                    user_preferences[req.user][route] = 0
                user_preferences[req.user][route] += 1
        
        # Update route weights based on performance
        self._update_route_weights(route_performance)
        
        # Update user preferences
        self.patterns["user_preferences"] = user_preferences
        
        self._save_patterns()
    
    def _update_route_weights(self, performance: Dict[str, Dict[str, float]]):
        """Update routing weights based on performance metrics"""
        base_weights = {"web": 1.0, "agent": 1.0, "ask": 1.0, "direct": 1.0}
        
        # Calculate efficiency scores (requests per dollar)
        efficiency_scores = {}
        for route, perf in performance.items():
            if perf["count"] > 0 and perf["total_cost"] > 0:
                efficiency = perf["count"] / perf["total_cost"]
                efficiency_scores[route] = efficiency
        
        if efficiency_scores:
            # Normalize efficiency scores to weight adjustments
            max_efficiency = max(efficiency_scores.values())
            for route in base_weights:
                if route in efficiency_scores:
                    # More efficient routes get higher weights (up to 1.5x)
                    weight_multiplier = 1.0 + (efficiency_scores[route] / max_efficiency) * 0.5
                    base_weights[route] = weight_multiplier
        
        self.patterns["route_weights"] = base_weights
    
    def get_adaptive_weights(self, user: Optional[str] = None) -> Dict[str, float]:
        """Get routing weights adapted for the team and optionally specific user"""
        weights = self.patterns["route_weights"].copy()
        
        # Apply user-specific preferences if available
        if user and user in self.patterns["user_preferences"]:
            user_prefs = self.patterns["user_preferences"][user]
            total_user_requests = sum(user_prefs.values())
            
            if total_user_requests > 10:  # Only apply if user has enough data
                for route, count in user_prefs.items():
                    preference_strength = count / total_user_requests
                    if preference_strength > 0.4:  # Strong preference (>40% of requests)
                        weights[route] *= 1.2  # Boost preferred routes
        
        return weights
    
    async def record_feedback(self, prompt: str, suggested_route: str, 
                            actual_route: str, outcome: str, user: Optional[str] = None):
        """
        Record user feedback to improve future suggestions
        """
        feedback_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "prompt_hash": hash(prompt) % 1000000,  # Simple hash for privacy
            "suggested_route": suggested_route,
            "actual_route": actual_route,
            "outcome": outcome,  # "good", "neutral", "bad"
            "user": user
        }
        
        if outcome == "good" and suggested_route == actual_route:
            self.patterns["successful_patterns"].append(feedback_entry)
        elif outcome == "bad":
            self.patterns["failed_patterns"].append(feedback_entry)
        
        # Keep only recent patterns (last 1000 entries)
        self.patterns["successful_patterns"] = self.patterns["successful_patterns"][-1000:]
        self.patterns["failed_patterns"] = self.patterns["failed_patterns"][-1000:]
        
        self._save_patterns()
    
    def suggest_with_learning(self, prompt: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Enhanced routing suggestion using learned patterns
        """
        # Get adaptive weights
        weights = self.get_adaptive_weights(user)
        
        # Use base scoring with adaptive weights
        scores = base_score(prompt, weights)
        
        # Apply learned keyword preferences
        scores = self._apply_keyword_learning(prompt, scores)
        
        # Sort by score
        ranked_routes = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "top_route": ranked_routes[0][0],
            "scores": scores,
            "learning_applied": True,
            "confidence": ranked_routes[0][1],
            "user_personalized": user is not None and user in self.patterns["user_preferences"]
        }
    
    def _apply_keyword_learning(self, prompt: str, scores: Dict[str, float]) -> Dict[str, float]:
        """Apply learned keyword-to-route associations"""
        prompt_lower = prompt.lower()
        
        # Check for learned successful patterns
        for pattern in self.patterns["successful_patterns"][-100:]:  # Recent patterns only
            # Simple keyword matching (could be enhanced with NLP)
            if pattern["suggested_route"] == pattern["actual_route"]:
                # This is a simplified approach - in production, you'd use more sophisticated matching
                route = pattern["suggested_route"]
                scores[route] *= 1.1  # Small boost for patterns that worked
        
        return scores
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get statistics about the learning system"""
        return {
            "org": self.org,
            "patterns_learned": len(self.patterns["successful_patterns"]),
            "failed_patterns": len(self.patterns["failed_patterns"]),
            "users_with_preferences": len(self.patterns["user_preferences"]),
            "route_weights": self.patterns["route_weights"],
            "last_updated": self.patterns["last_updated"]
        }


class TeamLearningManager:
    """
    Manages adaptive learning across multiple teams
    """
    
    def __init__(self):
        self.routers: Dict[str, AdaptiveRouter] = {}
    
    def get_router(self, org: str) -> AdaptiveRouter:
        """Get or create adaptive router for an organization"""
        if org not in self.routers:
            self.routers[org] = AdaptiveRouter(org)
        return self.routers[org]
    
    async def update_all_teams(self):
        """Update learning for all teams"""
        for router in self.routers.values():
            await router.learn_from_usage()
    
    async def get_cross_team_insights(self) -> Dict[str, Any]:
        """Get insights across all teams for benchmarking"""
        insights = {
            "total_teams": len(self.routers),
            "team_stats": {}
        }
        
        for org, router in self.routers.items():
            insights["team_stats"][org] = router.get_learning_stats()
        
        return insights


# Global learning manager instance
learning_manager = TeamLearningManager()


async def get_adaptive_suggestion(org: str, prompt: str, user: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to get adaptive routing suggestion
    """
    router = learning_manager.get_router(org)
    return router.suggest_with_learning(prompt, user)


async def record_team_feedback(org: str, prompt: str, suggested_route: str, 
                             actual_route: str, outcome: str, user: Optional[str] = None):
    """
    Convenience function to record feedback for learning
    """
    router = learning_manager.get_router(org)
    await router.record_feedback(prompt, suggested_route, actual_route, outcome, user)


# Scheduled learning update (would be called by a background task)
async def scheduled_learning_update():
    """Background task to update learning for all teams"""
    await learning_manager.update_all_teams()
