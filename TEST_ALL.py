#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Mining Profit Switcher - MASTER TEST SUITE
Testet ALLE Komponenten und zeigt Fehler an

Führe aus mit: python TEST_ALL.py
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Farben für Output
class Colors:
    OK = '\033[92m'      # Grün
    FAIL = '\033[91m'    # Rot
    WARN = '\033[93m'    # Gelb
    INFO = '\033[94m'    # Blau
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg): print(f"{Colors.OK}✅ {msg}{Colors.END}")
def fail(msg): print(f"{Colors.FAIL}❌ {msg}{Colors.END}")
def warn(msg): print(f"{Colors.WARN}⚠️  {msg}{Colors.END}")
def info(msg): print(f"{Colors.INFO}ℹ️  {msg}{Colors.END}")
def header(msg): print(f"\n{Colors.BOLD}{'='*60}\n  {msg}\n{'='*60}{Colors.END}")

# Test-Ergebnisse sammeln
test_results = {
    'passed': 0,
    'failed': 0,
    'warnings': 0,
    'errors': []
}

def test_pass(name):
    test_results['passed'] += 1
    ok(name)

def test_fail(name, error=""):
    test_results['failed'] += 1
    test_results['errors'].append((name, error))
    fail(f"{name}: {error}")

def test_warn(name, msg=""):
    test_results['warnings'] += 1
    warn(f"{name}: {msg}")


# =============================================================================
# TEST 1: Python-Umgebung
# =============================================================================
def test_python_environment():
    header("TEST 1: Python-Umgebung")
    
    # Python Version
    version = sys.version_info
    if version >= (3, 8):
        test_pass(f"Python Version: {version.major}.{version.minor}.{version.micro}")
    else:
        test_fail("Python Version", f"Mindestens 3.8 benötigt, gefunden: {version.major}.{version.minor}")
    
    # Benötigte Module
    required_modules = [
        ('requests', 'pip install requests'),
        ('PySide6', 'pip install PySide6'),
        ('pynvml', 'pip install pynvml'),
    ]
    
    optional_modules = [
        ('pyqtgraph', 'pip install pyqtgraph'),
        ('psutil', 'pip install psutil'),
    ]
    
    for module, install_cmd in required_modules:
        try:
            __import__(module)
            test_pass(f"Modul '{module}' verfügbar")
        except ImportError:
            test_fail(f"Modul '{module}'", f"Installiere mit: {install_cmd}")
    
    for module, install_cmd in optional_modules:
        try:
            __import__(module)
            test_pass(f"Modul '{module}' verfügbar (optional)")
        except ImportError:
            test_warn(f"Modul '{module}' fehlt (optional)", install_cmd)


# =============================================================================
# TEST 2: Projekt-Dateien
# =============================================================================
def test_project_files():
    header("TEST 2: Projekt-Dateien")
    
    required_files = [
        'mining_gui.py',
        'coinex_api.py',
        'wallet_manager.py',
        'profit_calculator.py',
        'auto_profit_switcher.py',
        'miner_installer.py',
        'gpu_monitor.py',
        'coin_config.py',
        'miner_config.py',
    ]
    
    optional_files = [
        'auto_pool_fetcher.py',
        'exchange_manager.py',
        'multi_gpu_widget.py',
        'hardware_db.py',
    ]
    
    config_files = [
        'coinex_config.json',
        'wallets.json',
        'flight_sheets.json',
    ]
    
    for f in required_files:
        if Path(f).exists():
            test_pass(f"Datei '{f}' vorhanden")
        else:
            test_fail(f"Datei '{f}'", "Nicht gefunden!")
    
    for f in optional_files:
        if Path(f).exists():
            test_pass(f"Datei '{f}' vorhanden (optional)")
        else:
            test_warn(f"Datei '{f}' fehlt", "Optional")
    
    for f in config_files:
        if Path(f).exists():
            test_pass(f"Config '{f}' vorhanden")
            # Validiere JSON
            try:
                with open(f, 'r') as file:
                    json.load(file)
                test_pass(f"Config '{f}' ist gültiges JSON")
            except json.JSONDecodeError as e:
                test_fail(f"Config '{f}' JSON", str(e))
        else:
            test_warn(f"Config '{f}' fehlt", "Wird beim Start erstellt")


