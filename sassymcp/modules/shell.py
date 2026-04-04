"""Shell - Execute PowerShell, CMD, and WSL commands.

Includes automatic syntax normalization:
- Converts && chains to PowerShell-compatible ; separators
- Converts cd/pushd to Set-Location for PowerShell
- Passes CMD and WSL commands through unchanged

Security:
- Enforces blockedCommands from runtime config
- Enforces hardcoded block list for destructive operations
- Clamps timeout to 300 seconds max
"""

import asyncio
import re

from sassymcp.modules._security import validate_command


_MAX_TIMEOUT = 300


def _normalize_for_powershell(command: str) -> str:
    """Convert bash/cmd syntax to PowerShell equivalents."""
    command = command.replace(" && ", "; ")
    parts = command.split(" || ")
    if len(parts) > 1:
        result = parts[0]
        for part in parts[1:]:
            result = f"{result}; if ($LASTEXITCODE -ne 0) {{ {part} }}"
        command = result
    command = re.sub(r'^cd\s+/d\s+(.+?)(?:;|$)', r'Set-Location \1;', command)
    command = re.sub(r'^cd\s+([^;]+?)(?:;)', r'Set-Location \1;', command)
    return command


def register(server):
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

        # Validate command against blocklist
        ok, err = validate_command(command)
        if not ok:
            return f"Error: {err}"

        # Clamp timeout
        timeout_seconds = min(max(timeout_seconds, 1), _MAX_TIMEOUT)

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
            try:
                proc.kill()
            except Exception:
                pass
            return f"Timed out after {timeout_seconds}s"
        except Exception as e:
            return f"Error: {e}"
