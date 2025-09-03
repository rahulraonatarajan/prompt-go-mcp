# 🎯 Prompt Go — Smart AI Workflow for Cursor Teams
**Prompt smarter, spend less, work faster.**  

Transform your team's AI workflow with intelligent routing, real-time cost optimization, and adaptive learning. Prompt Go automatically routes each prompt to the most effective channel while providing actionable insights to reduce costs by 25-40%.

## ✨ What Makes It Special for Cursor Teams

### 🧠 Invisible Intelligence
- **Zero-friction setup** - Works seamlessly in Cursor with one command
- **Smart routing** - Automatically suggests web/agent/ask/direct based on prompt analysis  
- **Visual indicators** - Subtle UI hints show routing confidence without interrupting flow
- **Adaptive learning** - Gets smarter from your team's usage patterns

### 💰 Proactive Cost Management  
- **Real-time budget tracking** with smart alerts before overruns
- **Automatic downgrades** when approaching limits (soft enforcement)
- **Cost predictions** based on current usage trends
- **Team efficiency scoring** - see who's optimizing best

### 📊 Team Insights Dashboard
- **Beautiful analytics** at `http://localhost:8000/insights/team/your-team`
- **Savings tracking** - see exactly how much smart routing saves
- **Weekly recommendations** - auto-generated Cursor rules for your team
- **Performance benchmarking** across team members

### 🔒 Privacy-First Design
- **100% local processing** - no data leaves your infrastructure
- **Prompt hashing** - content never stored, only patterns analyzed
- **Team isolation** - each org has separate database and config

## 🚀 Quick Start for Cursor Teams

### Automated Setup (Recommended - 2 minutes)
```bash
git clone https://github.com/rahulraonatarajan/prompt-go-mcp.git
cd prompt-go-mcp
python setup-cursor-team.py --org "Your Team Name" --budget 500
```

That's it! The script will:
- ✅ Install dependencies and setup database  
- ⚙️ Configure Cursor MCP settings automatically
- 📋 Create team-specific policy configuration
- 🧪 Test the integration

### Manual Setup (if needed)
```bash
python -m venv .venv && . .venv/bin/activate
pip install -e .
cp .env.example .env
```

Add to Cursor `settings.json`:
```json
{
  "mcpServers": {
    "prompt-go": {
      "command": "python", 
      "args": ["-m", "apps.mcp_server"],
      "cwd": "/absolute/path/to/prompt-go-mcp",
      "env": {
        "DATABASE_URL": "sqlite+aiosqlite:///./promptgo_yourteam.db",
        "PG_ORG": "Your Team Name",
        "PG_ENABLE_LEARNING": "true",
        "PG_BUDGET_MODE": "soft"
      }
    }
  }
}
```

## 📊 See It In Action

After setup, try these prompts in Cursor:
- `"What's the latest in React 19?"` → 🌐 **Web suggested**
- `"Implement OAuth flow for our app"` → 🤖 **Agent mode**  
- `"Best practices for..."` → 💬 **Ask for clarification**
- `"Explain useState hook"` → ⚡ **Direct answer**

Visit your team dashboard: `http://localhost:8000/insights/team/your-team-name`

## 🎯 Complete Documentation

📖 **[Cursor Team Setup Guide](./CURSOR_TEAM_SETUP.md)** - Comprehensive setup and configuration  
🔧 **[Integration Guide](./cursor-integration-guide.json)** - Technical details and troubleshooting  
📊 **Dashboard**: Start with `python -m apps.http_dashboard` then visit localhost:8000

