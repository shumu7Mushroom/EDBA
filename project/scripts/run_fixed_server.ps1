Write-Host "Starting fixed mock bank server..." -ForegroundColor Green

# Get the current directory and set up paths
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectDir = Split-Path -Parent $scriptDir
$serverScript = Join-Path $scriptDir "fixed_mock_bank_server.py"

# Verify the script exists
if (-not (Test-Path $serverScript)) {
    Write-Host "Error: Could not find server script at $serverScript" -ForegroundColor Red
    exit 1
}

Write-Host "Server script found at: $serverScript" -ForegroundColor Cyan
Write-Host "Starting server. Press Ctrl+C to stop."
Write-Host "====================================================="

# Start the server
python $serverScript
