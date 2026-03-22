"""EventLog - Windows Event Log + Android logcat."""

import asyncio
import re

_SAFE_NAME = re.compile(r'^[A-Za-z0-9 _\-\.]+$')


def _sanitize(value: str, label: str) -> str:
    """Reject values containing shell metacharacters."""
    if not _SAFE_NAME.match(value):
        raise ValueError(f"Invalid {label}: contains disallowed characters")
    return value


def register(server):
    @server.tool()
    async def sassy_eventlog(log_name: str = "System", count: int = 20, level: str = "", source: str = "") -> str:
        """Read Windows Event Log. log_name: System, Application, Security."""
        log_name = _sanitize(log_name, "log_name")
        count = max(1, min(count, 1000))
        filters = []
        if level:
            lvl = {"error": 2, "warning": 3, "information": 4}.get(level.lower())
            if lvl:
                filters.append(f"Level={lvl}")
        if source:
            source = _sanitize(source, "source")
            filters.append(f"ProviderName='{source}'")
        xpath = f' -FilterXPath "*[System[{" and ".join(filters)}]]"' if filters else ""
        ps_script = f'Get-WinEvent -LogName {log_name}{xpath} -MaxEvents {count} | Select TimeCreated,LevelDisplayName,ProviderName,Message | FL'
        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return stdout.decode("utf-8", errors="replace").strip()[:5000]
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return "Timed out after 30s"

    @server.tool()
    async def sassy_eventlog_search(keyword: str, log_name: str = "System", count: int = 20) -> str:
        """Search Windows Event Log for keyword."""
        log_name = _sanitize(log_name, "log_name")
        keyword = _sanitize(keyword, "keyword")
        count = max(1, min(count, 500))
        ps_script = f"Get-WinEvent -LogName {log_name} -MaxEvents 500 | Where {{ $_.Message -like '*{keyword}*' }} | Select -First {count} TimeCreated,LevelDisplayName,Message | FL"
        proc = await asyncio.create_subprocess_exec(
            "powershell.exe", "-NoProfile", "-Command", ps_script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return stdout.decode("utf-8", errors="replace").strip()[:5000]
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return "Timed out after 30s"

    @server.tool()
    async def sassy_android_logcat(tag: str = "", level: str = "", lines: int = 100, device: str = "") -> str:
        """Read Android logcat."""
        args = ["adb"] + (["-s", device] if device else []) + ["logcat", "-d", "-t", str(lines)]
        if tag and level:
            args.extend([f"{tag}:{level}", "*:S"])
        elif tag:
            args.extend([f"{tag}:V", "*:S"])
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            return stdout.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return "Timed out after 15s"
