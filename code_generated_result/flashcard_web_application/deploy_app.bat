@echo off
setlocal EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

call "%PROJECT_ROOT%venv\Scripts\activate.bat"
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
deactivate
exit /b 0
