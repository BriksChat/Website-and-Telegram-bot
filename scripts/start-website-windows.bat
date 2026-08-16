@echo off
setlocal
cd /d "%~dp0..\website"
if not exist "..\english_learning\.venv\Scripts\python.exe" (
  echo Run scripts\setup-backend-windows.bat first.
  pause
  exit /b 1
)
start "LearEnglish website" http://127.0.0.1:8000
"..\english_learning\.venv\Scripts\python.exe" -m http.server 8000 --bind 127.0.0.1
