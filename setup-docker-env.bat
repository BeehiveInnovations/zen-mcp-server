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
    REM Check if GEMINI_API_KEY is already set in environment
    if defined GEMINI_API_KEY (
        set API_KEY_VALUE=%GEMINI_API_KEY%
        echo Found existing GEMINI_API_KEY in environment
    ) else (
        set API_KEY_VALUE=your-gemini-api-key-here
    )
    
    REM Create the .env file
    (
    echo # Gemini MCP Server Docker Environment Configuration
    echo # Generated on %DATE% %TIME%
    echo.
    echo # Your Gemini API key ^(get one from https://makersuite.google.com/app/apikey^)
    echo # IMPORTANT: Replace this with your actual API key
    echo GEMINI_API_KEY=%API_KEY_VALUE%
    ) > .env
    echo.
    echo Created .env file
    echo.
)

REM Check if Docker is installed and running
where docker >nul 2>nul
if %errorlevel% neq 0 (
    echo Warning: Docker is not installed. Please install Docker first.
    echo Visit: https://docs.docker.com/get-docker/
) else (
    REM Check if Docker daemon is running
    docker info >nul 2>nul
    if %errorlevel% neq 0 (
        echo Warning: Docker daemon is not running. Please start Docker.
    ) else (
        REM Clean up and build Docker image
        echo.
        echo Building Docker image...
        
        REM Stop running containers
        echo   - Checking for running containers...
        for /f "tokens=*" %%i in ('docker ps -q --filter ancestor^=gemini-mcp-server 2^>nul') do (
            docker stop %%i >nul 2>&1
        )
        
        REM Remove containers
        echo   - Removing old containers...
        for /f "tokens=*" %%i in ('docker ps -aq --filter ancestor^=gemini-mcp-server 2^>nul') do (
            docker rm %%i >nul 2>&1
        )
        
        REM Remove existing image
        echo   - Removing old image...
        docker rmi gemini-mcp-server:latest >nul 2>&1
        
        REM Build fresh image
        echo   - Building fresh image with --no-cache...
        docker build -t gemini-mcp-server:latest . --no-cache >nul 2>&1
        if %errorlevel% equ 0 (
            echo Docker image built successfully!
        ) else (
            echo Failed to build Docker image. Run 'docker build -t gemini-mcp-server:latest .' manually to see errors.
        )
        echo.
    )
)

echo Next steps:
if "%API_KEY_VALUE%"=="your-gemini-api-key-here" (
    echo 1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key
    echo 2. Copy this configuration to your Claude Desktop config:
) else (
    echo 1. Copy this configuration to your Claude Desktop config:
)
echo.
echo ===== COPY BELOW THIS LINE =====
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "%CURRENT_DIR%\gemini-mcp-docker.bat"
echo     }
echo   }
echo }
echo ===== COPY ABOVE THIS LINE =====
echo.
echo Alternative: If you prefer the direct Docker command:
echo {
echo   "mcpServers": {
echo     "gemini": {
echo       "command": "docker",
echo       "args": [
echo         "run",
echo         "--rm",
echo         "-i",
echo         "--env-file", "%CURRENT_DIR%\.env",
echo         "-e", "WORKSPACE_ROOT=%USERPROFILE%",
echo         "-v", "%USERPROFILE%:/workspace:ro",
echo         "gemini-mcp-server:latest"
echo       ]
echo     }
echo   }
echo }
echo.
echo Config file location:
echo   Windows: %%APPDATA%%\Claude\claude_desktop_config.json
echo.
echo Note: This configuration mounts your user directory ^(%USERPROFILE%^).
echo Docker can access any file within your user directory.
echo.
echo If you want to restrict access to a specific directory:
echo Change both the mount ^(-v^) and WORKSPACE_ROOT to match:
echo Example: -v "%CURRENT_DIR%:/workspace:ro" and WORKSPACE_ROOT=%CURRENT_DIR%
echo The container will automatically use /workspace as the sandbox boundary.