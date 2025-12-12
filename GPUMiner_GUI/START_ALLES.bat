@echo off
:: ============================================================
:: GPU MINING GUI V12 - KOMPLETT INSTALLER & STARTER
:: Mit individueller Bestaetigung pro Miner
:: ============================================================

title GPU Mining GUI V12 - Installer

:: In den Ordner wechseln wo diese Datei liegt
cd /d "%~dp0"

:: Admin-Rechte anfordern
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Starte als Administrator...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cls
echo ============================================================
echo   GPU MINING GUI V12 - KOMPLETT INSTALLER
echo ============================================================
echo.
echo   Arbeitsverzeichnis: %CD%
echo.

:: ============================================================
:: SCHRITT 1: Python pruefen
:: ============================================================
echo [1/6] Pruefe Python Installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo   FEHLER: Python nicht gefunden!
    echo.
    echo   Bitte Python installieren von:
    echo   https://www.python.org/downloads/
    echo.
    echo   WICHTIG: "Add Python to PATH" aktivieren!
    echo.
    pause
    exit /b 1
)
python --version
echo   [OK] Python gefunden
echo.

:: ============================================================
:: SCHRITT 2: Python-Pakete installieren
:: ============================================================
echo [2/6] Installiere Python-Pakete...
echo.

pip install PySide6 --upgrade --quiet
pip install pynvml --upgrade --quiet 2>nul
pip install requests --upgrade --quiet
pip install PyYAML --upgrade --quiet
pip install pyqtgraph --upgrade --quiet
pip install psutil --upgrade --quiet
pip install Pillow --upgrade --quiet

echo   [OK] Python-Pakete installiert
echo.

:: ============================================================
:: SCHRITT 3: Ordner erstellen
:: ============================================================
echo [3/6] Erstelle Ordnerstruktur...

if not exist "miners" mkdir miners
if not exist "miners\trex" mkdir miners\trex
if not exist "miners\lolminer" mkdir miners\lolminer
if not exist "miners\nbminer" mkdir miners\nbminer
if not exist "miners\gminer" mkdir miners\gminer
if not exist "miners\rigel" mkdir miners\rigel
if not exist "logs" mkdir logs
if not exist "benchmarks" mkdir benchmarks

echo   [OK] Ordner erstellt
echo.

:: ============================================================
:: SCHRITT 4: Windows Defender Ausnahme
:: ============================================================
echo [4/6] Windows Defender Konfiguration...
echo.

set "MINERS_PATH=%CD%\miners"

:: Pruefen ob Ausnahme bereits existiert
powershell -Command "if ((Get-MpPreference).ExclusionPath -contains '%MINERS_PATH%') { exit 0 } else { exit 1 }" >nul 2>&1
if %errorLevel% equ 0 (
    echo   [OK] Defender-Ausnahme bereits vorhanden
) else (
    echo   Mining-Software wird oft faelschlicherweise als Virus erkannt.
    echo.
    choice /C JN /M "   Defender-Ausnahme fuer miners-Ordner hinzufuegen (J=Ja, N=Nein)"
    if %errorLevel% equ 1 (
        powershell -Command "Add-MpPreference -ExclusionPath '%MINERS_PATH%'" >nul 2>&1
        echo   [OK] Defender-Ausnahme hinzugefuegt
    ) else (
        echo   [SKIP] Keine Ausnahme - Miner koennten blockiert werden
    )
)
echo.

:: ============================================================
:: SCHRITT 5: Miner herunterladen
:: ============================================================
echo [5/6] Lade Mining-Software herunter...
echo.

:: ------------------------------
:: T-Rex Miner
:: ------------------------------
:install_trex
echo   [1/5] T-Rex Miner (RVN, ERG, ETC)...
if exist "miners\trex\t-rex.exe" (
    echo         [OK] Bereits installiert
) else (
    call :download_and_verify "T-Rex" "https://github.com/trexminer/T-Rex/releases/download/0.26.8/t-rex-0.26.8-win.zip" "miners\trex" "t-rex.exe"
)
echo.

:: ------------------------------
:: lolMiner
:: ------------------------------
:install_lolminer
echo   [2/5] lolMiner (GRIN, BEAM, ERG, ETC)...
if exist "miners\lolminer\lolMiner.exe" (
    echo         [OK] Bereits installiert
) else (
    call :download_and_verify "lolMiner" "https://github.com/Lolliedieb/lolMiner-releases/releases/download/1.88/lolMiner_v1.88_Win64.zip" "miners\lolminer" "lolMiner.exe"
)
echo.

:: ------------------------------
:: NBMiner
:: ------------------------------
:install_nbminer
echo   [3/5] NBMiner (ETH, ETC, ERG)...
if exist "miners\nbminer\nbminer.exe" (
    echo         [OK] Bereits installiert
) else (
    call :download_and_verify "NBMiner" "https://github.com/NebuTech/NBMiner/releases/download/v42.3/NBMiner_42.3_Win.zip" "miners\nbminer" "nbminer.exe"
)
echo.

:: ------------------------------
:: GMiner
:: ------------------------------
:install_gminer
echo   [4/5] GMiner (ETH, ETC, BEAM, GRIN)...
if exist "miners\gminer\miner.exe" (
    echo         [OK] Bereits installiert
) else (
    call :download_and_verify "GMiner" "https://github.com/develsoftware/GMinerRelease/releases/download/3.44/gminer_3_44_windows64.zip" "miners\gminer" "miner.exe"
)
echo.

