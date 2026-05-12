$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

Write-Host "=== ForgeVault Windows Desktop Build ==="
Write-Host "Repo: $repo"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating local virtual environment..."
    py -3.11 -m venv .venv
}

$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Python venv not found at $python"
}

Write-Host "Upgrading pip..."
& $python -m pip install --upgrade pip

Write-Host "Installing ForgeVault dev package and PyInstaller..."
& $python -m pip install -e ".[dev]"
& $python -m pip install pyinstaller

Write-Host "Running smoke test before packaging..."
& $python scripts\ci_smoke.py

Write-Host "Building ForgeVaultDesktop.exe..."
& $python -m PyInstaller --noconfirm --clean --name ForgeVaultDesktop --onefile --collect-all forgevault --add-data "frontend;frontend" backend\forgevault\desktop.py

$artifact = Join-Path $repo "dist\ForgeVaultDesktop.exe"
if (-not (Test-Path $artifact)) {
    throw "Build failed. Missing $artifact"
}

$package = Join-Path $repo "dist\ForgeVaultDesktop-windows"
New-Item -ItemType Directory -Force -Path $package | Out-Null
Copy-Item $artifact (Join-Path $package "ForgeVaultDesktop.exe") -Force
Copy-Item $artifact (Join-Path $package "START-FORGEVAULT.exe") -Force

@"
ForgeVault Desktop - Quick Start

1. Double-click START-FORGEVAULT.exe.
2. Your browser should open automatically.
3. In the left panel, click Browse for Source Folder or paste a folder path.
4. Click Add Source Folder.
5. Click Index Selected.
6. Search UNMAPPED to find files that need cleanup.

Safe rule:
ForgeVault indexes files and copies managed versions into its local vault. Removing a source folder from the UI removes it from the ForgeVault index only. It does not delete your real files.

Default local URL:
http://127.0.0.1:8765/ui

Default data folder:
%LOCALAPPDATA%\ForgeVault
"@ | Set-Content -Encoding UTF8 (Join-Path $package "START-HERE.txt")

@"
@echo off
cd /d "%~dp0"
start "" "%~dp0START-FORGEVAULT.exe"
"@ | Set-Content -Encoding ASCII (Join-Path $package "START-FORGEVAULT.bat")

Write-Host ""
Write-Host "Build complete: $artifact"
Write-Host "Packaged folder: $package"
Write-Host "Run it with:"
Write-Host "  .\dist\ForgeVaultDesktop-windows\START-FORGEVAULT.exe"
