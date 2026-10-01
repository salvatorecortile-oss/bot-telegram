@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Backtest V-Formation

echo ============================================================
echo   BACKTEST V-FORMATION  (scarica solo dati, NON apre ordini)
echo ============================================================
echo.
echo Prima di continuare:
echo  - MetaTrader 5 deve essere APERTO e collegato al tuo conto
echo  - in MT5: Strumenti - Opzioni - Grafici - "Max barre nel grafico" = Illimitato
echo.

rem --- trova Python ---
set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 set PY=py
%PY% --version >nul 2>&1
if errorlevel 1 (
    echo ERRORE: Python non trovato. Installa Python da python.org
    pause
    exit /b 1
)

echo I simboli del tuo broker hanno un suffisso? Per esempio il tuo oro e' XAUUSD-P,
echo quindi probabilmente l'euro-dollaro e' EURUSD-P.
set SUFFISSO=
set /p SUFFISSO="Scrivi il suffisso (es. -P) oppure premi INVIO se non c'e': "
echo.

echo [1/2] Installazione pacchetti necessari...
%PY% -m pip install -q -r requirements.txt
echo.

echo [2/2] Backtest in corso (la prima volta puo' richiedere diversi minuti)...
%PY% run_vformation.py --symbols EURUSD%SUFFISSO% GBPUSD%SUFFISSO% USDCHF%SUFFISSO% EURGBP%SUFFISSO% --timeframe M5 --from 2021-01-01 --compare --split 2024-01-01 > risultati.txt 2>&1

type risultati.txt
echo.
echo ============================================================
echo  FINITO. I risultati sono nel file "risultati.txt"
echo  in questa stessa cartella: mandalo a Claude.
echo ============================================================
pause
