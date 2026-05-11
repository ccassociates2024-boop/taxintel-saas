@echo off
REM ============================================================
REM  TaxIntel — Deploy Backend to Railway
REM  Double-click this file to deploy.
REM ============================================================
SET NODE=C:\Users\Piyush\OneDrive\Desktop\office work\LECTURE TIME\associate-piyus\node.exe
SET RAILWAY=%APPDATA%\npm\node_modules\@railway\cli\bin\railway.js
SET BACKEND=%~dp0backend

echo.
echo  ====================================================
echo   TaxIntel — Railway Backend Deployment
echo  ====================================================
echo.

REM ── Login ────────────────────────────────────────────────
echo [1/4] Logging into Railway (browser will open)...
"%NODE%" "%RAILWAY%" login
if %errorlevel% neq 0 (
    echo ERROR: Login failed. Press any key to exit.
    pause >nul
    exit /b 1
)
echo       Logged in!

REM ── Link or create project ───────────────────────────────
echo.
echo [2/4] Linking to Railway project...
echo       (Select "Create new project" if this is your first deploy)
cd /d "%BACKEND%"
"%NODE%" "%RAILWAY%" link
echo.

REM ── Add PostgreSQL plugin ────────────────────────────────
echo [3/4] Adding PostgreSQL database...
"%NODE%" "%RAILWAY%" add --plugin postgresql
echo.

REM ── Deploy ───────────────────────────────────────────────
echo [4/4] Deploying backend...
"%NODE%" "%RAILWAY%" up --service taxintel-backend
echo.

REM ── Get the URL ──────────────────────────────────────────
echo       Your backend URL:
"%NODE%" "%RAILWAY%" domain
echo.

echo  ====================================================
echo   Backend deployed!
echo.
echo   IMPORTANT next steps:
echo   1. In Railway dashboard, set these env vars:
echo      APP_ENV=production
echo      JWT_SECRET=7b5c8d48ecc9802e69e3bf57271620aca46d82caac490ba9e96745ffef00bf6b
echo      PII_ENCRYPTION_KEY=tOZ7CUXi3ue-vXRD6CTBAn9ODHeKFuoP6y62a2SLdx8=
echo      CORS_ORIGINS=https://YOUR-VERCEL-URL.vercel.app
echo.
echo   2. Railway auto-sets DATABASE_URL from the Postgres plugin.
echo  ====================================================
echo.
pause
