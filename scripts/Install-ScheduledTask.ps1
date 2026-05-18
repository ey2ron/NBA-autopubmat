<#
.SYNOPSIS
    Register a Windows Scheduled Task that runs the NBA pubmat generator daily.

.DESCRIPTION
    Creates (or replaces) a task named "NBA-Pubmat" that fires once per day
    at the time you choose (default 03:00 local — late enough that all NBA
    finals on the US west coast are over).

    The task runs:
        python -m nba_post.main
    from the repo root, capturing stdout/stderr to scripts/logs/.

.PARAMETER Time
    HH:mm clock time for the daily trigger. Default "03:00".

.PARAMETER TaskName
    Scheduled task name. Default "NBA-Pubmat".

.PARAMETER Python
    Python executable. Defaults to "python" on PATH.

.EXAMPLE
    .\scripts\Install-ScheduledTask.ps1
    .\scripts\Install-ScheduledTask.ps1 -Time 02:30
    .\scripts\Install-ScheduledTask.ps1 -Python "C:\Python314\python.exe"

.NOTES
    Run from an elevated PowerShell (Admin) the first time.
    Uninstall with:  Unregister-ScheduledTask -TaskName NBA-Pubmat -Confirm:$false
#>
[CmdletBinding()]
param(
    [string]$Time = "03:00",
    [string]$TaskName = "NBA-Pubmat",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

# Repo root = parent of this script's directory.
$RepoRoot = Split-Path -Parent $PSScriptRoot
$LogDir   = Join-Path $RepoRoot "scripts\logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$LogFile = Join-Path $LogDir "auto-pubmat.log"

# Wrap the python call so stdout+stderr are appended to a log file.
$Command = "$Python -m nba_post.main *>> `"$LogFile`""

# Use PowerShell as the runner so we can redirect output cleanly.
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command `"Set-Location '$RepoRoot'; $Command`""

$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

# Run under the current user, only when logged on, no stored password.
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Replacing existing task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Runs the NBA Final-Score pubmat generator daily at $Time." | Out-Null

Write-Host ""
Write-Host "Installed scheduled task '$TaskName'." -ForegroundColor Green
Write-Host "  Daily trigger : $Time"
Write-Host "  Working dir   : $RepoRoot"
Write-Host "  Log file      : $LogFile"
Write-Host ""
Write-Host "Test now with:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
Write-Host ""
Write-Host "Uninstall with:" -ForegroundColor Cyan
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
