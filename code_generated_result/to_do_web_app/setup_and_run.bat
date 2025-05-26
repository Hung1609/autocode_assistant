@echo off
setlocal EnableDelayedExpansion

:: Setup and run the generated application
echo Setting up and running the application... > debug.log 2>&1

:: Set project root
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%" >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%. >> debug.log 2>&1
    echo ERROR: Failed to change to project root directory %PROJECT_ROOT%.
    pause
    exit /b 1
)
echo Project root set to: %PROJECT_ROOT% >> debug.log 2>&1

:: Check for Python
echo Checking for Python... >> debug.log 2>&1
"C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe" --version >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python is not installed at C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe. Please ensure Python 3.8+ is installed. >> debug.log 2>&1
    echo ERROR: Python is not installed at C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe. Please ensure Python 3.8+ is installed.
    pause
    exit /b 1
)
echo Python found. >> debug.log 2>&1

:: Create and activate virtual environment in project directory
echo Setting up virtual environment in !PROJECT_ROOT!\venv... >> debug.log 2>&1
if not exist "!PROJECT_ROOT!\venv" (
    "C:\Users\ADMIN\AppData\Local\Programs\Python\Python312\python.exe" -m venv "!PROJECT_ROOT!\venv" >> debug.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv. >> debug.log 2>&1
        echo ERROR: Failed to create virtual environment in !PROJECT_ROOT!\venv.
        pause
        exit /b 1
    )
)
call "!PROJECT_ROOT!\venv\Scripts\activate.bat" >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat. >> debug.log 2>&1
    echo ERROR: Failed to activate virtual environment. Check !PROJECT_ROOT!\venv\Scripts\activate.bat.
    pause
    exit /b 1
)
echo Virtual environment activated. >> debug.log 2>&1

:: Install dependencies
echo Installing dependencies... >> debug.log 2>&1
if exist "requirements.txt" (
    pip install -r requirements.txt >> debug.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo ERROR: Failed to install dependencies. Check requirements.txt. >> debug.log 2>&1
        echo ERROR: Failed to install dependencies. Check requirements.txt.
        pause
        exit /b 1
    )
) else (
    echo WARNING: requirements.txt not found. Skipping dependency installation. >> debug.log 2>&1
    echo WARNING: requirements.txt not found. Skipping dependency installation.
)
echo Dependencies installed. >> debug.log 2>&1

:: Run the application
echo Starting the application... >> debug.log 2>&1
python -m uvicorn backend.main:app --reload --port 8001 >> debug.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to start the application. Check backend/main.py and uvicorn configuration. >> debug.log 2>&1
    echo ERROR: Failed to start the application. Check backend/main.py and uvicorn configuration.
    pause
    exit /b 1
)
echo Application started. >> debug.log 2>&1

pause
exit /b 0
