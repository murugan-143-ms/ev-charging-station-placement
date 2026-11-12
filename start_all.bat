@echo off
echo ===================================================
echo   Starting EV Charging PSO: Backend + Frontend
echo ===================================================

start "EV Charging - Backend (Port 8000)" cmd /k "call run.bat serve"
timeout /t 3 /nobreak >nul
start "EV Charging - Frontend (Port 5173)" cmd /k "call run.bat frontend"

echo.
echo Both servers have been launched in separate windows!
echo  - Backend API: http://127.0.0.1:8000
echo  - Swagger Docs: http://127.0.0.1:8000/docs
echo  - Frontend UI:  http://127.0.0.1:5173
echo.

