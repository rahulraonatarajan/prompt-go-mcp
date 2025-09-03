# Prompt Go — MCP Server for Cursor AI Teams
**Prompt smarter, spend less.**  
Prompt Go routes each prompt to the right channel (Ask / Agent / Direct / Web) and gives real-time ROI analytics. It also produces **Weekly Cursor Rule Recommendations** to help teams reduce spend and improve outcomes.

## Key Features
- 🔀 Intelligent prompt routing with reasons + suggestions
- 📊 Usage & cost analytics by org/user/feature/model
- 💡 Weekly Cursor Rule Recommendations (concise, actionable)
- 💸 Budgets & alerts (observe | soft | hard enforcement)
- 🌐 Multi-provider cost registry; local/offline model support
- 🧰 Optional HTTP dashboard; OTEL metrics

## Quick Start (local)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -U pip && pip install -e .
cp .env.example .env
python -m apps.mcp_server
```

Add to Cursor settings:
```json
{
  "mcpServers": {
    "prompt-go": {
      "command": "python",
      "args": ["-m", "apps.mcp_server"],
      "env": {
        "DATABASE_URL": "sqlite+aiosqlite:///./promptgo.db",
        "PG_ALLOW_WEB": "false",
        "PG_ORG": "offlyn.ai"
      }
    }
  }
}
```

