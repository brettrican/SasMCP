"""EventLog - Windows Event Log + Android logcat."""

import asyncio

def register(server):
    @server.tool()
    async def sassy_eventlog(log_name: str = "System", count: int = 20, level: str = "", source: str = "") -> str:
        """Read Windows Event Log. log_name: System, Application, Security."""
        filters = []
        if level:
            lvl = {"error": 2, "warning": 3, "information": 4}.get(level.lower())
            if lvl: filters.append(f"Level={lvl}")
        if source: filters.append(f"ProviderName='{source}'")
        xpath = f' -FilterXPath "*[System[{" and ".join(filters)}]]"' if filters else ""
        cmd = f'powershell -NoProfile -Command "Get-WinEvent -LogName {log_name}{xpath} -MaxEvents {count} | Select TimeCreated,LevelDisplayName,ProviderName,Message | FL"'
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace").strip()[:5000]

    @server.tool()
    async def sassy_eventlog_search(keyword: str, log_name: str = "System", count: int = 20) -> str:
        """Search Windows Event Log for keyword."""
        cmd = f"powershell -NoProfile -Command \"Get-WinEvent -LogName {log_name} -MaxEvents 500 | Where {{ $_.Message -like '*{keyword}*' }} | Select -First {count} TimeCreated,LevelDisplayName,Message | FL\""
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        return stdout.decode("utf-8", errors="replace").strip()[:5000]

    @server.tool()
    async def sassy_android_logcat(tag: str = "", level: str = "", lines: int = 100, device: str = "") -> str:
        """Read Android logcat."""
        args = ["adb"] + (["-s", device] if device else []) + ["logcat", "-d", "-t", str(lines)]
        if tag and level: args.extend([f"{tag}:{level}", "*:S"])
        elif tag: args.extend([f"{tag}:V", "*:S"])
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        return stdout.decode("utf-8", errors="replace").strip()
