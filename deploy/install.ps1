# SassyMCP install wrapper — registry backup before install.
# Usage:  .\install.ps1            installs SassyMCP-v*.msi from this folder
#         .\install.ps1 -MsiPath X explicit path
#         .\install.ps1 -Quiet     /quiet msiexec, no UI

[CmdletBinding()]
param(
    [string]$MsiPath = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$backupRoot = Join-Path $env:LOCALAPPDATA "SassyMCP\backups\$ts"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null

Write-Host "==> SassyMCP install — backup + msiexec wrapper"
Write-Host "    Backup folder: $backupRoot"

# 1. Locate the MSI ----------------------------------------------------------
if (-not $MsiPath) {
    $candidate = Get-ChildItem -Path $PSScriptRoot -Filter "SassyMCP-v*.msi" -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTime -Descending |
                 Select-Object -First 1
    if (-not $candidate) {
        throw "No SassyMCP-v*.msi found next to install.ps1. Pass -MsiPath."
    }
    $MsiPath = $candidate.FullName
}
if (-not (Test-Path $MsiPath)) {
    throw "MSI not found: $MsiPath"
}
Write-Host "    Installer:    $MsiPath"

# 2. Registry backup ---------------------------------------------------------
# Back up ONLY the keys this installer will modify. Two categories:
#   a) Per-product config keys we own       (HK*\Software\SassyMCP)
#   b) The MSI's own Uninstall entry, found by walking the Uninstall hive
#      for an existing SassyMCP record (so an upgrade can be rolled back).
# Each export is best-effort; absent keys leave a `.absent` marker.

$regKeys = @(
    @{ Hive = "HKCU\Software\SassyMCP";              File = "HKCU-SassyMCP.reg" },
    @{ Hive = "HKLM\Software\SassyMCP";              File = "HKLM-SassyMCP.reg" },
    @{ Hive = "HKLM\Software\WOW6432Node\SassyMCP";  File = "HKLM-WOW6432-SassyMCP.reg" }
)

foreach ($k in $regKeys) {
    $out = Join-Path $backupRoot $k.File
    & reg export $k.Hive $out /y 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    Backed up:    $($k.Hive)  ->  $($k.File)"
    } else {
        "Key not present at $ts: $($k.Hive)" | Set-Content -Path "$out.absent" -Encoding ASCII
    }
}

# Find the SassyMCP entry inside Uninstall (32-bit & 64-bit views).
# Match on DisplayName so we get the ProductCode that's actually installed.
$uninstallRoots = @(
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($root in $uninstallRoots) {
    if (-not (Test-Path $root)) { continue }
    Get-ChildItem $root -ErrorAction SilentlyContinue | ForEach-Object {
        $props = Get-ItemProperty $_.PSPath -ErrorAction SilentlyContinue
        if ($props.DisplayName -like "SassyMCP*") {
            $regPath = $_.PSPath -replace "^Microsoft\.PowerShell\.Core\\Registry::", ""
            $safeName = ($_.PSChildName -replace "[^A-Za-z0-9._-]", "_")
            $out = Join-Path $backupRoot "Uninstall-$safeName.reg"
            & reg export $regPath $out /y 2>&1 | Out-Null
            Write-Host "    Backed up:    $regPath  ->  Uninstall-$safeName.reg"
        }
    }
}

# 3. Snapshot user data folder if it exists (audit log, state) --------------
$userData = Join-Path $env:USERPROFILE ".sassymcp"
if (Test-Path $userData) {
    $userBackup = Join-Path $backupRoot "user-data.zip"
    Compress-Archive -Path "$userData\*" -DestinationPath $userBackup -CompressionLevel Optimal -Force
    Write-Host "    Backed up:    $userData  ->  user-data.zip"
}

# 4. Run msiexec -------------------------------------------------------------
$logPath = Join-Path $backupRoot "msiexec.log"
$argList = @("/i", "`"$MsiPath`"", "/L*v", "`"$logPath`"")
if ($Quiet) { $argList += "/quiet" }

Write-Host ""
Write-Host "==> Running: msiexec $($argList -join ' ')"
$proc = Start-Process -FilePath "msiexec.exe" -ArgumentList $argList -Wait -PassThru
if ($proc.ExitCode -eq 0) {
    Write-Host "==> Install OK. Backup retained at $backupRoot"
} else {
    Write-Warning "msiexec exit code $($proc.ExitCode) — see $logPath"
    exit $proc.ExitCode
}

# 5. Record the install in a manifest so uninstall can find this backup ----
$manifest = [ordered]@{
    timestamp   = $ts
    msi         = $MsiPath
    backup_root = $backupRoot
    msi_log     = $logPath
}
$manifest | ConvertTo-Json | Set-Content -Path (Join-Path $backupRoot "manifest.json") -Encoding UTF8
$latestPath = Join-Path $env:LOCALAPPDATA "SassyMCP\backups\latest.txt"
$backupRoot | Set-Content -Path $latestPath -Encoding ASCII

Write-Host ""
Write-Host "Tip: to fully uninstall and purge user data later, run:"
Write-Host "     .\uninstall.ps1 -Purge"
