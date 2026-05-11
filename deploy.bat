@echo off
REM ============================================================
REM  TaxIntel SaaS — One-Click Deploy to Railway + Vercel
REM  Run this ONCE from the project root.
REM ============================================================

SET GH=C:\Program Files\GitHub CLI\gh.exe
SET NODE=C:\Users\Piyush\OneDrive\Desktop\office work\LECTURE TIME\associate-piyus\node.exe
SET RAILWAY=%APPDATA%\npm\node_modules\@railway\cli\bin\railway.js
SET VERCEL=%APPDATA%\npm\node_modules\vercel\dist\index.js
SET PROJECT_DIR=%~dp0

echo.
echo  ========================================================
echo   TaxIntel SaaS — Deploying to Railway + Vercel
echo  ========================================================
echo.

REM ── STEP 1: GitHub auth + create repo ────────────────────────────────────
echo [1/5] GitHub — Logging in and creating repo...
"%GH%" auth status >nul 2>&1
if %errorlevel% neq 0 (
    echo       Opening GitHub login in browser...
    "%GH%" auth login --web --hostname github.com --git-protocol https
)

REM Create public repo (change --public to --private if you prefer)
"%GH%" repo create taxintel-saas --public --description "TaxIntel — Indian AI Tax Intelligence SaaS" --source=. --remote=origin --push
if %errorlevel% equ 0 (
    echo       Repo created and code pushed!
) else (
    echo       Repo may already exist. Pushing to origin...
    git push -u origin master
)

echo.
echo [2/5] Code pushed to GitHub.
echo.

REM ── STEP 2: Railway backend ───────────────────────────────────────────────
echo [3/5] Railway — Deploying backend...
echo.
echo  You will now be asked to log in to Railway in your browser.
echo  After login, select "Create new project" when prompted.
echo.
"%NODE%" "%RAILWAY%" login
echo.
echo  Now deploying backend service from the 'backend' folder...
cd /d "%PROJECT_DIR%backend"
"%NODE%" "%RAILWAY%" up --service taxintel-backend
cd /d "%PROJECT_DIR%"

echo.
echo [4/5] Backend deployed to Railway.
echo.

REM ── STEP 3: Vercel frontend ───────────────────────────────────────────────
echo [5/5] Vercel — Deploying frontend...
echo.
cd /d "%PROJECT_DIR%frontend"
"%NODE%" "%VERCEL%" deploy --prod
cd /d "%PROJECT_DIR%"

echo.
echo  ========================================================
echo   Deployment complete!
echo.
echo   Next steps:
echo   1. In Railway dashboard: add PostgreSQL plugin to your project
echo   2. Set env vars on Railway backend service (see .env.production.example)
echo   3. Set NEXT_PUBLIC_API_URL on Vercel to your Railway backend URL
echo  ========================================================
echo.
pause
