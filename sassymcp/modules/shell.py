"""Shell - Execute PowerShell, CMD, and WSL commands."""

import asyncio
from mcp.server import Server


def register(server: Server):
    @server.tool()
    async def sassy_shell(command: str, shell: str = "powershell", timeout_seconds: int = 30) -> str:
        """Execute a shell command. shell: powershell, cmd, or wsl."""
        shell_map = {
            "powershell": ["powershell.exe", "-NoProfile", "-Command"],
            "cmd": ["cmd.exe", "/c"],
            "wsl": ["wsl", "--", "bash", "-c"],
        }
        if shell not in shell_map:
            return "Error: unknown shell. Use: powershell, cmd, wsl"
        cmd = shell_map[shell] + [command]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
            output = stdout.decode("utf-8", errors="replace").strip()
            errors = stderr.decode("utf-8", errors="replace").strip()
            parts = [f"[exit: {proc.returncode}]"]
            if output: parts.append(output)
            if errors: parts.append(f"STDERR: {errors}")
            return "\n".join(parts)
        except asyncio.TimeoutError:
            return f"Timed out after {timeout_seconds}s"
        except Exception as e:
            return f"Error: {e}"