# =============================================================================
# TEST 3: CoinEx API
# =============================================================================
def test_coinex_api():
    header("TEST 3: CoinEx API")
    
    try:
        from coinex_api import CoinExAPI, CoinExWalletSync
        test_pass("CoinEx API Import")
    except ImportError as e:
        test_fail("CoinEx API Import", str(e))
        return
    
    # API initialisieren
    try:
        api = CoinExAPI()
        test_pass("CoinExAPI Instanz erstellt")
    except Exception as e:
        test_fail("CoinExAPI Instanz", str(e))
        return
    
    # Konfiguration prüfen
    if api.is_configured():
        test_pass(f"API konfiguriert (Key: {api.api_key[:10]}...)")
        
        # Verbindung testen
        try:
            success, msg = api.test_connection()
            if success:
                test_pass(f"API Verbindung: {msg}")
                
                # Wallets laden
                try:
                    info("Lade Wallets von CoinEx (kann 30-60 Sekunden dauern)...")
                    wallets = api.get_all_mining_wallets()
                    if wallets:
                        test_pass(f"Wallets geladen: {len(wallets)} Stück")
                        # Zeige erste 5
                        for i, (coin, data) in enumerate(list(wallets.items())[:5]):
                            print(f"      {coin}: {data['address'][:30]}...")
                        if len(wallets) > 5:
                            print(f"      ... und {len(wallets) - 5} weitere")
                    else:
                        test_warn("Keine Wallets", "Möglicherweise keine Coins auf CoinEx")
                except Exception as e:
                    test_fail("Wallets laden", str(e))
            else:
                test_fail(f"API Verbindung", msg)
        except Exception as e:
            test_fail("API Verbindung Test", str(e))
    else:
        test_warn("API nicht konfiguriert", "Erstelle coinex_config.json")


