@echo off
REM Windows batch script to run Gemini MCP server

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Check if virtual environment exists
if exist "%SCRIPT_DIR%venv\Scripts\activate.bat" (
    REM Activate the virtual environment
    call "%SCRIPT_DIR%venv\Scripts\activate.bat"
    python "%SCRIPT_DIR%server.py"
) else (
    REM Try to use python directly if no venv
    echo Warning: Virtual environment not found at %SCRIPT_DIR%venv >&2
    echo Attempting to run with system Python... >&2
    python "%SCRIPT_DIR%server.py"
    if errorlevel 1 (
        echo Error: Failed to run server. Please ensure Python is installed and dependencies are available. >&2
        echo Run: python -m venv venv >&2
        echo Then: venv\Scripts\activate >&2
        echo Then: pip install -r requirements.txt >&2
        exit /b 1
    )
)