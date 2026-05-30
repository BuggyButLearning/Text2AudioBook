; Text2AudioBook Inno Setup script.
; Build: install Inno Setup 6.x then run `iscc text2audiobook.iss` from this dir.
; Output: installer\output\text2audiobook-setup-v0.1.0.exe

#define MyAppName        "Text2AudioBook"
#define MyAppVersion     "0.1.0"
#define MyAppPublisher   "BuggyButLearning"
#define MyAppURL         "https://github.com/BuggyButLearning/Text2AudioBook"
#define MyAppExeName     "launch-gui.cmd"

[Setup]
AppId={{8F3A4C7E-1B5D-4E2A-9F6B-2C8D7E1A3B5F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Text2AudioBook
DefaultGroupName=Text2AudioBook
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename=text2audiobook-setup-v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesEnvironment=yes
UninstallDisplayIcon={app}\repo\docs\icon.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
ArchitecturesInstallIn64BitMode=x64compatible
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; The repo (everything one level up from installer/).
Source: "..\*"; \
    DestDir: "{app}\repo"; \
    Flags: recursesubdirs createallsubdirs ignoreversion; \
    Excludes: ".git\*,.conda\*,output\*,*.pyc,__pycache__\*,.pytest_cache\*,.vscode\*,installer\output\*,installer\*.exe,test_tracking\*"

; The launcher scripts + helper scripts (copied to {app}, NOT {app}\repo).
Source: "text2audiobook.cmd.template"; DestDir: "{app}"; Flags: ignoreversion
Source: "launch-gui.cmd.template";     DestDir: "{app}"; Flags: ignoreversion

; Post-install / pre-uninstall PowerShell helpers (extracted to {tmp} via dontcopy).
Source: "post-install.ps1";  DestDir: "{app}"; Flags: ignoreversion
Source: "pre-uninstall.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; \
    Filename: "{app}\launch-gui.cmd"; \
    WorkingDir: "{app}\repo"; \
    Comment: "Launch the Text2AudioBook GUI"
Name: "{group}\{#MyAppName} CLI Help"; \
    Filename: "{cmd}"; \
    Parameters: "/k ""{app}\text2audiobook.cmd"" --help"; \
    WorkingDir: "{app}\repo"; \
    Comment: "Show CLI help in a console window"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Configure conda env + PATH + write resolved .cmd wrappers.
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\post-install.ps1"" -InstallDir ""{app}"" -RepoDir ""{app}\repo"""; \
    StatusMsg: "Configuring conda environment and PATH..."; \
    Flags: runhidden waituntilterminated

[UninstallRun]
; Strip install dir from USER PATH before files are deleted.
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\pre-uninstall.ps1"" -InstallDir ""{app}"""; \
    RunOnceId: "RemoveFromUserPath"; \
    Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  // Verify conda is on PATH; bail cleanly if missing.
  Result := Exec('cmd.exe', '/c where conda >nul 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not Result or (ResultCode <> 0) then begin
    MsgBox('Miniconda or Anaconda is required but was not found on PATH.' + #13#10 +
           'Install from https://docs.conda.io/en/latest/miniconda.html, ' +
           'restart your shell, then re-run this installer.',
           mbError, MB_OK);
    Result := False;
    exit;
  end;
  Result := True;
end;
