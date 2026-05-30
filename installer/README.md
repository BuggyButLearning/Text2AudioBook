# Building the Windows Installer

`text2audiobook-setup-v0.1.0.exe` is built from `text2audiobook.iss` via Inno Setup.

## Prerequisites

1. **Inno Setup 6.x** on the build machine: https://jrsoftware.org/isdl.php
   Free, MIT-licensed, ~3 MB. Provides `iscc.exe` (the compiler).

2. **The repo** at a clean state — `installer/output/` is gitignored but rebuild from a fresh clone if shipping a release.

## Build

```cmd
cd installer
iscc text2audiobook.iss
```

Or with the full path to iscc:

```cmd
"C:\Program Files (x86)\Inno Setup 6\iscc.exe" text2audiobook.iss
```

Output: `installer\output\text2audiobook-setup-v0.1.0.exe` (~2-5 MB; the repo is the only payload).

## Test

On a clean Windows user profile (or VM) with Miniconda already installed:

1. Run the `.exe`. Wizard completes without UAC prompt (per-user install).
2. **Conda env prompt:** if `text2audiobook` env isn't present, accept the dialog. 5-10 min to create.
3. **Add/Remove Programs:** lists "Text2AudioBook 0.1.0".
4. **Start menu:** `Text2AudioBook` shortcut → GUI window opens (no console flash).
5. **CLI:** open a NEW PowerShell or cmd, run `text2audiobook list-providers` → 3 lines (OpenAI, Ollama, Kokoro).
6. **No-args help:** `text2audiobook` and `text2audiobook ?` both print help and exit 0.
7. **Uninstall** via Add/Remove Programs → install dir gone, USER PATH stripped of the install dir, env preserved.

## What ships inside

| Path | Source |
|------|--------|
| `{app}\repo\` | repo root (excluding `.git`, `.conda`, `output`, `__pycache__`, etc.) |
| `{app}\text2audiobook.cmd` | generated at install time from `text2audiobook.cmd.template` |
| `{app}\launch-gui.cmd` | generated at install time from `launch-gui.cmd.template` |
| `{app}\post-install.ps1` | conda env check + wrapper templating + USER PATH write |
| `{app}\pre-uninstall.ps1` | USER PATH cleanup |

## SmartScreen

First-run users see "Windows protected your PC" (unsigned binary). They click `More info → Run anyway`. Document this in release notes. v0.2 acquires a code-signing certificate.

## Versioning

Bump `#define MyAppVersion "0.1.0"` at the top of `text2audiobook.iss` for each release. The `AppId` UUID stays the same forever so Add/Remove Programs replaces (not duplicates) prior versions.
