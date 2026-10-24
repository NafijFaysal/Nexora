@echo off
rem Starts the backend bound to this computer only (127.0.0.1). API docs: http://127.0.0.1:8000/docs
setlocal
cd /d "%~dp0..\backend" || exit /b 1
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
