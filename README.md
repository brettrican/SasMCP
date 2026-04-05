# SassyMCP

**Unified MCP server for Windows desktop automation, Android device control, security auditing, GitHub operations, web inspection, cross-session communication, and AI workflow persona.**

**241 tools | 35 modules | 34MB standalone exe**

Compatible with Claude Desktop, Grok Desktop, Cursor, Windsurf, and any MCP client.

> **The official GitHub MCP server has [critical SHA-handling bugs](https://github.com/github/github-mcp-server/issues/2133).** SassyMCP's GitHub module uses correct blob SHA lookups, proper path encoding, atomic multi-file commits via Git Data API, retry logic with exponential backoff, and rate-limit awareness. It's a drop-in replacement that actually works.

## Why SassyMCP?

SassyMCP replaces multiple fragmented MCP servers (Windows-MCP, Desktop Commander, Filesystem, GitHub, etc.) with a single modular server. One install, smaller context footprint, more tools, smarter loading.

**Key differentiators:**
- **Smart Tool Loading** — Only loads tool groups you use. Reduces context window overhead from ~25K tokens to ~5K tokens by default.
- **Dynamic Vision** — Real-time screen monitoring with change detection for both desktop and Android. No more screenshot-and-pray.
- **Android Interaction** — Full phone control via UI accessibility tree: tap, swipe, type, with automatic sensitive context detection (auth/payment screens auto-block).
- **Pause/Resume** — User takes over the phone for manual steps (login, 2FA, account selection), AI watches and learns, then resumes autonomously.
- **Usage Tracking** — ML-lite scoring of tool invocations with exponential decay. Your most-used tools load first.
- **Context Estimation** — Built-in tool to measure how much of your 200K context window tool definitions consume.
- **Response Minification** — GitHub API responses stripped of URL metadata bloat (40-70% smaller).
- **Self-Modification** — Hot-reload modules without restart, git-backed rollback on syntax errors.
- **Guided Setup** — Wizard walks through persona, GitHub token, SSH credentials, and optional tool discovery.

## Modules

| Module | Tools | Group | Description |
|--------|-------|-------|-------------|
| **Meta** | 5 | meta | Context estimation, tool usage analytics, group management |
| **FileOps** | 9 | core | Read, write, search, move, copy, edit, mkdir, file info |
| **Shell** | 1 | core | PowerShell, CMD, WSL execution with syntax normalization |
| **UIAutomation** | 6 | core | Desktop state, click, type, hotkeys, screenshots, screen info |
| **Editor** | 2 | core | Surgical find/replace, multi-edit |
| **Audit** | 3 | core | Audit log read, search, clear |
| **Session** | 6 | core | Persistent terminal sessions (start, read, send, stop) |
| **GitHub Quick** | 6 | github_quick | Daily-driver: push_files, get_file, issue, PR, protect |
| **Persona** | 6 | persona | Expert-mode directives, decision framework, engineering standards |
| **Utility** | 11 | utility | Env vars, toast, zip/tar/unzip/untar, HTTP requests, file diff |
| **SelfMod** | 7 | selfmod | Self-edit, hot-reload, restart, rollback, status |
| **Setup** | 6 | setup | Setup wizard, GitHub token guide, SSH setup, tool checker |
| **Observability** | 3 | infrastructure | Health, metrics, tool stats |
| **StateManager** | 3 | infrastructure | Persistent key-value state across sessions |
| **RuntimeConfig** | 3 | infrastructure | Runtime config, recent tool calls |
| **GitHub Full** | 80 | github_full | Complete GitHub API: repos, issues, PRs, actions, security, gists |
| **ADB** | 10 | android | Android shell, packages, file transfer, logcat, screencap |
| **PhoneScreen** | 14 | android | UI tree reader, phone glance/watch, tap/swipe/type/key, pause/resume, scrcpy |
| **NetworkAudit** | 7 | system | netstat, ARP, WiFi scan, port scan, DNS, traceroute |
| **ProcessManager** | 5 | system | Windows + Android process list/kill, system info |
| **SecurityAudit** | 7 | system | Hash, permissions, certs, APK, firewall, Defender |
| **Registry** | 4 | system | Read, write, export, autorun forensics |
| **Bluetooth** | 3 | system | Windows + Android BT enumeration |
| **EventLog** | 3 | system | Windows Event Log + Android logcat |
| **Clipboard** | 4 | system | Windows + Android clipboard sync |
| **Vision** | 8 | v020 | Screen capture, OCR, dynamic glance/watch/diff |
| **AppLauncher** | 6 | v020 | Launch apps, focus/close/resize/snap windows |
| **WebInspector** | 5 | v020 | Security headers, URL screenshots, tech stack detection |
| **Crosslink** | 7 | v020 | Cross-session messaging via HTTP API + SQLite |
| **Linux** | 1 | linux | Remote SSH execution via plink |

## Dynamic Vision

### Desktop (Vision module)

Traditional MCP screenshots are blind — you capture one frame and hope it's the right one. SassyMCP's dynamic vision changes this:

| Tool | Purpose |
|------|---------|
| `sassy_screen_glance` | Fast grayscale capture at ~3-6KB. Call repeatedly to "watch" the screen. |
| `sassy_screen_watch` | Monitor for N seconds, returns **only frames where content changed** (pixel diff threshold). |
| `sassy_screen_diff` | Before/after comparison — takes frame, waits, takes another, returns both + a diff image highlighting changes. |

All three use grayscale + heavy JPEG compression to keep context cost minimal. A glance is ~2KB vs ~14KB for a full-color capture.

### Android (PhoneScreen module)

The phone isn't just a camera target — SassyMCP reads its UI accessibility tree:

| Tool | Purpose |
|------|---------|
| `sassy_phone_ui` | Reads **every visible UI element** — text, description, coordinates, clickable/focused/checked state. Structured data, not pixels. |
| `sassy_phone_state` | Foreground app, screen on/off, battery, WiFi, notification count. |
| `sassy_phone_glance` | Low-res grayscale phone screenshot via direct pipe (~4-8KB). |
| `sassy_phone_watch` | Monitors UI tree changes over duration. Returns snapshots only when elements change. |

## Phone Interaction

Full touch input via ADB — the AI can operate the phone:

| Tool | Purpose |
|------|---------|
| `sassy_phone_tap` | Tap screen coordinates |
| `sassy_phone_swipe` | Swipe between two points |
| `sassy_phone_type` | Type text into focused field |
| `sassy_phone_key` | Send key events (HOME, BACK, ENTER, VOLUME, etc.) |
| `sassy_phone_open` | Launch an app by package name |

### Sensitive Context Detection

All interaction tools (tap, swipe, type) automatically scan the UI tree before executing. If they detect **login screens, payment forms, account selectors, 2FA prompts, or permission dialogs**, the tool **refuses to execute** and returns what it sees instead. The AI then describes the screen to you and asks what to do. Pass `confirmed=True` after explicit user approval.

### Pause / Resume

For complex flows where the user needs to take over:

| Tool | Purpose |
|------|---------|
| `sassy_phone_pause` | Blocks all interaction tools. Observation tools (ui, glance, watch) still work. |
| `sassy_phone_resume` | Unblocks interaction. AI picks up where it left off, informed by everything it observed during pause. |

**Workflow:**
1. AI operates phone autonomously for routine tasks
2. AI hits a login screen → sensitive context auto-blocks → AI tells the user
3. User says "hold on" → AI calls `sassy_phone_pause`
4. User logs in manually. AI watches via `sassy_phone_ui` / `sassy_phone_glance`
5. User says "done" → AI calls `sassy_phone_resume`
6. AI continues, now aware the user logged into a specific account

## Guided Setup

On first launch, the AI guides you through configuration:

| Tool | Purpose |
|------|---------|
| `sassy_setup_wizard` | Create your persona profile (role, expertise, tech stack, preferences) |
| `sassy_setup_github` | Opens browser to GitHub token page, validates token, saves to env |
| `sassy_setup_ssh` | Collects SSH host/user/password, finds plink, tests connection |
| `sassy_setup_check_tools` | Scans for nmap, Tesseract, ADB, scrcpy, plink, Chrome — reports availability with install URLs |
| `sassy_setup_status` | Shows what's configured and what's missing |
| `sassy_setup_generate_token` | Creates auth tokens for HTTP/tunnel mode |

## Smart Loading

By default, SassyMCP only loads frequently-used tool groups. This keeps tool definitions under 5% of your context window.

```bash
# Default: loads core, github_quick, persona, meta, utility, selfmod, setup, infrastructure
uv run sassymcp

# Load everything (241 tools, ~22K tokens of context)
SASSYMCP_LOAD_ALL=1 uv run sassymcp

# Load specific groups
SASSYMCP_GROUPS=core,github_quick,android,v020 uv run sassymcp
```

### Available Groups

| Group | Modules | Default |
|-------|---------|---------|
| `core` | fileops, shell, ui_automation, editor, audit, session | Yes |
| `meta` | meta | Yes |
| `infrastructure` | observability, state_manager, runtime_config | Yes |
| `github_quick` | github_quick (6 lean tools) | Yes |
| `persona` | persona | Yes |
| `utility` | utility | Yes |
| `selfmod` | selfmod | Yes |
| `setup` | setup_wizard | Yes |
| `github_full` | github_ops (80 tools) | No |
| `android` | adb, phone_screen | No |
| `system` | network_audit, process_manager, security_audit, registry, bluetooth, eventlog, clipboard | No |
| `v020` | vision, app_launcher, web_inspector, crosslink | No |
| `linux` | linux | No |

## Install

### Standalone Executable (recommended)

Download `sassymcp.exe` from the [latest release](https://github.com/sassyconsultingllc/SassyMCP/releases). No Python required.

### From Source

```bash
git clone https://github.com/sassyconsultingllc/SassyMCP.git
cd SassyMCP
uv sync

# Optional dependencies:
uv pip install pytesseract playwright
playwright install chromium
```

## Claude Desktop Config

### Using the exe:
```json
{
  "mcpServers": {
    "sassymcp": {
      "command": "C:\\path\\to\\sassymcp.exe",
      "env": {
        "SASSYMCP_LOAD_ALL": "1",
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

### From source:
```json
{
  "mcpServers": {
    "sassymcp": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\SassyMCP", "run", "sassymcp"],
      "env": {
        "SASSYMCP_LOAD_ALL": "1",
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

## Transport Modes

| Mode | Command | Use Case |
|------|---------|----------|
| Stdio | `sassymcp.exe` | Claude Desktop, Cursor (direct pipe) |
| HTTP | `sassymcp.exe --http` | Grok Desktop, Windsurf (localhost:21001) |
| HTTP LAN | `sassymcp.exe --http --host 0.0.0.0` | Multi-device (requires auth token) |
| HTTPS | `sassymcp.exe --http --ssl` | Encrypted (auto-generates self-signed cert) |
| SSE | `sassymcp.exe --http --sse` | Legacy transport |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `SASSYMCP_LOAD_ALL=1` | Load all 241 tools |
| `SASSYMCP_GROUPS=core,android` | Load specific groups |
| `SASSYMCP_AUTH_TOKEN=xxx` | Bearer token for HTTP auth |
| `SASSYMCP_DEV=1` | Enable live reload (dev mode) |
| `GITHUB_TOKEN=xxx` | GitHub API access |
| `SSH_HOST=xxx` | Remote Linux hostname/IP |
| `SSH_USER=xxx` | Remote Linux username |
| `SSH_PASS=xxx` | Remote Linux password |

## Optional Tools

| Tool | Used By | Install |
|------|---------|---------|
| nmap | `sassy_port_scan` | [nmap.org](https://nmap.org/download.html) |
| Tesseract | `sassy_screen_ocr`, `sassy_find_text_on_screen` | [tesseract-ocr](https://github.com/tesseract-ocr/tesseract) |
| ADB | All `sassy_adb_*` + `sassy_phone_*` tools | [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools) |
| scrcpy | `sassy_scrcpy_*` tools | [scrcpy releases](https://github.com/Genymobile/scrcpy/releases) |
| plink | `sassy_linux_exec` | [PuTTY](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) |
| Chrome | `sassy_url_screenshot` | [google.com/chrome](https://www.google.com/chrome/) |

Run `sassy_setup_check_tools` to scan for all of these automatically.

## Requirements

- Windows 10/11
- Python 3.11+ (only if running from source; exe is self-contained)

## License

MIT License - Sassy Consulting LLC
