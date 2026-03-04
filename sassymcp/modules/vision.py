"""Vision - Desktop screen capture, OCR, and visual analysis.

Provides screenshot capture with compression for MCP limits,
OCR via Tesseract, text-on-screen finding with coordinates,
and per-window/per-region capture.

Dependencies: Pillow (required), pytesseract + Tesseract binary (optional for OCR).
"""

import base64
import io
import json
from pathlib import Path


def _find_window_rect(title_substring: str):
    """Find a window by title substring, return (x, y, w, h) or None."""
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend="uia")
        title_lower = title_substring.lower()
        for w in desktop.windows():
            try:
                if not w.is_visible():
                    continue
                wt = w.window_text()
                if wt and title_lower in wt.lower():
                    r = w.rectangle()
                    return (r.left, r.top, r.width(), r.height())
            except Exception:
                continue
    except ImportError:
        pass
    return None


def register(server):

    @server.tool()
    async def sassy_screen_capture(
        window_title: str = "",
        region: str = "",
        max_width: int = 1280,
        quality: int = 70,
        save_path: str = "",
    ) -> str:
        """Capture screen as compressed base64 JPEG for inline viewing.

        No args = full primary screen. window_title = capture specific window.
        region = "x,y,w,h" rectangle. max_width resizes for MCP size limits.
        quality = JPEG 1-100. save_path = also save to disk.
        Returns JSON with base64 image data and metadata.
        """
        import pyautogui
        from PIL import Image

        try:
            if window_title:
                rect = _find_window_rect(window_title)
                if rect is None:
                    return json.dumps({"error": f"Window not found: {window_title}"})
                img = pyautogui.screenshot(region=rect)
            elif region:
                parts = [int(x.strip()) for x in region.split(",")]
                if len(parts) != 4:
                    return json.dumps({"error": "Region must be x,y,w,h"})
                img = pyautogui.screenshot(region=tuple(parts))
            else:
                img = pyautogui.screenshot()

            orig_w, orig_h = img.size
            if orig_w > max_width:
                ratio = max_width / orig_w
                img = img.resize((max_width, int(orig_h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            if save_path:
                img.save(save_path)

            return json.dumps({
                "image_base64": b64,
                "format": "jpeg",
                "original_size": [orig_w, orig_h],
                "captured_size": list(img.size),
                "bytes": len(buf.getvalue()),
                "saved_to": save_path or None,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_screen_ocr(
        window_title: str = "",
        region: str = "",
        language: str = "eng",
    ) -> str:
        """Screenshot + OCR in one call. Returns extracted text.

        window_title or region to scope. Auto-detects dark themes and inverts
        for better OCR accuracy. Requires pytesseract + Tesseract binary.
        """
        import pyautogui

        try:
            import pytesseract
        except ImportError:
            return json.dumps({"error": "pytesseract not installed. pip install pytesseract"})

        try:
            if window_title:
                rect = _find_window_rect(window_title)
                if rect is None:
                    return json.dumps({"error": f"Window not found: {window_title}"})
                img = pyautogui.screenshot(region=rect)
            elif region:
                parts = [int(x.strip()) for x in region.split(",")]
                img = pyautogui.screenshot(region=tuple(parts))
            else:
                img = pyautogui.screenshot()

            from PIL import ImageStat, ImageOps
            stat = ImageStat.Stat(img.convert("L"))
            dark = stat.mean[0] < 128
            ocr_img = ImageOps.invert(img.convert("RGB")) if dark else img

            text = pytesseract.image_to_string(ocr_img, lang=language)
            return json.dumps({
                "text": text.strip(),
                "lines": len([l for l in text.strip().split("\n") if l.strip()]),
                "dark_theme_detected": dark,
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_find_text_on_screen(
        search_text: str,
        window_title: str = "",
        click: bool = False,
        language: str = "eng",
    ) -> str:
        """Find text on screen via OCR and return coordinates. Optionally click it.

        search_text = case-insensitive substring. window_title scopes the search.
        click=True clicks center of found text. Returns absolute screen coordinates.
        """
        import pyautogui

        try:
            import pytesseract
        except ImportError:
            return json.dumps({"error": "pytesseract not installed"})

        try:
            offset_x, offset_y = 0, 0
            if window_title:
                rect = _find_window_rect(window_title)
                if rect is None:
                    return json.dumps({"error": f"Window not found: {window_title}"})
                img = pyautogui.screenshot(region=rect)
                offset_x, offset_y = rect[0], rect[1]
            else:
                img = pyautogui.screenshot()

            from PIL import ImageStat, ImageOps
            stat = ImageStat.Stat(img.convert("L"))
            ocr_img = ImageOps.invert(img.convert("RGB")) if stat.mean[0] < 128 else img

            data = pytesseract.image_to_data(ocr_img, lang=language, output_type=pytesseract.Output.DICT)

            search_lower = search_text.lower()
            matches = []
            for i, word in enumerate(data["text"]):
                if search_lower in word.lower():
                    x = data["left"][i] + offset_x
                    y = data["top"][i] + offset_y
                    w = data["width"][i]
                    h = data["height"][i]
                    cx, cy = x + w // 2, y + h // 2
                    matches.append({"text": word, "x": x, "y": y, "w": w, "h": h,
                                    "center_x": cx, "center_y": cy})

            if not matches:
                full_text = " ".join(data["text"]).lower()
                if search_lower in full_text:
                    idx = full_text.find(search_lower)
                    char_count = 0
                    for i, word in enumerate(data["text"]):
                        char_count += len(word) + 1
                        if char_count > idx and data["width"][i] > 0:
                            x = data["left"][i] + offset_x
                            y = data["top"][i] + offset_y
                            w = data["width"][i]
                            h = data["height"][i]
                            cx, cy = x + w // 2, y + h // 2
                            matches.append({"text": search_text, "x": x, "y": y,
                                            "w": w, "h": h, "center_x": cx, "center_y": cy})
                            break

            if not matches:
                return json.dumps({"found": False, "search": search_text})

            result = {"found": True, "matches": matches, "count": len(matches)}

            if click and matches:
                m = matches[0]
                pyautogui.click(m["center_x"], m["center_y"])
                result["clicked"] = {"x": m["center_x"], "y": m["center_y"]}

            return json.dumps(result)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_screen_region(
        x: int, y: int, width: int, height: int,
        max_width: int = 1024,
        quality: int = 80,
    ) -> str:
        """Capture a specific screen region. Returns compressed base64 JPEG.

        Useful for zooming into UI elements, error dialogs, etc.
        """
        import pyautogui
        from PIL import Image

        try:
            img = pyautogui.screenshot(region=(x, y, width, height))
            orig_w, orig_h = img.size
            if orig_w > max_width:
                ratio = max_width / orig_w
                img = img.resize((max_width, int(orig_h * ratio)), Image.LANCZOS)

            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            return json.dumps({
                "image_base64": b64,
                "format": "jpeg",
                "region": [x, y, width, height],
                "captured_size": list(img.size),
                "bytes": len(buf.getvalue()),
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_list_windows(include_hidden: bool = False) -> str:
        """List all visible windows with title, process, position, and size.

        Enhanced version of desktop_state with process info.
        """
        try:
            from pywinauto import Desktop
            import psutil
        except ImportError:
            return json.dumps({"error": "pywinauto or psutil not installed"})

        try:
            desktop = Desktop(backend="uia")
            windows = []
            for w in desktop.windows():
                try:
                    if not include_hidden and not w.is_visible():
                        continue
                    title = w.window_text()
                    if not title:
                        continue
                    rect = w.rectangle()
                    pid = w.process_id()
                    proc_name = ""
                    try:
                        proc_name = psutil.Process(pid).name()
                    except Exception:
                        pass
                    windows.append({
                        "title": title,
                        "process": proc_name,
                        "pid": pid,
                        "left": rect.left,
                        "top": rect.top,
                        "width": rect.width(),
                        "height": rect.height(),
                        "visible": w.is_visible(),
                    })
                except Exception:
                    continue
            return json.dumps(windows, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
