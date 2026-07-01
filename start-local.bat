@echo off
chcp 65001 >nul
title CS599 智能助手 - 本地启动

echo ========================================
echo   CS599 智能助手 - 本地启动
echo   API 运行在 Windows 主机 (可访问 LLM API)
echo   MySQL/Redis 运行在 Docker 中
echo ========================================
echo.

REM ── 1. 启动 MySQL + Redis ──
echo [1/4] 启动 MySQL + Redis 容器...
docker-compose up -d mysql redis
if errorlevel 1 (
    echo   ✗ Docker 启动失败，请确认 Docker Desktop 正在运行
    pause
    exit /b 1
)
echo   ✓ MySQL + Redis 容器已启动

REM ── 2. 等待 MySQL ──
echo [2/4] 等待 MySQL 就绪...
set /a retries=30
:wait_mysql
for /f "delims=" %%i in ('docker inspect --format^="{{.State.Health.Status}}" cs599-project-audit-mysql-1 2^>nul') do set status=%%i
if "%status%"=="healthy" (
    echo   ✓ MySQL 已就绪
    goto mysql_ok
)
set /a retries-=1
if %retries% gtr 0 (
    timeout /t 2 /nobreak >nul
    goto wait_mysql
)
echo   ⚠ MySQL 等待超时，继续启动...
:mysql_ok

REM ── 3. 检查 venv ──
echo [3/4] 检查 Python 虚拟环境...
if not exist "venv\Scripts\python.exe" (
    echo   创建虚拟环境 ^(Python 3.12^)...
    py -3.12 -m venv venv
    if errorlevel 1 (
        echo   ✗ 创建虚拟环境失败，请确认已安装 Python 3.12
        pause
        exit /b 1
    )
)

REM 检查依赖是否已安装
venv\Scripts\python.exe -c "import fastapi, uvicorn, langchain_openai" 2>nul
if errorlevel 1 (
    echo   安装依赖包 ^(使用清华镜像加速^)...
    venv\Scripts\python.exe -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    venv\Scripts\python.exe -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo   ⚠ 清华镜像失败，尝试默认源...
        venv\Scripts\python.exe -m pip install -r requirements.txt
    )
)
echo   ✓ Python 环境就绪

REM ── 4. 启动 FastAPI ──
echo [4/4] 启动 FastAPI 服务...

REM 设置环境变量
set DATABASE_URL=mysql+pymysql://cs599:cs599pass@127.0.0.1:3307/cs599?charset=utf8mb4
set REDIS_URL=redis://127.0.0.1:6379/0
set JWT_SECRET_KEY=cs599-docker-jwt-key-change-this-in-real-deploy-2026
set CHROMA_PATH=%CD%\.chroma
set EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
set KEYS_DIR=%CD%\.cs599-agent

echo.
echo ========================================
echo   服务启动中...
echo   访问地址: http://localhost:8000
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

REM 启动 uvicorn
venv\Scripts\python.exe -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000

pause
