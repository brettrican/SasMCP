"""SassyMCP Server - Main entry point.

Unified MCP server combining Windows desktop automation, Android device
control (ADB/scrcpy), security auditing, forensics tools, desktop vision,
cross-session communication, web inspection, GitHub operations, and workflow persona.

Built for Claude Desktop by Sassy Consulting LLC.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from sassymcp.modules import (
    adb,
    app_launcher,
    bluetooth,
    clipboard,
    crosslink,
    eventlog,
    fileops,
    github_ops,
    github_quick,
    network_audit,
    persona,
    phone_screen,
    process_manager,
    registry,
    security_audit,
    shell,
    ui_automation,
    vision,
    web_inspector,
)

logger = logging.getLogger("sassymcp")

mcp = FastMCP("sassymcp")

MODULES = [
    # Core
    fileops, shell, ui_automation,
    # Android
    adb, phone_screen,
    # System
    network_audit, process_manager, security_audit,
    registry, bluetooth, eventlog, clipboard,
    # v0.2.0 — New modules
    vision, app_launcher, web_inspector, crosslink, persona,
    # v0.3.0 — GitHub (full + quick)
    github_ops, github_quick,
]

for module in MODULES:
    try:
        module.register(mcp)
        logger.info(f"Registered module: {module.__name__}")
    except Exception as e:
        logger.warning(f"Failed to register {module.__name__}: {e}")


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
