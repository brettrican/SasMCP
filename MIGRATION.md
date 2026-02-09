# Migrating to SassyMCP

**Replace 3+ MCP servers with one.** This guide helps you switch from Windows-MCP, Desktop Commander, and/or Filesystem MCP to SassyMCP.

## Why Switch?

| Before | After |
|--------|-------|
| Windows-MCP (~8K tokens) | **SassyMCP (~10K tokens total)** |
| Desktop Commander (~20K tokens) | replaces all three + adds |
| Filesystem MCP (~varies) | Android, security, forensics |
| **~35K+ tokens overhead** | **~10K tokens overhead** |

- **~25K fewer tokens** consumed by tool definitions
- **58 tools** across 12 modules (more than the 3 servers combined)
- **Syntax normalization** — no more PowerShell `&&` crashes
- **Android integration** — ADB, scrcpy, logcat built in
- **Security tools** — hash, certs, firewall, Defender, APK analysis
- **One process** instead of three

## Quick Start

### 1. Prerequisites

```
Python 3.11+
uv (pip install uv, or: curl -LsSf https://astral.sh/uv/install.sh | sh)
```

Optional (for extended features):
```
ADB (Android SDK Platform Tools) — for Android device control
scrcpy — for live Android screen mirroring
nmap — for advanced port scanning
```

### 2. Clone

```bash
git clone https://github.com/sassyconsultingllc/SassyMCP.git
cd SassyMCP
uv sync
```

### 3. Test It Works

```bash
uv run sassymcp
```

You should see it start and wait for MCP stdio input. Ctrl+C to exit.


### 4. Add to Claude Desktop

Edit `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this to the `mcpServers` section:

```json
"sassymcp": {
  "command": "uv",
  "args": ["--directory", "C:\\path\\to\\SassyMCP", "run", "sassymcp"]
}
```

Replace `C:\\path\\to\\SassyMCP` with your actual clone path.

### 5. Remove Old Servers

Remove or disable these from your config (if present):
- `Windows-MCP`
- `desktop-commander`
- `filesystem` (the Filesystem MCP server)

### 6. Restart Claude Desktop

Close and reopen Claude Desktop. SassyMCP should appear in your MCP tools.

## Tool Name Mapping

If you're used to the old tool names, here's what replaced what:

### From Windows-MCP
| Old Tool | SassyMCP Replacement |
|----------|---------------------|
| `State-Tool` | `sassy_desktop_state` (leaner output, no taskbar bloat) |
| `Click-Tool` | `sassy_click` |
| `Type-Tool` | `sassy_type_text` (auto ctrl-a+backspace clear) |
| `Scroll-Tool` | Use `sassy_hotkey` with Page Up/Down |
| `Shortcut-Tool` | `sassy_hotkey` |
| `Powershell-Tool` | `sassy_shell` (auto-normalizes && syntax) |
| `Scrape-Tool` | Use Claude's built-in web_fetch |

### From Desktop Commander
| Old Tool | SassyMCP Replacement |
|----------|---------------------|
| `read_file` | `sassy_read_file` |
| `write_file` | `sassy_write_file` |
| `list_directory` | `sassy_list_dir` |
| `start_search` | `sassy_search_files` |
| `start_process` | `sassy_shell` |
| `edit_block` | `sassy_read_file` + `sassy_write_file` |
| `get_file_info` | `sassy_file_info` |

### From Filesystem MCP
| Old Tool | SassyMCP Replacement |
|----------|---------------------|
| `read_file` | `sassy_read_file` |
| `write_file` | `sassy_write_file` |
| `list_directory` | `sassy_list_dir` |
| `search_files` | `sassy_search_files` |
| `move_file` | `sassy_move` |
| `create_directory` | `sassy_write_file` (auto-creates parents) |
| `get_file_info` | `sassy_file_info` |

### New Tools (not in any predecessor)
- `sassy_adb_*` — 10 Android device tools
- `sassy_scrcpy_*` — 3 screen mirroring tools
- `sassy_netstat`, `sassy_port_scan`, `sassy_arp_table` — network audit
- `sassy_hash_file`, `sassy_cert_check`, `sassy_apk_info` — security
- `sassy_reg_*`, `sassy_autorun_entries` — registry forensics
- `sassy_bt_*` — Bluetooth enumeration
- `sassy_eventlog*` — Windows Event Log
- `sassy_clipboard_*` — cross-device clipboard

## Publishing to npm/PyPI (Optional)

SassyMCP can be published for `uvx` one-liner install:

```bash
# Build
uv build

# Publish to PyPI
uv publish
```

Then users can run:
```bash
uvx sassymcp
```

And config becomes:
```json
"sassymcp": {
  "command": "uvx",
  "args": ["sassymcp"]
}
```

## Contributing

PRs welcome. Each module is self-contained in `sassymcp/modules/`.
To add a new module:

1. Create `sassymcp/modules/your_module.py`
2. Implement `def register(server: Server):`
3. Add `@server.tool()` decorated async functions
4. Import and add to `MODULES` list in `sassymcp/server.py`

## License

MIT — Sassy Consulting LLC (c) 2026
