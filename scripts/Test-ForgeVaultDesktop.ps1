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

Write-Host "Launching ForgeVault Desktop test mode..." -ForegroundColor Cyan
Write-Host "UI will open at http://127.0.0.1:8765/ui" -ForegroundColor DarkGray
Write-Host "Close this PowerShell window or press Ctrl+C to stop the server." -ForegroundColor DarkGray

& $Python -m forgevault.desktop --host 127.0.0.1 --port 8765
