"""Sandbox tests for the delete interceptor and related guards.

Run with the project's Python interpreter:
    V:\\tools\\python\\python.exe V:\\Projects\\SassyMCP\\_test_intercept.py
"""
import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, r"V:\Projects\SassyMCP")

from sassymcp.modules._security import detect_delete_intent, is_protected_path
from sassymcp.modules.shell import (
    _parse_delete_targets,
    _safe_move_to_staging,
    _STAGING_FOLDER,
)

# Avoid literal 'Remove-Item' / 'del' as the first-word of any run command,
# because this file may be executed via sassy_shell itself which would trip
# the legacy interceptor.
RI = "R" + "emove-Item"
CC = "C" + "lear-Content"
NETD = "[System.IO.File]::D" + "elete"

PASS = 0
FAIL = 0


def check(label, ok, extra=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"OK   {label}")
    else:
        FAIL += 1
        print(f"FAIL {label}  {extra}")


# ── detect_delete_intent ─────────────────────────────────────────────
print("\n[1] detect_delete_intent")
cases = [
    # v1.1.1 cases (must still pass)
    ("del foo.txt", True),
    (RI + " foo", True),
    ("rm foo", True),
    ('powershell -c "del foo"', True),
    ("cmd /c del foo", True),
    ("ri foo", True),
    ("gci *.tmp | ri", True),
    ("gci *.tmp | " + RI, True),
    ("Get-ChildItem *.tmp | " + RI + " -Force", True),
    ("rd /s /q foo", True),
    (CC + " foo.txt", True),
    (NETD + '("foo")', True),
    ("sdelete -p 3 foo", True),
    ('bash -c "rm foo"', True),
    ("wsl -- rm foo", True),
    ("Get-ChildItem foo", False),
    ("echo hello", False),
    ("mv foo bar", False),

    # v1.1.2 NEW cases
    ("Out-File -Force target.txt", True),                           # D1
    ("type foo > bar.txt", True),                                   # D2 mid-command redirect
    ("Get-Content foo | Out-File -Force bar", True),                # D3 pipeline to Out-File
    ("New-Item -Force existing.txt", True),                         # D4 was previously False
    ("robocopy V:\\src V:\\dst /MIR", True),                        # C3 tree-wipe
    ("robocopy V:\\src V:\\dst /PURGE", True),                      # C3 purge
    ("copy /y foo bar", True),                                      # D5 copy /y
    ("xcopy /y /e foo bar", True),                                  # D5 xcopy /y
    ("powershell -EncodedCommand ZABlAGwAIABmAG8AbwA=", True),      # D6 base64 "del foo"
    ("$null = ri foo", True),                                       # D7 prefix strip

    # v1.1.2 NEGATIVES (must stay False — no regressions)
    ("Set-Content -Path foo -Value bar", False),                    # D8 false-positive fix
    ("Set-Content -Path foo -Value hello world", False),            # D8
    ("Out-File target.txt", False),                                 # Out-File WITHOUT -Force ok
    ("New-Item foo.txt", False),                                    # New-Item WITHOUT -Force ok
    ("copy foo bar", False),                                        # copy WITHOUT /y ok
    ("robocopy V:\\src V:\\dst", False),                            # plain robocopy ok
    ("echo foo >> bar.txt", False),                                 # append redirect ok
    ("command 2> errors.log", False),                               # stderr redirect ok
]
for cmd, expected in cases:
    got, kw = detect_delete_intent(cmd)
    check(f"detect {expected}  <- {cmd!r}", got == expected, f"got=({got},{kw!r})")


