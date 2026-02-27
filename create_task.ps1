param(
    [Parameter(Mandatory=$true)][string]$ExePath,
    [Parameter(Mandatory=$true)][string]$TaskName
)

$action = New-ScheduledTaskAction -Execute $ExePath -Argument '--once'

$trigger1 = New-ScheduledTaskTrigger -Daily -At 9:00AM
$trigger2 = New-ScheduledTaskTrigger -Daily -At 4:00PM

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger1,$trigger2 `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null
