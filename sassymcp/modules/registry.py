"""Registry - Windows Registry read/write for forensics."""

import asyncio
from mcp.server import Server


async def _reg(cmd, timeout=15):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    out = stdout.decode("utf-8", errors="replace").strip()
    return out if out else stderr.decode("utf-8", errors="replace").strip()


def register(server: Server):
    @server.tool()
    async def sassy_reg_read(key_path: str, value_name: str = "") -> str:
        """Read a Windows registry key or value."""
        if value_name:
            return await _reg(f'reg query "{key_path}" /v "{value_name}"')
        return await _reg(f'reg query "{key_path}"')

    @server.tool()
    async def sassy_reg_write(key_path: str, value_name: str, value_data: str, value_type: str = "REG_SZ") -> str:
        """Write a Windows registry value."""
        return await _reg(f'reg add "{key_path}" /v "{value_name}" /t {value_type} /d "{value_data}" /f')

    @server.tool()
    async def sassy_reg_export(key_path: str, output_file: str) -> str:
        """Export registry key to .reg file."""
        return await _reg(f'reg export "{key_path}" "{output_file}" /y', timeout=30)

    @server.tool()
    async def sassy_autorun_entries() -> str:
        """List common autorun/startup registry entries."""
        keys = [
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
            r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
        ]
        results = []
        for key in keys:
            out = await _reg(f'reg query "{key}" 2>nul')
            if out: results.append(f"--- {key} ---\n{out}")
        return "\n\n".join(results) if results else "No autorun entries found"
