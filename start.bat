@echo off
echo ============================================
echo  Acuron Invoice Intelligence - Starting Up
echo ============================================

echo.
echo [1/2] Starting FastAPI Backend...
start "Acuron Backend" cmd /k "cd /d %~dp0server && acuron_env\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 >nul

echo [2/2] Starting Next.js Frontend...
start "Acuron Frontend" cmd /k "cd /d %~dp0client && npm run dev"

echo.
echo ============================================
echo  Backend  : http://localhost:8000
echo  Frontend : http://localhost:3000
echo  API Docs : http://localhost:8000/docs
echo ============================================
echo.
pause
