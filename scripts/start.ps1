# Ira Startup Script
# Run this script with: .\scripts\start.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Ira - Local AI Assistant    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $ProjectRoot) { $ProjectRoot = "c:\Users\nandi\OneDrive\Desktop\Ira" }

# Check if Ollama is running
$ollamaRunning = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    Write-Host "Starting Ollama server..." -ForegroundColor Yellow
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  ✓ Ollama server started" -ForegroundColor Green
} else {
    Write-Host "  ✓ Ollama server already running" -ForegroundColor Green
}

# Start Backend
Write-Host "Starting backend server..." -ForegroundColor Yellow
$backendPath = Join-Path $ProjectRoot "backend"
$backendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
) -PassThru
Write-Host "  ✓ Backend started on http://127.0.0.1:8000" -ForegroundColor Green

# Give backend time to start
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting frontend..." -ForegroundColor Yellow
$frontendPath = Join-Path $ProjectRoot "frontend"
$frontendProcess = Start-Process -FilePath "powershell" -ArgumentList @(
    "-NoExit", 
    "-Command",
    "cd '$frontendPath'; npm run dev"
) -PassThru
Write-Host "  ✓ Frontend started" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ira is now running!                  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend API: http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Frontend:    http://127.0.0.1:3000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Gray
Write-Host ""

# Wait for user to stop
try {
    Wait-Process -Id $backendProcess.Id
} finally {
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
    Stop-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue
}
