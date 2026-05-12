$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Setup = Join-Path $PSScriptRoot "Setup-ForgeVault.ps1"
$Dist = Join-Path $RepoRoot "dist"
$Build = Join-Path $RepoRoot "build"
$Icon = Join-Path $RepoRoot "assets\icon\forgevault-icon.ico"

if (-not (Test-Path $Python)) {
    Write-Host "ForgeVault virtual environment not found. Running setup first..." -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File $Setup
}

if (-not (Test-Path $Python)) {
    throw "ForgeVault setup did not create .venv\Scripts\python.exe"
}

Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
& $Python -m pip install --upgrade pyinstaller

if (Test-Path $Dist) { Remove-Item -Recurse -Force $Dist }
if (Test-Path $Build) { Remove-Item -Recurse -Force $Build }

$Args = @(
    "-m", "PyInstaller",
    "--name", "ForgeVault",
    "--onefile",
    "--noconfirm",
    "--clean",
    "--add-data", "frontend;frontend",
    "--hidden-import", "forgevault.api.desktop",
    "--hidden-import", "forgevault.source_folders_model"
)

if (Test-Path $Icon) {
    $Args += @("--icon", $Icon)
}

$Args += @("backend\forgevault\desktop.py")

Write-Host "Building ForgeVault.exe..." -ForegroundColor Cyan
& $Python @Args

$Exe = Join-Path $Dist "ForgeVault.exe"
if (-not (Test-Path $Exe)) {
    throw "Build failed: dist\ForgeVault.exe was not created"
}

Write-Host "ForgeVault.exe created:" -ForegroundColor Green
Write-Host $Exe
