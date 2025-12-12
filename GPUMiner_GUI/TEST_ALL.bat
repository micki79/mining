@echo off
title GPU Mining Profit Switcher - Test Suite
cd /d "%~dp0"

echo.
echo  ============================================================
echo   GPU MINING PROFIT SWITCHER - TEST SUITE
echo   Testet ALLE Komponenten auf Fehler
echo  ============================================================
echo.

python TEST_ALL.py

echo.
pause
