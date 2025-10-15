# Development startup script for Persona-MCP dual-service architecture
# Usage: .\dev-start.ps1 [mcp|api|both]
# - mcp: Start only MCP server
# - api: Start only PersonaAPI server  
# - both: Start both servers (default)

param(
    [string]$Service = "both"
)

$Service = $Service.ToLower()
if ($Service -notin @("mcp", "api", "both")) {
    Write-Host "Invalid service specified. Use: mcp, api, or both" -ForegroundColor Red
    Write-Host "Usage: .\dev-start.ps1 [mcp|api|both]" -ForegroundColor Gray
    exit 1
}

Write-Host "Starting Persona-MCP Development Environment ($Service)" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""

# Function to cleanup background processes
function Cleanup {
    Write-Host ""
    Write-Host "Shutting down services..." -ForegroundColor Yellow
    if ($MCPProcess) {
        Stop-Process -Id $MCPProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "   MCP Server stopped" -ForegroundColor Green
    }
    if ($PersonaAPIProcess) {
        Stop-Process -Id $PersonaAPIProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "   PersonaAPI Server stopped" -ForegroundColor Green
    }
    Write-Host "   Cleanup complete" -ForegroundColor Green
    exit 0
}

# Set trap for cleanup
$null = Register-EngineEvent PowerShell.Exiting -Action { Cleanup }

# Check if virtual environment is activated and get Python path
$PythonPath = "python"
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment detected: $env:VIRTUAL_ENV" -ForegroundColor Green
    $PythonPath = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} elseif (Test-Path "venv\Scripts\python.exe") {
    Write-Host "Virtual environment not activated but found. Using venv Python..." -ForegroundColor Yellow
    $PythonPath = "venv\Scripts\python.exe"
    # Also set the VIRTUAL_ENV for the child processes
    $env:VIRTUAL_ENV = (Resolve-Path "venv").Path
} else {
    Write-Host "No virtual environment found. Please activate your venv first:" -ForegroundColor Red
    Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
    exit 1
}

Write-Host "Using Python: $PythonPath" -ForegroundColor Cyan

try {
    # Start MCP Intelligence Server (if requested)
    if ($Service -in @("mcp", "both")) {
        Write-Host "Starting MCP Intelligence Server (port 8000)..." -ForegroundColor Cyan
        $MCPProcess = Start-Process -FilePath $PythonPath -ArgumentList "-m", "persona_mcp.mcp.server" -PassThru -WindowStyle Hidden
        
        # Wait for MCP server to initialize
        Write-Host "   Waiting for MCP server to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
        
        # Check if MCP server started successfully
        if ($MCPProcess.HasExited) {
            Write-Host "   MCP server failed to start" -ForegroundColor Red
            exit 1
        }
        Write-Host "   MCP server started (PID: $($MCPProcess.Id))" -ForegroundColor Green
    }
    
    # Start PersonaAPI Server (if requested)
    if ($Service -in @("api", "both")) {
        Write-Host "Starting PersonaAPI Server (port 8081)..." -ForegroundColor Cyan
        $PersonaAPIProcess = Start-Process -FilePath $PythonPath -ArgumentList "-m", "persona_mcp.dashboard.server" -PassThru -WindowStyle Hidden
        
        # Wait for PersonaAPI server to initialize
        Write-Host "   Waiting for PersonaAPI server to initialize..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
        
        # Check if PersonaAPI server started successfully
        if ($PersonaAPIProcess.HasExited) {
            Write-Host "   PersonaAPI server failed to start" -ForegroundColor Red
            Cleanup
            exit 1
        }
        Write-Host "   PersonaAPI server started (PID: $($PersonaAPIProcess.Id))" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "Persona-MCP Development Environment Ready!" -ForegroundColor Green
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Services:" -ForegroundColor White
    if ($Service -in @("mcp", "both")) {
        Write-Host "  MCP Intelligence Server:  ws://localhost:8000/mcp" -ForegroundColor Cyan
    }
    if ($Service -in @("api", "both")) {
        Write-Host "  PersonaAPI Server:        http://localhost:8081" -ForegroundColor Cyan
        Write-Host "  API Documentation:        http://localhost:8081/docs" -ForegroundColor Cyan
    }
    Write-Host ""
    
    if ($Service -in @("api", "both")) {
        Write-Host "Quick Tests:" -ForegroundColor White
        Write-Host "  Test PersonaAPI: " -NoNewline -ForegroundColor White
        Write-Host "Invoke-RestMethod http://localhost:8081/api/personas" -ForegroundColor Gray
        Write-Host "  Health Check:    " -NoNewline -ForegroundColor White
        Write-Host "Invoke-RestMethod http://localhost:8081/api/health" -ForegroundColor Gray
        Write-Host "  Open Browser:    " -NoNewline -ForegroundColor White
        Write-Host "Start-Process http://localhost:8081" -ForegroundColor Gray
        Write-Host ""
    }
    
    if ($Service -eq "both") {
        Write-Host "Architecture:" -ForegroundColor White
        Write-Host "  [PersonaAPI     ]    [   MCP Server    ]" -ForegroundColor Gray
        Write-Host "  [  (port 8081)  ]<-->[  (port 8000)   ]" -ForegroundColor Gray
        Write-Host "  [               ]    [                 ]" -ForegroundColor Gray
        Write-Host "  [ HTTP/REST API ]    [ WebSocket       ]" -ForegroundColor Gray
        Write-Host "  [ Bot Management]    [ Intelligence    ]" -ForegroundColor Gray
        Write-Host "  [ Admin UI      ]    [ Pure MCP        ]" -ForegroundColor Gray
        Write-Host "           |                        |" -ForegroundColor Gray
        Write-Host "           +----------+-------------+" -ForegroundColor Gray
        Write-Host "                      |" -ForegroundColor Gray
        Write-Host "           [  Shared Core    ]" -ForegroundColor Gray
        Write-Host "           [  Foundation     ]" -ForegroundColor Gray
        Write-Host "           [                 ]" -ForegroundColor Gray
        Write-Host "           [ DatabaseMgr     ]" -ForegroundColor Gray
        Write-Host "           [ MemoryMgr       ]" -ForegroundColor Gray
        Write-Host "           [ ConfigMgr       ]" -ForegroundColor Gray
        Write-Host ""
    }
    
    Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
    Write-Host ""
    
    # Wait for interrupt
    while ($true) {
        Start-Sleep -Seconds 1
        $ProcessExited = $false
        if ($MCPProcess -and $MCPProcess.HasExited) {
            Write-Host "MCP Server has stopped unexpectedly" -ForegroundColor Red
            $ProcessExited = $true
        }
        if ($PersonaAPIProcess -and $PersonaAPIProcess.HasExited) {
            Write-Host "PersonaAPI Server has stopped unexpectedly" -ForegroundColor Red
            $ProcessExited = $true
        }
        if ($ProcessExited) { break }
    }
} catch {
    Write-Host "Error occurred: $_" -ForegroundColor Red
} finally {
    Cleanup
}