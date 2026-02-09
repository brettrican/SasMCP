"""NetworkAudit - Network scanning and monitoring."""

import asyncio
import shutil
from mcp.server import Server


async def _run_cmd(cmd, timeout=30):
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return stdout.decode("utf-8", errors="replace").strip()
    except asyncio.TimeoutError:
        proc.kill(); return f"Timed out after {timeout}s"


def register(server: Server):
    @server.tool()
    async def sassy_netstat(filter: str = "") -> str:
        """Show active network connections."""
        out = await _run_cmd("netstat -ano")
        if filter:
            lines = [l for l in out.splitlines() if filter.lower() in l.lower()]
            return "\n".join(lines[:100])
        return "\n".join(out.splitlines()[:100])

    @server.tool()
    async def sassy_arp_table() -> str:
        """Show ARP table."""
        return await _run_cmd("arp -a")

    @server.tool()
    async def sassy_wifi_networks() -> str:
        """Scan visible WiFi networks."""
        return await _run_cmd("netsh wlan show networks mode=bssid")

    @server.tool()
    async def sassy_port_scan(target: str = "127.0.0.1", ports: str = "1-1024") -> str:
        """Port scan. Uses nmap if available."""
        if shutil.which("nmap"):
            return await _run_cmd(f"nmap -p {ports} {target}", timeout=60)
        return await _run_cmd(f'powershell -NoProfile -Command "1..1024 | % {{ $t=New-Object Net.Sockets.TcpClient; try {{ $t.ConnectAsync(\'{target}\',$_).Wait(200)|Out-Null; if($t.Connected){{$_}} }} catch {{}} finally {{ $t.Dispose() }} }}"', timeout=60)

    @server.tool()
    async def sassy_dns_lookup(hostname: str) -> str:
        """DNS lookup."""
        return await _run_cmd(f"nslookup {hostname}")

    @server.tool()
    async def sassy_traceroute(target: str) -> str:
        """Traceroute to target."""
        return await _run_cmd(f"tracert -d {target}", timeout=60)

    @server.tool()
    async def sassy_wifi_profile(profile: str = "") -> str:
        """Show WiFi profile details."""
        if profile:
            return await _run_cmd(f'netsh wlan show profile name="{profile}" key=clear')
        return await _run_cmd("netsh wlan show profiles")
