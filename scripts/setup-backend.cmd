@echo off
rem Creates the backend virtual environment, installs dependencies, then runs tests and lint.
rem Double-click it or run it from any terminal. A .cmd file is not affected by PowerShell's
rem script-execution policy. Venv creation can be silent for a few minutes: do not close it.
setlocal
cd /d "%~dp0..\backend" || exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment. This can take a few minutes with no output...
    python -m venv .venv || (echo FAILED: venv creation & exit /b 1)
)

echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || (echo FAILED: pip install & exit /b 1)

echo Running tests...
".venv\Scripts\python.exe" -m pytest -v
set TEST_EXIT=%ERRORLEVEL%

echo Running lint...
".venv\Scripts\python.exe" -m ruff check .
set LINT_EXIT=%ERRORLEVEL%

echo.
echo pytest exit code: %TEST_EXIT%   ruff exit code: %LINT_EXIT%   (0 means success)
echo Installed versions:
".venv\Scripts\python.exe" -m pip freeze
pause
