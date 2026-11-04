@echo off
REM Avvia il Bot Guardiano e lo riavvia da solo se si ferma (es. internet caduto).
REM Per fermarlo: chiudi questa finestra.
cd /d "%~dp0"
:loop
python guardiano.py
echo.
echo Guardiano fermato. Riparto tra 10 secondi... (chiudi la finestra per fermarlo)
timeout /t 10 /nobreak >nul
goto loop
