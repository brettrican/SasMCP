"""Shell - Execute PowerShell, CMD, and WSL commands.

Includes automatic syntax normalization:
- Converts && chains to PowerShell-compatible ; separators
- Converts cd/pushd to Set-Location for PowerShell
- Passes CMD and WSL commands through unchanged

Security:
- Enforces blockedCommands from runtime config
- Enforces hardcoded block list for destructive operations
- Intercepts delete commands and moves targets to _DELETE_ staging folder
- Clamps timeout to 300 seconds max
"""

import asyncio
import glob as glob_mod
import os
import re
import shlex
import shutil
import sys
from pathlib import Path

from sassymcp.modules._security import (
    detect_delete_intent,
    is_protected_path,
    validate_command,
)
from sassymcp.modules import audit as _audit


_MAX_TIMEOUT = 300
_STAGING_FOLDER = "_DELETE_"

# CMD flag allowlist — only these short /X tokens are treated as flags.
# Everything else starting with "/" is a POSIX-style path target.
_CMD_FLAG_ALLOWLIST = {
    "/s", "/q", "/f", "/p", "/a", "/ah", "/ar", "/as", "/aa", "/q",
    "/r", "/e", "/d", "/b", "/v", "/l", "/y", "/-y",
}

# PowerShell flags whose next token is NOT a deletion target
_PS_SKIP_FLAGS = {"-include", "-exclude", "-filter", "-depth", "-recurse", "-force"}
# PowerShell flags whose next token IS the target path
_PS_PATH_FLAGS = {"-path", "-literalpath"}


def _split_preserve_paths(command: str) -> list[str]:
    """Split a command preserving Windows paths.

    shlex with posix=True mangles backslashes ('C:\\foo' -> 'C:foo').
    On Windows we use posix=False; elsewhere posix=True.
    Falls back to str.split() if shlex raises.
    """
    try:
        use_posix = (os.name != "nt")
        return shlex.split(command, posix=use_posix)
    except ValueError:
        return command.split()


def _parse_delete_targets(command: str) -> list[str]:
    """Extract target file/directory paths from a delete command."""
    parts = _split_preserve_paths(command)
    targets: list[str] = []
    skip_next = False

    for i, part in enumerate(parts):
        if skip_next:
            skip_next = False
            continue
        if i == 0:                           # skip the command keyword itself
            continue
        # Strip quotes that posix=False leaves behind.
        clean = part.strip("'\"")
        lower = clean.lower()
        if lower in _PS_SKIP_FLAGS:          # flag that consumes the next token
            skip_next = True
            continue
        if lower in _PS_PATH_FLAGS:          # flag whose value IS a target
            if i + 1 < len(parts):
                targets.append(parts[i + 1].strip("'\""))
            skip_next = True
            continue
        if clean.startswith("-"):            # other PS/Unix flags
            continue
        # CMD flag? Must be in the allowlist, otherwise treat as a path.
        if clean.startswith("/") and lower in _CMD_FLAG_ALLOWLIST:
            continue
        if clean:
            targets.append(clean)

    # Expand globs; preserve the original literal if the glob matches nothing
    # (so the caller can report "not found" rather than silently losing it).
    expanded: list[str] = []
    for t in targets:
        if any(c in t for c in ("*", "?", "[")):
            matches = glob_mod.glob(t)
            expanded.extend(matches if matches else [t])
        else:
            expanded.append(t)
    return expanded


async def _safe_move_to_staging(targets: list[str], keyword: str, raw_command: str) -> str:
    """Move deletion targets to a _DELETE_ staging folder in the same directory."""
    if not targets:
        msg = (
            f"Delete command blocked ('{keyword}'). "
            "Could not parse target paths from command.\n"
            "Use sassy_safe_delete(path) to move items to the _DELETE_ staging folder."
        )
        _audit.log_intercept("sassy_shell", keyword, raw_command, [], ["no targets parsed"])
        return msg

    results: list[str] = []
    for target in targets:
        # absolute() — NOT resolve() — so symlinks are moved as symlinks
        # instead of dragging their real target into staging.
        try:
            p = Path(target).absolute()
        except (OSError, ValueError) as e:
            results.append(f"  Error resolving path {target!r}: {e}")
            continue

        if not p.exists() and not p.is_symlink():
            results.append(f"  Skipped (not found): {target}")
            continue

        # Never let the interceptor delete/move the SassyMCP source tree
        # or the staging folder itself.
        prot, reason = is_protected_path(p)
        if prot:
            results.append(f"  REFUSED (protected): {p}  [{reason}]")
            continue

        staging = p.parent / _STAGING_FOLDER
        try:
            staging.mkdir(exist_ok=True)
        except OSError as e:
            results.append(f"  Error creating staging folder {staging}: {e}")
            continue

        dest = staging / p.name
        if dest.exists():
            stem = p.stem
            suffix = p.suffix if p.is_file() else ""
            counter = 1
            while dest.exists():
                new_name = f"{stem}_{counter}{suffix}" if suffix else f"{p.name}_{counter}"
                dest = staging / new_name
                counter += 1

        try:
            shutil.move(str(p), str(dest))
            results.append(f"  Moved: {p} -> {dest}")
        except (OSError, shutil.Error) as e:
            results.append(f"  Error moving {target}: {e}")

    header = (
        f"Delete command blocked ('{keyword}'). "
        f"Items moved to {_STAGING_FOLDER}/ staging folder for review:"
    )
    _audit.log_intercept("sassy_shell", keyword, raw_command, targets, results)
    return header + "\n" + "\n".join(results)


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

        # Validate command against blocklist (catches catastrophic patterns first)
        ok, err = validate_command(command)
        if not ok:
            return f"Error: {err}"

        # Intercept delete commands — move targets to staging folder
        is_delete, keyword = detect_delete_intent(command)
        if is_delete:
            targets = _parse_delete_targets(command)
            return await _safe_move_to_staging(targets, keyword, command)

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
