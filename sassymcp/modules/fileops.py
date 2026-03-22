"""FileOps - Fast file I/O operations."""

import shutil
import re
import json
from pathlib import Path
def register(server):
    @server.tool()
    async def sassy_read_file(path: str, offset: int = 0, length: int = 1000) -> str:
        """Read file contents. offset/length for line-based pagination.
        Negative offset reads from end (e.g. offset=-20 = last 20 lines)."""
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if offset < 0:
            selected = lines[offset:]
        else:
            selected = lines[offset:offset + length]
        return "\n".join(selected)

    @server.tool()
    async def sassy_write_file(path: str, content: str, mode: str = "rewrite") -> str:
        """Write or append to a file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with open(p, "a", encoding="utf-8") as f:
                f.write(content)
        else:
            p.write_text(content, encoding="utf-8")
        return f"Written to {path} ({mode})"

    @server.tool()
    async def sassy_list_dir(path: str, depth: int = 2) -> str:
        """List directory contents with [FILE]/[DIR] prefixes."""
        results = []
        p = Path(path)
        if not p.is_dir():
            return f"Error: {path} is not a directory"
        def _walk(current, d, prefix=""):
            if d > depth: return
            try:
                entries = sorted(current.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                results.append(f"[DENIED] {prefix}{current.name}"); return
            for entry in entries[:100]:
                rel = f"{prefix}{entry.name}"
                if entry.is_dir():
                    results.append(f"[DIR] {rel}"); _walk(entry, d + 1, f"{rel}/")
                else:
                    results.append(f"[FILE] {rel}")
        _walk(p, 1)
        return "\n".join(results[:500])

    @server.tool()
    async def sassy_search_files(path: str, pattern: str, search_type: str = "files") -> str:
        """Search for files by name or content."""
        results = []
        p = Path(path)
        if search_type == "files":
            for match in p.rglob(f"*{pattern}*"):
                results.append(str(match))
                if len(results) >= 50: break
        else:
            pat = re.compile(pattern, re.IGNORECASE)
            for fpath in p.rglob("*"):
                if fpath.is_file() and fpath.stat().st_size < 5_000_000:
                    try:
                        for i, line in enumerate(fpath.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                            if pat.search(line):
                                results.append(f"{fpath}:{i}: {line.strip()[:200]}")
                                if len(results) >= 50: return "\n".join(results)
                    except Exception: continue
        return "\n".join(results) if results else "No matches found"

    @server.tool()
    async def sassy_move(source: str, destination: str) -> str:
        """Move or rename a file/directory."""
        shutil.move(source, destination)
        return f"Moved {source} -> {destination}"

    @server.tool()
    async def sassy_copy(source: str, destination: str) -> str:
        """Copy a file or directory."""
        (shutil.copytree if Path(source).is_dir() else shutil.copy2)(source, destination)
        return f"Copied {source} -> {destination}"

    @server.tool()
    async def sassy_file_info(path: str) -> str:
        """Get file/directory metadata."""
        p = Path(path)
        if not p.exists(): return f"Error: {path} does not exist"
        stat = p.stat()
        info = {"path": str(p.resolve()), "type": "directory" if p.is_dir() else "file",
                "size_bytes": stat.st_size, "modified": stat.st_mtime, "created": stat.st_ctime}
        if p.is_file():
            with open(p, encoding="utf-8", errors="replace") as f:
                info["lines"] = sum(1 for _ in f)
        return json.dumps(info, indent=2)

    @server.tool()
    async def sassy_mkdir(path: str) -> str:
        """Create a directory (and any missing parents)."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return f"Created {p.resolve()}"
