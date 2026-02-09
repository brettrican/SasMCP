"""PhoneScreen - Live Android screen via scrcpy."""

import asyncio
import shutil
import os
from mcp.server import Server

_scrcpy_proc = None

def _find_scrcpy():
    path = shutil.which("scrcpy")
    if path: return path
    for c in [r"C:\scrcpy\scrcpy.exe", os.path.expandvars(r"%USERPROFILE%\scrcpy\scrcpy.exe")]:
        if os.path.isfile(c): return c
    return "scrcpy"


def register(server: Server):
    @server.tool()
    async def sassy_scrcpy_start(device: str = "", max_size: int = 1024, no_audio: bool = True) -> str:
        """Start scrcpy screen mirroring."""
        global _scrcpy_proc
        if _scrcpy_proc and _scrcpy_proc.returncode is None:
            return f"scrcpy already running (PID: {_scrcpy_proc.pid})"
        cmd = [_find_scrcpy(), "--max-size", str(max_size)]
        if no_audio: cmd.append("--no-audio")
        if device: cmd.extend(["-s", device])
        try:
            _scrcpy_proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            return f"scrcpy started (PID: {_scrcpy_proc.pid})"
        except FileNotFoundError:
            return "Error: scrcpy not found"

    @server.tool()
    async def sassy_scrcpy_stop() -> str:
        """Stop scrcpy screen mirroring."""
        global _scrcpy_proc
        if _scrcpy_proc and _scrcpy_proc.returncode is None:
            _scrcpy_proc.terminate()
            await _scrcpy_proc.wait()
            _scrcpy_proc = None
            return "scrcpy stopped"
        return "scrcpy not running"

    @server.tool()
    async def sassy_scrcpy_record(output_path: str, device: str = "", time_limit: int = 30) -> str:
        """Record Android screen to file."""
        cmd = [_find_scrcpy(), "--no-display", "--record", output_path,
               "--max-size", "1024", "--time-limit", str(time_limit)]
        if device: cmd.extend(["-s", device])
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await asyncio.wait_for(proc.communicate(), timeout=time_limit + 10)
            return f"Recording saved to {output_path}"
        except asyncio.TimeoutError:
            return f"Recording may be at {output_path}"
