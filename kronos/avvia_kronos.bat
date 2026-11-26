@echo off
REM Avvia il servizio Kronos e lo riavvia da solo se si ferma.
REM Doppio clic su questo file (MetaTrader 5 deve essere aperto).
cd /d "%~dp0"
title Kronos - servizio previsioni
:loop
python main.py
echo.
echo Kronos si e' fermato. Riavvio tra 30 secondi... (chiudi la finestra per fermarlo)
timeout /t 30 /nobreak
goto loop
