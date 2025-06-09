@echo off
REM Gemini MCP Server Setup Script for Windows
REM This script helps users set up the virtual environment and install dependencies

echo Gemini MCP Server Setup
echo =======================

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.10 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation.
    exit /b 1
)

REM Display Python version
echo Found Python:
python --version

REM Check Python version is at least 3.10
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

if %PYTHON_MAJOR% LSS 3 (
    goto :pythonTooOld
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 10 (
    goto :pythonTooOld
)
goto :pythonOk

:pythonTooOld
echo Error: Python 3.10 or higher is required (you have Python %PYTHON_VERSION%)
echo.
echo The 'mcp' package requires Python 3.10 or newer.
echo Please download and install Python from https://python.org
echo Make sure to check "Add Python to PATH" during installation.
exit /b 1

:pythonOk

REM Check if venv exists
if exist "venv\" (
    echo Virtual environment already exists
) else (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Error: Failed to create virtual environment
        exit /b 1
    )
    echo Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo Error: Failed to install dependencies
    echo Please check the error messages above and try again.
    exit /b 1
) else (
    echo.
    echo Setup completed successfully!
    echo.
    echo Next steps:
    echo 1. Get your Gemini API key from: https://makersuite.google.com/app/apikey
    echo 2. Configure Claude Desktop with your API key (see README.md)
    echo 3. Restart Claude Desktop
    echo.
    echo Note: The virtual environment has been activated for this session.
    echo The run_gemini.bat script will automatically activate it when needed.
)