# Platform-independent configuration
import os
import sys
import platform
from pathlib import Path
from typing import Dict, List, Optional

class PlatformConfig:
    """Handle platform-specific configurations"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == 'windows'
        self.is_linux = self.system == 'linux'
        self.is_mac = self.system == 'darwin'
    
    def get_python_executable(self) -> str:
        """Get the current Python executable path"""
        return sys.executable
    
    def get_venv_activate_script(self, venv_path: str) -> str:
        """Get the virtual environment activation script path"""
        if self.is_windows:
            return os.path.join(venv_path, 'Scripts', 'activate.bat')
        else:
            return os.path.join(venv_path, 'bin', 'activate')
    
    def get_startup_script_extension(self) -> str:
        """Get the appropriate startup script extension"""
        return '.bat' if self.is_windows else '.sh'
    
    def generate_startup_script(self, project_root: str, backend_module_path: str, 
                              framework: str = 'fastapi') -> str:
        """Generate platform-specific startup script"""
        if self.is_windows:
            return self._generate_windows_batch(project_root, backend_module_path, framework)
        else:
            return self._generate_unix_shell(project_root, backend_module_path, framework)
    
    def _generate_windows_batch(self, project_root: str, backend_module_path: str, 
                               framework: str) -> str:
        python_path = self.get_python_executable()
        run_command = self._get_run_command(backend_module_path, framework)
        
        return f'''@echo off
setlocal EnableDelayedExpansion

echo Setting up and running the application...
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo Checking for Python...
"{python_path}" --version
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found
    pause
    exit /b 1
)

echo Setting up virtual environment...
if not exist "venv" (
    "{python_path}" -m venv venv
)
call venv\\Scripts\\activate.bat

echo Installing dependencies...
if exist "requirements.txt" (
    pip install -r requirements.txt
)

echo Starting application...
{run_command}
pause
'''
    
    def _generate_unix_shell(self, project_root: str, backend_module_path: str, 
                            framework: str) -> str:
        python_path = self.get_python_executable()
        run_command = self._get_run_command(backend_module_path, framework)
        
        return f'''#!/bin/bash
set -e

echo "Setting up and running the application..."
cd "$(dirname "$0")"

echo "Checking for Python..."
if ! command -v "{python_path}" &> /dev/null; then
    echo "ERROR: Python not found"
    exit 1
fi

echo "Setting up virtual environment..."
if [ ! -d "venv" ]; then
    "{python_path}" -m venv venv
fi
source venv/bin/activate

echo "Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

echo "Starting application..."
{run_command}
'''
    
    def _get_run_command(self, backend_module_path: str, framework: str) -> str:
        """Get the appropriate run command for the framework"""
        if framework.lower() == 'fastapi':
            return f'python -m uvicorn {backend_module_path}:app --reload --port 8001'
        elif framework.lower() == 'flask':
            return f'python -m flask --app {backend_module_path.replace(".", "/")} run --port 8001'
        elif framework.lower() == 'django':
            return 'python manage.py runserver 8001'
        else:
            return f'python {backend_module_path.replace(".", "/")}.py'

# Global instance
platform_config = PlatformConfig()