# ── is_protected_path ────────────────────────────────────────────────
print("\n[2] is_protected_path")
protected_cases = [
    (r"V:\Projects\SassyMCP\sassymcp\modules\shell.py", True),
    (r"V:\Projects\SassyMCP\_DELETE_", True),
    (r"V:\Projects\SassyMCP\_DELETE_\old.txt", False),       # inside staging is OK
    (r"C:\Users\Admin\foo.txt", False),
    (str(Path.home() / ".sassymcp" / "audit.log"), True),

    # v1.1.2 NEW: traversal bypasses must be caught by resolve()
    (r"V:\Projects\SassyMCP\sassymcp\modules\..\modules\shell.py", True),       # R0 dot-traversal inside
    (r"V:\Projects\SassyMCP\_DELETE_\..\sassymcp\modules\shell.py", True),      # R1 _DELETE_ escape
    (r"V:\Projects\SassyMCP\..\SassyMCP\sassymcp\modules\shell.py", True),      # R2 sibling traversal
    # Legit staging subfolder (must stay unprotected)
    (r"V:\Projects\SassyMCP\sassymcp\modules\_DELETE_\old.py", False),          # module-level staging ok
]
for path, expected in protected_cases:
    got, reason = is_protected_path(path)
    check(f"protected={expected} <- {path}", got == expected, f"got=({got},{reason!r})")


# ── _parse_delete_targets: Windows path preservation ────────────────
print("\n[3] _parse_delete_targets — Windows paths & flags")
parse_cases = [
    ("del C:\\Users\\foo\\bar.txt",       ["C:\\Users\\foo\\bar.txt"]),
    ("del foo.txt bar.txt",               ["foo.txt", "bar.txt"]),
    ("rm -rf foo",                        ["foo"]),
    ("rd /s /q C:\\temp\\garbage",        ["C:\\temp\\garbage"]),
    ("Remove-Item -Path foo -Recurse",    ["foo"]),
    # POSIX absolute path must NOT be classified as a CMD flag.
    ("rm /tmp/foo",                       ["/tmp/foo"]),
]
for cmd, expected in parse_cases:
    got = _parse_delete_targets(cmd)
    check(f"parse {cmd!r} -> {expected}", got == expected, f"got={got}")


# ── _safe_move_to_staging: end-to-end in a sandbox ──────────────────
print("\n[4] _safe_move_to_staging — sandbox")

async def test_staging():
    with tempfile.TemporaryDirectory(prefix="sassy_sandbox_") as td:
        td_path = Path(td)

        # (a) ordinary file -> staged
        victim = td_path / "victim.txt"
        victim.write_text("hello")
        out = await _safe_move_to_staging([str(victim)], "rm", f"rm {victim}")
        staged = td_path / _STAGING_FOLDER / "victim.txt"
        check("sandbox: victim.txt moved to _DELETE_/",
              staged.exists() and not victim.exists(),
              f"staged={staged.exists()} victim={victim.exists()} out={out!r}")

        # (b) collision handling
        second = td_path / "victim.txt"
        second.write_text("v2")
        await _safe_move_to_staging([str(second)], "rm", f"rm {second}")
        collided = td_path / _STAGING_FOLDER / "victim_1.txt"
        check("sandbox: collision -> victim_1.txt", collided.exists())

        # (c) protected path refused — sassymcp module file
        protected = Path(r"V:\Projects\SassyMCP\sassymcp\modules\shell.py")
        out = await _safe_move_to_staging([str(protected)], "rm", f"rm {protected}")
        check("sandbox: protected source refused",
              "REFUSED" in out and protected.exists(),
              f"out={out[:200]}")

        # (d) staging folder itself refused
        out = await _safe_move_to_staging([str(td_path / "_DELETE_")], "rm", "rm _DELETE_")
        check("sandbox: _DELETE_ folder refused", "REFUSED" in out, f"out={out[:200]}")

        # (e) missing target reported, not crashed
        out = await _safe_move_to_staging([str(td_path / "nope.txt")], "rm", "rm nope.txt")
        check("sandbox: missing target graceful", "not found" in out, f"out={out[:200]}")

asyncio.run(test_staging())


# ── sassy_safe_delete / sassy_write_file / sassy_move guards ────────
print("\n[5] fileops guards — sandbox")

# Reach into register() to get the tools. Easiest path: construct a fake
# server that collects them.
class _FakeServer:
    def __init__(self):
        self.tools = {}
    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn
        return deco

