# setup_autostart.ps1
# Run this on your DESKTOP to register the GPU server as a Windows auto-start task.
# It will launch gpu_server.py every time you log in.

$TaskName = "MathGpuServer"
$PythonExe = python
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServerScript = Join-Path $ScriptDir "gpu_server.py"

Write-Host "Registering scheduled task: $TaskName"
Write-Host "  Python:  $PythonExe"
Write-Host "  Script:  $ServerScript"

$action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ServerScript`"" `
    -WorkingDirectory $ScriptDir

$trigger = New-ScheduledTaskTrigger -AtLogon

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force

Write-Host ""
Write-Host "Done. '$TaskName' will auto-start on next login."
Write-Host "To start it now: Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "To remove it:    Unregister-ScheduledTask -TaskName '$TaskName'"
