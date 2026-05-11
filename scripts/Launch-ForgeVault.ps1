$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot
$Python = "python"
if (Test-Path ".venv\Scripts\python.exe") { $Python = ".venv\Scripts\python.exe" }
& $Python -m pip install -e ".[dev]"
& $Python -m forgevault.desktop @args
