#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoinEx Wallet Sync - Testet und synchronisiert alle Wallets

Führe aus mit: python SYNC_COINEX.py
"""

import json
import time
from pathlib import Path

def main():
    print("\n" + "="*60)
    print("  COINEX WALLET SYNC")
    print("="*60 + "\n")
    
    # CoinEx API importieren
    try:
        from coinex_api import CoinExAPI, CoinExWalletSync
        print("✅ CoinEx API Import OK")
    except ImportError as e:
        print(f"❌ Import Fehler: {e}")
        return
    
    # API initialisieren
    api = CoinExAPI()
    
    if not api.is_configured():
        print("❌ CoinEx API nicht konfiguriert!")
        print("   Bitte coinex_config.json erstellen mit api_key und api_secret")
        return
    
    print(f"✅ API konfiguriert: {api.api_key[:15]}...")
    
    # Verbindung testen
    print("\n--- Teste Verbindung ---")
    success, msg = api.test_connection()
    
    if not success:
        print(f"❌ Verbindung fehlgeschlagen: {msg}")
        return
    
    print(f"✅ Verbindung OK: {msg}")
    
    # Wallets laden
    print("\n--- Lade Wallets von CoinEx ---")
    print("   (Dies kann 30-60 Sekunden dauern...)\n")
    
    wallets = api.get_all_mining_wallets()
    
    if not wallets:
        print("❌ Keine Wallets gefunden!")
        return
    
    print(f"✅ {len(wallets)} Wallets von CoinEx geladen!\n")
    
    # Zeige alle Wallets
    print("--- Geladene Wallets ---")
    for coin, data in sorted(wallets.items()):
        addr = data['address']
        print(f"   {coin:6} → {addr[:40]}...")
    
    # In wallets.json speichern (EINFACHES FORMAT!)
    print("\n--- Speichere in wallets.json ---")
    
    wallets_file = Path('wallets.json')
    
    # Bestehendes laden
    existing = {}
    if wallets_file.exists():
        try:
            with open(wallets_file, 'r') as f:
                existing = json.load(f)
        except:
            pass
    
    # Wallets aktualisieren (einfaches Format!)
    if 'wallets' not in existing:
        existing['wallets'] = {}
    
    new_count = 0
    for coin, data in wallets.items():
        if coin not in existing['wallets']:
            new_count += 1
        existing['wallets'][coin] = data['address']  # Nur Adresse!
    
    # Metadata hinzufügen
    existing['coinex_sync'] = time.strftime('%Y-%m-%d %H:%M:%S')
    existing['total_wallets'] = len(existing['wallets'])
    
    # Speichern
    with open(wallets_file, 'w') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {len(existing['wallets'])} Wallets gespeichert ({new_count} neu)")
    
    # Prüfen
    print("\n--- Prüfe wallets.json ---")
    with open(wallets_file, 'r') as f:
        data = json.load(f)
    
    wallet_count = len(data.get('wallets', {}))
    print(f"   Wallets in Datei: {wallet_count}")
    
    # Zeige wichtige Mining-Coins
    important_coins = ['RVN', 'ERG', 'ETC', 'FLUX', 'KAS', 'ALPH', 'GRIN', 'BEAM', 'FIRO', 'XNA', 'CLORE']
    print("\n   Wichtige Mining-Coins:")
    for coin in important_coins:
        addr = data['wallets'].get(coin)
        if addr:
            print(f"   ✅ {coin:6} → {addr[:30]}...")
        else:
            print(f"   ❌ {coin:6} → FEHLT!")
    
    print("\n" + "="*60)
    print("  FERTIG!")
    print("  Starte jetzt die GUI neu - alle Wallets sind verfügbar!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
