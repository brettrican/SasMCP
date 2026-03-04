"""AppLauncher - Application control and window management.

Launch apps by name, focus/close/resize windows, and manage
the desktop workspace programmatically.

Dependencies: pywinauto, psutil, pyautogui.
"""

import json
import subprocess
import time


def register(server):

    @server.tool()
    async def sassy_launch_app(name: str, wait_seconds: float = 2.0) -> str:
        """Launch an application by name via Start menu search.

        name = app name as you'd type it in Start (e.g. "notepad", "chrome", "code").
        Waits wait_seconds for it to appear. Returns window info if found.
        """
        import pyautogui

        try:
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.typewrite(name, interval=0.05)
            time.sleep(0.8)
            pyautogui.press("enter")
            time.sleep(wait_seconds)

            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            name_lower = name.lower()
            for w in desktop.windows():
                try:
                    if not w.is_visible():
                        continue
                    title = w.window_text()
                    if title and name_lower in title.lower():
                        r = w.rectangle()
                        return json.dumps({
                            "launched": name,
                            "window_title": title,
                            "pid": w.process_id(),
                            "position": [r.left, r.top, r.width(), r.height()],
                        })
                except Exception:
                    continue

            return json.dumps({"launched": name, "note": "App started but window not detected by title match"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_launch_exe(path: str, args: str = "") -> str:
        """Launch an executable directly by path.

        path = full path to .exe. args = command-line arguments.
        """
        try:
            cmd = [path] + (args.split() if args else [])
            proc = subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS)
            time.sleep(1)
            return json.dumps({
                "launched": path,
                "pid": proc.pid,
                "args": args or None,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_focus_window(title: str) -> str:
        """Bring a window to the foreground by title substring."""
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            title_lower = title.lower()
            for w in desktop.windows():
                try:
                    wt = w.window_text()
                    if wt and title_lower in wt.lower() and w.is_visible():
                        w.set_focus()
                        time.sleep(0.3)
                        return json.dumps({"focused": wt, "pid": w.process_id()})
                except Exception:
                    continue
            return json.dumps({"error": f"Window not found: {title}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_close_window(title: str, force: bool = False) -> str:
        """Close a window by title. Sends WM_CLOSE (graceful) unless force=True.

        Apps may show save dialogs. force=True kills the process.
        """
        try:
            from pywinauto import Desktop
            import psutil

            desktop = Desktop(backend="uia")
            title_lower = title.lower()
            for w in desktop.windows():
                try:
                    wt = w.window_text()
                    if wt and title_lower in wt.lower() and w.is_visible():
                        pid = w.process_id()
                        if force:
                            psutil.Process(pid).kill()
                            return json.dumps({"killed": wt, "pid": pid})
                        else:
                            w.close()
                            return json.dumps({"closed": wt, "pid": pid, "method": "WM_CLOSE"})
                except Exception:
                    continue
            return json.dumps({"error": f"Window not found: {title}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_resize_window(
        title: str,
        x: int = -1, y: int = -1,
        width: int = -1, height: int = -1,
        maximize: bool = False,
        minimize: bool = False,
        restore: bool = False,
    ) -> str:
        """Move and/or resize a window by title.

        x/y = position (-1 to keep current). width/height = size (-1 to keep).
        maximize/minimize/restore for window state changes.
        """
        try:
            from pywinauto import Desktop
            desktop = Desktop(backend="uia")
            title_lower = title.lower()
            for w in desktop.windows():
                try:
                    wt = w.window_text()
                    if wt and title_lower in wt.lower() and w.is_visible():
                        if maximize:
                            w.maximize()
                            return json.dumps({"maximized": wt})
                        if minimize:
                            w.minimize()
                            return json.dumps({"minimized": wt})
                        if restore:
                            w.restore()
                            time.sleep(0.2)

                        rect = w.rectangle()
                        new_x = x if x >= 0 else rect.left
                        new_y = y if y >= 0 else rect.top
                        new_w = width if width > 0 else rect.width()
                        new_h = height if height > 0 else rect.height()

                        w.move_window(new_x, new_y, new_w, new_h)
                        return json.dumps({
                            "resized": wt,
                            "position": [new_x, new_y],
                            "size": [new_w, new_h],
                        })
                except Exception:
                    continue
            return json.dumps({"error": f"Window not found: {title}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_snap_window(title: str, position: str = "left") -> str:
        """Snap a window to a screen edge. Like Win+Arrow.

        position: "left", "right", "top-left", "top-right",
                  "bottom-left", "bottom-right", "center"
        """
        try:
            from pywinauto import Desktop
            import pyautogui

            screen_w, screen_h = pyautogui.size()
            half_w, half_h = screen_w // 2, screen_h // 2
            taskbar_h = 48

            positions = {
                "left":         (0, 0, half_w, screen_h - taskbar_h),
                "right":        (half_w, 0, half_w, screen_h - taskbar_h),
                "top-left":     (0, 0, half_w, half_h),
                "top-right":    (half_w, 0, half_w, half_h),
                "bottom-left":  (0, half_h, half_w, half_h - taskbar_h),
                "bottom-right": (half_w, half_h, half_w, half_h - taskbar_h),
                "center":       (screen_w // 4, screen_h // 4, half_w, half_h),
            }

            if position not in positions:
                return json.dumps({"error": f"Invalid position. Use: {list(positions.keys())}"})

            desktop = Desktop(backend="uia")
            title_lower = title.lower()
            for w in desktop.windows():
                try:
                    wt = w.window_text()
                    if wt and title_lower in wt.lower() and w.is_visible():
                        w.restore()
                        time.sleep(0.1)
                        px, py, pw, ph = positions[position]
                        w.move_window(px, py, pw, ph)
                        return json.dumps({"snapped": wt, "position": position,
                                           "rect": [px, py, pw, ph]})
                except Exception:
                    continue
            return json.dumps({"error": f"Window not found: {title}"})
        except Exception as e:
            return json.dumps({"error": str(e)})
