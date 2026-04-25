```json
{
  "severity": "critical",
  "category": "SECURITY",
  "file": "sassymcp/modules/_security.py",
  "symbol": "validate_url",
  "issue": "SSR​F protection only checks literal IPs and a few hard‑coded hostnames; DNS names are never resolved, allowing SSRF via DNS rebinding or internal hostnames.",
  "why": "An attacker‑controlled URL can resolve to a private/internal address after DNS rebinding, letting the server reach internal services (e.g., metadata endpoint) and exfiltrate data.",
  "fix": "Resolve the hostname to an IP (using socket.getaddrinfo) and apply the private‑range check on the resolved address; also reject hostnames that resolve to loopback or link‑local ranges.",
  "confidence": 0.96
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/_security.py",
  "symbol": "validate_path",
  "issue": "When `allowedDirectories` is empty or mis‑configured, `validate_path` permits any path, effectively disabling path restrictions.",
  "why": "Tools like `sassy_read_file`, `sassy_write_file`, `sassy_move`, etc., call `_check_path` which forwards to `validate_path`; an attacker can read/write arbitrary files on the host, leading to data exfiltration or tampering.",
  "fix": "Enforce a default safe directory (e.g., `~/.sassymcp`) when `allowedDirectories` is not set, and log a warning if the config is missing. Reject paths outside this default.",
  "confidence": 0.94
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/adb.py",
  "symbol": "sassy_adb_shell",
  "issue": "Command is passed to `adb shell` after only a substring‑based block list; many destructive commands (e.g., `rm -rf /tmp/*`, `busybox rm -rf /`) bypass the check.",
  "why": "An adversarial LLM can issue destructive commands on the Android device, causing data loss or device bricking.",
  "fix": "Replace `validate_command` with a whitelist of allowed commands or use a proper command parser; additionally, split the command on whitespace and reject any token that matches a destructive pattern before invoking `adb shell`.",
  "confidence": 0.92
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/adb.py",
  "symbol": "sassy_adb_pull",
  "issue": "`local_path` argument is not validated; the tool can write to any location on the host filesystem.",
  "why": "An attacker can pull arbitrary files from the Android device and write them to privileged locations (e.g., `C:\\Windows\\system32\\evil.dll`), achieving arbitrary file write on the host.",
  "fix": "Validate `local_path` with `validate_path` (or a dedicated safe‑path check) and restrict it to a user‑writable directory, e.g., `~/.sassymcp/adb/`.",
  "confidence": 0.9
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/adb.py",
  "symbol": "sassy_adb_push",
  "issue": "`local_path` argument is not validated; the tool can read any file on the host and push it to the Android device.",
  "why": "Allows exfiltration of arbitrary host files (e.g., password stores) to the Android device, where they could be later retrieved.",
  "fix": "Validate `local_path` with `validate_path` and restrict to a safe directory; optionally limit file size.",
  "confidence": 0.9
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/adb.py",
  "symbol": "sassy_adb_install",
  "issue": "`apk_path` is not validated; arbitrary files can be installed on the Android device.",
  "why": "An attacker could install a malicious APK that gains elevated privileges on the device, leading to full device compromise.",
  "fix": "Validate `apk_path` with `validate_path` and enforce that it points to a `.apk` file; optionally scan the APK hash against a whitelist.",
  "confidence": 0.88
}
{
  "severity": "medium",
  "category": "RESOURCE",
  "file": "sassymcp/modules/fileops.py",
  "symbol": "sassy_read_file",
  "issue": "Reads the entire file into memory without any size limit.",
  "why": "A large file (e.g., multi‑GB log) can exhaust the server’s memory, causing denial‑of‑service.",
  "fix": "Add a configurable `max_bytes` limit (e.g., 10 MB) and stream the file in chunks if larger, returning a truncated preview.",
  "confidence": 0.94
}
{
  "severity": "medium",
  "category": "RESOURCE",
  "file": "sassymcp/modules/fileops.py",
  "symbol": "sassy_read_multiple",
  "issue": "Accepts an arbitrary list of paths and reads each file fully into memory.",
  "why": "A malicious request can cause massive memory consumption and I/O load, leading to DoS.",
  "fix": "Enforce a maximum number of files (e.g., 20) and a per‑file size cap; read files incrementally and truncate output.",
  "confidence": 0.92
}
{
  "severity": "medium",
  "category": "RESOURCE",
  "file": "sassymcp/modules/fileops.py",
  "symbol": "sassy_write_file",
  "issue": "Writes arbitrary `content` without size validation.",
  "why": "An attacker can fill the host disk with large payloads, causing storage exhaustion.",
  "fix": "Introduce a `max_input_size` check (reuse `validate_input_size`) and reject writes exceeding the limit.",
  "confidence": 0.9
}
{
  "severity": "high",
  "category": "SECURITY",
  "file": "sassymcp/modules/crosslink.py",
  "symbol": "register",
  "issue": "HTTP server runs on plain HTTP without TLS and defaults to binding 0.0.0.0 with no authentication when `SASSYMCP_CROSSLINK_TOKEN` is unset.",
  "why": "Anyone on the LAN can connect to the cross‑link API, read/write messages, and potentially inject malicious payloads or exfiltrate data.",
  "fix": "Require a token for any non‑localhost bind; default bind to 127.0.0.1 when no token is provided; optionally enable HTTPS (e.g., via `ssl` module).",
  "confidence": 0.95
}
{
  "severity": "high",
  "category": "CONCURRENCY",
  "file": "sassymcp/modules/crosslink.py",
  "symbol": "_read_messages",
  "issue": "SQLite connections are opened per request with `check_same_thread=False` but no locking; concurrent reads/writes can corrupt the DB or raise `sqlite3.OperationalError`.",
  "why": "Multiple LLM tool calls may invoke cross‑link read/write simultaneously, causing race conditions and possible data loss.",
  "fix": "Use a single thread‑safe SQLite connection with a `threading.Lock` around all DB operations, or switch to `aiosqlite` for async‑compatible access.",
  "confidence": 0.88
}
{
  "severity": "medium",
  "category": "SECURITY",
  "file": "sassymcp/modules/audit.py",
  "symbol": "log_tool_call",
  "issue": "Sanitizes arguments by truncating but does not redact secrets; tokens or passwords passed as arguments can be written to the audit log.",
  "why": "Audit logs are stored on disk and may be readable by other users; leaking secrets compromises credential confidentiality.",
  "fix": "Add a configurable list of secret‑key patterns (e.g., `*_TOKEN`, `*_SECRET`, `password`) and replace their values with `<redacted>` before logging.",
  "confidence": 0.9
}
{
  "severity": "medium",
  "category": "SECURITY",
  "file": "sassymcp/modules/_security.py",
  "symbol": "validate_url",
  "issue": "Allows URLs with unusually long hostnames or excessive path length without size limits.",
  "why": "An attacker could craft extremely long URLs that cause memory exhaustion when logged or processed, leading to DoS.",
  "fix": "Enforce a reasonable maximum length (e.g., 2048 characters) and reject URLs exceeding it.",
  "confidence": 0.85
}
{
  "severity": "low",
  "category": "CONCURRENCY",
  "file": "sassymcp/modules/_rate_limiter.py",
  "symbol": "GroupRateLimiter.acquire",
  "issue": "If `bucket.acquire()` returns `False` after a semaphore has been acquired, the semaphore is released, but the code does not handle the case where `bucket` is `None` and `sem` is not; potential double‑release if `bucket` is `None` and `sem` already released elsewhere.",
  "why": "Incorrect semaphore handling could lead to `ValueError: Semaphore released too many times`, breaking rate‑limiting logic.",
  "fix": "Guard the release with `if sem is not None and isinstance(sem, asyncio.BoundedSemaphore):` (already present) but also ensure that the release only happens when the semaphore was actually acquired; track acquisition state with a flag.",
  "confidence": 0.78
}
{
  "severity": "low",
  "category": "API",
  "file": "sassymcp/modules/observability.py",
  "symbol": "sassy_observability_metrics",
  "issue": "Declared as `async` but returns a plain `dict`; the server may serialize it automatically, but the async signature is unnecessary.",
  "why": "Unnecessary async overhead and potential confusion for future maintainers.",
  "fix": "Remove `async` and make it a regular function, or explicitly `return json.dumps(obs.get_metrics())` if a string is expected.",
  "confidence": 0.85
}
```

**Top 5 things to fix before release**

1. **SSR​F protection** – `validate_url` must resolve hostnames and reject private/internal IPs after DNS resolution; otherwise an attacker can reach internal services.  
2. **Unrestricted file access** – When `allowedDirectories` is empty, all path‑based tools accept any path. Enforce a safe default directory and log a warning if the config is missing.  
3. **ADB command injection** – `sassy_adb_shell` (and related ADB tools) only use a substring block list; many destructive commands bypass it. Switch to a whitelist or a proper command parser and validate every token.  
4. **Cross‑link server exposure** – The HTTP server defaults to `0.0.0.0` without TLS and without authentication when no token is set. Require a token for any non‑localhost bind and consider HTTPS.  
5. **Audit‑log secret leakage** – `log_tool_call` truncates arguments but never redacts secrets. Add secret‑field detection and replace values with `<redacted>` before writing to the log.

**Release‑readiness verdict:** **hold** – critical security issues (SSRF, unrestricted file access, ADB injection, unauthenticated cross‑link server) must be addressed before the installer can be shipped safely.