@echo off
REM ============================================================
REM  TaxIntel SaaS — One-Click Dev Launcher
REM  Starts: PostgreSQL → FastAPI backend → Next.js frontend
REM ============================================================

SET PGBIN=C:\Program Files\PostgreSQL\16\bin
SET PGDATA=C:\Program Files\PostgreSQL\16\data
SET BACKEND_DIR=%~dp0backend
SET FRONTEND_DIR=%~dp0frontend
SET NODE_EXE=C:\Users\Piyush\OneDrive\Desktop\office work\LECTURE TIME\associate-piyus\node.exe
SET NEXT_BIN=%FRONTEND_DIR%\node_modules\next\dist\bin\next
SET UPLOADS_DIR=C:\taxintel_uploads

echo.
echo  ████████╗ █████╗ ██╗  ██╗██╗███╗   ██╗████████╗███████╗██╗
echo  ╚══██╔══╝██╔══██╗╚██╗██╔╝██║████╗  ██║╚══██╔══╝██╔════╝██║
echo     ██║   ███████║ ╚███╔╝ ██║██╔██╗ ██║   ██║   █████╗  ██║
echo     ██║   ██╔══██║ ██╔██╗ ██║██║╚██╗██║   ██║   ██╔══╝  ██║
echo     ██║   ██║  ██║██╔╝ ██╗██║██║ ╚████║   ██║   ███████╗███████╗
echo     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚══════╝
echo.
echo  Indian AI Tax Intelligence Platform — Local Dev Stack
echo  =======================================================
echo.

REM ── 1. Create uploads directory ───────────────────────────────────────────
if not exist "%UPLOADS_DIR%" mkdir "%UPLOADS_DIR%"

REM ── 2. Start PostgreSQL (pg_ctl, non-service mode) ────────────────────────
echo [1/3] Starting PostgreSQL 16...
"%PGBIN%\pg_ctl.exe" status -D "%PGDATA%" >nul 2>&1
if %errorlevel% neq 0 (
    "%PGBIN%\pg_ctl.exe" start -D "%PGDATA%" -w -t 20 >nul 2>&1
    if %errorlevel% equ 0 (
        echo       PostgreSQL started successfully.
    ) else (
        echo       WARNING: Could not start PostgreSQL. Continuing anyway...
    )
) else (
    echo       PostgreSQL already running.
)

REM ── 3. Start FastAPI backend ──────────────────────────────────────────────
echo.
echo [2/3] Starting FastAPI backend on http://localhost:8000 ...
cd /d "%BACKEND_DIR%"

REM Set env vars for backend
SET APP_ENV=local
SET DATABASE_URL=postgresql+psycopg://taxintel:taxintel@localhost:5432/taxintel
SET JWT_SECRET=dd1a81aad951133ac8bcac0cfe6eab253534fb842d2712c5463beee9f5e24b62
SET PII_ENCRYPTION_KEY=9EofrE2bzVGCRIbwABYPGsqUnlYDjQ82nI6O0KEHcPY=
SET CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002
SET BASE_URL=http://localhost:8000
SET S3_ACCESS_KEY=minioadmin
SET S3_SECRET_KEY=minioadmin
SET LOCAL_STORAGE_DIR=C:\taxintel_uploads
SET LOG_LEVEL=INFO

start "TaxIntel Backend" cmd /k "cd /d %BACKEND_DIR% && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

REM Wait for backend to be ready
echo       Waiting for backend...
timeout /t 8 /nobreak >nul

REM ── 4. Start Next.js dev server ───────────────────────────────────────────
echo.
echo [3/3] Starting Next.js frontend on http://localhost:3001 ...
cd /d "%FRONTEND_DIR%"

start "TaxIntel Frontend" cmd /k "cd /d %FRONTEND_DIR% && SET NEXT_PUBLIC_API_URL=http://localhost:8000 && "%NODE_EXE%" "%NEXT_BIN%" dev -p 3001"

REM ── 5. Done ───────────────────────────────────────────────────────────────
echo.
echo  ✓ All services starting!
echo.
echo  Frontend  →  http://localhost:3001
echo  Backend   →  http://localhost:8000
echo  API Docs  →  http://localhost:8000/api/docs
echo.
echo  Default login: demo@taxintel.in / Demo@12345
echo.
echo  Press any key to open the app in Chrome...
pause >nul
start chrome http://localhost:3001
