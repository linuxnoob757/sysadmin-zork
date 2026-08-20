# Create a "Sysadmin Zork" shortcut on the user's Desktop that launches
# launch.bat. Run once:  powershell -ExecutionPolicy Bypass -File make_shortcut.ps1
$ErrorActionPreference = "Stop"

$repo    = $PSScriptRoot
$launcher = Join-Path $repo "launch.bat"
if (-not (Test-Path $launcher)) { throw "launch.bat not found next to this script ($launcher)" }

$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Sysadmin Zork.lnk"

$sc = $shell.CreateShortcut($shortcutPath)
$sc.TargetPath       = $launcher
$sc.WorkingDirectory = $repo
$sc.Description       = "Launch Sysadmin Zork (text-based Linux sysadmin training game)"
$sc.IconLocation      = "shell32.dll,25"   # a generic terminal-ish icon
$sc.Save()

Write-Host "Shortcut created: $shortcutPath"
