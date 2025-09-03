#!/usr/bin/env python3
"""
One-click setup script for Cursor AI teams to install and configure Prompt Go MCP.
Usage: python setup-cursor-team.py --org "your-team-name"
"""
import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from typing import Dict, Any


def find_cursor_config() -> Path:
    """Find Cursor configuration directory across different OS"""
    if sys.platform == "darwin":  # macOS
        config_paths = [
            Path.home() / "Library" / "Application Support" / "Cursor" / "User",
            Path.home() / ".cursor",
        ]
    elif sys.platform.startswith("linux"):
        config_paths = [
            Path.home() / ".config" / "cursor",
            Path.home() / ".cursor",
        ]
    elif sys.platform == "win32":
        config_paths = [
            Path(os.getenv("APPDATA", "")) / "Cursor" / "User",
            Path.home() / ".cursor",
        ]
    else:
        config_paths = [Path.home() / ".cursor"]
    
    for path in config_paths:
        if path.exists():
            return path
    
    # Create default if none exist
    return Path.home() / ".cursor"


def setup_mcp_server(org_name: str, cursor_config_dir: Path) -> Dict[str, Any]:
    """Configure MCP server settings for Cursor"""
    settings_file = cursor_config_dir / "settings.json"
    
    # Load existing settings or create new
    settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print("⚠️  Warning: Could not parse existing settings.json, creating new one")
    
    # Add or update MCP servers configuration
    if "mcpServers" not in settings:
        settings["mcpServers"] = {}
    
    # Get current working directory for the MCP server
    current_dir = Path.cwd()
    
    settings["mcpServers"]["prompt-go"] = {
        "command": "python",
        "args": ["-m", "apps.mcp_server"],
        "cwd": str(current_dir),
        "env": {
            "DATABASE_URL": f"sqlite+aiosqlite:///{current_dir}/promptgo_{org_name.lower().replace(' ', '_')}.db",
            "PG_ALLOW_WEB": "true",
            "PG_ORG": org_name,
            "PG_BUDGET_MODE": "soft",
            "PG_ENABLE_LEARNING": "true"
        }
    }
    
    # Ensure cursor config directory exists
    cursor_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Write updated settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    
    return settings["mcpServers"]["prompt-go"]


def install_dependencies():
    """Install Python dependencies for Prompt Go"""
    print("📦 Installing Prompt Go dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", "."])
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)


def create_team_config(org_name: str):
    """Create team-specific configuration"""
    config_dir = Path("config")
    team_config_file = config_dir / f"{org_name.lower().replace(' ', '_')}_policy.yaml"
    
    team_config = f"""# Team Policy Configuration for {org_name}
org: "{org_name}"

# Routing preferences (0.0 to 2.0, higher = more likely to route there)
routing_weights:
  web: 1.0      # Web search for fresh info
  agent: 1.0    # Agent mode for complex tasks
  ask: 1.0      # Ask for clarification
  direct: 1.0   # Direct LLM response

# Budget management
budget:
  mode: "soft"           # observe | soft | hard
  monthly_limit_usd: 500 # Set your team's monthly budget
  alert_threshold: 0.8   # Alert at 80% of budget

# Team preferences
preferences:
  # Domains that should prefer web search
  freshness_domains:
    - "docs"
    - "pricing" 
    - "latest"
    - "update"
    - "version"
  
  # Auto-downgrade models when over budget
  budget_fallbacks:
    - "gpt-4" -> "gpt-3.5-turbo"
    - "claude-3-opus" -> "claude-3-haiku"
  
  # Learning preferences
  enable_team_learning: true
  share_successful_patterns: true

# Weekly recommendations
recommendations:
  enabled: true
  delivery_method: "dashboard"  # dashboard | email | slack
"""
    
    config_dir.mkdir(exist_ok=True)
    with open(team_config_file, 'w') as f:
        f.write(team_config)
    
    print(f"📋 Created team configuration: {team_config_file}")
    return team_config_file


def setup_database(org_name: str):
    """Initialize database for the team"""
    db_name = f"promptgo_{org_name.lower().replace(' ', '_')}.db"
    print(f"🗄️  Initializing database: {db_name}")
    
    # Create .env file if it doesn't exist
    env_file = Path(".env")
    if not env_file.exists():
        with open(env_file, 'w') as f:
            f.write(f"""DATABASE_URL=sqlite+aiosqlite:///./{db_name}
PG_ORG={org_name}
PG_ALLOW_WEB=true
PG_BUDGET_MODE=soft
PG_ENABLE_LEARNING=true
""")
        print("📝 Created .env configuration file")


def main():
    parser = argparse.ArgumentParser(description="Setup Prompt Go MCP for Cursor AI teams")
    parser.add_argument("--org", required=True, help="Your team/organization name")
    parser.add_argument("--budget", type=int, default=500, help="Monthly budget in USD (default: 500)")
    parser.add_argument("--mode", choices=["observe", "soft", "hard"], default="soft", 
                       help="Budget enforcement mode (default: soft)")
    
    args = parser.parse_args()
    
    print(f"🚀 Setting up Prompt Go MCP for team: {args.org}")
    print("=" * 50)
    
    # Step 1: Install dependencies
    install_dependencies()
    
    # Step 2: Setup database
    setup_database(args.org)
    
    # Step 3: Create team configuration
    team_config_file = create_team_config(args.org)
    
    # Step 4: Configure Cursor MCP settings
    try:
        cursor_config_dir = find_cursor_config()
        mcp_config = setup_mcp_server(args.org, cursor_config_dir)
        print(f"⚙️  Configured Cursor MCP settings in: {cursor_config_dir}")
        print(f"   Database: {mcp_config['env']['DATABASE_URL']}")
    except Exception as e:
        print(f"⚠️  Could not auto-configure Cursor settings: {e}")
        print("   Please manually add the MCP server configuration to Cursor settings")
    
    # Step 5: Test the setup
    print("\n🧪 Testing MCP server...")
    try:
        subprocess.check_call([sys.executable, "-m", "apps.mcp_server", "--test"], 
                            timeout=10, stdout=subprocess.DEVNULL)
        print("✅ MCP server test passed")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        print("⚠️  MCP server test failed - check configuration")
    
    print("\n🎉 Setup Complete!")
    print(f"""
Next steps:
1. Restart Cursor to load the new MCP server
2. Try a prompt like "What's the latest in React 19?" 
3. Check your team dashboard at: http://localhost:8000/reports/{args.org.lower().replace(' ', '_')}
4. Review your team policy: {team_config_file}

Your Prompt Go MCP is now optimized for {args.org}! 🎯
""")


if __name__ == "__main__":
    main()
