@echo off
setlocal
set "PY_EXE=C:\Users\Murugan Durai\AppData\Local\Programs\Python\Python312\python.exe"

if not exist "%PY_EXE%" (
    where python >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PY_EXE=python"
    ) else (
        echo [ERROR] Python 3.12 executable not found.
        exit /b 1
    )
)

if "%1"=="serve" (
    echo Starting FastAPI Backend Server on http://127.0.0.1:8000 ...
    echo Documentation available at http://127.0.0.1:8000/docs
    "%PY_EXE%" run.py --serve
) else if "%1"=="frontend" (
    echo Starting Frontend Dev Server on http://localhost:5173 ...
    set "PATH=C:\Program Files\nodejs;%PATH%"
    cd /d "%~dp0frontend"
    call npm.cmd run dev
) else if "%1"=="test" (
    echo Running Backend Test Suite...
    "%PY_EXE%" -m pytest backend/tests/test_pso.py
) else (
    "%PY_EXE%" run.py %*
)

