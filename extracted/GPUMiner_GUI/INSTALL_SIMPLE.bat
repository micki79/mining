@echo off
title GPU Mining GUI - Installation
color 0A

echo.
echo ============================================================
echo        GPU MINING GUI - INSTALLATION
echo ============================================================
echo.

:: Zum richtigen Ordner wechseln
cd /d C:\GPUMiner_GUI
if %errorLevel% neq 0 (
    echo [FEHLER] Ordner C:\GPUMiner_GUI existiert nicht!
    echo.
    echo Bitte zuerst:
    echo   1. Ordner erstellen: mkdir C:\GPUMiner_GUI
    echo   2. ZIP-Dateien dorthin entpacken
    echo   3. Dieses Script nochmal starten
    echo.
    pause
    exit /b 1
)

echo Arbeite in: %CD%
echo.

echo [1/4] Pruefe Python...
python --version
if %errorLevel% neq 0 (
    echo [FEHLER] Python nicht gefunden!
    echo Bitte Python installieren: https://www.python.org/downloads/
    echo WICHTIG: "Add Python to PATH" aktivieren!
    pause
    exit /b 1
)
echo [OK] Python gefunden
echo.

echo [2/4] Installiere Python-Pakete...
echo Dies dauert 1-2 Minuten...
echo.

pip install PySide6 --upgrade
pip install pynvml --upgrade
pip install requests --upgrade
pip install PyYAML --upgrade
pip install pyqtgraph --upgrade
pip install psutil --upgrade
pip install Pillow --upgrade

echo.
echo [OK] Pakete installiert
echo.

echo [3/4] Erstelle Ordner...
if not exist "miners" mkdir miners
if not exist "miners\trex" mkdir miners\trex
if not exist "miners\lolminer" mkdir miners\lolminer
if not exist "miners\nbminer" mkdir miners\nbminer
if not exist "miners\gminer" mkdir miners\gminer
if not exist "miners\rigel" mkdir miners\rigel
if not exist "logs" mkdir logs
if not exist "benchmarks" mkdir benchmarks
echo [OK] Ordner erstellt
echo.

echo [4/4] Teste Installation...
echo.
python -c "import PySide6; print('[OK] PySide6')"
python -c "import requests; print('[OK] requests')"
python -c "import yaml; print('[OK] PyYAML')"
python -c "import pyqtgraph; print('[OK] pyqtgraph')"
python -c "import psutil; print('[OK] psutil')"
python -c "import pynvml; print('[OK] pynvml')" 2>nul || echo [HINWEIS] pynvml braucht NVIDIA GPU

echo.
echo ============================================================
echo        INSTALLATION ABGESCHLOSSEN!
echo ============================================================
echo.
echo Naechste Schritte:
echo.
echo   1. Miner installieren:
echo      Doppelklick auf DOWNLOAD_MINERS.bat
echo.
echo   2. GUI starten:
echo      Doppelklick auf START_GUI.bat
echo.
echo ============================================================
echo.
pause
