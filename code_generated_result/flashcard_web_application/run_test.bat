
@echo off  REM Turn off echo to make Python capture output easier to read
setlocal EnableDelayedExpansion

REM Write directly to stdout so Python can capture, don't use log file immediately
echo --- run_test.bat STARTED ---

REM The following commands are redirected to debug_test_agent.log
echo Current Directory (when batch started): "%CD%" > debug_test_agent.log 2>&1
echo PROJECT_ROOT variable (calculated): "%~dp0" >> debug_test_agent.log 2>&1

echo Changing directory to project root... >> debug_test_agent.log 2>&1
cd /d "%~dp0" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory. Exiting with code %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    exit /b 1
)
echo Current Directory (after cd): "%CD%" >> debug_test_agent.log 2>&1

echo Cleaning up previous test log file... >> debug_test_agent.log 2>&1
if exist "test_results.log" (
    del "test_results.log" >> debug_test_agent.log 2>&1
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to delete old test log file: "test_results.log". >> debug_test_agent.log 2>&1
    ) else (
        echo Old test log file deleted: "test_results.log". >> debug_test_agent.log 2>&1
    )
) else (
    echo No old test log file to delete: "test_results.log". >> debug_test_agent.log 2>&1
)

echo Checking for Python at: "C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" >> debug_test_agent.log 2>&1
"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" --version >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found at "C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe". Exiting with code %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    exit /b 1
)

echo Attempting to activate virtual environment... >> debug_test_agent.log 2>&1
echo Activating script path: "%~dp0venv\Scripts\activate.bat" >> debug_test_agent.log 2>&1
call "%~dp0venv\Scripts\activate.bat" >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Error code: %ERRORLEVEL%. >> debug_test_agent.log 2>&1
    echo Please ensure the venv\Scripts\activate.bat exists and is not corrupted. >> debug_test_agent.log 2>&1
    exit /b 1
)
echo Virtual environment activated successfully. >> debug_test_agent.log 2>&1

echo Now, checking python.exe in PATH from activated venv: >> debug_test_agent.log 2>&1
where python.exe >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: python.exe not found in PATH after venv activation. This might indicate an issue with activate.bat. >> debug_test_agent.log 2>&1
)

echo Running pytest with --exitfirst and --tb=long... >> debug_test_agent.log 2>&1
"C:\Users\ADMIN\Documents\Foxconn\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" -m pytest tests --exitfirst --tb=long -v > "test_results.log" 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%

echo Deactivating virtual environment... >> debug_test_agent.log 2>&1
deactivate >> debug_test_agent.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to deactivate virtual environment. >> debug_test_agent.log 2>&1
)

if %TEST_EXIT_CODE% neq 0 (
    echo ERROR: Tests failed. Check "test_results.log" for details. >> debug_test_agent.log 2>&1
    exit /b %TEST_EXIT_CODE%
)

echo Tests completed successfully. >> debug_test_agent.log 2>&1
exit /b 0
