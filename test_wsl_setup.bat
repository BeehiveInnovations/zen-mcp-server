@echo off
REM Test script for Windows users to verify WSL setup

echo Testing WSL setup for Gemini MCP Server...
echo.

REM Check if WSL is available
wsl --status >nul 2>&1
if errorlevel 1 (
    echo ERROR: WSL is not installed or not available.
    echo Please install WSL2 from: https://docs.microsoft.com/en-us/windows/wsl/install
    exit /b 1
)

echo [OK] WSL is installed
echo.

REM Get default WSL distribution
for /f "tokens=1" %%i in ('wsl -l -q') do (
    set WSL_DISTRO=%%i
    goto :found_distro
)

:found_distro
echo Default WSL distribution: %WSL_DISTRO%
echo.

REM Test Python in WSL
echo Testing Python in WSL...
wsl python3 --version
if errorlevel 1 (
    echo ERROR: Python3 not found in WSL
    echo Please install Python in your WSL distribution:
    echo   wsl sudo apt update
    echo   wsl sudo apt install python3 python3-pip python3-venv
    exit /b 1
)

echo [OK] Python is available in WSL
echo.

REM Provide example configurations
echo Example Claude Desktop configurations:
echo.
echo For WSL (if your code is in Windows filesystem):
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "wsl.exe",
echo       "args": ["/mnt/c/path/to/gemini-mcp-server/run_gemini.sh"],
echo       "env": {
echo         "GEMINI_API_KEY": "your-key-here"
echo       }
echo     }
echo   }
echo }
echo.
echo For WSL (if your code is in WSL home directory - recommended):
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "wsl.exe",
echo       "args": ["~/gemini-mcp-server/run_gemini.sh"],
echo       "env": {
echo         "GEMINI_API_KEY": "your-key-here"
echo       }
echo     }
echo   }
echo }
echo.
echo For Native Windows:
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "C:\\path\\to\\gemini-mcp-server\\run_gemini.bat",
echo       "env": {
echo         "GEMINI_API_KEY": "your-key-here"
echo       }
echo     }
echo   }
echo }
