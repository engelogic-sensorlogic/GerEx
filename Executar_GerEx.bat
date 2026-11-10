@echo off
SETLOCAL
chcp 65001 >nul
cd /d "%~dp0"

title GerEx - Gerador de Laudos de Area Classificada

python main.py
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo   O aplicativo encerrou com erro ^(veja a mensagem acima^).
    echo ============================================================
    pause
)
