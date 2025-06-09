@echo off
REM Helper script to set up .env file for Docker usage on Windows

echo Setting up .env file for Gemini MCP Server Docker...

REM Get the current working directory (absolute path)
set CURRENT_DIR=%CD%

REM Check if .env already exists
if exist .env (
    echo Warning: .env file already exists! Skipping creation.
    echo.
) else (
    REM Create the .env file
    (
    echo # Gemini MCP Server Docker Environment Configuration
    echo # Generated on %DATE% %TIME%
    echo.
    echo # The absolute path to your project root on the host machine
    echo # This should be the directory containing your code that you want to analyze
    echo WORKSPACE_ROOT=%CURRENT_DIR%
    echo.
    echo # Your Gemini API key ^(get one from https://makersuite.google.com/app/apikey^)
    echo # IMPORTANT: Replace this with your actual API key
    echo GEMINI_API_KEY=your-gemini-api-key-here
    echo.
    echo # Optional: Set logging level ^(DEBUG, INFO, WARNING, ERROR^)
    echo # LOG_LEVEL=INFO
    ) > .env
    echo.
    echo Created .env file
    echo.
)
echo Next steps:
echo 1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key
echo 2. Run 'docker build -t gemini-mcp-server .' to build the Docker image
echo 3. Copy this configuration to your Claude Desktop config:
echo.
echo ===== COPY BELOW THIS LINE =====
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "docker",
echo       "args": [
echo         "run",
echo         "--rm",
echo         "-i",
echo         "--env-file", "%CURRENT_DIR%\.env",
echo         "-v", "%CURRENT_DIR%:/workspace:ro",
echo         "gemini-mcp-server:latest"
echo       ]
echo     }
echo   }
echo }
echo ===== COPY ABOVE THIS LINE =====
echo.
echo Config file location:
echo   Windows: %%APPDATA%%\Claude\claude_desktop_config.json
echo.
echo Note: The configuration above mounts the current directory ^(%CURRENT_DIR%^)
echo as the workspace. You can change this path to any project directory you want to analyze.