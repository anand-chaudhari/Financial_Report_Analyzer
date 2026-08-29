@echo off
title FinSight AI Backend - Auto-Restart Server
cd /d "%~dp0"

:loop
echo =========================================================
echo  FinSight AI Backend starting on http://127.0.0.1:8000
echo =========================================================
call .venv\Scripts\python.exe run_server.py
echo.
echo [Auto-Restart Guard] Backend stopped or crashed. Restarting in 2 seconds...
timeout /t 2 /nobreak >nul
goto loop
