@echo off
title Teste de Sensores (Admin)
echo ========================================
echo  TESTE DE SENSORES COM ADMIN
echo ========================================
echo.

:: Verifica se está rodando como admin
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Executando como Administrador...
    echo.
    cd /d "%~dp0"
    ".venv\Scripts\python.exe" test_admin_sensors.py
    pause
) else (
    echo Solicitando permissoes de administrador...
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
)
