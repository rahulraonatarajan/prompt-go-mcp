"""
MCP server over stdio. Exposes MCP-ish endpoints (initialize, tools/list, tools/call)
and also supports convenience methods used by tests (suggestRoute, getUsageSummary, etc.).
"""
from __future__ import annotations
import sys, json, asyncio
from typing import Any, Dict
from packages.core.schemas import SuggestRequest, UsageSummaryRequest, LogRequest
from .tools import t_suggest_route, t_usage_summary, t_optimize_report, t_weekly_cursor_rules, t_log_request


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": "suggestRoute",
            "description": "Suggest a routing channel for a prompt with reasons and suggestions.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "context": {
                        "type": "object",
                        "properties": {
                            "repoDetected": {"type": ["boolean", "null"]},
                            "filesTouched": {"type": ["array", "null"], "items": {"type": "string"}},
                            "hasInternet": {"type": ["boolean", "null"]},
                            "org": {"type": ["string", "null"]},
                            "user": {"type": ["string", "null"]},
                            "featureTag": {"type": ["string", "null"]},
                            "sourceApp": {"type": ["string", "null"]},
                        },
                    },
                },
                "required": ["prompt"],
            },
            "outputSchema": {"type": "object"},
        },
        {
            "name": "getUsageSummary",
            "description": "Summarize usage and costs for an org between two ISO timestamps.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "org": {"type": "string"},
                    "since": {"type": "string"},
                    "until": {"type": "string"},
                    "by": {"type": "string", "enum": ["user", "feature", "model"]},
                },
                "required": ["org", "since", "until"],
            },
            "outputSchema": {"type": "object"},
        },
        {
            "name": "optimizeReport",
            "description": "Generate an ROI markdown report for the last 7 days.",
            "inputSchema": {"type": "object", "properties": {"org": {"type": "string"}}, "required": ["org"]},
            "outputSchema": {"type": "object"},
        },
        {
            "name": "weeklyCursorRuleRecommendations",
            "description": "Suggest concise weekly Cursor rule recommendations.",
            "inputSchema": {"type": "object", "properties": {"org": {"type": "string"}}, "required": ["org"]},
            "outputSchema": {"type": "object"},
        },
        {
            "name": "logRequest",
            "description": "Persist a usage sample (tokens, latency, model) and return computed cost.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "route": {"type": "string", "enum": ["web", "agent", "ask", "direct"]},
                    "model": {"type": "string"},
                    "tokens_in": {"type": "integer"},
                    "tokens_out": {"type": "integer"},
                    "latency_ms": {"type": "integer"},
                    "org": {"type": ["string", "null"]},
                    "user": {"type": ["string", "null"]},
                    "feature": {"type": ["string", "null"]},
                    "source_app": {"type": ["string", "null"]},
                },
                "required": ["prompt", "route", "model"],
            },
            "outputSchema": {"type": "object"},
        },
    ]


async def handle(req: Dict[str, Any]) -> Dict[str, Any]:
    method = req.get("method")
    params = req.get("params") or {}
    # MCP handshake + tools
    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "prompt-go", "version": "0.1.0"},
        }
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": result}
    if method in ("tools/list", "tools.list"):
        return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"tools": _tool_schemas()}}
    if method in ("tools/call", "tools.call"):
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "suggestRoute":
            res = await t_suggest_route(SuggestRequest(**arguments))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "json", "json": res.model_dump()}]}}
        if name == "getUsageSummary":
            res = await t_usage_summary(UsageSummaryRequest(**arguments))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "json", "json": res}]}}
        if name == "optimizeReport":
            res = await t_optimize_report(arguments.get("org"))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "json", "json": res}]}}
        if name == "weeklyCursorRuleRecommendations":
            res = await t_weekly_cursor_rules(arguments.get("org"))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "json", "json": res}]}}
        if name == "logRequest":
            res = await t_log_request(LogRequest(**arguments))
            return {"jsonrpc": "2.0", "id": req.get("id"), "result": {"content": [{"type": "json", "json": res}]}}
        return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": f"Unknown tool: {name}"}}

    # Convenience direct methods for local tests
    if method == "suggestRoute":
        body = SuggestRequest(**params)
        res = await t_suggest_route(body)
        return {"jsonrpc": "2.0", "id": req["id"], "result": res.model_dump()}
    if method == "getUsageSummary":
        res = await t_usage_summary(UsageSummaryRequest(**params))
        return {"jsonrpc": "2.0", "id": req["id"], "result": res}
    if method == "optimizeReport":
        res = await t_optimize_report(params.get("org"))
        return {"jsonrpc": "2.0", "id": req["id"], "result": res}
    if method == "weeklyCursorRuleRecommendations":
        res = await t_weekly_cursor_rules(params.get("org"))
        return {"jsonrpc": "2.0", "id": req["id"], "result": res}
    if method == "logRequest":
        res = await t_log_request(LogRequest(**params))
        return {"jsonrpc": "2.0", "id": req["id"], "result": res}
    return {"jsonrpc": "2.0", "id": req.get("id"), "error": {"code": -32601, "message": "Method not found"}}


async def main() -> None:
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        try:
            req = json.loads(line)
            resp = await handle(req)
            sys.stdout.write(json.dumps(resp, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        except Exception as e:  # pragma: no cover - robust stdio
            err = {"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(e)}}
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main())
