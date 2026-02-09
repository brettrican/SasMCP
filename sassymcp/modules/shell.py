"""Shell - Execute PowerShell, CMD, and WSL commands.

Includes automatic syntax normalization:
- Converts && chains to PowerShell-compatible ; separators
- Converts cd/pushd to Set-Location for PowerShell
- Passes CMD and WSL commands through unchanged
"""

import asyncio
import re
from mcp.server import Server


def _normalize_for_powershell(command: str) -> str:
    """Convert bash/cmd syntax to PowerShell equivalents.

    Handles:
    - && chains -> ; (semicolon separated)
    - || chains -> ; if ($LASTEXITCODE -ne 0) {
    - cd /d X -> Set-Location X
    - Leading 'cd X &&' -> Set-Location X;
    """
    # Replace && with ; for PowerShell
    command = command.replace(" && ", "; ")
    # Replace || with PowerShell error handling
    command = command.replace(" || ", "; if ($LASTEXITCODE -ne 0) { ")
    # Convert 'cd /d path' (cmd syntax) to Set-Location
    command = re.sub(r'^cd\s+/d\s+(.+?)(?:;|$)', r'Set-Location \1;', command)
    # Convert plain 'cd path' at start to Set-Location
    command = re.sub(r'^cd\s+([^;]+?)(?:;)', r'Set-Location \1;', command)
    return command


def register(server: Server):
    @server.tool()
    async def sassy_shell(command: str, shell: str = "powershell", timeout_seconds: int = 30) -> str:
        """Execute a shell command. shell: powershell, cmd, or wsl.
        Automatically normalizes syntax (e.g. && to ; for PowerShell)."""
        shell_map = {
            "powershell": ["powershell.exe", "-NoProfile", "-Command"],
            "cmd": ["cmd.exe", "/c"],
            "wsl": ["wsl", "--", "bash", "-c"],
        }
        if shell not in shell_map:
            return "Error: unknown shell. Use: powershell, cmd, wsl"

        # Normalize syntax for PowerShell
        if shell == "powershell":
            command = _normalize_for_powershell(command)

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
