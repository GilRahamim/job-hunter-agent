<#
.SYNOPSIS
  Registers (or removes) the daily Job Hunter run in Windows Task Scheduler.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1            # daily at 08:30
  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -At 7:15am
  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -RunNow    # register + start once
  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -Remove
  powershell -ExecutionPolicy Bypass -File scripts\schedule_windows.ps1 -User dana   # a user added in the dashboard
#>
param(
  [string]$At = "8:30am",
  [string]$TaskName = "JobHunterAgent",
  [string]$User = "",
  [switch]$RunNow,
  [switch]$Remove
)

$ErrorActionPreference = "Stop"
# One task per user: "JobHunterAgent-dana" runs  run_agent.py --user dana
if ($User) { $TaskName = "$TaskName-$User" }

if ($Remove) {
  if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task '$TaskName'."
  } else {
    Write-Host "Task '$TaskName' does not exist."
  }
  return
}

$proj = Split-Path -Parent $PSScriptRoot
# Prefer the project's venv so the task does not depend on PATH.
$venv = Join-Path $proj ".venv\Scripts\python.exe"
$python = if (Test-Path $venv) { $venv } else { (Get-Command python).Source }
# `python` may be a Store/launcher shim; register the real interpreter that has the packages.
$real = & $python -c "import sys; print(sys.executable)" 2>$null
if ($LASTEXITCODE -eq 0 -and $real -and (Test-Path $real)) { $python = $real.Trim() }

# powershell -WindowStyle Hidden keeps a console window from popping up at 08:30.
$userArg = if ($User) { " --user $User" } else { "" }
$command = "& '$python' run_agent.py$userArg"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -WindowStyle Hidden -Command `"$command`"" -WorkingDirectory $proj
$trigger = New-ScheduledTaskTrigger -Daily -At $At
# StartWhenAvailable: a run missed because the PC was off happens at next boot/login.
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
  -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
  -Description "Daily Job Hunter search (collect, filter, score)" -Force | Out-Null

$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Registered '$TaskName': daily at $At, python = $python"
Write-Host "Next run: $($info.NextRunTime)"

if ($RunNow) {
  Start-ScheduledTask -TaskName $TaskName
  $logs = if ($User) { "$proj\users\$User\data\logs" } else { "$proj\data\logs" }
  Write-Host "Started once now. Logs: $logs"
}
