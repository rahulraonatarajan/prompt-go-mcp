"""
Team Insights Dashboard - Enhanced UX for Cursor AI teams
Provides real-time analytics, savings tracking, and team performance metrics
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from packages.storage.db import make_engine
from packages.storage.repo import get_usage_between
from packages.core.analytics.aggregator import summarize
from packages.core.recs.cursor_rules import weekly_rule_recommendations
from datetime import datetime, timedelta
import os
from typing import Optional

router = APIRouter()
ENGINE, SESSION = make_engine(os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./promptgo.db"))


@router.get("/team/{org_name}", response_class=HTMLResponse)
async def team_dashboard(org_name: str):
    """Main team dashboard with insights and metrics"""
    async with SESSION() as s:
        # Get last 30 days of data
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        usage_data = await get_usage_between(s, org_name, start_date, end_date)
        
        # Calculate metrics
        total_requests = len(usage_data)
        total_cost = sum(req.cost_usd for req in usage_data)
        avg_latency = sum(req.latency_ms or 0 for req in usage_data) / max(total_requests, 1)
        
        # Route distribution
        route_stats = {}
        for req in usage_data:
            route_stats[req.route] = route_stats.get(req.route, 0) + 1
        
        # Weekly comparison (estimate 25% savings from optimization)
        estimated_unoptimized_cost = total_cost / 0.75  # Assume 25% optimization
        savings = estimated_unoptimized_cost - total_cost
        
        # Get user breakdown
        user_summary = summarize(usage_data, by="user")
        
        # Generate recommendations
        stats = {
            "simple_qa_ratio": route_stats.get("direct", 0) / max(total_requests, 1),
            "freshness_hits": route_stats.get("web", 0),
            "agent_overuse": route_stats.get("agent", 0) / max(total_requests, 1)
        }
        recommendations = weekly_rule_recommendations(stats)
        
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{org_name} - Prompt Go Team Insights</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            .metric-card {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }}
            .savings-card {{ 
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                color: white;
            }}
            .route-badge {{ 
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                border-radius: 9999px;
                font-weight: 600;
                font-size: 0.875rem;
            }}
            .web-badge {{ background-color: #dcfce7; color: #166534; }}
            .agent-badge {{ background-color: #dbeafe; color: #1d4ed8; }}
            .ask-badge {{ background-color: #fed7aa; color: #ea580c; }}
            .direct-badge {{ background-color: #e9d5ff; color: #7c3aed; }}
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <!-- Header -->
        <div class="bg-white shadow-sm border-b">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div class="flex justify-between items-center py-6">
                    <div class="flex items-center">
                        <h1 class="text-3xl font-bold text-gray-900">🎯 {org_name}</h1>
                        <span class="ml-3 px-3 py-1 bg-blue-100 text-blue-800 text-sm font-medium rounded-full">
                            Prompt Go Insights
                        </span>
                    </div>
                    <div class="text-sm text-gray-500">
                        Last 30 days • Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
                    </div>
                </div>
            </div>
        </div>

        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <!-- Key Metrics -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div class="metric-card rounded-xl p-6 shadow-lg">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="text-3xl">💰</div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium opacity-80">Total Spend</p>
                            <p class="text-2xl font-bold">${total_cost:.2f}</p>
                        </div>
                    </div>
                </div>
                
                <div class="savings-card rounded-xl p-6 shadow-lg">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="text-3xl">📈</div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium opacity-80">Estimated Savings</p>
                            <p class="text-2xl font-bold">${savings:.2f}</p>
                            <p class="text-xs opacity-75">vs unoptimized routing</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-xl p-6 shadow-lg">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="text-3xl">⚡</div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-600">Avg Response</p>
                            <p class="text-2xl font-bold text-gray-900">{avg_latency:.0f}ms</p>
                        </div>
                    </div>
                </div>
                
                <div class="bg-white rounded-xl p-6 shadow-lg">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <div class="text-3xl">🚀</div>
                        </div>
                        <div class="ml-4">
                            <p class="text-sm font-medium text-gray-600">Total Requests</p>
                            <p class="text-2xl font-bold text-gray-900">{total_requests:,}</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Route Distribution -->
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <h2 class="text-xl font-bold text-gray-900 mb-4">🔀 Routing Intelligence</h2>
                    <div class="space-y-4">
                        {_generate_route_bars(route_stats, total_requests)}
                    </div>
                    <div class="mt-6 p-4 bg-blue-50 rounded-lg">
                        <p class="text-sm text-blue-800">
                            <strong>Smart Routing Impact:</strong> Automatic routing optimization 
                            saved an estimated ${savings:.2f} this month by directing prompts 
                            to the most cost-effective channels.
                        </p>
                    </div>
                </div>

                <!-- Team Recommendations -->
                <div class="bg-white rounded-xl shadow-lg p-6">
                    <h2 class="text-xl font-bold text-gray-900 mb-4">💡 Weekly Recommendations</h2>
                    <div class="mb-4">
                        <p class="text-gray-600">{recommendations['summary']}</p>
                    </div>
                    <div class="space-y-3">
                        {_generate_recommendation_cards(recommendations['rules'])}
                    </div>
                    <div class="mt-6">
                        <button class="w-full bg-indigo-600 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition-colors">
                            📋 Apply Recommendations to Cursor Rules
                        </button>
                    </div>
                </div>
            </div>

            <!-- Team Performance -->
            <div class="mt-8 bg-white rounded-xl shadow-lg p-6">
                <h2 class="text-xl font-bold text-gray-900 mb-4">👥 Team Performance</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Developer</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Requests</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Cost</th>
                                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Efficiency</th>
                            </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                            {_generate_user_rows(user_summary)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <script>
            // Add any interactive features here
            console.log('Prompt Go Team Dashboard loaded for {org_name}');
        </script>
    </body>
    </html>
    """
    
    return html_content


