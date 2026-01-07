@echo off
chcp 65001 > nul
cls
echo.
echo ╔══════════════════════════════════════════════╗
echo ║   📡 SISTEMA DE TELEMETRIA DE HARDWARE      ║
echo ║            Executável Unificado              ║
echo ╚══════════════════════════════════════════════╝
echo.
echo Iniciando Telemetria.exe...
echo.
echo Você poderá escolher:
echo   💻 SENDER (PC Principal)   - Requer Admin
echo   📊 RECEIVER (Dashboard)    - Sem Admin
echo.
echo ══════════════════════════════════════════════
echo.

cd /d "%~dp0..\dist"

if exist "Telemetria.exe" (
    start "" "Telemetria.exe"
    echo ✓ Telemetria iniciado com sucesso!
) else (
    echo ✗ ERRO: Telemetria.exe não encontrado em dist/
    echo.
    echo Execute primeiro: python scripts/build_unified.py
)

echo.
timeout /t 3 > nul
exit
