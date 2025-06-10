# PowerShell script to set up .env file for Docker usage on Windows

Write-Host "Setting up .env file for Gemini MCP Server Docker..."

# Get the current working directory (absolute path)
$CurrentDir = Get-Location

# Check if .env already exists
if (Test-Path .env) {
    Write-Host "Warning: .env file already exists! Skipping creation." -ForegroundColor Yellow
    Write-Host ""
} else {
    # Check if GEMINI_API_KEY is already set in environment
    if ($env:GEMINI_API_KEY) {
        $ApiKeyValue = $env:GEMINI_API_KEY
        Write-Host "Found existing GEMINI_API_KEY in environment" -ForegroundColor Green
    } else {
        $ApiKeyValue = "your-gemini-api-key-here"
    }
    
    # Create the .env file
    @"
# Gemini MCP Server Docker Environment Configuration
# Generated on $(Get-Date)

# Your Gemini API key (get one from https://makersuite.google.com/app/apikey)
# IMPORTANT: Replace this with your actual API key
GEMINI_API_KEY=$ApiKeyValue
"@ | Out-File -FilePath .env -Encoding utf8

    Write-Host "Created .env file" -ForegroundColor Green
    Write-Host ""
}

Write-Host "Next steps:"
if ($ApiKeyValue -eq "your-gemini-api-key-here") {
    Write-Host "1. Edit .env and replace 'your-gemini-api-key-here' with your actual Gemini API key"
    Write-Host "2. Run 'docker build -t gemini-mcp-server .' to build the Docker image"
    Write-Host "3. Copy this configuration to your Claude Desktop config:"
} else {
    Write-Host "1. Run 'docker build -t gemini-mcp-server .' to build the Docker image"
    Write-Host "2. Copy this configuration to your Claude Desktop config:"
}
Write-Host ""
Write-Host "===== COPY BELOW THIS LINE =====" -ForegroundColor Cyan
Write-Host @"
{
  "mcpServers": {
    "gemini": {
      "command": "$CurrentDir\gemini-mcp-docker.ps1"
    }
  }
}
"@
Write-Host "===== COPY ABOVE THIS LINE =====" -ForegroundColor Cyan
Write-Host ""
Write-Host "Alternative: If you prefer the direct Docker command:"
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
        "-e", "WORKSPACE_ROOT=$env:USERPROFILE",
        "-v", "${env:USERPROFILE}:/workspace:ro",
        "gemini-mcp-server:latest"
      ]
    }
  }
}
"@
Write-Host ""
Write-Host "Config file location:"
Write-Host "  Windows: %APPDATA%\Claude\claude_desktop_config.json"
Write-Host ""
Write-Host "Note: This configuration mounts your user directory ($env:USERPROFILE)."
Write-Host "Docker can access any file within your user directory."
Write-Host ""
Write-Host "If you want to restrict access to a specific directory:"
Write-Host "Change both the mount (-v) and WORKSPACE_ROOT to match:"
Write-Host "Example: -v `"$CurrentDir:/workspace:ro`" and WORKSPACE_ROOT=$CurrentDir"
Write-Host "The container will automatically use /workspace as the sandbox boundary."