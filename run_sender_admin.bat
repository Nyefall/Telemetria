@echo off
echo ================================================
echo TELEMETRIA SENDER - EXECUCAO COMO ADMINISTRADOR
echo ================================================
echo.
echo Este script inicia o sender com privilegios
echo de administrador para acesso aos sensores.
echo.
cd /d "%~dp0"
echo Iniciando sender_pc.py...
".venv\Scripts\python.exe" sender_pc.py
pause
