param(
    [Parameter(Mandatory = $true)]
    [string]$PythonPath,
    [ValidateSet('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday')]
    [string]$Day = 'Saturday',
    [ValidatePattern('^([01][0-9]|2[0-3]):[0-5][0-9]$')]
    [string]$Time = '08:00',
    [string]$TaskName = 'JobMarketIntelligence-WeeklyCollection'
)

$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$resolvedPython = (Resolve-Path -LiteralPath $PythonPath).Path
$entryPoint = Join-Path $PSScriptRoot 'collect_weekly.py'
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    throw "Task '$TaskName' already exists. Edit it in Task Scheduler instead of creating a duplicate."
}
& $resolvedPython -c 'import pandas, selenium'
if ($LASTEXITCODE -ne 0) { throw 'The selected Python environment cannot import scraper dependencies.' }

$action = New-ScheduledTaskAction -Execute $resolvedPython `
    -Argument ('"{0}" --delay 3' -f $entryPoint) -WorkingDirectory $projectPath
$atTime = [datetime]::Today.Add([TimeSpan]::Parse($Time))
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Day -At $atTime
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 12) `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description 'Weekly incremental NFJ collection to raw CSV. Requires a logged-in user; no database writes.'
Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object TaskName, NextRunTime, LastTaskResult
