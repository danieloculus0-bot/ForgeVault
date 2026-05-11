@echo off
setlocal
cd /d "%~dp0\.."
set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" set PYTHON_EXE=.venv\Scripts\python.exe
%PYTHON_EXE% -m pip install -e ".[dev]" || exit /b 1
%PYTHON_EXE% -m forgevault.desktop %*
