@echo off
:: ============================================================
:: GPU Mining Profit Switcher V11.0 - Miner Installer
:: Lädt T-Rex automatisch herunter
:: ============================================================

title Miner Installer

cd /d "%~dp0"

echo ============================================================
echo GPU Mining - Miner Installer
echo ============================================================
echo.

:: Prüfe ob miners-Ordner existiert
if not exist "miners" (
    echo Erstelle miners-Ordner...
    mkdir miners
)

:: T-Rex Miner
echo.
echo [1/4] T-Rex Miner...
if exist "miners\trex\t-rex.exe" (
    echo      BEREITS INSTALLIERT
) else (
    echo      Wird heruntergeladen...
    mkdir miners\trex 2>nul
    
    :: PowerShell zum Download nutzen
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip' -OutFile 'miners\trex\trex.zip'}"
    
    if exist "miners\trex\trex.zip" (
        echo      Entpacke...
        powershell -Command "Expand-Archive -Path 'miners\trex\trex.zip' -DestinationPath 'miners\trex' -Force"
        del "miners\trex\trex.zip" 2>nul
        echo      OK
    ) else (
        echo      FEHLER beim Download!
        echo      Bitte manuell von https://trex-miner.com herunterladen
    )
)

:: NBMiner
echo.
echo [2/4] NBMiner...
if exist "miners\nbminer\nbminer.exe" (
    echo      BEREITS INSTALLIERT
) else (
    echo      Wird heruntergeladen...
    mkdir miners\nbminer 2>nul
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/NebuTech/NBMiner/releases/download/v42.3/NBMiner_42.3_Win.zip' -OutFile 'miners\nbminer\nbminer.zip'}"
    
    if exist "miners\nbminer\nbminer.zip" (
        echo      Entpacke...
        powershell -Command "Expand-Archive -Path 'miners\nbminer\nbminer.zip' -DestinationPath 'miners\nbminer' -Force"
        del "miners\nbminer\nbminer.zip" 2>nul
        :: Dateien aus Unterordner verschieben
        for /d %%i in (miners\nbminer\NBMiner*) do (
            move /y "%%i\*" "miners\nbminer\" >nul 2>nul
            rmdir "%%i" 2>nul
        )
        echo      OK
    ) else (
        echo      FEHLER beim Download!
    )
)

:: GMiner
echo.
echo [3/4] GMiner...
if exist "miners\gminer\miner.exe" (
    echo      BEREITS INSTALLIERT
) else (
    echo      Wird heruntergeladen...
    mkdir miners\gminer 2>nul
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_windows64.zip' -OutFile 'miners\gminer\gminer.zip'}"
    
    if exist "miners\gminer\gminer.zip" (
        echo      Entpacke...
        powershell -Command "Expand-Archive -Path 'miners\gminer\gminer.zip' -DestinationPath 'miners\gminer' -Force"
        del "miners\gminer\gminer.zip" 2>nul
        echo      OK
    ) else (
        echo      FEHLER beim Download!
    )
)

:: lolMiner
echo.
echo [4/4] lolMiner...
if exist "miners\lolminer\lolMiner.exe" (
    echo      BEREITS INSTALLIERT
) else (
    echo      Wird heruntergeladen...
    mkdir miners\lolminer 2>nul
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.88/lolMiner_v1.88_Win64.zip' -OutFile 'miners\lolminer\lolminer.zip'}"
    
    if exist "miners\lolminer\lolminer.zip" (
        echo      Entpacke...
        powershell -Command "Expand-Archive -Path 'miners\lolminer\lolminer.zip' -DestinationPath 'miners\lolminer' -Force"
        del "miners\lolminer\lolminer.zip" 2>nul
        :: Dateien aus Unterordner verschieben
        for /d %%i in (miners\lolminer\lolMiner*) do (
            move /y "%%i\*" "miners\lolminer\" >nul 2>nul
            rmdir "%%i" 2>nul
        )
        echo      OK
    ) else (
        echo      FEHLER beim Download!
    )
)

echo.
echo ============================================================
echo Installation abgeschlossen!
echo ============================================================
echo.
echo Installierte Miner:
if exist "miners\trex\t-rex.exe" (echo   [X] T-Rex) else (echo   [ ] T-Rex)
if exist "miners\nbminer\nbminer.exe" (echo   [X] NBMiner) else (echo   [ ] NBMiner)
if exist "miners\gminer\miner.exe" (echo   [X] GMiner) else (echo   [ ] GMiner)
if exist "miners\lolminer\lolMiner.exe" (echo   [X] lolMiner) else (echo   [ ] lolMiner)
echo.
echo Starte jetzt START_GUI.bat um die GUI zu oeffnen!
echo.
pause
