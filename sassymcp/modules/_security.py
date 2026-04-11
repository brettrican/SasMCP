"""SassyMCP Security — Input validation for paths, commands, and network targets.

Enforces:
- allowedDirectories: restrict file operations to specific directories
- blockedCommands: prevent execution of dangerous shell commands
- SSRF protection: block requests to private/internal IPs
- ADB device validation
- Registry path restrictions

All checks return (ok: bool, error: str | None).
On failure, the tool should return the error message and NOT proceed.
"""

import ipaddress
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger("sassymcp.security")


def _get_config_value(key: str, default=None):
    """Lazy-load a runtime config value."""
    try:
        from sassymcp.modules.runtime_config import get
        return get(key, default)
    except Exception:
        return default


# ── Path Validation ──────────────────────────────────────────────────

def validate_path(path: str) -> tuple[bool, Optional[str]]:
    """Check if a path is within allowedDirectories.

    If allowedDirectories is empty or not configured, all paths are allowed
    (backwards compatible). When configured, paths must resolve to within
    one of the allowed directories.
    """
    allowed = _get_config_value("allowedDirectories", [])
    if not allowed:
        return True, None

    try:
        resolved = Path(path).resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"

    for allowed_dir in allowed:
        try:
            allowed_resolved = Path(allowed_dir).resolve()
            if resolved == allowed_resolved or allowed_resolved in resolved.parents:
                return True, None
        except (OSError, ValueError):
            continue

    return False, f"Path '{path}' is outside allowed directories: {allowed}"


# ── Command Validation ───────────────────────────────────────────────

# Always blocked regardless of config — these are never safe to run from an MCP tool
_HARDCODED_BLOCKS = {
    "format", "diskpart", "cipher /w",
    "rm -rf /", "rm -rf /*", "dd if=/dev/zero",
    "mkfs", ":(){ :|:& };:",
    "shutdown", "reboot", "halt", "init 0", "init 6",
}


def validate_command(command: str) -> tuple[bool, Optional[str]]:
    """Check if a shell command is blocked.

    Checks against both the hardcoded block list and the user-configurable
    blockedCommands list from runtime config.
    """
    cmd_lower = command.strip().lower()

    # Hardcoded blocks
    for blocked in _HARDCODED_BLOCKS:
        if blocked in cmd_lower:
            return False, f"Command blocked (safety): contains '{blocked}'"

    # User-configured blocks
    blocked_commands = _get_config_value("blockedCommands", [])
    for blocked in blocked_commands:
        if blocked.lower() in cmd_lower:
            return False, f"Command blocked (config): contains '{blocked}'"

    return True, None


# ── ADB Input Validation ─────────────────────────────────────────────

_ADB_DEVICE_PATTERN = re.compile(r"^[A-Za-z0-9.:_\-]+$")
_ADB_PACKAGE_PATTERN = re.compile(r"^[A-Za-z0-9._\-]+$")


def validate_adb_device(device: str) -> tuple[bool, Optional[str]]:
    """Validate ADB device identifier."""
    if not device:
        return True, None  # empty = default device
    if not _ADB_DEVICE_PATTERN.match(device):
        return False, f"Invalid device identifier: {device}"
    return True, None


def validate_adb_package(package: str) -> tuple[bool, Optional[str]]:
    """Validate Android package name."""
    if not _ADB_PACKAGE_PATTERN.match(package):
        return False, f"Invalid package name: {package}"
    return True, None


