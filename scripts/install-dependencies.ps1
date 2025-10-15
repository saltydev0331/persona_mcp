# Install additional dependencies for PersonaAPI server
# Run this after activating your virtual environment

Write-Host "Installing PersonaAPI Server Dependencies" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Please activate your virtual environment first:" -ForegroundColor Red
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host "Virtual environment: $env:VIRTUAL_ENV" -ForegroundColor Green
Write-Host ""

# List of additional dependencies needed
$Dependencies = @(
    "fastapi",
    "uvicorn[standard]",
    "websockets",
    "aiohttp"
)

Write-Host "Installing dependencies..." -ForegroundColor Cyan
foreach ($dep in $Dependencies) {
    Write-Host "Installing $dep..." -ForegroundColor Yellow
    $result = & pip install $dep
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Successfully installed $dep" -ForegroundColor Green
    } else {
        Write-Host "Failed to install $dep" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run the development environment:" -ForegroundColor White
Write-Host "  .\scripts\dev-start.ps1" -ForegroundColor Cyan