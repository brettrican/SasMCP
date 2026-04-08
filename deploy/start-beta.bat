@echo off
:: SassyMCP Beta — Full 257-tool build with bundled tools
:: Just double-click this. The exe auto-detects HTTP mode and prints
:: connection instructions.

set SCRIPT_DIR=%~dp0
set PATH=%SCRIPT_DIR%tools\adb;%SCRIPT_DIR%tools\nmap;%SCRIPT_DIR%tools\putty;%SCRIPT_DIR%tools\scrcpy;%SCRIPT_DIR%tools\tesseract;%PATH%
set TESSDATA_PREFIX=%SCRIPT_DIR%tools\tesseract\tessdata
set SASSYMCP_LOAD_ALL=1

"%SCRIPT_DIR%sassymcp.exe" %*