# ── SSRF Protection ──────────────────────────────────────────────────

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def validate_url(url: str, allow_private: bool = False) -> tuple[bool, Optional[str]]:
    """Validate a URL for SSRF protection.

    Blocks: private IPs, link-local, cloud metadata, file:// scheme.
    Set allow_private=True for tools that intentionally target LAN (e.g., crosslink).
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return False, f"Blocked URL scheme: {parsed.scheme}"

    if not parsed.hostname:
        return False, "URL has no hostname"

    if allow_private:
        return True, None

    # Resolve hostname to check for private IPs
    try:
        addr = ipaddress.ip_address(parsed.hostname)
        for net in _PRIVATE_RANGES:
            if addr in net:
                return False, f"Blocked: URL resolves to private/internal address ({parsed.hostname})"
    except ValueError:
        # Not an IP literal — hostname. Check common dangerous hostnames.
        hostname = parsed.hostname.lower()
        if hostname in ("localhost", "metadata.google.internal", "169.254.169.254"):
            return False, f"Blocked: dangerous hostname ({hostname})"

    return True, None


# ── Delete Command Detection ────────────────────────────────────────

# Commands that indicate file/directory deletion intent.
# These are intercepted and targets are moved to a _DELETE_ staging folder
# instead of being destroyed — minimising data loss from AI hallucinations.
_DELETE_KEYWORDS = frozenset({
    "rm", "rmdir", "unlink",                  # Unix / WSL
    "del", "erase", "rd",                     # Windows CMD
    "remove-item", "ri", "rni",               # PowerShell (incl. aliases)
    "sdelete", "sdelete64",                   # Sysinternals secure-delete
})

# Shell wrappers whose payload must be recursively scanned.
# Format: command-name -> flags that consume the next arg as a nested command.
_WRAPPER_CMDS = {
    "powershell":    {"-c", "-command", "-encodedcommand", "-enc"},
    "powershell.exe":{"-c", "-command", "-encodedcommand", "-enc"},
    "pwsh":          {"-c", "-command", "-encodedcommand", "-enc"},
    "pwsh.exe":      {"-c", "-command", "-encodedcommand", "-enc"},
    "cmd":           {"/c", "/k", "/r"},
    "cmd.exe":       {"/c", "/k", "/r"},
    "wsl":           {"-e", "--exec", "--"},
    "wsl.exe":       {"-e", "--exec", "--"},
    "bash":          {"-c"},
    "sh":            {"-c"},
    "zsh":           {"-c"},
}

# Destructive patterns that aren't bare keywords (regex, evaluated on lowered cmd).
_DESTRUCTIVE_PATTERNS = [
    (re.compile(r"\bclear-content\b"),                                  "clear-content"),
    (re.compile(r"\bset-content\b[^|;&\n]*-value\s+['\"]?\s*['\"]?"),   "set-content -value ''"),
    (re.compile(r"\[system\.io\.file\]::delete"),                       ".net file.delete"),
    (re.compile(r"\[system\.io\.directory\]::delete"),                  ".net directory.delete"),
    (re.compile(r"\[io\.file\]::delete"),                               ".net file.delete"),
    (re.compile(r"\bout-null\s*;\s*.*>\s*\$null"),                      "redirect to $null"),
    (re.compile(r"^\s*>\s*\S"),                                          "truncate-by-redirect"),
    (re.compile(r"[;&|]\s*>\s*\S"),                                      "truncate-by-redirect"),
    (re.compile(r"\bmove-item\b[^|;&\n]*\s+\$null"),                    "move-item to $null"),
]


def _scan_segment(seg: str) -> tuple[bool, str]:
    """Scan a single command segment (already split on ; & | newlines)."""
    stripped = seg.strip()
    if not stripped:
        return False, ""

    # Destructive regex patterns — run first so they catch things keywords miss.
    for pat, label in _DESTRUCTIVE_PATTERNS:
        if pat.search(stripped):
            return True, label

    words = stripped.split()
    if not words:
        return False, ""

    first = words[0].lstrip("&").lstrip(".")   # strip PS invocation prefixes
    first = first.strip("'\"")                  # strip quoted invocations
    first_lower = first.lower()

    # Direct keyword match.
    if first_lower in _DELETE_KEYWORDS:
        return True, first_lower

    # Shell wrapper — recursively scan the inner payload.
    if first_lower in _WRAPPER_CMDS:
        flags = _WRAPPER_CMDS[first_lower]
        # Find the first non-flag token that isn't a wrapper-flag, OR the arg
        # following a payload-bearing flag.
        i = 1
        while i < len(words):
            tok = words[i].lower()
            if tok in flags and i + 1 < len(words):
                inner = " ".join(words[i + 1:])
                # Strip matching outer quotes if present.
                if len(inner) >= 2 and inner[0] == inner[-1] and inner[0] in ("'", '"'):
                    inner = inner[1:-1]
                return detect_delete_intent(inner)
            if tok.startswith("-") or tok.startswith("/"):
                i += 1
                continue
            # First positional token after a shell name — treat as command.
            inner = " ".join(words[i:])
            return detect_delete_intent(inner)
        return False, ""

    return False, ""


def detect_delete_intent(command: str) -> tuple[bool, str]:
    """Detect if a command attempts to delete files/directories.

    Returns (is_delete, matched_keyword).
    Delete commands are intercepted — targets are moved to a _DELETE_
    staging folder instead of being destroyed.

    Handles: direct keywords, PowerShell aliases (ri/rni), shell wrappers
    (powershell/cmd/wsl/bash -c), .NET File.Delete, Clear-Content,
    truncate-by-redirect, and segmented commands joined by ; & | \\n.
    """
    # Preserve case for regex patterns but lower for keyword comparisons.
    segments = re.split(r'[;&|\n]+', command)
    for seg in segments:
        is_del, kw = _scan_segment(seg.lower())
        if is_del:
            return True, kw
    return False, ""


# ── Protected Paths — never delete/overwrite ────────────────────────

def _protected_roots() -> list[Path]:
    """Paths that no tool should delete, move, or overwrite."""
    roots = []
    try:
        # The SassyMCP source tree itself.
        roots.append(Path(__file__).resolve().parent.parent)  # sassymcp/
    except Exception:
        pass
    # User config/audit.
    roots.append(Path.home() / ".sassymcp")
    return roots


def is_protected_path(path: str | Path) -> tuple[bool, Optional[str]]:
    """Check if a path is protected from deletion/overwrite.

    Returns (is_protected, reason). Uses absolute path (NOT resolve) so
    symlinks can be moved without following them into a protected target.
    """
    try:
        p = Path(path).absolute()
    except (OSError, ValueError):
        return False, None

    name = p.name
    # The staging folder itself — never recurse into it.
    if name == "_DELETE_":
        return True, "path is a _DELETE_ staging folder"

    for root in _protected_roots():
        try:
            root_abs = root.absolute()
        except (OSError, ValueError):
            continue
        if p == root_abs or root_abs in p.parents:
            # Allow operations on _DELETE_ subfolders inside protected roots.
            if "_DELETE_" in p.parts:
                return False, None
            return True, f"path is inside protected root: {root_abs}"

    return False, None


# ── Input Size Validation ────────────────────────────────────────────

def validate_input_size(value: str, max_bytes: int = 10_000_000, label: str = "input") -> tuple[bool, Optional[str]]:
    """Reject inputs that exceed a size threshold."""
    if len(value) > max_bytes:
        return False, f"{label} exceeds maximum size ({len(value)} > {max_bytes} bytes)"
    return True, None
