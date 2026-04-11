===========================================================
 SassyMCP v1.1.3 — Setup Guide
 257 tools | 31 modules | All tools bundled
 Sassy Consulting LLC | sassyconsultingllc.com
===========================================================

 QUICK START (zip package):

 1. Unzip to any folder (e.g. C:\SassyMCP)
 2. Run start-beta.bat
    This auto-sets PATH for all bundled tools (ADB, nmap,
    plink, scrcpy, Tesseract) and starts with all 257 tools.
 3. The first AI session will guide you through setup.

 BUNDLED TOOLS:

 All five optional tools are included in this package:
   tools\adb\        Android Debug Bridge (device control)
   tools\nmap\       Network scanner (port scanning)
   tools\putty\      plink SSH client (remote Linux)
   tools\scrcpy\     Android screen mirroring
   tools\tesseract\  Tesseract OCR engine + English data

 No additional installs needed (except Chrome for web
 screenshots — most systems already have it).

 MCP CLIENT CONFIGURATION:

 Claude Desktop — edit %APPDATA%\Claude\claude_desktop_config.json:

   {
     "mcpServers": {
       "sassymcp": {
         "command": "C:\\SassyMCP\\sassymcp.exe",
         "env": { "SASSYMCP_LOAD_ALL": "1" }
       }
     }
   }

 Grok Desktop / Cursor / Windsurf — use HTTP mode:
   Run start-beta.bat --http
   Point your client to http://127.0.0.1:21001/mcp/

 GUIDED SETUP:

 After first launch, the AI will guide you through:
   sassy_setup_wizard      - Create your user profile
   sassy_setup_github      - Connect GitHub (opens browser)
   sassy_setup_ssh         - Connect remote Linux
   sassy_setup_check_tools - Verify all tools are detected

 TRANSPORT MODES:

 Stdio (Claude Desktop):  start-beta.bat
 HTTP (localhost):         start-beta.bat --http
 HTTP (LAN):              start-beta.bat --http --host 0.0.0.0
 HTTPS:                   start-beta.bat --http --ssl

 For LAN/tunnel access, set SASSYMCP_AUTH_TOKEN or use
 sassy_setup_generate_token to create scoped tokens.

 ENVIRONMENT VARIABLES:

 SASSYMCP_LOAD_ALL=1          Load all 257 tools (default in beta)
 SASSYMCP_GROUPS=core,android  Load specific groups only
 SASSYMCP_AUTH_TOKEN=xxx       Bearer token for HTTP auth
 GITHUB_TOKEN=xxx              GitHub API access
 SSH_HOST / SSH_USER / SSH_PASS  Remote Linux credentials

 KNOWN LIMITATIONS (beta):

 - Windows only (10/11). No macOS/Linux build yet.
 - Phone tools require USB debugging enabled on Android.
 - Web screenshots require Chrome/Chromium installed.
 - OCR accuracy depends on screen resolution and font size.
 - First-run extraction may trigger antivirus (PyInstaller
   single-file exe). Whitelist sassymcp.exe if needed.

 FEEDBACK:

 Report bugs and request features on GitHub:
   https://github.com/sassyconsultingllc/SassyMCP/issues

 DATA FILES:

 ~/.sassymcp/persona.md       Your user profile
 ~/.sassymcp/config.json      Server configuration
 ~/.sassymcp/tokens.json      Auth tokens
 ~/.sassymcp/tool_usage.json  Tool analytics data
 ~/.sassymcp/audit.log        Audit trail
 ~/.sassymcp/memory/          Persistent memory store
===========================================================
