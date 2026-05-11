$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Setup = Join-Path $PSScriptRoot "Setup-ForgeVault.ps1"

if (-not (Test-Path $Python)) {
    Write-Host "ForgeVault virtual environment not found. Running setup first..." -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Setup
}

if (-not (Test-Path $Python)) {
    throw "ForgeVault setup did not create .venv\Scripts\python.exe"
}

& $Python -m forgevault.desktop @args
