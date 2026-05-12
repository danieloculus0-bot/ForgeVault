$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Svg = Join-Path $RepoRoot "assets\icon\forgevault-icon.svg"
$Png = Join-Path $RepoRoot "assets\icon\forgevault-icon-256.png"
$Ico = Join-Path $RepoRoot "assets\icon\forgevault-icon.ico"
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Svg)) {
    throw "Missing SVG icon source: $Svg"
}

if (-not (Test-Path $Python)) {
    throw "Missing Python venv. Run scripts\Setup-ForgeVault.ps1 first."
}

Write-Host "Installing icon conversion dependencies..." -ForegroundColor Cyan
& $Python -m pip install --upgrade cairosvg pillow

$Code = @'
from pathlib import Path
from PIL import Image
import cairosvg

repo = Path(__file__).resolve().parents[1]
svg = repo / "assets" / "icon" / "forgevault-icon.svg"
png = repo / "assets" / "icon" / "forgevault-icon-256.png"
ico = repo / "assets" / "icon" / "forgevault-icon.ico"

cairosvg.svg2png(url=str(svg), write_to=str(png), output_width=256, output_height=256)
base = Image.open(png).convert("RGBA")
sizes = [(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)]
base.save(ico, sizes=sizes)
print(ico)
'@

$Temp = Join-Path $env:TEMP "make-forgevault-icon.py"
Set-Content -Path $Temp -Value $Code -Encoding UTF8
& $Python $Temp
Remove-Item $Temp -Force

Write-Host "ForgeVault icon created:" -ForegroundColor Green
Write-Host $Ico
