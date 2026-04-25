$content = @'
@echo off
REM =============================================================
REM  SassyMCP Autostart Bridge (scheduled task at logon)
REM  Runs python directly - simpler than wrapping start-tunnel.bat
REM =============================================================

setlocal

set LOGDIR=%LOCALAPPDATA%\\SassyMCP
set LOGFILE=%LOGDIR%\\bridge.log
if not exist \"%LOGDIR%\" mkdir \"%LOGDIR%\"

REM Wait for V: drive (max 60s, 2s interval)
set /a WAITED=0
:wait_v
if exist \"V:\\Projects\\SassyMCP\\.venv\\Scripts\\python.exe\" goto v_ready
if %WAITED% geq 60 (
    echo [%DATE% %TIME%] FAIL: V: drive not mounted after 60s >> \"%LOGFILE%\"
    exit /b 1
)
timeout /t 2 /nobreak >nul
set /a WAITED+=2
goto wait_v

:v_ready
echo [%DATE% %TIME%] V: drive ready after %WAITED%s >> \"%LOGFILE%\"

REM Preflight: token must be set
if not defined SASSYMCP_AUTH_TOKEN (
    echo [%DATE% %TIME%] FAIL: SASSYMCP_AUTH_TOKEN not in env >> \"%LOGFILE%\"
    exit /b 1
)
echo [%DATE% %TIME%] Token visible, length=X >> \"%LOGFILE%\"

REM Kill stale bridge on :21001
for /f \"tokens=5\" %%P in ('netstat -ano ^| findstr /R /C:\"LISTENING.*:21001 \"') do (
    echo [%DATE% %TIME%] Killing stale PID %%P >> \"%LOGFILE%\"
    taskkill /f /pid %%P >nul 2>&1
)

set SASSYMCP_LOAD_ALL=1

echo [%DATE% %TIME%] Launching bridge >> \"%LOGFILE%\"
\"V:\\Projects\\SassyMCP\\.venv\\Scripts\\python.exe\" -m sassymcp.server --http --host 127.0.0.1 --port 21001 >> \"%LOGFILE%\" 2>&1

echo [%DATE% %TIME%] Bridge exited (code %ERRORLEVEL%) >> \"%LOGFILE%\"
endlocal
'@
$content | Set-Content \"V:\\Projects\\SassyMCP\\autostart-bridge.bat\" -Encoding ascii
Write-Host \"Rewrote autostart-bridge.bat ($((Get-Item 'V:\\Projects\\SassyMCP\\autostart-bridge.bat').Length) bytes)\""
}
Response
