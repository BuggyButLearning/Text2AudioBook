# Inno Setup [UninstallRun] hook. Invoked once during uninstall.
# Responsibility: strip $InstallDir from USER PATH BEFORE Inno deletes files.
# Leaves the conda env intact (user may have other uses for it).

param(
    [Parameter(Mandatory=$true)] [string] $InstallDir
)

$ErrorActionPreference = "SilentlyContinue"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath) {
    $newPath = ($userPath -split ";" | Where-Object { $_ -and $_ -ne $InstallDir }) -join ";"
    if ($newPath -ne $userPath) {
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    }
}
