@echo off
title Intelligence System - Final Project

echo ==========================================
echo    INTELLIGENCE SYSTEM - FINAL PROJECT
echo ==========================================
echo.

echo [1/3] Iniciando Redis...
docker compose up -d

if %errorlevel% neq 0 (
    echo.
    echo ERROR: No se pudo iniciar Docker Compose.
    pause
    exit /b 1
)

echo.
echo [2/3] Iniciando API FastAPI...
start "Intelligence System - API" cmd /k "py -m uvicorn app.api:app --reload"

echo.
echo [3/3] Iniciando Worker...
start "Intelligence System - Worker" cmd /k "py -m app.worker"

echo.
echo ==========================================
echo Sistema iniciado correctamente.
echo.
echo API: http://127.0.0.1:8000
echo Docs: http://127.0.0.1:8000/docs
echo ==========================================
echo.

pause

