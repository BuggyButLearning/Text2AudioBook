# Text2AudioBook manual installer (fallback for users who don't want the .exe).
#
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File install.ps1
#
# What it does:
#   1. Verifies conda is on PATH
#   2. Checks for the `text2audiobook` conda env; offers to create it
#   3. Creates %LOCALAPPDATA%\Text2AudioBook
#   4. Writes a text2audiobook.cmd wrapper there pointing at THIS repo's cli.py
#   5. Adds the install dir to USER PATH (idempotent)
#
# Run uninstall.ps1 to reverse.

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot
$InstallDir = "$env:LOCALAPPDATA\Text2AudioBook"

Write-Host "Text2AudioBook installer" -ForegroundColor Cyan
Write-Host "Repo root:   $RepoRoot"
Write-Host "Install dir: $InstallDir"

# 1. Verify conda.
$conda = Get-Command conda -ErrorAction SilentlyContinue
if (-not $conda) {
    Write-Error "conda not found on PATH. Install Miniconda from https://docs.conda.io/en/latest/miniconda.html and re-run."
    exit 1
}

# 2. Check env.
$envExists = (conda env list 2>$null | Select-String '^text2audiobook\s') -ne $null
if (-not $envExists) {
    $resp = Read-Host "Conda env 'text2audiobook' not found. Create from environment.yml now? [Y/n]"
    if ($resp -eq "" -or $resp -match "^[Yy]") {
        Write-Host "Creating conda env (5-10 min)..." -ForegroundColor Yellow
        conda env create --file "$RepoRoot\environment.yml"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "conda env create failed (exit $LASTEXITCODE)"
            exit 1
        }
    } else {
        Write-Warning "Skipped env creation. The wrapper will fail until you run: conda env create --file environment.yml"
    }
}

# 3. Install dir.
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 4. Write wrapper. Repo path baked in at install time.
$cliPath = "$RepoRoot\cli.py"
$wrapper = @"
@echo off
call conda run --no-capture-output -n text2audiobook python "$cliPath" %*
"@
Set-Content -Path "$InstallDir\text2audiobook.cmd" -Value $wrapper -Encoding ASCII
Write-Host "Wrote $InstallDir\text2audiobook.cmd" -ForegroundColor Green

# Also write GUI launcher (no console window; suppresses cmd flash).
$mainPath = "$RepoRoot\main.py"
$guiWrapper = @"
@echo off
start "" /B conda run --no-capture-output -n text2audiobook pythonw "$mainPath" %*
"@
Set-Content -Path "$InstallDir\text2audiobook-gui.cmd" -Value $guiWrapper -Encoding ASCII
Write-Host "Wrote $InstallDir\text2audiobook-gui.cmd" -ForegroundColor Green

# 5. USER PATH (idempotent).
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$InstallDir*") {
    $newPath = if ($userPath) { "$userPath;$InstallDir" } else { $InstallDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    Write-Host "Added $InstallDir to USER PATH." -ForegroundColor Green
} else {
    Write-Host "$InstallDir already on USER PATH; skipping." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Done. Open a NEW PowerShell or cmd session and try:" -ForegroundColor Cyan
Write-Host "    text2audiobook list-providers"
Write-Host "    text2audiobook ?"
Write-Host "    text2audiobook-gui              (launches GUI)"
