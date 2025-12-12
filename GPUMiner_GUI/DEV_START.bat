@echo off
:: ============================================================
:: GPU Mining Profit Switcher - ENTWICKLUNGSMODUS (SCHNELL)
:: Überspringt Miner-Installation komplett!
:: ============================================================

:: Prüfe ob bereits Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    goto :StartApp
)

:: Nicht Admin - starte als Administrator neu
echo.
echo  Starte als Administrator...
echo.
powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:StartApp
title GPU Mining Dashboard - DEV MODE

cd /d "%~dp0"

echo.
echo  ============================================================
echo   GPU MINING PROFIT SWITCHER V11.0 - DEV MODE
echo   Miner-Installation UEBERSPRUNGEN (schneller Start)
echo  ============================================================
echo.

:: Nur Python prüfen
echo [1/2] Pruefe Python...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo       FEHLER: Python nicht gefunden!
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo       Python %PYVER% gefunden

:: Dependencies
echo.
echo [2/2] Pruefe Dependencies...
python -c "import PySide6" >nul 2>nul
if %errorlevel% neq 0 (
    echo       Installiere GUI-Pakete...
    pip install PySide6 pyqtgraph nvidia-ml-py requests pyyaml colorama psutil
)
echo       OK

:: GUI starten (OHNE Miner-Check!)
echo.
echo  ============================================================
echo   Starte GUI... (Miner werden bei Bedarf installiert)
echo  ============================================================
echo.

python mining_gui.py 2>&1

pause >nul
