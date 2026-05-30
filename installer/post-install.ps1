# Inno Setup [Run] hook. Invoked once during install.
# Responsibilities:
#   1. Ensure the `text2audiobook` conda env exists (prompt user; create on yes)
#   2. Generate the .cmd wrappers from templates with the actual paths baked in
#   3. Add $InstallDir to USER PATH (idempotent)

param(
    [Parameter(Mandatory=$true)] [string] $InstallDir,
    [Parameter(Mandatory=$true)] [string] $RepoDir
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms

# Inno Setup runs us with --no-profile; conda's shell hook isn't loaded.
# `conda env list` works because conda is on PATH (verified by InitializeSetup).

# 1. Conda env presence.
$envExists = $false
try {
    $envExists = (conda env list 2>$null | Select-String '^text2audiobook\s') -ne $null
} catch {
    $envExists = $false
}

if (-not $envExists) {
    $choice = [System.Windows.Forms.MessageBox]::Show(
        "The 'text2audiobook' conda environment was not found.`n`n" +
        "Create it now from environment.yml? This takes 5-10 minutes and downloads dependencies (openai, kokoro, soundfile, etc).",
        "Text2AudioBook Setup",
        [System.Windows.Forms.MessageBoxButtons]::YesNo,
        [System.Windows.Forms.MessageBoxIcon]::Question
    )
    if ($choice -eq [System.Windows.Forms.DialogResult]::Yes) {
        $envYml = Join-Path $RepoDir "environment.yml"
        conda env create --file "$envYml" 2>&1 | Out-Host
        if ($LASTEXITCODE -ne 0) {
            [System.Windows.Forms.MessageBox]::Show(
                "conda env create failed (exit $LASTEXITCODE). You can retry manually:`n`n" +
                "conda env create --file ""$envYml""",
                "Text2AudioBook Setup",
                [System.Windows.Forms.MessageBoxButtons]::OK,
                [System.Windows.Forms.MessageBoxIcon]::Warning
            ) | Out-Null
        }
    } else {
        [System.Windows.Forms.MessageBox]::Show(
            "Skipped env creation. text2audiobook will not work until you run:`n`n" +
            "conda env create --file ""$(Join-Path $RepoDir 'environment.yml')""",
            "Text2AudioBook Setup",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information
        ) | Out-Null
    }
}

# 2. Resolve wrappers from templates.
$cliPath  = Join-Path $RepoDir "cli.py"
$mainPath = Join-Path $RepoDir "main.py"

$cliTmpl = Get-Content -Path (Join-Path $InstallDir "text2audiobook.cmd.template") -Raw
$cliResolved = $cliTmpl.Replace("{REPO_PATH}", $cliPath)
Set-Content -Path (Join-Path $InstallDir "text2audiobook.cmd") -Value $cliResolved -Encoding ASCII

$guiTmpl = Get-Content -Path (Join-Path $InstallDir "launch-gui.cmd.template") -Raw
$guiResolved = $guiTmpl.Replace("{REPO_PATH}", $mainPath)
Set-Content -Path (Join-Path $InstallDir "launch-gui.cmd") -Value $guiResolved -Encoding ASCII

# 3. USER PATH (idempotent).
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not $userPath) { $userPath = "" }
if ($userPath -notlike "*$InstallDir*") {
    $newPath = if ($userPath) { "$userPath;$InstallDir" } else { $InstallDir }
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
}
