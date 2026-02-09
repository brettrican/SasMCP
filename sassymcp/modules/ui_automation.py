"""UIAutomation - Windows UI control with lean output.

IMPORTANT: All text input operations use ctrl-a + backspace to clear
the field before typing, ensuring clean output every time.
"""

import json
import asyncio

def register(server):
    @server.tool()
    async def sassy_desktop_state(include_taskbar: bool = False) -> str:
        """Get desktop state: open windows and positions. Lean output."""
        try:
            from pywinauto import Desktop
        except ImportError:
            return "Error: pywinauto not installed"
        desktop = Desktop(backend="uia")
        windows = []
        for w in desktop.windows():
            try:
                if not w.is_visible(): continue
                title = w.window_text()
                if not title: continue
                if not include_taskbar and "taskbar" in title.lower(): continue
                rect = w.rectangle()
                windows.append({"title": title, "left": rect.left, "top": rect.top,
                                "width": rect.width(), "height": rect.height()})
            except Exception: continue
        return json.dumps(windows, indent=2)

    @server.tool()
    async def sassy_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
        """Click at screen coordinates."""
        import pyautogui
        pyautogui.click(x, y, clicks=clicks, button=button)
        return f"Clicked ({x}, {y}) {button} x{clicks}"

    @server.tool()
    async def sassy_type_text(text: str, target_x: int = 0, target_y: int = 0, interval: float = 0.02) -> str:
        """Type text into a field. Always clears field first with ctrl-a + backspace.
        If target_x/target_y provided, clicks the field first."""
        import pyautogui
        import time
        if target_x and target_y:
            pyautogui.click(target_x, target_y)
            time.sleep(0.1)
        # Always clear field before typing - ensures clean output
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
        pyautogui.press("backspace")
        time.sleep(0.05)
        pyautogui.typewrite(text, interval=interval)
        return f"Typed {len(text)} chars (field cleared first)"

    @server.tool()
    async def sassy_hotkey(keys: str) -> str:
        """Press keyboard shortcut. Keys separated by +, e.g. ctrl+c."""
        import pyautogui
        key_list = [k.strip() for k in keys.split("+")]
        pyautogui.hotkey(*key_list)
        return f"Pressed {keys}"

    @server.tool()
    async def sassy_screenshot(path: str = "", region: str = "") -> str:
        """Take screenshot. Optional region as x,y,w,h."""
        import pyautogui
        from pathlib import Path
        if not path:
            path = str(Path.home() / "sassymcp_screenshot.png")
        kwargs = {}
        if region:
            parts = [int(x) for x in region.split(",")]
            if len(parts) == 4: kwargs["region"] = tuple(parts)
        img = pyautogui.screenshot(**kwargs)
        img.save(path)
        return f"Screenshot saved to {path}"
