@echo off
setlocal
cd /d "%~dp0\.."

set PYTHON_EXE=%CD%\.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
  echo ForgeVault virtual environment not found. Running setup first...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-ForgeVault.ps1"
)

if not exist "%PYTHON_EXE%" (
  echo ForgeVault setup did not create .venv\Scripts\python.exe
  exit /b 1
)

"%PYTHON_EXE%" -m forgevault.desktop %*
