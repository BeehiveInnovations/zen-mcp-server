# PowerShell script to set up .env file for Docker usage on Windows

Write-Host "Setting up .env file for Gemini MCP Server Docker..."

# Get the current working directory (absolute path)
$CurrentDir = Get-Location

# Check if .env already exists
if (Test-Path .env) {
    Write-Host "Warning: .env file already exists! Skipping creation." -ForegroundColor Yellow
    Write-Host ""
} else {
    # Create the .env file
    @"
# Gemini MCP Server Docker Environment Configuration
# Generated on $(Get-Date)

# The absolute path to your project root on the host machine
# This should be the directory containing your code that you want to analyze
WORKSPACE_ROOT=$CurrentDir

# Your Gemini API key (get one from https://makersuite.google.com/app/apikey)
# IMPORTANT: Replace this with your actual API key
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: Set logging level (DEBUG, INFO, WARNING, ERROR)
# LOG_LEVEL=INFO
"@ | Out-File -FilePath .env -Encoding utf8

    Write-Host "Created .env file" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Next steps:"
Write-Host "1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key"
Write-Host "2. Run 'docker build -t gemini-mcp-server .' to build the Docker image"
Write-Host "3. Copy this configuration to your Claude Desktop config:"
Write-Host ""
Write-Host "===== COPY BELOW THIS LINE =====" -ForegroundColor Cyan
Write-Host @"
{
  "mcpServers": {
    "gemini": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "--env-file", "$CurrentDir\.env",
        "-v", "${CurrentDir}:/workspace:ro",
        "gemini-mcp-server:latest"
      ]
    }
  }
}
"@
Write-Host "===== COPY ABOVE THIS LINE =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Config file location:"
Write-Host "  Windows: %APPDATA%\Claude\claude_desktop_config.json"
Write-Host ""
Write-Host "Note: The configuration above mounts the current directory ($CurrentDir)"
Write-Host "as the workspace. You can change this path to any project directory you want to analyze."
Write-Host "Docker on Windows accepts both forward slashes and backslashes in paths."