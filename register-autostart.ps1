# SassyMCP Autostart Registration
#
# Creates a scheduled task that starts the HTTP bridge at logon.
# Runs as the interactive user so it inherits User-scope env vars
# and has access to the mounted V: drive.
#
# Usage:
#   .\register-autostart.ps1            register
#   .\register-autostart.ps1 -Remove    unregister
#   .\register-autostart.ps1 -Status    show current state

param(
    [switch]$Remove,
    [switch]$Status
)

$TaskName = "SassyMCP Bridge (Logon)"
$ScriptPath = "V:\Projects\SassyMCP\autostart-bridge.bat"

if ($Status) {
    $t = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($t) {
        $info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "Task: $TaskName"
        Write-Host "  State:         $($t.State)"
        Write-Host "  Last run:      $($info.LastRunTime)"
        Write-Host "  Last result:   0x$('{0:X}' -f $info.LastTaskResult)"
        Write-Host "  Next run:      $($info.NextRunTime)"
    } else {
        Write-Host "Task '$TaskName' is not registered."
    }
    exit 0
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed task: $TaskName"
    exit 0
}

if (-not (Test-Path $ScriptPath)) {
    Write-Error "autostart-bridge.bat not found at $ScriptPath"
    exit 1
}

if (-not [Environment]::GetEnvironmentVariable("SASSYMCP_AUTH_TOKEN", "User")) {
    Write-Warning "SASSYMCP_AUTH_TOKEN not set at User scope."
    Write-Warning "Set it before the task fires, or the bridge will refuse to start."
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$ScriptPath`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -DontStopOnIdleEnd `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Starts SassyMCP HTTP bridge on :21001 for Cloudflare tunnel access" | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "  Script:    $ScriptPath"
Write-Host "  Trigger:   At logon of $env:USERDOMAIN\$env:USERNAME"
Write-Host "  Log:       $env:LOCALAPPDATA\SassyMCP\bridge.log"
Write-Host ""
Write-Host "Trigger once now for testing:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"

