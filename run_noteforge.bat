@echo off
setlocal
set ROOT=%~dp0
set PY=%ROOT%..\.venv\Scripts\python.exe
if not exist "%PY%" (
  echo Python not found: %PY%
  exit /b 1
)
cd /d "%ROOT%"
"%PY%" -m pip install -r requirements.txt >nul
start "Sakura NoteForge" "%PY%" -m noteforge.main
