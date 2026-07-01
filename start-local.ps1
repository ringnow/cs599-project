# CS599 Local Startup Script
# Run in PowerShell (NOT through Trae IDE)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CS599 Local Startup" -ForegroundColor Cyan
Write-Host "  API on Windows Host | MySQL/Redis in Docker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Start MySQL + Redis
Write-Host "[1/4] Starting MySQL + Redis containers..." -ForegroundColor Yellow
docker-compose up -d mysql redis
if ($LASTEXITCODE -ne 0) {
    Write-Host "  FAIL: Docker not running?" -ForegroundColor Red
    exit 1
}
Write-Host "  OK" -ForegroundColor Green

# 2. Wait for MySQL
Write-Host "[2/4] Waiting for MySQL..." -ForegroundColor Yellow
for ($i = 0; $i -lt 30; $i++) {
    $st = docker inspect --format "{{.State.Health.Status}}" cs599-project-audit-mysql-1 2>$null
    if ($st -eq "healthy") { Write-Host "  MySQL ready" -ForegroundColor Green; break }
    Start-Sleep -Seconds 2
}

# 3. Check venv + install deps
Write-Host "[3/4] Checking Python venv..." -ForegroundColor Yellow
$vp = "$PSScriptRoot\venv\Scripts\python.exe"
if (-not (Test-Path $vp)) {
    Write-Host "  Creating venv (Python 3.12)..." -ForegroundColor Gray
    & py -3.12 -m venv venv
}

& $vp -c "import fastapi, uvicorn, langchain_openai" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Installing dependencies (Tsinghua mirror)..." -ForegroundColor Gray
    & $vp -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    & $vp -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Retrying with default PyPI..." -ForegroundColor DarkYellow
        & $vp -m pip install -r requirements.txt
    }
}
Write-Host "  Python ready" -ForegroundColor Green

# 4. Start FastAPI
Write-Host "[4/4] Starting FastAPI..." -ForegroundColor Yellow
$env:DATABASE_URL = "mysql+pymysql://cs599:cs599pass@127.0.0.1:3307/cs599?charset=utf8mb4"
$env:REDIS_URL = "redis://127.0.0.1:6379/0"
$env:JWT_SECRET_KEY = "cs599-docker-jwt-key-change-this-in-real-deploy-2026"
$env:CHROMA_PATH = "$PSScriptRoot\.chroma"
$env:EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
$env:KEYS_DIR = "$PSScriptRoot\.cs599-agent"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Running: http://localhost:8000" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

& $vp -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000
