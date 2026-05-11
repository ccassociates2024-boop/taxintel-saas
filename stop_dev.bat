@echo off
REM ============================================================
REM  TaxIntel SaaS — Stop Dev Stack
REM ============================================================
echo Stopping TaxIntel dev servers...

REM Kill uvicorn (FastAPI)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo   Killing backend process %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Kill Next.js
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr "LISTENING"') do (
    echo   Killing frontend process %%a
    taskkill /F /PID %%a >nul 2>&1
)

REM Stop PostgreSQL gracefully
echo   Stopping PostgreSQL...
"C:\Program Files\PostgreSQL\16\bin\pg_ctl.exe" stop -D "C:\Program Files\PostgreSQL\16\data" -m fast >nul 2>&1

echo Done.
