===========================================================
 SassyMCP - Setup Guide
===========================================================

 QUICK START:

 1. Run sassymcp.exe --setup
    This starts the server and flags the setup wizard.
    The first AI session will guide you through configuration.

 TRANSPORT MODES:

 Pick based on your client.

 [1] Claude Desktop (config file, stdio) -- RECOMMENDED
   This is the seamless path for Claude Desktop.
   Run: start-local.bat  (or just sassymcp.exe)
   Config: Copy claude_desktop_config.template.json to
           %APPDATA%\Claude\claude_desktop_config.json
           Edit the "command" path to point at your sassymcp.exe.
   No HTTPS, no ports, no tokens. Restart Claude Desktop.

 [2] Cursor / Windsurf / Grok Desktop (HTTP on localhost or LAN)
   Run: start-lan.bat
   Interactive: choose bind address (127.0.0.1 or 0.0.0.0),
   port, and auth token. LAN mode requires a token.
   Point your client at http://<host>:<port>/mcp/

 [3] Claude Desktop Custom Connectors / remote clients (HTTPS)
   Claude Desktop's Custom Connectors feature REQUIRES an HTTPS
   URL with a publicly-trusted certificate. Plain http://127.0.0.1
   is rejected, and so are self-signed certs.
   Run: start-tunnel.bat
   This uses the BUNDLED cloudflared.exe to spin an ephemeral
   trycloudflare.com tunnel -- no Cloudflare account, no login,
   no domain needed. The script prints the HTTPS URL and auth
   token; paste them into Claude Desktop's Custom Connector form.
   Note: the URL changes each run (ephemeral by design). For a
   stable URL, bring your own Cloudflare Tunnel and edit the
   script to use "cloudflared tunnel run <name>" instead.

 AUTH TOKENS:

 For HTTP/tunnel modes, set SASSYMCP_AUTH_TOKEN env var or
 use the sassy_setup_generate_token tool to create scoped
 tokens saved to ~/.sassymcp/tokens.json.

 GUIDED SETUP:

 After first launch, the AI will guide you through:
   sassy_setup_wizard      - Create your user profile
   sassy_setup_github      - Connect GitHub (opens browser for token)
   sassy_setup_ssh         - Connect remote Linux (host/user/pass)
   sassy_setup_check_tools - Scan for optional tools (nmap, adb, etc.)

 ENVIRONMENT VARIABLES:

 SASSYMCP_LOAD_ALL=1          Load all tool modules
 SASSYMCP_GROUPS=core,github  Load specific groups only
 SASSYMCP_AUTH_TOKEN=xxx      Bearer token for HTTP auth
 SASSYMCP_DEV=1               Enable live reload (dev mode)
 GITHUB_TOKEN=xxx             GitHub API access
 SSH_HOST=xxx                 Remote Linux hostname/IP
 SSH_USER=xxx                 Remote Linux username
 SSH_PASS=xxx                 Remote Linux password

 FILES:

 ~/.sassymcp/persona.md       Your user profile
 ~/.sassymcp/config.json      Server configuration
 ~/.sassymcp/tokens.json      Auth tokens
 ~/.sassymcp/tool_usage.json  Tool analytics data
 ~/.sassymcp/audit.log        Audit trail
===========================================================
