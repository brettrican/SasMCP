"""Crosslink - Cross-session communication for SassyMCP.

Enables different Claude sessions (Desktop, mobile, web) to communicate
through a shared local message queue backed by SQLite.

Architecture:
  - SQLite DB at ~/.sassymcp/crosslink.db
  - HTTP API on localhost:9377 (built-in http.server, no deps)
  - Messages have sender, channel, payload, timestamp
  - Sessions register with ID/name/platform
  - Read tracking per-session
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DB_PATH = Path.home() / ".sassymcp" / "crosslink.db"
DEFAULT_PORT = 9377
_server_thread = None
_server_instance = None


def _ensure_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, channel TEXT DEFAULT 'default', payload TEXT NOT NULL, created_at TEXT NOT NULL, read_by TEXT DEFAULT '')")
    conn.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, name TEXT, platform TEXT, last_seen TEXT, created_at TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_chan ON messages(channel)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_ts ON messages(created_at)")
    conn.commit(); conn.close()


def _post_message(sid, channel, payload):
    _ensure_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.execute("INSERT INTO messages (session_id,channel,payload,created_at) VALUES (?,?,?,?)", (sid, channel, payload, now))
    mid = cur.lastrowid; conn.commit(); conn.close()
    return {"id": mid, "session_id": sid, "channel": channel, "created_at": now}


def _read_messages(sid, channel="default", limit=20, unread_only=True, since=""):
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    q, p = "SELECT * FROM messages WHERE channel=?", [channel]
    if unread_only: q += " AND read_by NOT LIKE ?"; p.append(f"%{sid}%")
    if since: q += " AND created_at>?"; p.append(since)
    q += " ORDER BY created_at DESC LIMIT ?"; p.append(limit)
    rows = conn.execute(q, p).fetchall(); msgs = [dict(r) for r in rows]
    for m in msgs:
        rb = m.get("read_by", "")
        if sid not in rb:
            conn.execute("UPDATE messages SET read_by=? WHERE id=?", (f"{rb},{sid}" if rb else sid, m["id"]))
    conn.commit(); conn.close()
    return msgs


def _register_session(sid, name="", platform=""):
    _ensure_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("INSERT INTO sessions (session_id,name,platform,last_seen,created_at) VALUES (?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET last_seen=?,name=COALESCE(?,name)", (sid, name, platform, now, now, now, name or None))
    conn.commit(); conn.close()
    return {"session_id": sid, "name": name, "platform": platform, "last_seen": now}


def _list_sessions():
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM sessions ORDER BY last_seen DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers(); self.wfile.write(json.dumps(data).encode())
    def do_OPTIONS(self):
        self.send_response(200)
        for h, v in [("Access-Control-Allow-Origin","*"),("Access-Control-Allow-Methods","GET,POST,OPTIONS"),("Access-Control-Allow-Headers","Content-Type")]: self.send_header(h, v)
        self.end_headers()
    def do_GET(self):
        p = urlparse(self.path); qs = parse_qs(p.query)
        if p.path == "/health": self._json({"status": "ok", "service": "sassymcp-crosslink"})
        elif p.path == "/sessions": self._json({"sessions": _list_sessions()})
        elif p.path == "/messages":
            self._json({"messages": _read_messages(qs.get("session_id",["anon"])[0], qs.get("channel",["default"])[0], int(qs.get("limit",["20"])[0]), qs.get("unread",["true"])[0]=="true", qs.get("since",[""])[0]), "count": 0})
        else: self._json({"error": "Not found"}, 404)
    def do_POST(self):
        p = urlparse(self.path); body = json.loads(self.rfile.read(int(self.headers.get("Content-Length",0)))) if int(self.headers.get("Content-Length",0)) else {}
        if p.path == "/messages":
            if not body.get("payload"): self._json({"error": "payload required"}, 400); return
            self._json(_post_message(body.get("session_id","anon"), body.get("channel","default"), body["payload"]), 201)
        elif p.path == "/sessions": self._json(_register_session(body.get("session_id",uuid.uuid4().hex[:8]), body.get("name",""), body.get("platform","")), 201)
        else: self._json({"error": "Not found"}, 404)


def register(server):

    @server.tool()
    async def sassy_crosslink_start(port: int = DEFAULT_PORT) -> str:
        """Start the Crosslink HTTP API on localhost:{port}.

        Endpoints: GET /health, GET/POST /sessions, GET/POST /messages.
        Enables cross-session communication between Claude Desktop/mobile/web.
        """
        global _server_thread, _server_instance
        if _server_instance is not None:
            return json.dumps({"status": "already_running", "port": port})
        _ensure_db()
        try:
            _server_instance = HTTPServer(("127.0.0.1", port), _Handler)
            _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
            _server_thread.start()
            return json.dumps({"status": "started", "port": port, "url": f"http://127.0.0.1:{port}", "db": str(DB_PATH)})
        except Exception as e:
            _server_instance = None; return json.dumps({"error": str(e)})

    @server.tool()
    async def sassy_crosslink_stop() -> str:
        """Stop the Crosslink HTTP API server."""
        global _server_thread, _server_instance
        if _server_instance is None: return json.dumps({"status": "not_running"})
        _server_instance.shutdown(); _server_instance = None; _server_thread = None
        return json.dumps({"status": "stopped"})

    @server.tool()
    async def sassy_crosslink_send(payload: str, channel: str = "default", session_id: str = "") -> str:
        """Send a message to the crosslink queue. payload=content, channel=topic, session_id=sender."""
        if not session_id: session_id = f"sassymcp-{uuid.uuid4().hex[:6]}"
        return json.dumps(_post_message(session_id, channel, payload))

    @server.tool()
    async def sassy_crosslink_recv(session_id: str = "sassymcp", channel: str = "default", limit: int = 20, unread_only: bool = True) -> str:
        """Read messages from the crosslink queue. Marks them as read for this session."""
        msgs = _read_messages(session_id, channel, limit, unread_only)
        return json.dumps({"messages": msgs, "count": len(msgs)})

    @server.tool()
    async def sassy_crosslink_status() -> str:
        """Check crosslink status: server running, sessions, message counts, channels."""
        _ensure_db()
        conn = sqlite3.connect(str(DB_PATH))
        total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        channels = [r[0] for r in conn.execute("SELECT DISTINCT channel FROM messages").fetchall()]
        conn.close()
        return json.dumps({"server_running": _server_instance is not None, "port": DEFAULT_PORT if _server_instance else None, "db": str(DB_PATH), "total_messages": total, "channels": channels, "sessions": _list_sessions()}, indent=2)

    @server.tool()
    async def sassy_crosslink_register(session_id: str = "", name: str = "", platform: str = "") -> str:
        """Register a session. session_id auto-generated if empty. name/platform for identification."""
        if not session_id: session_id = f"session-{uuid.uuid4().hex[:8]}"
        return json.dumps(_register_session(session_id, name, platform))

    @server.tool()
    async def sassy_crosslink_broadcast(payload: str, session_id: str = "sassymcp") -> str:
        """Broadcast a message to ALL known channels."""
        _ensure_db()
        conn = sqlite3.connect(str(DB_PATH))
        channels = [r[0] for r in conn.execute("SELECT DISTINCT channel FROM messages").fetchall()]
        conn.close()
        if not channels: channels = ["default"]
        results = [_post_message(session_id, ch, payload) for ch in channels]
        return json.dumps({"broadcast_to": channels, "results": results})
