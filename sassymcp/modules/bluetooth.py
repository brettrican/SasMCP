"""Bluetooth - Device enumeration and diagnostics."""

import asyncio

def register(server):
    @server.tool()
    async def sassy_bt_devices() -> str:
        """List paired Bluetooth devices."""
        proc = await asyncio.create_subprocess_shell(
            'powershell -NoProfile -Command "Get-PnpDevice -Class Bluetooth | Where { $_.Status -eq \'OK\' } | Select FriendlyName,DeviceID,Status | FT -Auto"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        return stdout.decode("utf-8", errors="replace").strip()

    @server.tool()
    async def sassy_bt_scan() -> str:
        """List all Bluetooth devices."""
        proc = await asyncio.create_subprocess_shell(
            'powershell -NoProfile -Command "Get-PnpDevice -Class Bluetooth | Select FriendlyName,DeviceID,Status,InstanceId | FT -Auto"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        return stdout.decode("utf-8", errors="replace").strip()

    @server.tool()
    async def sassy_bt_android(device: str = "") -> str:
        """List Bluetooth devices from Android."""
        args = ["adb"] + (["-s", device] if device else []) + ["shell", "dumpsys bluetooth_manager"]
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode("utf-8", errors="replace")
        relevant = []
        capture = False
        for line in output.splitlines():
            if "Bonded devices" in line or "Connected devices" in line: capture = True
            elif capture and line.strip() == "": capture = False
            if capture: relevant.append(line)
        return "\n".join(relevant[:50]) if relevant else "No Bluetooth info found"
