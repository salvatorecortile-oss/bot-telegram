@echo off
REM ============================================================
REM  Compila FactMachine.exe TUTTO-IN-UNO (browser incluso).
REM  Lancia questo file su Windows con doppio click.
REM  Alla fine trovi l'exe in:  dist\FactMachine.exe
REM ============================================================
cd /d "%~dp0"

echo.
echo [1/4] Installo gli strumenti (pyinstaller + playwright)...
pip install --upgrade pyinstaller playwright
if errorlevel 1 goto errore

echo.
echo [2/4] Scarico il browser Chromium in una cartella locale...
set PLAYWRIGHT_BROWSERS_PATH=%CD%\pw-browsers
playwright install chromium
if errorlevel 1 goto errore

echo.
echo [3/4] Compilo l'exe con dentro il browser (puo' metterci qualche minuto)...
pyinstaller --onefile --noconsole --name FactMachine ^
  --collect-all playwright ^
  --add-data "pw-browsers;pw-browsers" ^
  dashboard.py
if errorlevel 1 goto errore

echo.
echo [4/4] FATTO!
echo L'eseguibile unico e' qui:  %CD%\dist\FactMachine.exe
echo Questo e' il file da dare ai clienti (browser gia' incluso).
echo.
pause
goto fine

:errore
echo.
echo *** ERRORE durante la compilazione. Leggi i messaggi qui sopra. ***
echo Assicurati che Python sia installato e che tu sia nella cartella del bot.
echo.
pause

:fine
