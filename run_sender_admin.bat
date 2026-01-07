@echo off
echo ================================================
echo TELEMETRIA SENDER - EXECUCAO COMO ADMINISTRADOR
echo ================================================
echo.
cd /d "%~dp0"
echo Iniciando sender_pc.py...
echo O console sera minimizado apos a inicializacao.
echo.
".venv\Scripts\python.exe" sender_pc.py
