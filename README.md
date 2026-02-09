# SassyMCP

**Unified MCP server for Windows desktop automation, Android device control, security auditing, and forensics.**

Built for [Claude Desktop](https://claude.com/download) by [Sassy Consulting LLC](https://sassyconsultingllc.com).

## What is this?

SassyMCP replaces multiple fragmented MCP servers (Windows-MCP, Desktop Commander, Filesystem, etc.) with a single modular server. One MCP, smaller context footprint, more tools.

| Module | Tools | Description |
|--------|-------|-------------|
| **FileOps** | 7 | Read, write, search, move, copy files |
| **Shell** | 1 | PowerShell, CMD, WSL command execution |
| **UIAutomation** | 5 | Desktop state, click, type (ctrl-a+backspace clear), hotkeys, screenshots |
| **ADB** | 10 | Android shell, packages, file transfer, logcat, screencap |
| **PhoneScreen** | 3 | scrcpy start/stop, screen recording |
| **NetworkAudit** | 7 | netstat, ARP, WiFi scan, port scan, DNS, traceroute |
| **ProcessManager** | 4 | Windows + Android process list/kill, system info |
| **SecurityAudit** | 7 | Hash, permissions, certs, APK, firewall, Defender |
| **Registry** | 4 | Read, write, export, autorun forensics |
| **Bluetooth** | 3 | Windows + Android BT enumeration |
| **EventLog** | 3 | Windows Event Log + Android logcat |
| **Clipboard** | 4 | Windows + Android clipboard sync |

**58 tools** across 12 modules.

## Install

```bash
git clone https://github.com/sassyconsultingllc/SassyMCP.git
cd SassyMCP
uv sync
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

## Requirements

- Python 3.11+, Windows 10/11
- Optional: ADB, scrcpy, nmap

## License

MIT - Sassy Consulting LLC (c) 2026
