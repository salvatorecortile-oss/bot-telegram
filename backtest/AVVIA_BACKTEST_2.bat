@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Backtest V-Formation - secondo giro

echo ============================================================
echo   BACKTEST V-FORMATION - SECONDO GIRO (solo dati, NON apre ordini)
echo   3 prove: M15, H1 e M5 senza spread
echo ============================================================
echo.
echo MetaTrader 5 deve essere APERTO e collegato al conto.
echo.

set PY=python
%PY% --version >nul 2>&1
if errorlevel 1 set PY=py

set SUFFISSO=
set /p SUFFISSO="Suffisso dei simboli (la volta scorsa era -P), poi INVIO: "
set SIMBOLI=EURUSD%SUFFISSO% GBPUSD%SUFFISSO% USDCHF%SUFFISSO% EURGBP%SUFFISSO%
echo.

echo [1/3] Timeframe M15 dal 2018...
%PY% run_vformation.py --symbols %SIMBOLI% --timeframe M15 --from 2018-01-01 --compare --split 2023-01-01 > risultati_M15.txt 2>&1

echo [2/3] Timeframe H1 dal 2015...
%PY% run_vformation.py --symbols %SIMBOLI% --timeframe H1 --from 2015-01-01 --compare --split 2021-01-01 > risultati_H1.txt 2>&1

echo [3/3] M5 senza spread (per misurare quanto pesano i costi)...
%PY% run_vformation.py --symbols %SIMBOLI% --timeframe M5 --from 2021-01-01 --compare --split 2024-01-01 --set spread_pips=0 > risultati_M5_senza_spread.txt 2>&1

echo.
echo ============================================================
echo  FINITO. Manda a Claude questi 3 file (sono in questa cartella):
echo    risultati_M15.txt
echo    risultati_H1.txt
echo    risultati_M5_senza_spread.txt
echo ============================================================
pause
