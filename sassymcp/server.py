"""SassyMCP Server - Main entry point.

Unified MCP server combining Windows desktop automation, Android device
control (ADB/scrcpy), security auditing, and forensics tools.

Built for Claude Desktop by Sassy Consulting LLC.
"""

import asyncio
import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

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

MODULES = [
    fileops, shell, ui_automation, adb, phone_screen,
    network_audit, process_manager, security_audit,
    registry, bluetooth, eventlog, clipboard,
]


def create_server() -> Server:
    """Create and configure the SassyMCP server with all modules."""
    server = Server("sassymcp")
    for module in MODULES:
        try:
            module.register(server)
            logger.info(f"Registered module: {module.__name__}")
        except Exception as e:
            logger.warning(f"Failed to register {module.__name__}: {e}")
    return server


async def run_server():
    """Run the MCP server over stdio."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