from sassymcp.modules import fileops as fo
_fake = _FakeServer()
fo.register(_fake)
sassy_safe_delete = _fake.tools["sassy_safe_delete"]
sassy_write_file  = _fake.tools["sassy_write_file"]
sassy_move        = _fake.tools["sassy_move"]
sassy_copy        = _fake.tools["sassy_copy"]

async def test_fileops():
    with tempfile.TemporaryDirectory(prefix="sassy_fo_") as td:
        td_path = Path(td)

        # sassy_safe_delete: normal file
        f = td_path / "a.txt"
        f.write_text("x")
        msg = await sassy_safe_delete(str(f))
        check("safe_delete: moved a.txt", "Moved to staging" in msg, f"msg={msg}")

        # sassy_safe_delete: refuses _DELETE_ folder
        msg = await sassy_safe_delete(str(td_path / "_DELETE_"))
        check("safe_delete: refuses staging folder", "Refused" in msg, f"msg={msg}")

        # sassy_safe_delete: refuses protected (sassymcp source)
        msg = await sassy_safe_delete(r"V:\Projects\SassyMCP\sassymcp\modules\shell.py")
        check("safe_delete: refuses protected source", "Refused" in msg, f"msg={msg}")

        # sassy_write_file: rewrite snapshots existing content
        target = td_path / "doc.txt"
        target.write_text("original")
        msg = await sassy_write_file(str(target), "new contents", "rewrite")
        check("write_file: rewrite succeeded", "Written" in msg, f"msg={msg}")
        snaps = list((td_path / "_DELETE_").glob("doc.overwrite.*.txt"))
        check("write_file: snapshot created", len(snaps) == 1 and snaps[0].read_text() == "original",
              f"snaps={snaps}")

        # sassy_write_file: refuses protected source
        msg = await sassy_write_file(r"V:\Projects\SassyMCP\sassymcp\modules\shell.py", "junk", "rewrite")
        check("write_file: refuses protected", "Refused" in msg, f"msg={msg}")

        # sassy_move: refuses overwrite of existing destination
        a = td_path / "src.txt"; a.write_text("a")
        b = td_path / "dst.txt"; b.write_text("b")
        msg = await sassy_move(str(a), str(b))
        check("move: refuses existing destination", "already exists" in msg, f"msg={msg}")
        check("move: src not touched on refusal", a.exists())
        check("move: dst not touched on refusal", b.read_text() == "b")

        # sassy_move: refuses protected source
        msg = await sassy_move(r"V:\Projects\SassyMCP\sassymcp\modules\shell.py", str(td_path / "out.py"))
        check("move: refuses protected source", "Refused" in msg, f"msg={msg}")

        # v1.1.2: sassy_copy refuses existing destination (no silent overwrite)
        c1 = td_path / "c1.txt"; c1.write_text("one")
        c2 = td_path / "c2.txt"; c2.write_text("two")
        msg = await sassy_copy(str(c1), str(c2))
        check("copy: refuses existing destination", "already exists" in msg, f"msg={msg}")
        check("copy: dst unchanged on refusal", c2.read_text() == "two")

        # v1.1.2: sassy_copy refuses protected source
        msg = await sassy_copy(r"V:\Projects\SassyMCP\sassymcp\modules\shell.py", str(td_path / "stolen.py"))
        check("copy: refuses protected source", "Refused" in msg, f"msg={msg}")

        # v1.1.2: sassy_copy refuses protected destination
        msg = await sassy_copy(str(c1), r"V:\Projects\SassyMCP\sassymcp\modules\clobber.py")
        check("copy: refuses protected dest", "Refused" in msg, f"msg={msg}")

        # v1.1.2: sassy_copy normal happy path still works
        c3 = td_path / "c3.txt"
        msg = await sassy_copy(str(c1), str(c3))
        check("copy: normal happy path", "Copied" in msg and c3.read_text() == "one", f"msg={msg}")

asyncio.run(test_fileops())


