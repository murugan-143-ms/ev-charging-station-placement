@echo off
echo Starting EV Charging PSO Frontend Dev Server...
set "PATH=C:\Program Files\nodejs;%PATH%"
cd /d "%~dp0frontend"
call npm.cmd run dev
pause

