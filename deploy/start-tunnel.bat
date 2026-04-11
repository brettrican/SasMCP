@echo off
setlocal enabledelayedexpansion
REM ==============================================================
REM  SassyMCP - Cloudflare Tunnel Mode (turnkey HTTPS)
REM  For: Claude Desktop Custom Connectors, or any remote MCP client
REM  that requires an HTTPS URL with a publicly-trusted cert.
REM
REM  This spins an EPHEMERAL trycloudflare.com tunnel - no Cloudflare
REM  account, no login, no domain needed. URL changes each run.
REM ==============================================================

set SCRIPT_DIR=%~dp0
set SASSYMCP_LOAD_ALL=1
set PORT=21001

echo ===========================================
echo  SassyMCP - Cloudflare Tunnel (HTTPS)
echo ===========================================
echo.

REM -- Locate cloudflared (prefer bundled, fall back to PATH) ---
set CLOUDFLARED=
if exist "%SCRIPT_DIR%tools\cloudflared\cloudflared.exe" (
    set "CLOUDFLARED=%SCRIPT_DIR%tools\cloudflared\cloudflared.exe"
) else (
    where cloudflared >nul 2>&1
    if !ERRORLEVEL! equ 0 set CLOUDFLARED=cloudflared
)
if "!CLOUDFLARED!"=="" (
    echo [ERROR] cloudflared not found.
    echo         Expected at: %SCRIPT_DIR%tools\cloudflared\cloudflared.exe
    echo         Or install:  winget install Cloudflare.cloudflared
    pause
    exit /b 1
)

REM -- Auth Token (required for remote access) -----------------
if not defined SASSYMCP_AUTH_TOKEN (
    echo  Tunnel mode requires an auth token.
    echo  Press Enter to auto-generate one, or paste your own:
    set /p USER_TOKEN="  Token: "
    if "!USER_TOKEN!"=="" (
        for /f "delims=" %%T in ('powershell -NoProfile -Command "[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).Replace('+','-').Replace('/','_').TrimEnd('=')"') do set SASSYMCP_AUTH_TOKEN=%%T
    ) else (
        set SASSYMCP_AUTH_TOKEN=!USER_TOKEN!
    )
)
echo  [OK] Auth token:
echo       !SASSYMCP_AUTH_TOKEN!
echo.

REM -- Check for existing instance ------------------------------
tasklist /FI "IMAGENAME eq sassymcp.exe" 2>nul | find "sassymcp.exe" >nul
if %ERRORLEVEL%==0 (
    echo [WARN] sassymcp.exe already running. Kill it first:
    echo        taskkill /f /im sassymcp.exe
    pause
    exit /b 1
)

REM -- Launch HTTP server (minimized) --------------------------
echo [1/2] Starting HTTP server on 127.0.0.1:%PORT%...
if exist "%SCRIPT_DIR%sassymcp.exe" (
    start "SassyMCP HTTP" /MIN "%SCRIPT_DIR%sassymcp.exe" --http --host 127.0.0.1 --port %PORT%
) else if exist "%SCRIPT_DIR%.venv\Scripts\python.exe" (
    start "SassyMCP HTTP" /MIN "%SCRIPT_DIR%.venv\Scripts\python.exe" -m sassymcp.server --http --host 127.0.0.1 --port %PORT%
) else (
    echo [ERROR] sassymcp.exe not found next to this script.
    pause
    exit /b 1
)

REM Wait for the HTTP server to bind
timeout /t 3 /nobreak >nul

REM -- Launch tunnel (visible window so user can see the URL) --
echo [2/2] Starting ephemeral Cloudflare tunnel...
echo.
echo  Look in the "Cloudflared Tunnel" window for a line like:
echo    https://random-words.trycloudflare.com
echo  That is your MCP HTTPS endpoint. Append /mcp/ when pointing
echo  a client at it.
echo.
start "Cloudflared Tunnel" "!CLOUDFLARED!" tunnel --url http://127.0.0.1:%PORT%

echo ===========================================
echo  Local:   http://127.0.0.1:%PORT%/mcp/
echo  Remote:  https://<see-cloudflared-window>.trycloudflare.com/mcp/
echo  Header:  Authorization: Bearer !SASSYMCP_AUTH_TOKEN!
echo.
echo  Claude Desktop - add a Custom Connector:
echo    Settings -^> Connectors -^> Add custom connector
echo    URL:    the trycloudflare.com URL above + /mcp/
echo    Header: Authorization: Bearer !SASSYMCP_AUTH_TOKEN!
echo.
echo  To stop: taskkill /f /im sassymcp.exe ^&^& taskkill /f /im cloudflared.exe
echo ===========================================
pause
