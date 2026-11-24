@echo off
title Job Hunter Bot - Segundo Plano
cd /d "%~dp0"

if not exist "data" mkdir data

echo ========================================================
echo   Iniciando Job Hunter Bot en Segundo Plano (Headless)
echo ========================================================
echo El scraper operara de forma silenciosa cada 60 minutos.
echo No se abriran ventanas de navegador en tu pantalla.
echo.

start "" ".\venv\Scripts\pythonw.exe" "src/main.py" --loop

echo [OK] El bot ya esta activo en la memoria de Windows.
echo Podes revisar las ofertas en Supabase o en la Web App.
echo Para detenerlo en cualquier momento ejecuta: detener_segundo_plano.bat
echo ========================================================
pause
