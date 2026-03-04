"""SassyMCP Server — Main entry point with smart tool loading.

Unified MCP server combining Windows desktop automation, Android device
control (ADB/scrcpy), security auditing, forensics tools, desktop vision,
cross-session communication, web inspection, GitHub operations, and workflow persona.

v0.3.0: Smart loading — only loads frequently-used tool groups by default.
Set SASSYMCP_LOAD_ALL=1 to load everything, or SASSYMCP_GROUPS=core,github_quick,persona
to select specific groups.

Built for Claude Desktop by Sassy Consulting LLC.
"""

import json
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from sassymcp.modules._tool_loader import (
    get_tracker,
    get_default_modules,
    get_all_modules,
    TOOL_GROUPS,
)

logger = logging.getLogger("sassymcp")

mcp = FastMCP("sassymcp")


def _resolve_modules() -> list[str]:
    """Determine which modules to load based on env vars.

    Priority:
    1. SASSYMCP_LOAD_ALL=1 → load everything
    2. SASSYMCP_GROUPS=core,github_quick → load specific groups
    3. Default: load always_load=True groups only
    """
    if os.environ.get("SASSYMCP_LOAD_ALL", "").strip() == "1":
        logger.info("SASSYMCP_LOAD_ALL=1 — loading all modules")
        return get_all_modules()

    groups_env = os.environ.get("SASSYMCP_GROUPS", "").strip()
    if groups_env:
        requested = [g.strip() for g in groups_env.split(",") if g.strip()]
        modules = []
        for g in requested:
            if g in TOOL_GROUPS:
                modules.extend(TOOL_GROUPS[g]["modules"])
            else:
                logger.warning(f"Unknown group: {g}")
        logger.info(f"SASSYMCP_GROUPS={groups_env} — loading: {modules}")
        return modules

    defaults = get_default_modules()
    logger.info(f"Default load: {defaults}")
    return defaults


def _import_module(name: str):
    """Import a SassyMCP module by name."""
    return __import__(f"sassymcp.modules.{name}", fromlist=[name])


# ── Module Registration ─────────────────────────────────────────────

# Always register meta tools (context estimation, usage stats)
from sassymcp.modules import meta
meta.register(mcp)
logger.info("Registered module: sassymcp.modules.meta")

# Load configured modules
_target_modules = _resolve_modules()
_loaded_count = 0

for mod_name in _target_modules:
    try:
        module = _import_module(mod_name)
        module.register(mcp)
        _loaded_count += 1
        logger.info(f"Registered module: {mod_name}")
    except Exception as e:
        logger.warning(f"Failed to register {mod_name}: {e}")

logger.info(f"SassyMCP ready: {_loaded_count} modules loaded")


def main():
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    mcp.run()


if __name__ == "__main__":
    main()
