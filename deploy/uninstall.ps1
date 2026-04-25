# SassyMCP uninstall wrapper — removes the MSI, optionally purges user data.
# Usage:  .\uninstall.ps1            uninstall MSI, leave user data intact
#         .\uninstall.ps1 -Purge     also purge ~/.sassymcp/ and %LOCALAPPDATA%\SassyMCP\
#         .\uninstall.ps1 -Quiet     /quiet msiexec, no UI

[CmdletBinding()]
param(
    [switch]$Purge,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

# 1. Find the installed product by DisplayName ------------------------------
$uninstallRoots = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
)
$productCode = $null
foreach ($root in $uninstallRoots) {
    if (-not (Test-Path $root)) { continue }
    $hit = Get-ChildItem $root -ErrorAction SilentlyContinue | Where-Object {
        (Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue).DisplayName -like "SassyMCP*"
    } | Select-Object -First 1
    if ($hit) { $productCode = $hit.PSChildName; break }
}

if (-not $productCode) {
    Write-Warning "SassyMCP not found in any Uninstall registry root. Nothing to uninstall via MSI."
} else {
    Write-Host "==> Found SassyMCP product code: $productCode"

    # 2. Snapshot the Uninstall key before removal so this action is undoable
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupDir = Join-Path $env:LOCALAPPDATA "SassyMCP\backups\uninstall-$ts"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    & reg export "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\$productCode" `
        (Join-Path $backupDir "Uninstall-$productCode.reg") /y 2>&1 | Out-Null
    Write-Host "    Pre-uninstall snapshot: $backupDir"

    # 3. msiexec /x ------------------------------------------------------------
    $logPath = Join-Path $backupDir "msiexec-uninstall.log"
    $argList = @("/x", $productCode, "/L*v", "`"$logPath`"")
    if ($Quiet) { $argList += "/quiet" }
    Write-Host "==> Running: msiexec $($argList -join ' ')"
    $proc = Start-Process -FilePath "msiexec.exe" -ArgumentList $argList -Wait -PassThru
    if ($proc.ExitCode -eq 0) {
        Write-Host "==> Uninstall OK."
    } else {
        Write-Warning "msiexec exit code $($proc.ExitCode) - see $logPath"
        exit $proc.ExitCode
    }
}

# 4. Optional purge of user data -------------------------------------------
if ($Purge) {
    Write-Host ""
    Write-Host "==> -Purge requested. Removing user state."
    $purgeTargets = @(
        (Join-Path $env:USERPROFILE   ".sassymcp"),
        (Join-Path $env:LOCALAPPDATA  "SassyMCP\updates"),
        (Join-Path $env:LOCALAPPDATA  "SassyMCP\state")
    )
    # NOTE: $LOCALAPPDATA\SassyMCP\backups\ is intentionally NOT purged so
    # the registry-backup history survives a -Purge run. Delete it manually
    # if you really want a clean slate.
    foreach ($p in $purgeTargets) {
        if (Test-Path $p) {
            Remove-Item -Recurse -Force -Path $p
            Write-Host "    Removed: $p"
        }
    }
    Write-Host "    (kept) $env:LOCALAPPDATA\SassyMCP\backups\  - registry-backup history"
}

Write-Host ""
Write-Host "Done. To restore a backed-up registry state, import the .reg files in"
Write-Host "$env:LOCALAPPDATA\SassyMCP\backups\<timestamp>\ via:  reg import <file>.reg"
