---
name: sassymcp-update
description: Use when the user wants to check, review, or apply a SassyMCP update — e.g. "is there a new version of sassymcp?", "update sassymcp", "what changed in the latest sassymcp release?", "show the sassymcp changelog". Walks through Kali-style apt-update / apt-show / apt-upgrade against this server's GitHub Releases (or the license-gated sassyconsultingllc.com endpoint when SASSYMCP_LICENSE_KEY is set). Never auto-installs — surfaces the asset, downloads to staging, and hands the user the run command.
---

# SassyMCP Update Walkthrough

This skill walks through the four updater tools added in v1.3.0:

| Step | Tool | apt analogue |
|---|---|---|
| 1 | `sassy_update_check` | `apt update` — refresh remote state |
| 2 | `sassy_update_changelog` | `apt show <pkg>` — read release notes |
| 3 | `sassy_update_list` | `apt list --upgradable` — see assets |
| 4 | `sassy_update_apply` | `apt upgrade` (download phase) — stage the install |

## When to invoke

Trigger when the user asks anything like:
- "check for sassymcp updates"
- "is there a new version?"
- "what's in the latest release?"
- "update sassymcp" / "upgrade sassymcp"
- "show me the changelog"
- "download the new MSI"

## Workflow

1. **Call `sassy_update_check`** with `force=False` (cached, 5 min TTL).
   - If `upgradable: false` — tell the user they're on the latest, stop.
   - If `upgradable: true` — surface the `summary` field (e.g. `1.2.0 → 1.3.0 available`).

2. **Call `sassy_update_changelog`** with no `tag` (defaults to latest).
   - Show the user the `name`, `published_at`, and `body` so they know what's
     in the release before downloading 100+ MB.

3. **Ask the user which asset to install**:
   - MSI installer (recommended for Windows — bundled tools + launchers)
   - Standalone exe (no tools bundled, ~35 MB)
   - Portable bundle zip (exe + tools, ~123 MB)
   - Or skip — they read the changelog and don't want to upgrade right now.

4. **Call `sassy_update_apply`** with the chosen `asset_name`.
   - Returns `downloaded_to` (a path under `%LOCALAPPDATA%\SassyMCP\updates\`)
     and `next_step` (e.g. `Run: msiexec /i "C:\..\SassyMCP-v1.3.0.msi"`).
   - Echo the `next_step` to the user verbatim — **do not** auto-execute it.
     The MSI needs UAC; this is an explicit user action by design.

## License-aware download

If the env var `SASSYMCP_LICENSE_KEY` is set, `sassy_update_apply`
automatically rewrites the download URL to the gated
`https://sassyconsultingllc.com/download/sassymcp/windows/<asset>?key=...`
endpoint. The user gets the same file from the licensed mirror instead of
public GitHub Releases.

## What this skill does NOT do

- **Never auto-runs the installer.** UAC + user intent. Always returns the
  command for the user to run themselves.
- **Never modifies the running server.** Update applies on next launch.
- **Never blocks a downgrade.** If the user passes an older `tag` to
  `sassy_update_apply`, that's their call.
