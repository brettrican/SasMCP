"""NetworkAudit - Network scanning and monitoring."""

import asyncio
import re
import shutil

_SAFE_HOST = re.compile(r'^[A-Za-z0-9\.\-\:]+$')
_SAFE_PORTS = re.compile(r'^[0-9,\-]+$')
_SAFE_PROFILE = re.compile(r'^[A-Za-z0-9 _\-\.]+$')


def _validate_host(value: str) -> str:
    """Validate hostname/IP — alphanumeric, dots, hyphens, colons only."""
    if not _SAFE_HOST.match(value):
        raise ValueError(f"Invalid host/target: {value!r}")
    return value


def _validate_ports(value: str) -> str:
    """Validate port spec — digits, commas, hyphens only."""
    if not _SAFE_PORTS.match(value):
        raise ValueError(f"Invalid port spec: {value!r}")
    return value


async def _run_exec(*args, timeout=30):
    """Run a command via subprocess_exec (no shell interpretation)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        proc.kill()
        return f"Timed out after {timeout}s"
    except FileNotFoundError:
        return f"Error: {args[0]} not found"


def register(server):
    @server.tool()
    async def sassy_netstat(filter_str: str = "") -> str:
        """Show active network connections."""
        out = await _run_exec("netstat", "-ano")
        if filter_str:
            lines = [line for line in out.splitlines() if filter_str.lower() in line.lower()]
            return "\n".join(lines[:100])
        return "\n".join(out.splitlines()[:100])

    @server.tool()
    async def sassy_arp_table() -> str:
        """Show ARP table."""
        return await _run_exec("arp", "-a")

    @server.tool()
    async def sassy_wifi_networks() -> str:
        """Scan visible WiFi networks."""
        return await _run_exec("netsh", "wlan", "show", "networks", "mode=bssid")

    @server.tool()
    async def sassy_port_scan(target: str = "127.0.0.1", ports: str = "1-1024") -> str:
        """Port scan. Uses nmap if available."""
        target = _validate_host(target)
        ports = _validate_ports(ports)
        if shutil.which("nmap"):
            return await _run_exec("nmap", "-p", ports, target, timeout=60)
        ps_script = f"1..1024 | % {{ $t=New-Object Net.Sockets.TcpClient; try {{ $t.ConnectAsync('{target}',$_).Wait(200)|Out-Null; if($t.Connected){{$_}} }} catch {{}} finally {{ $t.Dispose() }} }}"
        return await _run_exec("powershell.exe", "-NoProfile", "-Command", ps_script, timeout=60)

    @server.tool()
    async def sassy_dns_lookup(hostname: str) -> str:
        """DNS lookup."""
        hostname = _validate_host(hostname)
        return await _run_exec("nslookup", hostname)

    @server.tool()
    async def sassy_traceroute(target: str) -> str:
        """Traceroute to target."""
        target = _validate_host(target)
        return await _run_exec("tracert", "-d", target, timeout=60)

    @server.tool()
    async def sassy_wifi_profile(profile: str = "") -> str:
        """Show WiFi profile details."""
        if profile:
            if not _SAFE_PROFILE.match(profile):
                return f"Error: invalid profile name: {profile!r}"
            return await _run_exec("netsh", "wlan", "show", "profile", f"name={profile}", "key=clear")
        return await _run_exec("netsh", "wlan", "show", "profiles")
