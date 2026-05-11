@echo off
REM ============================================================
REM  TaxIntel — Deploy Frontend to Vercel
REM  Run AFTER deploy_railway.bat and you have the Railway URL.
REM ============================================================
SET NODE=C:\Users\Piyush\OneDrive\Desktop\office work\LECTURE TIME\associate-piyus\node.exe
SET VERCEL=%APPDATA%\npm\node_modules\vercel\dist\index.js
SET FRONTEND=%~dp0frontend

echo.
echo  ====================================================
echo   TaxIntel — Vercel Frontend Deployment
echo  ====================================================
echo.

REM Ask for the Railway backend URL
set /p BACKEND_URL="Enter your Railway backend URL (e.g. https://taxintel-backend.up.railway.app): "

echo.
echo [1/3] Logging into Vercel (browser will open)...
"%NODE%" "%VERCEL%" login
if %errorlevel% neq 0 (
    echo ERROR: Login failed. Press any key to exit.
    pause >nul
    exit /b 1
)

echo.
echo [2/3] Setting API URL environment variable...
cd /d "%FRONTEND%"
"%NODE%" "%VERCEL%" env add NEXT_PUBLIC_API_URL production <<< "%BACKEND_URL%"

echo.
echo [3/3] Deploying frontend to production...
"%NODE%" "%VERCEL%" deploy --prod
echo.

echo  ====================================================
echo   Frontend deployed!
echo.
echo   IMPORTANT: Go to your Railway dashboard and update:
echo      CORS_ORIGINS=https://YOUR-VERCEL-URL.vercel.app
echo  ====================================================
echo.
pause