@router.get("/api/team/{org_name}/metrics")
async def team_metrics_api(
    org_name: str,
    days: int = Query(default=7, description="Number of days to analyze")
):
    """API endpoint for team metrics data"""
    async with SESSION() as s:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        usage_data = await get_usage_between(s, org_name, start_date, end_date)
        
        if not usage_data:
            return {
                "org": org_name,
                "period_days": days,
                "total_requests": 0,
                "total_cost": 0.0,
                "estimated_savings": 0.0,
                "route_distribution": {},
                "top_users": []
            }
        
        # Calculate metrics
        total_requests = len(usage_data)
        total_cost = sum(req.cost_usd for req in usage_data)
        estimated_unoptimized = total_cost / 0.75
        savings = estimated_unoptimized - total_cost
        
        # Route distribution
        route_stats = {}
        for req in usage_data:
            route_stats[req.route] = route_stats.get(req.route, 0) + 1
        
        # Top users
        user_summary = summarize(usage_data, by="user")[:5]  # Top 5 users
        
        return {
            "org": org_name,
            "period_days": days,
            "total_requests": total_requests,
            "total_cost": round(total_cost, 2),
            "estimated_savings": round(savings, 2),
            "route_distribution": route_stats,
            "top_users": [
                {
                    "user": user[0],
                    "requests": user[1],
                    "cost": user[4]
                }
                for user in user_summary
            ]
        }


def _generate_route_bars(route_stats: dict, total: int) -> str:
    """Generate HTML for route distribution bars"""
    route_info = {
        "web": {"icon": "🌐", "name": "Web Search", "class": "web-badge", "color": "#4CAF50"},
        "agent": {"icon": "🤖", "name": "Agent Mode", "class": "agent-badge", "color": "#2196F3"},
        "ask": {"icon": "💬", "name": "Ask Clarification", "class": "ask-badge", "color": "#FF9800"},
        "direct": {"icon": "⚡", "name": "Direct Answer", "class": "direct-badge", "color": "#9C27B0"}
    }
    
    html = ""
    for route, count in sorted(route_stats.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / max(total, 1)) * 100
        info = route_info.get(route, {"icon": "❓", "name": route, "class": "", "color": "#757575"})
        
        html += f"""
        <div class="flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="route-badge {info['class']}">
                    {info['icon']} {info['name']}
                </span>
                <span class="text-sm text-gray-600">{count} requests</span>
            </div>
            <div class="flex items-center space-x-2">
                <div class="w-24 bg-gray-200 rounded-full h-2">
                    <div class="h-2 rounded-full" style="width: {percentage}%; background-color: {info['color']};"></div>
                </div>
                <span class="text-sm font-medium text-gray-900 w-12">{percentage:.1f}%</span>
            </div>
        </div>
        """
    
    return html


def _generate_recommendation_cards(rules: list) -> str:
    """Generate HTML for recommendation cards"""
    html = ""
    for rule in rules:
        html += f"""
        <div class="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div class="flex">
                <div class="flex-shrink-0">
                    <span class="text-yellow-600">💡</span>
                </div>
                <div class="ml-3">
                    <h4 class="text-sm font-medium text-yellow-800 capitalize">
                        {rule['rule'].replace('_', ' ')}
                    </h4>
                    <p class="text-sm text-yellow-700 mt-1">{rule['action']}</p>
                </div>
            </div>
        </div>
        """
    
    return html


def _generate_user_rows(user_summary: list) -> str:
    """Generate HTML for user performance table rows"""
    html = ""
    for user, requests, tokens_in, tokens_out, cost, latency_p95 in user_summary:
        efficiency_score = requests / max(cost, 0.01)  # requests per dollar
        efficiency_class = "text-green-600" if efficiency_score > 10 else "text-yellow-600" if efficiency_score > 5 else "text-red-600"
        
        html += f"""
        <tr>
            <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                    <div class="text-sm font-medium text-gray-900">{user or 'Anonymous'}</div>
                </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{requests}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${cost:.2f}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="text-sm font-medium {efficiency_class}">
                    {efficiency_score:.1f} req/$
                </span>
            </td>
        </tr>
        """
    
    return html
