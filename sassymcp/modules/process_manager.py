"""ProcessManager - Windows + Android process control."""

import asyncio
import json

def register(server):
    @server.tool()
    async def sassy_processes(filter_str: str = "", sort_by: str = "cpu") -> str:
        """List running processes. sort_by: cpu, memory, name."""
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                if filter_str and filter_str.lower() not in info["name"].lower(): continue
                procs.append({"pid": info["pid"], "name": info["name"],
                    "cpu": info["cpu_percent"] or 0,
                    "mem_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / 1048576, 1)})
            except Exception: continue
        key = {"cpu": "cpu", "memory": "mem_mb", "name": "name"}.get(sort_by, "cpu")
        procs.sort(key=lambda x: x[key], reverse=(key != "name"))
        return json.dumps(procs[:50], indent=2)

    @server.tool()
    async def sassy_kill_process(pid: int, force: bool = False) -> str:
        """Kill a process by PID."""
        import psutil
        try:
            p = psutil.Process(pid)
            name = p.name()
            p.kill() if force else p.terminate()
            return f"Terminated {name} (PID: {pid})"
        except psutil.NoSuchProcess:
            return f"Error: No process with PID {pid}"
        except psutil.AccessDenied:
            return f"Error: Access denied to kill PID {pid}"
        except Exception as e:
            return f"Error: {e}"

    @server.tool()
    async def sassy_android_processes(device: str = "") -> str:
        """List running processes on Android device."""
        args = ["adb"] + (["-s", device] if device else []) + ["shell", "ps -A -o PID,NAME,%CPU,RSS"]
        try:
            proc = await asyncio.create_subprocess_exec(
                *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            return stdout.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return "Timed out after 15s"
        except FileNotFoundError:
            return "Error: adb not found"
        except Exception as e:
            return f"Error: {e}"

    @server.tool()
    async def sassy_system_info() -> str:
        """Get system resource summary."""
        import psutil
        import platform
        import sys
        import time
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk_path = "C:\\" if sys.platform == "win32" else "/"
        disk = psutil.disk_usage(disk_path)
        uptime = time.time() - psutil.boot_time()
        return json.dumps({
            "hostname": platform.node(), "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": cpu, "cpu_cores": psutil.cpu_count(),
            "ram_total_gb": round(mem.total / 1073741824, 1),
            "ram_used_gb": round(mem.used / 1073741824, 1),
            "ram_percent": mem.percent,
            "disk_total_gb": round(disk.total / 1073741824, 1),
            "disk_percent": disk.percent,
            "uptime": f"{int(uptime//3600)}h {int((uptime%3600)//60)}m",
        }, indent=2)
