@echo off
title CoinEx Wallet Sync
cd /d "%~dp0"

echo.
echo  ============================================================
echo   COINEX WALLET SYNC
echo   Laedt ALLE Wallets von deinem CoinEx Account
echo  ============================================================
echo.

python SYNC_COINEX.py

echo.
pause