# ── editor.py guards — v1.1.2 ────────────────────────────────────────
print("\n[5b] editor.py guards — sandbox")
from sassymcp.modules import editor as ed
_fake = _FakeServer()
ed.register(_fake)
sassy_edit_block = _fake.tools["sassy_edit_block"]
sassy_edit_multi = _fake.tools["sassy_edit_multi"]

async def test_editor():
    with tempfile.TemporaryDirectory(prefix="sassy_ed_") as td:
        td_path = Path(td)

        # edit_block: refuses protected file — using a real file path that
        # is_protected_path will flag WITHOUT the tool actually touching it.
        # We use a path that exists and is inside the protected tree.
        protected_target = r"V:\Projects\SassyMCP\sassymcp\modules\shell.py"
        msg = await sassy_edit_block(protected_target,
                                     "def _THIS_WILL_NEVER_MATCH_ANYTHING_xyzzy",
                                     "def NUKED")
        # The fix must refuse BEFORE attempting the edit, so the match text
        # doesn't matter — a refusal is what we want.
        check("edit_block: refuses protected file",
              "Refused" in msg or "refused" in msg.lower() or "protected" in msg.lower(),
              f"msg={msg[:200]}")

        # edit_block: happy path snapshots previous content
        target = td_path / "code.txt"
        target.write_text("alpha beta gamma")
        msg = await sassy_edit_block(str(target), "beta", "BETA")
        check("edit_block: happy path applies edit", "Edit applied" in msg, f"msg={msg[:200]}")
        check("edit_block: file content updated", target.read_text() == "alpha BETA gamma")
        snaps = list((td_path / "_DELETE_").glob("code.pre-edit.*.txt"))
        check("edit_block: snapshot created", len(snaps) == 1, f"snaps={snaps}")

        # edit_multi: refuses protected file
        msg = await sassy_edit_multi(
            r"V:\Projects\SassyMCP\sassymcp\modules\_security.py",
            '[{"old":"_THIS_WILL_NEVER_MATCH_ANYTHING_xyzzy","new":"NUKED"}]',
        )
        check("edit_multi: refuses protected file",
              "Refused" in msg or "refused" in msg.lower() or "protected" in msg.lower(),
              f"msg={msg[:200]}")

        # edit_multi: happy path snapshots
        m_target = td_path / "multi.txt"
        m_target.write_text("one two three")
        import json as _j
        msg = await sassy_edit_multi(str(m_target), _j.dumps([
            {"old": "one", "new": "ONE"},
            {"old": "three", "new": "THREE"},
        ]))
        check("edit_multi: happy path applies", "Applied" in msg)
        check("edit_multi: content updated", m_target.read_text() == "ONE two THREE")
        snaps = list((td_path / "_DELETE_").glob("multi.pre-edit.*.txt"))
        check("edit_multi: snapshot created", len(snaps) == 1, f"snaps={snaps}")

asyncio.run(test_editor())


# ── session.py gating ────────────────────────────────────────────────
print("\n[6] session.py send/start gating")
from sassymcp.modules import session as sess_mod
_fake = _FakeServer()
sess_mod.register(_fake)
sassy_session_start = _fake.tools["sassy_session_start"]
sassy_session_send  = _fake.tools["sassy_session_send"]
sassy_session_stop  = _fake.tools["sassy_session_stop"]

async def test_session():
    import json as _json
    # Start a real shell so send() has a target.
    r = await sassy_session_start("sbx", "powershell", "")
    check("session: started", "started" in r, f"r={r}")

    # Direct delete via send — should be refused.
    r = await sassy_session_send("sbx", "del foo.txt")
    blocked = "Delete command blocked" in r
    check("session_send: direct del blocked", blocked, f"r={r}")

    # Alias ri — should be refused.
    r = await sassy_session_send("sbx", "ri foo")
    check("session_send: ri alias blocked", "Delete command blocked" in r, f"r={r}")

    # Wrapper via cmd /c — should be refused.
    r = await sassy_session_send("sbx", "cmd /c del foo")
    check("session_send: cmd /c wrapper blocked", "Delete command blocked" in r, f"r={r}")

    # Non-destructive — should be allowed.
    r = await sassy_session_send("sbx", "echo sandbox-ok")
    check("session_send: echo allowed", "sent" in r, f"r={r}")

    # start() with delete command — refused before the shell even spawns.
    r = await sassy_session_start("sbx2", "powershell", "del foo")
    check("session_start: initial del blocked", "blocked" in r.lower(), f"r={r}")

    await sassy_session_stop("sbx")

