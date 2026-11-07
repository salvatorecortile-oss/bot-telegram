@echo off
REM ============================================================
REM  Compila FactMachine.exe PROTETTO con PyArmor (offuscato) +
REM  browser incluso. Lancia con doppio click su Windows.
REM  Alla fine:  dist\FactMachine.exe
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/5] Installo gli strumenti (pyinstaller + playwright + pyarmor)...
pip install --upgrade pyinstaller playwright pyarmor
if errorlevel 1 goto errore

echo.
echo [2/5] Scarico il browser Chromium in una cartella locale...
set PLAYWRIGHT_BROWSERS_PATH=%CD%\pw-browsers
playwright install chromium
if errorlevel 1 goto errore

echo.
echo [3/5] Creo la configurazione di PyInstaller (spec) con browser incluso...
pyinstaller --onefile --noconsole --name FactMachine ^
  --collect-all playwright ^
  --add-data "pw-browsers;pw-browsers" ^
  dashboard.py
if errorlevel 1 goto errore

echo.
echo [4/5] Offusco il codice con PyArmor e re-impacchetto l'exe...
pyarmor gen --pack FactMachine.spec -r dashboard.py license_client.py license_config.py
if errorlevel 1 goto errore

echo.
echo [5/5] FATTO!
echo Exe PROTETTO (offuscato) qui:  %CD%\dist\FactMachine.exe
echo Questo e' il file da dare ai clienti.
echo.
pause
goto fine

:errore
echo.
echo *** ERRORE durante la compilazione. Leggi i messaggi qui sopra. ***
echo Se l'errore riguarda PyArmor, copia il messaggio e chiedi aiuto.
echo In alternativa usa lo script semplice (COMPILA_EXE.bat), senza offuscamento.
echo.
pause

:fine
