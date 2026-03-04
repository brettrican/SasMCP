# SassyMCP

**Unified MCP server for Windows desktop automation, Android device control, security auditing, web inspection, cross-session communication, and AI workflow persona.**

Built for [Claude Desktop](https://claude.com/download) by [Sassy Consulting LLC](https://sassyconsultingllc.com).

## What is this?

SassyMCP replaces multiple fragmented MCP servers (Windows-MCP, Desktop Commander, Filesystem, etc.) with a single modular server. One MCP, smaller context footprint, more tools.

| Module | Tools | Description |
|--------|-------|-------------|
| **FileOps** | 9 | Read, write, search, move, copy, edit, mkdir, file info |
| **Shell** | 6 | PowerShell, CMD, WSL, exec (Python/Node), persistent sessions |
| **UIAutomation** | 5 | Desktop state, click, type (ctrl-a+backspace clear), hotkeys, screenshots |
| **ADB** | 10 | Android shell, packages, file transfer, logcat, screencap |
| **PhoneScreen** | 3 | scrcpy start/stop, screen recording |
| **NetworkAudit** | 8 | netstat, ARP, WiFi scan, port scan, DNS, traceroute, URL fetch |
| **ProcessManager** | 4 | Windows + Android process list/kill, system info |
| **SecurityAudit** | 7 | Hash, permissions, certs, APK, firewall, Defender |
| **Registry** | 4 | Read, write, export, autorun forensics |
| **Bluetooth** | 3 | Windows + Android BT enumeration |
| **EventLog** | 3 | Windows Event Log + Android logcat |
| **Clipboard** | 4 | Windows + Android clipboard sync |
| **Vision** | 5 | Screen capture (base64), OCR, find text on screen, window screenshots |
| **AppLauncher** | 7 | Launch apps, focus/close/resize/snap windows, launch by exe path |
| **WebInspector** | 5 | Security headers audit, URL screenshots, tech stack detection, link extraction, performance |
| **Crosslink** | 7 | Cross-session messaging (HTTP API + SQLite), session registration, broadcast |
| **Persona** | 5 | SaS workflow style, decision framework, dev best practices, user context |

**93+ tools** across 17 modules.

## Install

```bash
git clone https://github.com/sassyconsultingllc/SassyMCP.git
cd SassyMCP
uv sync

# Optional dependencies for new modules:
uv pip install pytesseract httpx playwright
playwright install chromium
```

## Claude Desktop Config

```json
{
  "mcpServers": {
    "sassymcp": {
      "command": "uv",
      "args": ["--directory", "C:\\path\\to\\SassyMCP", "run", "sassymcp"]
    }
  }
}
```

## New in v0.2.0

### Vision Module
Screen capture with MCP-compatible compression, OCR via Tesseract with dark theme auto-detection, find-and-click text on screen.

### AppLauncher Module
Launch apps via Start menu search or direct exe path. Focus, close, resize, minimize, maximize, and snap windows to screen edges.

### WebInspector Module
Security header auditing with letter grades (A+ to F), URL screenshots via Playwright or Chrome headless, tech stack detection, link extraction, and performance measurement.

### Crosslink Module
Cross-session communication via localhost HTTP API backed by SQLite. Register sessions, send/receive messages by channel, broadcast to all channels. Enables Claude Desktop <-> mobile <-> web coordination.

### Persona Module
Embeds the SaS workflow directly into SassyMCP. Communication style, decision framework, development best practices (security hardening by default), and user context — automatically available to any connecting Claude session.

## Requirements

- Python 3.11+, Windows 10/11
- Optional: ADB, scrcpy, nmap, Tesseract OCR, Chrome/Playwright

## License

MIT - Sassy Consulting LLC (c) 2026
