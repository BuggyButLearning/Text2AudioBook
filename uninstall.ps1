# Text2AudioBook uninstaller (mirrors install.ps1).
#
# Run from anywhere:
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1
#
# What it does:
#   1. Strips %LOCALAPPDATA%\Text2AudioBook from USER PATH
#   2. Removes %LOCALAPPDATA%\Text2AudioBook
#   3. Leaves the conda env intact (user may have other uses)

$ErrorActionPreference = "Stop"
$InstallDir = "$env:LOCALAPPDATA\Text2AudioBook"

Write-Host "Text2AudioBook uninstaller" -ForegroundColor Cyan
Write-Host "Removing: $InstallDir"

# 1. Strip from USER PATH.
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    $newPath = ($userPath -split ";" | Where-Object { $_ -and $_ -ne $InstallDir }) -join ";"
    if ($newPath -ne $userPath) {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
        Write-Host "Removed $InstallDir from USER PATH." -ForegroundColor Green
    } else {
        Write-Host "$InstallDir not on USER PATH; skipping." -ForegroundColor DarkGray
    }
}

# 2. Remove install dir.
if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
    Write-Host "Deleted $InstallDir" -ForegroundColor Green
} else {
    Write-Host "$InstallDir did not exist; skipping." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Done. The conda env 'text2audiobook' was left in place." -ForegroundColor Cyan
Write-Host "Remove it manually if desired: conda env remove -n text2audiobook"
