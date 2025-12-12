@echo off
title Miner Download
color 0B

echo.
echo ============================================================
echo        MINER DOWNLOAD - T-Rex, lolMiner, Rigel
echo ============================================================
echo.

:: Zum richtigen Ordner wechseln
cd /d C:\GPUMiner_GUI
if %errorLevel% neq 0 (
    echo [FEHLER] Ordner C:\GPUMiner_GUI nicht gefunden!
    pause
    exit /b 1
)

echo Arbeite in: %CD%
echo.

:: Ordner erstellen
if not exist "miners" mkdir miners
if not exist "miners\trex" mkdir miners\trex
if not exist "miners\lolminer" mkdir miners\lolminer
if not exist "miners\rigel" mkdir miners\rigel
if not exist "miners\gminer" mkdir miners\gminer
if not exist "miners\nbminer" mkdir miners\nbminer

echo ============================================================
echo [1/5] T-Rex Miner herunterladen...
echo ============================================================
echo.
echo Downloading von GitHub...
curl -L -o "%TEMP%\trex.zip" "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip" --progress-bar

if exist "%TEMP%\trex.zip" (
    echo Entpacke T-Rex...
    powershell -Command "Expand-Archive -Path '%TEMP%\trex.zip' -DestinationPath 'miners\trex' -Force"
    del "%TEMP%\trex.zip"
    echo [OK] T-Rex installiert
) else (
    echo [FEHLER] Download fehlgeschlagen
)
echo.

echo ============================================================
echo [2/5] lolMiner herunterladen...
echo ============================================================
echo.
curl -L -o "%TEMP%\lolminer.zip" "https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.88/lolMiner_v1.88_Win64.zip" --progress-bar

if exist "%TEMP%\lolminer.zip" (
    echo Entpacke lolMiner...
    powershell -Command "Expand-Archive -Path '%TEMP%\lolminer.zip' -DestinationPath 'miners\lolminer' -Force"
    del "%TEMP%\lolminer.zip"
    echo [OK] lolMiner installiert
) else (
    echo [FEHLER] Download fehlgeschlagen
)
echo.

echo ============================================================
echo [3/5] Rigel Miner herunterladen...
echo ============================================================
echo.
curl -L -o "%TEMP%\rigel.zip" "https://github.com/rigelminer/rigel/releases/download/1.20.1/rigel-1.20.1-win.zip" --progress-bar

if exist "%TEMP%\rigel.zip" (
    echo Entpacke Rigel...
    powershell -Command "Expand-Archive -Path '%TEMP%\rigel.zip' -DestinationPath 'miners\rigel' -Force"
    del "%TEMP%\rigel.zip"
    echo [OK] Rigel installiert
) else (
    echo [FEHLER] Download fehlgeschlagen
)
echo.

echo ============================================================
echo [4/5] GMiner herunterladen...
echo ============================================================
echo.
curl -L -o "%TEMP%\gminer.zip" "https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_windows64.zip" --progress-bar

if exist "%TEMP%\gminer.zip" (
    echo Entpacke GMiner...
    powershell -Command "Expand-Archive -Path '%TEMP%\gminer.zip' -DestinationPath 'miners\gminer' -Force"
    del "%TEMP%\gminer.zip"
    echo [OK] GMiner installiert
) else (
    echo [FEHLER] Download fehlgeschlagen
)
echo.

echo ============================================================
echo [5/5] NBMiner herunterladen...
echo ============================================================
echo.
curl -L -o "%TEMP%\nbminer.zip" "https://github.com/NebuTech/NBMiner/releases/download/v42.3/NBMiner_42.3_Win.zip" --progress-bar

if exist "%TEMP%\nbminer.zip" (
    echo Entpacke NBMiner...
    powershell -Command "Expand-Archive -Path '%TEMP%\nbminer.zip' -DestinationPath 'miners\nbminer' -Force"
    del "%TEMP%\nbminer.zip"
    echo [OK] NBMiner installiert
) else (
    echo [FEHLER] Download fehlgeschlagen
)
echo.

echo ============================================================
echo        DOWNLOAD ABGESCHLOSSEN
echo ============================================================
echo.
echo Installierte Miner in C:\GPUMiner_GUI\miners\
echo.
dir miners /b
echo.
echo ============================================================
echo.
echo WICHTIG: Windows Defender blockiert oft Miner!
echo.
echo Falls Miner fehlen:
echo   1. Windows Sicherheit oeffnen
echo   2. Viren- und Bedrohungsschutz
echo   3. Schutzverlauf
echo   4. Blockierte Dateien wiederherstellen
echo.
echo ============================================================
echo.
pause
