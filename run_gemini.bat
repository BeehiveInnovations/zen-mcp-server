@echo off
REM Windows batch script to run Gemini MCP server

REM Get the directory where this script is located
set SCRIPT_DIR=%~dp0

REM Change to script directory to ensure proper working directory
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
if not exist "%SCRIPT_DIR%venv\" (
    echo Virtual environment not found. Running setup... >&2
    
    REM Check if setup.bat exists
    if exist "%SCRIPT_DIR%setup.bat" (
        REM Run setup script
        call "%SCRIPT_DIR%setup.bat" >&2
        
        REM Check if setup was successful
        if errorlevel 1 (
            echo Setup failed. Please run setup.bat manually to see the error. >&2
            exit /b 1
        )
    ) else (
        echo Error: setup.bat not found. Please ensure you have the complete repository. >&2
        exit /b 1
    )
)

REM Activate virtual environment
call "%SCRIPT_DIR%venv\Scripts\activate.bat"

REM Run the server
python "%SCRIPT_DIR%server.py"