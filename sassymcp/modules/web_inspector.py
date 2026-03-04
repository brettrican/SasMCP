"""WebInspector - URL-level analysis and inspection tools.

Screenshot URLs, analyze security headers, check accessibility,
and audit performance without needing a browser open.

Dependencies: httpx (for async HTTP), playwright (optional for screenshots).
Falls back to urllib if httpx unavailable, Chrome CLI if playwright unavailable.
"""

import json
import subprocess
import tempfile
from pathlib import Path


def register(server):

    @server.tool()
    async def sassy_url_headers(url: str, follow_redirects: bool = True) -> str:
        """Fetch and analyze HTTP security headers for a URL.

        Checks HSTS, CSP, X-Frame-Options, X-Content-Type-Options,
        Referrer-Policy, Permissions-Policy, COOP, CORP, X-XSS-Protection.
        Returns a security grade (A+ to F) and recommendations.
        """
        try:
            import httpx
        except ImportError:
            import urllib.request
            try:
                req = urllib.request.Request(url, method="HEAD")
                req.add_header("User-Agent", "SassyMCP-WebInspector/1.0")
                resp = urllib.request.urlopen(req, timeout=10)
                headers = dict(resp.headers)
                status = resp.status
            except Exception as e:
                return json.dumps({"error": str(e)})
        else:
            try:
                async with httpx.AsyncClient(follow_redirects=follow_redirects, timeout=15) as client:
                    resp = await client.head(url, headers={"User-Agent": "SassyMCP-WebInspector/1.0"})
                    headers = dict(resp.headers)
                    status = resp.status_code
            except Exception as e:
                return json.dumps({"error": str(e)})

        checks = {
            "strict-transport-security": {"present": False, "header": "HSTS", "severity": "high"},
            "content-security-policy": {"present": False, "header": "CSP", "severity": "high"},
            "x-frame-options": {"present": False, "header": "X-Frame-Options", "severity": "medium"},
            "x-content-type-options": {"present": False, "header": "X-Content-Type-Options", "severity": "medium"},
            "referrer-policy": {"present": False, "header": "Referrer-Policy", "severity": "medium"},
            "permissions-policy": {"present": False, "header": "Permissions-Policy", "severity": "low"},
            "x-xss-protection": {"present": False, "header": "X-XSS-Protection", "severity": "low"},
            "cross-origin-opener-policy": {"present": False, "header": "COOP", "severity": "low"},
            "cross-origin-resource-policy": {"present": False, "header": "CORP", "severity": "low"},
        }

        headers_lower = {k.lower(): v for k, v in headers.items()}
        for key, check in checks.items():
            if key in headers_lower:
                check["present"] = True
                check["value"] = headers_lower[key]

        total = len(checks)
        present = sum(1 for c in checks.values() if c["present"])
        high_missing = [c["header"] for c in checks.values() if not c["present"] and c["severity"] == "high"]
        medium_missing = [c["header"] for c in checks.values() if not c["present"] and c["severity"] == "medium"]

        if present == total: grade = "A+"
        elif present >= total - 1 and not high_missing: grade = "A"
        elif not high_missing: grade = "B"
        elif len(high_missing) == 1: grade = "C"
        else: grade = "D" if present > 2 else "F"

        recommendations = []
        if "HSTS" in high_missing:
            recommendations.append("Add Strict-Transport-Security header (max-age=31536000; includeSubDomains)")
        if "CSP" in high_missing:
            recommendations.append("Add Content-Security-Policy header to prevent XSS")
        for h in medium_missing:
            recommendations.append(f"Add {h} header")

        leaks = {}
        for lh in ["server", "x-powered-by", "x-aspnet-version", "x-generator"]:
            if lh in headers_lower:
                leaks[lh] = headers_lower[lh]
        if leaks:
            recommendations.append(f"Remove server info headers: {', '.join(leaks.keys())}")

        return json.dumps({
            "url": url, "status": status, "grade": grade, "score": f"{present}/{total}",
            "headers": {c["header"]: {"present": c["present"], "value": c.get("value"), "severity": c["severity"]} for c in checks.values()},
            "server_leaks": leaks or None, "recommendations": recommendations,
        }, indent=2)

    @server.tool()
    async def sassy_url_screenshot(url: str, width: int = 1280, height: int = 720, full_page: bool = False, save_path: str = "") -> str:
        """Screenshot a URL via headless Chrome or Playwright. Returns base64 JPEG."""
        import base64, io
        save = save_path or str(Path(tempfile.gettempdir()) / "sassymcp_url_screenshot.png")

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.screenshot(path=save, full_page=full_page)
                browser.close()
            from PIL import Image
            img = Image.open(save)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=75, optimize=True)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return json.dumps({"image_base64": b64, "format": "jpeg", "size": list(img.size), "bytes": len(buf.getvalue()), "saved_to": save, "method": "playwright"})
        except ImportError: pass
        except Exception: pass

        try:
            chrome_paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe", "chrome", "chromium"]
            chrome = None
            for cp in chrome_paths:
                try:
                    subprocess.run([cp, "--version"], capture_output=True, timeout=5)
                    chrome = cp
                    break
                except Exception: continue
            if not chrome:
                return json.dumps({"error": "No Chrome/Chromium found. Install Playwright or Chrome."})
            cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox", f"--window-size={width},{height}", f"--screenshot={save}", url]
            subprocess.run(cmd, capture_output=True, timeout=30)
            if Path(save).exists():
                from PIL import Image
                img = Image.open(save)
                buf = io.BytesIO()
                img.convert("RGB").save(buf, format="JPEG", quality=75, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                return json.dumps({"image_base64": b64, "format": "jpeg", "size": list(img.size), "bytes": len(buf.getvalue()), "saved_to": save, "method": "chrome-headless"})
            return json.dumps({"error": "Chrome screenshot failed"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_url_tech_stack(url: str) -> str:
        """Detect technology stack from HTTP headers and HTML (CDN, CMS, framework, analytics)."""
        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(url, headers={"User-Agent": "SassyMCP-WebInspector/1.0"})
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.text[:50000]
        except ImportError:
            import urllib.request
            req = urllib.request.Request(url); req.add_header("User-Agent", "SassyMCP-WebInspector/1.0")
            resp = urllib.request.urlopen(req, timeout=15)
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read(50000).decode("utf-8", errors="replace")

        d = {}
        if "server" in headers: d["server"] = headers["server"]
        if "cf-ray" in headers or "cf-cache-status" in headers: d["cdn"] = "Cloudflare"
        elif "x-vercel" in headers or "x-vercel-id" in headers: d["cdn"] = "Vercel"
        elif "x-netlify" in headers: d["cdn"] = "Netlify"
        bl = body.lower()
        if "wp-content" in bl: d["cms"] = "WordPress"
        elif "shopify" in bl: d["cms"] = "Shopify"
        if "__next" in bl or "_next/static" in bl: d["framework"] = "Next.js"
        elif "__nuxt" in bl: d["framework"] = "Nuxt.js"
        elif "ng-version" in bl: d["framework"] = "Angular"
        analytics = []
        if "google-analytics.com" in bl or "gtag" in bl: analytics.append("Google Analytics")
        if "cloudflareinsights.com" in bl: analytics.append("Cloudflare Web Analytics")
        if "plausible.io" in bl: analytics.append("Plausible")
        if analytics: d["analytics"] = analytics
        if "x-powered-by" in headers: d["x_powered_by"] = headers["x-powered-by"]
        if "strict-transport-security" in headers: d["hsts"] = True
        return json.dumps({"url": url, "detected": d}, indent=2)

    @server.tool()
    async def sassy_url_links(url: str, external_only: bool = False) -> str:
        """Extract all links from a URL. Useful for site auditing and SEO."""
        from urllib.parse import urlparse, urljoin
        import re
        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(url, headers={"User-Agent": "SassyMCP-WebInspector/1.0"})
                body = resp.text
        except ImportError:
            import urllib.request
            req = urllib.request.Request(url); req.add_header("User-Agent", "SassyMCP-WebInspector/1.0")
            body = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")

        matches = re.findall(r'href=["\']([^"\']+)["\']', body, re.IGNORECASE)
        base_domain = urlparse(url).netloc.lower()
        links = {"internal": [], "external": [], "resources": [], "anchors": []}
        seen = set()
        for href in matches:
            if href in seen: continue
            seen.add(href)
            if href.startswith("#"): links["anchors"].append(href); continue
            if href.startswith(("mailto:", "tel:")): continue
            full = urljoin(url, href); parsed = urlparse(full)
            if parsed.path.endswith((".css",".js",".png",".jpg",".svg",".ico",".woff",".woff2")): links["resources"].append(full)
            elif parsed.netloc.lower() == base_domain or not parsed.netloc: links["internal"].append(full)
            else: links["external"].append(full)
        result = {"url": url, "total_links": len(links["internal"]) + len(links["external"]), "internal": len(links["internal"]), "external": len(links["external"]), "resources": len(links["resources"])}
        result["links"] = links["external"] if external_only else links
        return json.dumps(result, indent=2)

    @server.tool()
    async def sassy_url_performance(url: str) -> str:
        """Quick performance check: response time, page size, compression, caching."""
        import time as t, re
        try:
            import httpx
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                start = t.monotonic()
                resp = await client.get(url, headers={"User-Agent": "SassyMCP-WebInspector/1.0"})
                elapsed = t.monotonic() - start
                headers = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.content
        except ImportError:
            import urllib.request
            req = urllib.request.Request(url); req.add_header("User-Agent", "SassyMCP-WebInspector/1.0")
            start = t.monotonic()
            resp = urllib.request.urlopen(req, timeout=30)
            elapsed = t.monotonic() - start
            headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read()
        return json.dumps({
            "url": url, "response_time_ms": round(elapsed * 1000),
            "page_size_bytes": len(body), "page_size_kb": round(len(body) / 1024, 1),
            "compressed": "content-encoding" in headers,
            "compression": headers.get("content-encoding", "none"),
            "cache_control": headers.get("cache-control", "none"),
            "external_resources": len(re.findall(r'(?:src|href)=["\']https?://', body.decode("utf-8", errors="replace"))),
            "content_type": headers.get("content-type", "unknown"),
        }, indent=2)
