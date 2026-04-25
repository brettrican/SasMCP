@echo off
REM SassyMCP Remote MCP Status Check

setlocal enabledelayedexpansion

echo ==============================================================
echo  SassyMCP Remote Status
echo ==============================================================
echo.

if exist "V:\Projects\SassyMCP\.venv\Scripts\python.exe" (
    echo [OK]   V: drive mounted, SassyMCP venv present
) else (
    echo [FAIL] V: drive NOT mounted or SassyMCP missing
)

if defined SASSYMCP_AUTH_TOKEN (
    echo [OK]   SASSYMCP_AUTH_TOKEN set in this shell
) else (
    powershell -NoProfile -File "%~dp0scripts\check-token.ps1"
    if !ERRORLEVEL! equ 0 (
        echo [OK]   SASSYMCP_AUTH_TOKEN set at User scope
    ) else (
        echo [FAIL] SASSYMCP_AUTH_TOKEN not set anywhere
    )
)

REM Match any listener on :21001 (works for both IPv4 and IPv6)
netstat -an | findstr /C:":21001" | findstr /C:"LISTENING"
if %ERRORLEVEL% equ 0 (
    echo [OK]   HTTP bridge listening on :21001
) else (
    echo [FAIL] Nothing listening on :21001 - bridge not running
)

sc query Cloudflared | findstr /C:"RUNNING"
if %ERRORLEVEL% equ 0 (
    echo [OK]   Cloudflared service RUNNING
) else (
    echo [FAIL] Cloudflared service not running
)

schtasks /query /tn "SassyMCP Bridge (Logon)"
if %ERRORLEVEL% equ 0 (
    echo [OK]   Autostart scheduled task registered
) else (
    echo [WARN] Autostart task not registered
    echo        Run: powershell -File register-autostart.ps1
)

echo.
echo --- Tunnel edge connections ---
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel info sassymcp

echo.
echo --- Smoke tests ---
powershell -NoProfile -File "%~dp0scripts\smoke-test.ps1"

echo.
endlocal
