@echo off
setlocal
cd /d "%~dp0..\english_learning"
if not exist ".venv\Scripts\activate.bat" (
  echo Run scripts\setup-backend-windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m flask --app app.server run --host 127.0.0.1 --port 5000
if errorlevel 1 (
  echo.
  echo API failed to start. Read the error message above.
  pause
)
