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

Write-Host ""
Write-Host "Build complete: $artifact"
Write-Host "Run it with:"
Write-Host "  .\dist\ForgeVaultDesktop.exe"