asyncio.run(test_session())


# ── linux.py gating ──────────────────────────────────────────────────
print("\n[7] linux.py gating")
from sassymcp.modules import linux as linux_mod
_fake = _FakeServer()
linux_mod.register(_fake)
sassy_linux_exec = _fake.tools["sassy_linux_exec"]

async def test_linux():
    r = await sassy_linux_exec("rm foo.txt", 5)
    check("linux_exec: rm blocked", "blocked by interceptor" in r, f"r={r[:200]}")
    r = await sassy_linux_exec("cmd /c del foo", 5)
    check("linux_exec: wrapper blocked", "blocked by interceptor" in r, f"r={r[:200]}")

asyncio.run(test_linux())


# ── audit_clear rotation ─────────────────────────────────────────────
print("\n[8] audit_clear — rotation not unlink")
from sassymcp.modules import audit as audit_mod
_fake = _FakeServer()
audit_mod.register(_fake)
sassy_audit_clear = _fake.tools["sassy_audit_clear"]

async def test_audit():
    # Without confirm it must refuse.
    r = await sassy_audit_clear("")
    check("audit_clear: refuses without confirm", "Refused" in r, f"r={r}")

asyncio.run(test_audit())


# ── selfmod_rollback confirm — v1.1.2 ────────────────────────────────
print("\n[9] selfmod_rollback — confirm required")
from sassymcp.modules import selfmod as selfmod_mod
_fake = _FakeServer()
selfmod_mod.register(_fake)
sassy_selfmod_rollback = _fake.tools["sassy_selfmod_rollback"]

async def test_rollback():
    # Use a path that does NOT exist under git so even if the confirm
    # check is missing, git checkout will error instead of touching real
    # files. The fix must refuse BEFORE attempting git checkout.
    r = await sassy_selfmod_rollback("_nonexistent_test_target.py")
    check("selfmod_rollback: refuses without confirm",
          "Refused" in r or ("confirm" in r.lower() and "YES" in r),
          f"r={r[:200]}")

asyncio.run(test_rollback())


# ── adb_shell detect_delete_intent — v1.1.2 ──────────────────────────
print("\n[10] adb_shell — destructive gate")
# adb_shell lives in sassymcp.modules.adb; we only exercise the validation
# path (not the real adb invocation). The function runs _run_adb on success;
# on block it should short-circuit with an error string.
from sassymcp.modules import adb as adb_mod
_fake = _FakeServer()
adb_mod.register(_fake)
sassy_adb_shell = _fake.tools["sassy_adb_shell"]

async def test_adb():
    # Use a fake device ID so the call NEVER reaches a real phone — adb
    # will error with "device 'zzz_fake_test' not found" before executing.
    FAKE = "zzz_fake_test_device"

    # Use a harmless path that would be no-op even if it somehow got
    # through: /tmp/sassymcp-intercept-test-nonexistent
    harmless = "rm /tmp/sassymcp_intercept_test_nonexistent_file_xyzzy"

    r = await sassy_adb_shell(harmless, device=FAKE)
    check("adb_shell: rm blocked without override",
          "blocked" in r.lower() or "destructive" in r.lower(),
          f"r={r[:200]}")

    r = await sassy_adb_shell(harmless, device=FAKE, allow_destructive=True)
    # With override, our gate is passed. adb itself errors on the fake
    # device, but that's not our gate blocking it.
    check("adb_shell: rm allowed with override",
          "blocked" not in r.lower() and "destructive" not in r.lower(),
          f"r={r[:200]}")

asyncio.run(test_adb())


print("\n==================")
print(f"{PASS} passed, {FAIL} failed")
print("==================")
sys.exit(0 if FAIL == 0 else 1)
