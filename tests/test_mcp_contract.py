import json, asyncio
from apps.mcp_server.server_mcp import handle


def test_suggest_route_jsonrpc():
    req = {"jsonrpc": "2.0", "id": 1, "method": "suggestRoute", "params": {"prompt": "Explain list vs tuple?"}}
    resp = asyncio.get_event_loop().run_until_complete(handle(req))
    assert resp["result"]["top_route"] in ("direct", "ask", "web", "agent")