# =============================================================================
# TEST 4: Wallet-Speicherung
# =============================================================================
def test_wallet_storage():
    header("TEST 4: Wallet-Speicherung")
    
    wallets_file = Path('wallets.json')
    
    # Test-Wallets
    test_wallets = {
        "TEST_RVN": "RTestAddress123456789012345678901234",
        "TEST_ERG": "9TestErgoAddress12345678901234567890123456789012",
    }
    
    # Speichern testen
    try:
        # Backup bestehende Datei
        backup_data = None
        if wallets_file.exists():
            with open(wallets_file, 'r') as f:
                backup_data = json.load(f)
        
        # Test-Daten schreiben
        test_data = {"wallets": test_wallets, "test": True}
        with open(wallets_file, 'w') as f:
            json.dump(test_data, f, indent=2)
        test_pass("Wallets schreiben")
        
        # Lesen testen
        with open(wallets_file, 'r') as f:
            loaded = json.load(f)
        
        if loaded.get('wallets', {}).get('TEST_RVN') == test_wallets['TEST_RVN']:
            test_pass("Wallets lesen (Format korrekt)")
        else:
            test_fail("Wallets lesen", "Format nicht korrekt!")
        
        # Backup wiederherstellen
        if backup_data:
            with open(wallets_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            test_pass("Backup wiederhergestellt")
        else:
            # Test-Daten löschen
            wallets_file.unlink()
            
    except Exception as e:
        test_fail("Wallet-Speicherung", str(e))


# =============================================================================
# TEST 5: Pool-Fetcher
# =============================================================================
def test_pool_fetcher():
    header("TEST 5: Pool-Fetcher")
    
    try:
        from auto_pool_fetcher import AutoPoolFetcher, KNOWN_POOLS, get_best_pool_for_coin
        test_pass("Pool-Fetcher Import")
    except ImportError as e:
        test_warn("Pool-Fetcher Import", f"Datei fehlt: {e}")
        return
    
    # Bekannte Pools prüfen
    test_coins = ["RVN", "ERG", "ETC", "KAS", "GRIN", "BEAM"]
    
    for coin in test_coins:
        if coin in KNOWN_POOLS:
            pools = KNOWN_POOLS[coin]
            test_pass(f"{coin}: {len(pools)} Pools bekannt ({pools[0]['name']})")
        else:
            test_warn(f"{coin}", "Keine bekannten Pools")
    
    # Pool-Fetcher testen
    try:
        fetcher = AutoPoolFetcher()
        test_pass("AutoPoolFetcher Instanz")
        
        pool = fetcher.get_best_pool("RVN")
        if pool:
            test_pass(f"Bester Pool für RVN: {pool['name']}")
        else:
            test_warn("Kein Pool für RVN", "Cache leer?")
    except Exception as e:
        test_fail("Pool-Fetcher", str(e))


# =============================================================================
# TEST 6: Miner-Installer
# =============================================================================
def test_miner_installer():
    header("TEST 6: Miner-Installer")
    
    try:
        from miner_installer import MinerInstaller, MINERS
        test_pass("Miner-Installer Import")
    except ImportError as e:
        test_fail("Miner-Installer Import", str(e))
        return
    
    # Miner-Konfiguration prüfen
    test_pass(f"{len(MINERS)} Miner konfiguriert")
    
    required_miners = ['trex', 'lolminer', 'gminer', 'nbminer']
    for miner in required_miners:
        if miner in MINERS:
            cfg = MINERS[miner]
            test_pass(f"{cfg['name']} v{cfg['version']} konfiguriert")
        else:
            test_fail(f"Miner '{miner}'", "Nicht in MINERS definiert!")
    
    # Installer-Klasse testen
    try:
        installer = MinerInstaller()
        test_pass("MinerInstaller Instanz")
        
        # Methoden prüfen
        if hasattr(installer, 'install_miner'):
            test_pass("Methode 'install_miner' vorhanden")
        else:
            test_fail("Methode 'install_miner'", "Fehlt!")
        
        if hasattr(installer, 'install_essential'):
            test_pass("Methode 'install_essential' vorhanden")
        else:
            test_fail("Methode 'install_essential'", "Fehlt!")
        
        if hasattr(installer, 'is_installed'):
            test_pass("Methode 'is_installed' vorhanden")
        else:
            test_fail("Methode 'is_installed'", "Fehlt!")
        
        # Installierte Miner prüfen
        installed = installer.get_installed_miners()
        if installed:
            test_pass(f"Installierte Miner: {', '.join(installed)}")
        else:
            test_warn("Keine Miner installiert", "Führe INSTALL_ESSENTIAL.bat aus")
            
    except Exception as e:
        test_fail("MinerInstaller", str(e))


# =============================================================================
# TEST 7: GPU-Erkennung
# =============================================================================
def test_gpu_detection():
    header("TEST 7: GPU-Erkennung")
    
    # pynvml Test
    try:
        import pynvml
        test_pass("pynvml Import")
        
        pynvml.nvmlInit()
        test_pass("NVML initialisiert")
        
        # Device Count (verschiedene Versionen)
        device_count = 0
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            test_pass(f"nvmlDeviceGetCount(): {device_count} GPUs")
        except AttributeError:
            try:
                device_count = pynvml.nvmlDeviceGetDeviceCount()
                test_pass(f"nvmlDeviceGetDeviceCount(): {device_count} GPUs")
            except AttributeError:
                test_fail("GPU Count", "Keine passende Funktion gefunden!")
        
        # GPUs auflisten
        for i in range(device_count):
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                # iGPU Check
                name_lower = name.lower()
                is_igpu = any([
                    'radeon(tm)' in name_lower,
                    'radeon graphics' in name_lower,
                    'intel' in name_lower,
                ])
                
                if is_igpu:
                    test_warn(f"GPU {i}: {name}", "iGPU - wird übersprungen")
                else:
                    # Mehr Info holen
                    try:
                        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
                        test_pass(f"GPU {i}: {name} ({temp}°C, {power:.0f}W)")
                    except:
                        test_pass(f"GPU {i}: {name}")
                        
            except Exception as e:
                test_fail(f"GPU {i}", str(e))
        
        pynvml.nvmlShutdown()
        
    except ImportError:
        test_fail("pynvml Import", "pip install pynvml")
    except Exception as e:
        test_fail("GPU-Erkennung", str(e))


# =============================================================================
# TEST 8: Profit-Calculator
# =============================================================================
def test_profit_calculator():
    header("TEST 8: Profit-Calculator")
    
    try:
        from profit_calculator import ProfitCalculator, get_profit_calculator
        test_pass("Profit-Calculator Import")
    except ImportError as e:
        test_fail("Profit-Calculator Import", str(e))
        return
    
    try:
        calc = get_profit_calculator()
        test_pass("ProfitCalculator Instanz")
        
        # WhatToMine testen
        info("Lade Daten von WhatToMine...")
        try:
            top_coins = calc.get_most_profitable()[:10]
            if top_coins:
                test_pass(f"WhatToMine: {len(top_coins)} Coins geladen")
                for coin in top_coins[:5]:
                    print(f"      {coin['coin']}: ${coin['usd_profit_24h']:.2f}/Tag ({coin['algorithm']})")
            else:
                test_warn("WhatToMine", "Keine Coins zurückgegeben")
        except Exception as e:
            test_fail("WhatToMine API", str(e))
            
    except Exception as e:
        test_fail("Profit-Calculator", str(e))


# =============================================================================
# TEST 9: Auto-Profit Switcher
# =============================================================================
def test_auto_profit_switcher():
    header("TEST 9: Auto-Profit Switcher")
    
    try:
        from auto_profit_switcher import BEST_POOLS, ALGO_MINER_MAP
        test_pass("Auto-Profit Switcher Import")
        
        # BEST_POOLS prüfen
        if BEST_POOLS:
            test_pass(f"BEST_POOLS: {len(BEST_POOLS)} Coins konfiguriert")
        else:
            test_warn("BEST_POOLS", "Leer!")
        
        # ALGO_MINER_MAP prüfen
        if ALGO_MINER_MAP:
            test_pass(f"ALGO_MINER_MAP: {len(ALGO_MINER_MAP)} Algorithmen")
            important_algos = ['kawpow', 'autolykos2', 'etchash', 'cuckatoo32']
            for algo in important_algos:
                if algo in ALGO_MINER_MAP:
                    miners = ALGO_MINER_MAP[algo]
                    test_pass(f"  {algo}: {', '.join(miners[:2])}")
                else:
                    test_warn(f"  {algo}", "Nicht in ALGO_MINER_MAP!")
        else:
            test_fail("ALGO_MINER_MAP", "Leer!")
            
    except ImportError as e:
        test_fail("Auto-Profit Switcher Import", str(e))


# =============================================================================
# TEST 10: GUI-Module Syntax
# =============================================================================
def test_gui_modules():
    header("TEST 10: GUI-Module Syntax")
    
    gui_modules = [
        'mining_gui',
        'multi_gpu_widget',
        'gpu_optimizer_widget',
        'themes',
    ]
    
    for module in gui_modules:
        try:
            # Syntax prüfen ohne zu importieren (würde Qt starten)
            module_path = Path(f"{module}.py")
            if module_path.exists():
                import py_compile
                py_compile.compile(str(module_path), doraise=True)
                test_pass(f"{module}.py Syntax OK")
            else:
                test_warn(f"{module}.py", "Nicht gefunden")
        except py_compile.PyCompileError as e:
            test_fail(f"{module}.py Syntax", str(e))
        except Exception as e:
            test_fail(f"{module}.py", str(e))


# =============================================================================
# TEST 11: Integration - Wallets → Auto-Switch
# =============================================================================
def test_integration_wallets():
    header("TEST 11: Integration - Wallets verfügbar für Auto-Switch")
    
    # Wallets laden
    wallets = {}
    
    # 1. Aus wallets.json
    try:
        if Path('wallets.json').exists():
            with open('wallets.json', 'r') as f:
                data = json.load(f)
                for coin, value in data.get('wallets', {}).items():
                    if isinstance(value, str) and len(value) > 10:
                        wallets[coin] = value
                    elif isinstance(value, dict) and value.get('address'):
                        wallets[coin] = value['address']
            test_pass(f"wallets.json: {len(wallets)} Wallets")
    except Exception as e:
        test_warn("wallets.json", str(e))
    
    # 2. Profit-Coins laden
    try:
        from profit_calculator import get_profit_calculator
        calc = get_profit_calculator()
        top_coins = calc.get_most_profitable()[:15]
        
        mineable = 0
        not_mineable = 0
        
        print("\n      Coin-Status für Auto-Switch:")
        for coin_data in top_coins[:10]:
            coin = coin_data['coin']
            profit = coin_data['usd_profit_24h']
            has_wallet = coin in wallets
            
            status = "✅" if has_wallet else "❌"
            print(f"      {status} {coin:6} ${profit:.2f}/Tag")
            
            if has_wallet:
                mineable += 1
            else:
                not_mineable += 1
        
        if mineable > 0:
            test_pass(f"Minebar: {mineable} von Top 10 Coins")
        else:
            test_fail("Keine Coins minebar!", "Wallets fehlen - führe CoinEx-Sync aus")
            
    except Exception as e:
        test_fail("Integration", str(e))


# =============================================================================
# ZUSAMMENFASSUNG
# =============================================================================
def print_summary():
    header("ZUSAMMENFASSUNG")
    
    total = test_results['passed'] + test_results['failed']
    
    print(f"\n  {Colors.OK}Bestanden: {test_results['passed']}{Colors.END}")
    print(f"  {Colors.FAIL}Fehlgeschlagen: {test_results['failed']}{Colors.END}")
    print(f"  {Colors.WARN}Warnungen: {test_results['warnings']}{Colors.END}")
    print(f"  Gesamt: {total} Tests\n")
    
    if test_results['errors']:
        print(f"\n{Colors.FAIL}FEHLER DIE BEHOBEN WERDEN MÜSSEN:{Colors.END}")
        for name, error in test_results['errors']:
            print(f"  ❌ {name}")
            print(f"     → {error}")
        print()
    
    if test_results['failed'] == 0:
        print(f"{Colors.OK}{Colors.BOLD}🎉 ALLE TESTS BESTANDEN! System bereit.{Colors.END}")
    else:
        print(f"{Colors.FAIL}{Colors.BOLD}⚠️  {test_results['failed']} FEHLER müssen behoben werden!{Colors.END}")
    
    print()


# =============================================================================
# MAIN
# =============================================================================
def main():
    print(f"""
{Colors.BOLD}╔══════════════════════════════════════════════════════════════╗
║     GPU MINING PROFIT SWITCHER - MASTER TEST SUITE           ║
║                                                              ║
║     Testet alle Komponenten auf Fehler                       ║
╚══════════════════════════════════════════════════════════════╝{Colors.END}
""")
    
    # Alle Tests ausführen
    test_python_environment()
    test_project_files()
    test_coinex_api()
    test_wallet_storage()
    test_pool_fetcher()
    test_miner_installer()
    test_gpu_detection()
    test_profit_calculator()
    test_auto_profit_switcher()
    test_gui_modules()
    test_integration_wallets()
    
    # Zusammenfassung
    print_summary()
    
    # Exit-Code
    sys.exit(0 if test_results['failed'] == 0 else 1)


if __name__ == "__main__":
    main()
