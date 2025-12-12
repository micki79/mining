@echo off
title GPU Mining GUI
color 0A

cd /d C:\GPUMiner_GUI
if %errorLevel% neq 0 (
    echo [FEHLER] Ordner C:\GPUMiner_GUI nicht gefunden!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo        GPU MINING GUI STARTEN
echo ============================================================
echo.
echo Arbeite in: %CD%
echo.

if not exist "mining_gui.py" (
    echo [FEHLER] mining_gui.py nicht gefunden!
    echo Bitte zuerst die ZIP-Datei hier entpacken.
    pause
    exit /b 1
)

echo Starte GUI...
echo.
python mining_gui.py

if %errorLevel% neq 0 (
    echo.
    echo [FEHLER] GUI konnte nicht gestartet werden!
    echo.
    echo Moegliche Probleme:
    echo   - Python-Pakete fehlen: INSTALL_SIMPLE.bat ausfuehren
    echo   - Python nicht installiert
    echo.
    pause
)
