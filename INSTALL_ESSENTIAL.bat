@echo off
:: ============================================================
:: Installiert nur die 2 wichtigsten Miner:
:: - T-Rex (kawpow, progpow, ethash, etchash, autolykos2)
:: - lolMiner (cuckatoo32, beamhashiii, equihash, ethash)
:: 
:: Damit sind ~95% aller profitablen Coins abgedeckt!
:: ============================================================

title Miner Installation - Essential Pack

cd /d "%~dp0"

echo.
echo  ============================================================
echo   ESSENTIAL MINER PACK
echo   T-Rex + lolMiner = 95%% Coin-Abdeckung
echo  ============================================================
echo.

:: Python pruefen
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo  FEHLER: Python nicht gefunden!
    echo  Bitte Python von https://www.python.org installieren
    pause
    exit /b 1
)

:: Requests pruefen/installieren
echo  Pruefe requests Modul...
python -c "import requests" >nul 2>nul
if %errorlevel% neq 0 (
    echo  Installiere requests...
    pip install requests
)

:: T-Rex installieren
echo.
echo  [1/2] Installiere T-Rex...
echo        Unterstuetzt: kawpow, progpow, ethash, etchash, autolykos2
echo.
if exist "miners\trex\t-rex.exe" (
    echo        T-Rex bereits installiert!
) else (
    python -c "from miner_installer import MinerInstaller; m = MinerInstaller(); m.install_miner('trex')"
)

:: lolMiner installieren
echo.
echo  [2/2] Installiere lolMiner...
echo        Unterstuetzt: cuckatoo32, beamhashiii, equihash, ethash
echo.
if exist "miners\lolminer\lolMiner.exe" (
    echo        lolMiner bereits installiert!
) else (
    python -c "from miner_installer import MinerInstaller; m = MinerInstaller(); m.install_miner('lolminer')"
)

:: Zusammenfassung
echo.
echo  ============================================================
echo   INSTALLATION ABGESCHLOSSEN
echo  ============================================================
echo.
echo   Installierte Miner:
if exist "miners\trex\t-rex.exe" (
    echo   [X] T-Rex      - RVN, EPIC, FIRO, ERG, ETC, ETHW, XNA, FREN, NEOX, CLORE
) else (
    echo   [ ] T-Rex      - NICHT INSTALLIERT!
)
if exist "miners\lolminer\lolMiner.exe" (
    echo   [X] lolMiner   - GRIN, BEAM, ZEC, BTG
) else (
    echo   [ ] lolMiner   - NICHT INSTALLIERT!
)
echo.
echo   Starte jetzt DEV_START.bat fuer die GUI!
echo.
pause
