"""Clipboard - Cross-device clipboard (Windows <-> Android)."""

import asyncio

def register(server):
    @server.tool()
    async def sassy_clipboard_get() -> str:
        """Get Windows clipboard text."""
        proc = await asyncio.create_subprocess_shell(
            'powershell -NoProfile -Command "Get-Clipboard"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return stdout.decode("utf-8", errors="replace").strip()

    @server.tool()
    async def sassy_clipboard_set(text: str) -> str:
        """Set Windows clipboard text."""
        escaped = text.replace("'", "''")
        proc = await asyncio.create_subprocess_shell(
            f"powershell -NoProfile -Command \"Set-Clipboard -Value '{escaped}'\"",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc.communicate(), timeout=10)
        return f"Clipboard set ({len(text)} chars)"

    @server.tool()
    async def sassy_clipboard_to_android(device: str = "") -> str:
        """Send Windows clipboard to Android."""
        proc = await asyncio.create_subprocess_shell(
            'powershell -NoProfile -Command "Get-Clipboard"',
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        text = stdout.decode("utf-8", errors="replace").strip()
        if not text: return "Windows clipboard is empty"
        args = ["adb"] + (["-s", device] if device else [])
        escaped = text.replace('"', '\\"')
        args.extend(["shell", f'am broadcast -a clipper.set -e text "{escaped}"'])
        proc2 = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        await asyncio.wait_for(proc2.communicate(), timeout=10)
        return f"Sent to Android: {text[:50]}..."

    @server.tool()
    async def sassy_clipboard_from_android(device: str = "") -> str:
        """Get Android clipboard to Windows."""
        args = ["adb"] + (["-s", device] if device else []) + ["shell", "am broadcast -a clipper.get"]
        proc = await asyncio.create_subprocess_exec(
            *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        return stdout.decode("utf-8", errors="replace").strip()[:200]
