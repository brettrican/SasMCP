"""SassyMCP Server - Main entry point.

Unified MCP server combining Windows desktop automation, Android device
control (ADB/scrcpy), security auditing, and forensics tools.

Built for Claude Desktop by Sassy Consulting LLC.
"""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from sassymcp.modules import (
    adb,
    bluetooth,
    clipboard,
    eventlog,
    fileops,
    network_audit,
    phone_screen,
    process_manager,
    registry,
    security_audit,
    shell,
    ui_automation,
)

logger = logging.getLogger("sassymcp")

mcp = FastMCP("sassymcp")

MODULES = [
    fileops, shell, ui_automation, adb, phone_screen,
    network_audit, process_manager, security_audit,
    registry, bluetooth, eventlog, clipboard,
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
