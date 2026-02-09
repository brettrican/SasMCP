"""ADB - Android Debug Bridge integration."""

import asyncio
import shutil
import os

def _adb_path() -> str:
    path = shutil.which("adb")
    if path: return path
    for c in [os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
              r"C:\Android\platform-tools\adb.exe"]:
        if os.path.isfile(c): return c
    return "adb"


async def _run_adb(*args, timeout=30):
    cmd = [_adb_path()] + list(args)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 and err: return f"Error (exit {proc.returncode}): {err}"
        return out if out else err
    except asyncio.TimeoutError: return f"Timed out after {timeout}s"
    except FileNotFoundError: return "Error: adb not found"


def register(server):
    @server.tool()
    async def sassy_adb_devices() -> str:
        """List connected Android devices."""
        return await _run_adb("devices", "-l")

    @server.tool()
    async def sassy_adb_shell(command: str, device: str = "") -> str:
        """Run shell command on Android device."""
        args = ["-s", device] if device else []
        return await _run_adb(*(args + ["shell", command]))

    @server.tool()
    async def sassy_adb_packages(filter: str = "") -> str:
        """List installed packages."""
        cmd = "pm list packages" + (f" | grep -i {filter}" if filter else "")
        return await _run_adb("shell", cmd)

    @server.tool()
    async def sassy_adb_pull(remote_path: str, local_path: str, device: str = "") -> str:
        """Pull file from Android to local."""
        args = (["-s", device] if device else []) + ["pull", remote_path, local_path]
        return await _run_adb(*args)

    @server.tool()
    async def sassy_adb_push(local_path: str, remote_path: str, device: str = "") -> str:
        """Push file from local to Android."""
        args = (["-s", device] if device else []) + ["push", local_path, remote_path]
        return await _run_adb(*args)

    @server.tool()
    async def sassy_adb_install(apk_path: str, device: str = "") -> str:
        """Install APK on Android device."""
        args = (["-s", device] if device else []) + ["install", "-r", apk_path]
        return await _run_adb(*args, timeout=120)

    @server.tool()
    async def sassy_adb_logcat(filter: str = "", lines: int = 100, device: str = "") -> str:
        """Get Android logcat output."""
        args = (["-s", device] if device else []) + ["logcat", "-d", "-t", str(lines)]
        if filter: args.append(filter)
        return await _run_adb(*args)

    @server.tool()
    async def sassy_adb_screencap(local_path: str = "", device: str = "") -> str:
        """Capture Android screen to local PNG."""
        from pathlib import Path
        if not local_path: local_path = str(Path.home() / "android_screen.png")
        d = ["-s", device] if device else []
        remote = "/sdcard/sassymcp_screen.png"
        await _run_adb(*(d + ["shell", f"screencap -p {remote}"]))
        result = await _run_adb(*(d + ["pull", remote, local_path]))
        await _run_adb(*(d + ["shell", f"rm {remote}"]))
        return f"Screen captured to {local_path}" if "error" not in result.lower() else result

    @server.tool()
    async def sassy_adb_app_info(package: str, device: str = "") -> str:
        """Get detailed info about an installed Android app."""
        d = ["-s", device] if device else []
        return await _run_adb(*(d + ["shell", f"dumpsys package {package}"]))

    @server.tool()
    async def sassy_adb_wifi_connect(ip: str, port: int = 5555) -> str:
        """Connect to Android device over WiFi."""
        return await _run_adb("connect", f"{ip}:{port}")
