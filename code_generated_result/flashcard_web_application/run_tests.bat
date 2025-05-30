
@echo off  REM Tắt echo lệnh để output Python capture dễ đọc hơn
setlocal EnableDelayedExpansion

REM Ghi trực tiếp ra stdout để Python capture được, không dùng file log ngay lập tức
echo --- run_tests.bat STARTED ---

REM Các lệnh sau đó mới chuyển hướng vào debug_tests.log
echo Current Directory (when batch started): "%CD%" > debug_tests.log 2>&1
echo PROJECT_ROOT variable (calculated): "%~dp0" >> debug_tests.log 2>&1

echo Changing directory to project root... >> debug_tests.log 2>&1
cd /d "%~dp0" >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to change to project root directory. Exiting with code %ERRORLEVEL%. >> debug_tests.log 2>&1
    exit /b 1
)
echo Current Directory (after cd): "%CD%" >> debug_tests.log 2>&1

echo Checking for Python at: "C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" >> debug_tests.log 2>&1
"C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" --version >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found at "C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe". Exiting with code %ERRORLEVEL%. >> debug_tests.log 2>&1
    exit /b 1
)

echo Attempting to activate virtual environment... >> debug_tests.log 2>&1
echo Activating script path: "%~dp0venv\Scripts\activate.bat" >> debug_tests.log 2>&1
call "%~dp0venv\Scripts\activate.bat" >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment. Error code: %ERRORLEVEL%. >> debug_tests.log 2>&1
    echo Please ensure the venv\Scripts\activate.bat exists and is not corrupted. >> debug_tests.log 2>&1
    exit /b 1
)
echo Virtual environment activated successfully. >> debug_tests.log 2>&1

echo Now, checking python.exe in PATH from activated venv: >> debug_tests.log 2>&1
where python.exe >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: python.exe not found in PATH after venv activation. This might indicate an issue with activate.bat. >> debug_tests.log 2>&1
)

echo Running pytest with --exitfirst... >> debug_tests.log 2>&1
"C:\Users\Hoang Duy\Documents\Phan Lac Hung\autocode_assistant\code_generated_result\flashcard_web_application\venv\Scripts\python.exe" -m pytest tests --exitfirst --tb=short -v > "test_results.log" 2>&1
set TEST_EXIT_CODE=%ERRORLEVEL%

echo Deactivating virtual environment... >> debug_tests.log 2>&1
deactivate >> debug_tests.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to deactivate virtual environment. >> debug_tests.log 2>&1
)

if %TEST_EXIT_CODE% neq 0 (
    echo ERROR: Tests failed. Check "test_results.log" for details. >> debug_tests.log 2>&1
    exit /b %TEST_EXIT_CODE%
)

echo Tests completed successfully. >> debug_tests.log 2>&1
exit /b 0