:: ------------------------------
:: Rigel
:: ------------------------------
:install_rigel
echo   [5/5] Rigel Miner (KAS, ALPH, IRON)...
if exist "miners\rigel\rigel.exe" (
    echo         [OK] Bereits installiert
) else (
    call :download_and_verify "Rigel" "https://github.com/rigelminer/rigel/releases/download/1.20.1/rigel-1.20.1-win.zip" "miners\rigel" "rigel.exe"
)
echo.

:: ============================================================
:: SCHRITT 6: GUI starten
:: ============================================================
echo [6/6] Starte Mining GUI...
echo.

if not exist "mining_gui.py" (
    echo   FEHLER: mining_gui.py nicht gefunden!
    pause
    exit /b 1
)

echo ============================================================
echo   INSTALLATION ABGESCHLOSSEN!
echo ============================================================
echo.
echo   Installierte Miner:
if exist "miners\trex\t-rex.exe" (echo      [X] T-Rex) else (echo      [ ] T-Rex - FEHLT)
if exist "miners\lolminer\lolMiner.exe" (echo      [X] lolMiner) else (echo      [ ] lolMiner - FEHLT)
if exist "miners\nbminer\nbminer.exe" (echo      [X] NBMiner) else (echo      [ ] NBMiner - FEHLT)
if exist "miners\gminer\miner.exe" (echo      [X] GMiner) else (echo      [ ] GMiner - FEHLT)
if exist "miners\rigel\rigel.exe" (echo      [X] Rigel) else (echo      [ ] Rigel - FEHLT)
echo.
echo   Starte GUI in 3 Sekunden...
timeout /t 3 /nobreak >nul

python mining_gui.py

if %errorLevel% neq 0 (
    echo.
    echo   FEHLER beim Starten der GUI!
    pause
)
exit /b 0


:: ============================================================
:: FUNKTION: download_and_verify
:: Laedt herunter, verifiziert, fragt bei Fehler nach Retry
:: Parameter: %1=Name, %2=URL, %3=Zielordner, %4=EXE-Name
:: ============================================================
:download_and_verify
set "M_NAME=%~1"
set "M_URL=%~2"
set "M_DIR=%~3"
set "M_EXE=%~4"

:: Erster Versuch
echo         Downloading von GitHub...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%M_URL%' -OutFile '%M_DIR%\download.zip' -TimeoutSec 120 } catch { }}" 2>nul

if exist "%M_DIR%\download.zip" (
    echo         Entpacke...
    powershell -Command "Expand-Archive -Path '%M_DIR%\download.zip' -DestinationPath '%M_DIR%' -Force" 2>nul
    del "%M_DIR%\download.zip" 2>nul
    
    :: Unterordner aufloesen
    for /d %%i in ("%M_DIR%\*") do (
        if exist "%%i\%M_EXE%" (
            move /y "%%i\*" "%M_DIR%\" >nul 2>nul
            rmdir "%%i" 2>nul
        )
    )
)

:: Verifizierung
if exist "%M_DIR%\%M_EXE%" (
    echo         [OK] %M_NAME% installiert und verifiziert
    goto :eof
)

:: ============================================================
:: FEHLER - Miner nicht gefunden, frage nach Retry
:: ============================================================
echo.
echo         ============================================
echo         [!] %M_NAME% INSTALLATION FEHLGESCHLAGEN!
echo         ============================================
echo.
echo         Die Datei %M_EXE% wurde nicht gefunden.
echo         Windows Defender hat sie vermutlich blockiert.
echo.
choice /C JN /M "        Nochmal versuchen mit deaktiviertem Defender (J=Ja, N=Nein)"
if %errorLevel% neq 1 (
    echo         [SKIP] %M_NAME% wird uebersprungen
    goto :eof
)

:: Defender temporaer deaktivieren
echo.
echo         Deaktiviere Echtzeit-Schutz temporaer...
powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $true" >nul 2>&1

:: Alte Dateien loeschen falls vorhanden
if exist "%M_DIR%\download.zip" del "%M_DIR%\download.zip" 2>nul

:: Zweiter Versuch
echo         Downloading (Versuch 2)...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri '%M_URL%' -OutFile '%M_DIR%\download.zip' -TimeoutSec 120 } catch { }}" 2>nul

if exist "%M_DIR%\download.zip" (
    echo         Entpacke...
    powershell -Command "Expand-Archive -Path '%M_DIR%\download.zip' -DestinationPath '%M_DIR%' -Force" 2>nul
    del "%M_DIR%\download.zip" 2>nul
    
    :: Unterordner aufloesen
    for /d %%i in ("%M_DIR%\*") do (
        if exist "%%i\%M_EXE%" (
            move /y "%%i\*" "%M_DIR%\" >nul 2>nul
            rmdir "%%i" 2>nul
        )
    )
)

:: Defender wieder aktivieren
echo         Aktiviere Echtzeit-Schutz wieder...
powershell -Command "Set-MpPreference -DisableRealtimeMonitoring $false" >nul 2>&1

:: Finale Verifizierung
if exist "%M_DIR%\%M_EXE%" (
    echo         [OK] %M_NAME% installiert und verifiziert!
) else (
    echo.
    echo         [X] %M_NAME% konnte nicht installiert werden!
    echo.
    echo         Bitte manuell herunterladen von:
    echo         %M_URL%
    echo.
    echo         Und entpacken nach: %M_DIR%\
    echo.
    pause
)

goto :eof
