@echo off
setlocal
cd /d "%~dp0..\english_learning"

set "PYTHON_COMMAND="
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if not errorlevel 1 set "PYTHON_COMMAND=python"

if not defined PYTHON_COMMAND (
  py -3.12 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_COMMAND=py -3.12"
)

if not defined PYTHON_COMMAND (
  echo Python was not found. Starting Python 3.12 installation through winget...
  where winget
  if errorlevel 1 goto python_error
  winget install --exact --id Python.Python.3.12
  if errorlevel 1 goto python_error
  echo Close this window and run this file again after Python installation.
  pause
  exit /b 0
)

echo Creating the virtual environment...
%PYTHON_COMMAND% -m venv .venv
if errorlevel 1 goto venv_error

call .venv\Scripts\activate.bat
echo Updating pip...
python -m pip install --upgrade pip
if errorlevel 1 goto packages_error

echo Installing project packages. Please wait...
python -m pip install -r requirements.txt
if errorlevel 1 goto packages_error

if not exist "..\.env" copy "..\.env.example" "..\.env"
if errorlevel 1 goto env_error

echo.
echo Backend environment is ready.
echo Local .env file is ready in the project root.
pause
exit /b 0

:python_error
echo Python installation failed. Install Python 3.12 or newer and run this file again.
pause
exit /b 1

:venv_error
echo Virtual environment creation failed.
pause
exit /b 1

:packages_error
echo Package installation failed. Check the messages above and your internet connection.
pause
exit /b 1

:env_error
echo The .env file could not be created. Check that .env.example exists in the project root.
pause
exit /b 1
