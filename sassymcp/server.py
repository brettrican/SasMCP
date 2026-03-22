"""SassyMCP Server — Main entry point with smart tool loading.
Unified MCP server combining Windows desktop automation, Android device
control (ADB/scrcpy), security auditing, forensics tools, desktop vision,
cross-session communication, web inspection, GitHub operations, and workflow persona.
v0.3.1: Smart loading — only loads frequently-used tool groups by default.
Set SASSYMCP_LOAD_ALL=1 to load everything, or SASSYMCP_GROUPS=core,github_quick,persona
to select specific groups.
Built for Claude Desktop by Sassy Consulting LLC.
"""
import json
import logging
import os
import sys
import time
import functools
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from sassymcp.modules._tool_loader import (
    get_tracker,
    get_default_modules,
    get_all_modules,
    TOOL_GROUPS,
)
logger = logging.getLogger("sassymcp")

# Disable DNS rebinding protection — Cloudflare Tunnel handles access control
_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("sassymcp", transport_security=_security)


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


# ── Audit Middleware ────────────────────────────────────────────────

def _get_audit_logger():
    """Lazy-import audit module to avoid circular deps."""
    try:
        from sassymcp.modules.audit import log_tool_call
        return log_tool_call
    except Exception:
        return None


def audit_tool(fn):
    """Decorator that logs every tool invocation via audit.py."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        log_tool_call = _get_audit_logger()
        start = time.monotonic()
        error = None
        result = None
        try:
            result = await fn(*args, **kwargs)
            return result
        except Exception as e:
            error = str(e)
            raise
        finally:
            if log_tool_call:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                try:
                    # Sanitize: truncate large args
                    safe_args = {
                        k: (str(v)[:200] if len(str(v)) > 200 else v)
                        for k, v in kwargs.items()
                    }
                    log_tool_call(
                        tool_name=fn.__name__,
                        args=safe_args,
                        elapsed_ms=elapsed_ms,
                        error=error,
                    )
                except Exception:
                    pass  # Never let audit failures break tools
    return wrapper


def _wrap_all_tools():
    """Walk mcp's registered tools and wrap each with audit_tool."""
    try:
        # FastMCP stores tools in ._tool_manager._tools (dict of name→Tool)
        tools = mcp._tool_manager._tools
        for name, tool in tools.items():
            if hasattr(tool, "fn") and not getattr(tool.fn, "_audit_wrapped", False):
                tool.fn = audit_tool(tool.fn)
                tool.fn._audit_wrapped = True
        logger.info(f"Audit middleware applied to {len(tools)} tools")
    except Exception as e:
        logger.warning(f"Audit middleware wiring failed (non-fatal): {e}")


# ── Module Registration ─────────────────────────────────────────────
# Always register meta tools (context estimation, usage stats)
from sassymcp.modules import meta
meta.register(mcp)
logger.info("Registered module: sassymcp.modules.meta")

# Load configured modules
_target_modules = _resolve_modules()
_loaded_count = 0
for mod_name in _target_modules:
    if mod_name == "meta":
        continue  # Already registered above
    try:
        module = _import_module(mod_name)
        module.register(mcp)
        _loaded_count += 1
        logger.info(f"Registered module: {mod_name}")
    except Exception as e:
        logger.warning(f"Failed to register {mod_name}: {e}")

logger.info(f"SassyMCP ready: {_loaded_count} modules loaded")

# Wire audit middleware after all tools are registered
_wrap_all_tools()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SassyMCP Server")
    parser.add_argument(
        "--http", "--serve", action="store_true",
        help="Run as HTTP server (for remote/tunnel access via cloudflared)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=21001)
    parser.add_argument(
        "--sse", action="store_true",
        help="Use legacy SSE transport instead of streamable-http",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    if args.http:
        # Remote mode: run with uvicorn behind cloudflared tunnel
        import uvicorn

        if args.sse:
            logger.info(f"Starting SassyMCP (SSE) on {args.host}:{args.port}")
            app = mcp.sse_app()
        else:
            logger.info(f"Starting SassyMCP (streamable-http) on {args.host}:{args.port}")
            app = mcp.streamable_http_app()

        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # Local mode: stdio for Claude Desktop
        logger.info("Starting SassyMCP (stdio)")
        mcp.run()

if __name__ == "__main__":
    main()