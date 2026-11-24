@echo off
title Job Hunter Bot - Detener Segundo Plano
cd /d "%~dp0"

echo ========================================================
echo   Deteniendo Job Hunter Bot en Segundo Plano
echo ========================================================
echo Cerrando instancias de pythonw.exe...
taskkill /F /IM pythonw.exe 2>nul

echo.
echo [OK] El bot se ha detenido.
echo ========================================================
pause
