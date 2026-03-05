# Ira Backend Installation Script for Windows
# Run this script with: .\scripts\install.ps1

Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Ira - Local AI Assistant Installer   "  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $ProjectRoot) { 
    $ProjectRoot = "c:\Users\nandi\OneDrive\Desktop\Ira" 
}

Set-Location $ProjectRoot

Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Check Python
$pythonFound = $false
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  + Python found: $pythonVersion" -ForegroundColor Green
    $pythonFound = $true
}
catch {
    Write-Host "  X Python not found. Please install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}

# Check Node.js
$nodeFound = $false
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  + Node.js found: $nodeVersion" -ForegroundColor Green
    $nodeFound = $true
}
catch {
    Write-Host "  X Node.js not found. Please install Node.js 20+ from nodejs.org" -ForegroundColor Red
    exit 1
}

# Check Ollama
$ollamaFound = $false
try {
    $ollamaCheck = ollama --version 2>&1
    Write-Host "  + Ollama found" -ForegroundColor Green
    $ollamaFound = $true
}
catch {
    Write-Host "  X Ollama not found. Please install from ollama.com" -ForegroundColor Yellow
    Write-Host "    After installing Ollama, run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2/7] Creating directory structure..." -ForegroundColor Yellow

$directories = @(
    "backend\app\models",
    "backend\app\services",
    "backend\app\memory",
    "backend\app\utils",
    "backend\tests",
    "frontend\src\components",
    "frontend\src\services",
    "frontend\electron",
    "models\whisper",
    "models\piper",
    "data\documents",
    "data\chroma_db"
)

foreach ($dir in $directories) {
    $fullPath = Join-Path $ProjectRoot $dir
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "  + Directory structure created" -ForegroundColor Green

Write-Host ""
Write-Host "[3/7] Setting up Python virtual environment..." -ForegroundColor Yellow

$backendPath = Join-Path $ProjectRoot "backend"
Set-Location $backendPath

if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "  + Virtual environment created" -ForegroundColor Green
}
else {
    Write-Host "  + Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
$activateScript = Join-Path $backendPath ".venv\Scripts\Activate.ps1"
if (Test-Path $activateScript) {
    & $activateScript
}

Write-Host ""
Write-Host "[4/7] Installing Python dependencies..." -ForegroundColor Yellow

pip install --upgrade pip --quiet 2>&1 | Out-Null
pip install -r requirements.txt --quiet 2>&1 | Out-Null
Write-Host "  + Python dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "[5/7] Pulling Ollama models..." -ForegroundColor Yellow

Write-Host "  Pulling multimodal model (this may take a while)..." -ForegroundColor Gray
ollama pull llava:7b
Write-Host "  + LLaVA 7B model downloaded" -ForegroundColor Green

Write-Host "  Pulling embedding model..." -ForegroundColor Gray
ollama pull nomic-embed-text
Write-Host "  + Embedding model downloaded" -ForegroundColor Green

Write-Host ""
Write-Host "[6/7] Setting up frontend..." -ForegroundColor Yellow

$frontendPath = Join-Path $ProjectRoot "frontend"
Set-Location $frontendPath

if (-not (Test-Path "node_modules")) {
    npm install --silent 2>&1 | Out-Null
    Write-Host "  + Frontend dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  + Frontend dependencies already installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "[7/7] Final setup..." -ForegroundColor Yellow

# Copy env example if .env doesn't exist
$envExample = Join-Path $ProjectRoot "backend\.env.example"
$envFile = Join-Path $ProjectRoot "backend\.env"
if ((Test-Path $envExample) -and (-not (Test-Path $envFile))) {
    Copy-Item $envExample $envFile
    Write-Host "  + Created .env from template" -ForegroundColor Green
}

Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host "  Installation Complete!               "  -ForegroundColor Cyan
Write-Host "========================================"  -ForegroundColor Cyan
Write-Host ""
Write-Host "To start Ira, run:" -ForegroundColor White
Write-Host "  .\scripts\start.ps1" -ForegroundColor Yellow
Write-Host ""
