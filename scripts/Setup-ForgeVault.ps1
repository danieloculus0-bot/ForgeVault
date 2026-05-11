$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step($Message) {
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Get-PythonCommand {
    $candidates = @("py -3", "python")
    foreach ($candidate in $candidates) {
        try {
            $parts = $candidate -split " "
            $exe = $parts[0]
            $args = $parts[1..($parts.Length - 1)]
            if ($parts.Length -eq 1) { $args = @() }
            & $exe @args --version 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return $candidate }
        } catch {}
    }
    throw "Python 3 was not found. Install Python 3 or add it to PATH, then rerun setup."
}

Write-Step "Checking Python"
$PythonCommand = Get-PythonCommand
Write-Host "Using: $PythonCommand" -ForegroundColor Green

Write-Step "Creating virtual environment"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    $parts = $PythonCommand -split " "
    $exe = $parts[0]
    $args = $parts[1..($parts.Length - 1)]
    if ($parts.Length -eq 1) { $args = @() }
    & $exe @args -m venv .venv
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Virtual environment Python was not created: $Python" }

Write-Step "Upgrading installer tools"
& $Python -m pip install --upgrade pip setuptools wheel

Write-Step "Installing ForgeVault"
& $Python -m pip install -e ".[dev]"

Write-Step "Running smoke import"
& $Python -c "import forgevault.main, forgevault.desktop; print('ForgeVault import OK')"

Write-Step "Setup complete"
Write-Host "Launch with:" -ForegroundColor Green
Write-Host ".\scripts\Launch-ForgeVault.ps1 --manage-folder \"C:\Engineering\Jobs\"" -ForegroundColor Yellow
