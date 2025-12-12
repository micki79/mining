#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wallet Manager - Speichert und lädt Wallet-Adressen für alle Coins
Teil des GPU Mining Profit Switcher V11.0 Ultimate
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Standard-Datei für Wallets
WALLETS_FILE = "wallets.json"

# Bekannte Coins mit Wallet-Format-Hinweisen
COIN_WALLET_INFO = {
    "RVN": {"name": "Ravencoin", "prefix": "R", "length": 34, "example": "RUVuL3CG2c9qTX3bCr32AfCZ5DJEfdJUTR"},
    "ERG": {"name": "Ergo", "prefix": "9", "length": 51, "example": "9gXA8UYPGvh4FMy5K1JQRqhp7rSUzZ3Y4kz4BfQhRnwJEuvYmqX"},
    "ETC": {"name": "Ethereum Classic", "prefix": "0x", "length": 42, "example": "0x1234..."},
    "FLUX": {"name": "Flux", "prefix": "t1", "length": 35, "example": "t1abc..."},
    "KAS": {"name": "Kaspa", "prefix": "kaspa:", "length": 67, "example": "kaspa:qz..."},
    "CLORE": {"name": "Clore.AI", "prefix": "", "length": 34, "example": ""},
    "ALPH": {"name": "Alephium", "prefix": "", "length": 50, "example": ""},
    "NEXA": {"name": "Nexa", "prefix": "nexa:", "length": 54, "example": "nexa:nq..."},
    "DNX": {"name": "Dynex", "prefix": "", "length": 98, "example": ""},
    "CFX": {"name": "Conflux", "prefix": "cfx:", "length": 50, "example": "cfx:..."},
    "FIRO": {"name": "Firo", "prefix": "a", "length": 34, "example": "a1..."},
    "RXD": {"name": "Radiant", "prefix": "", "length": 34, "example": ""},
    "XNA": {"name": "Neurai", "prefix": "", "length": 34, "example": ""},
    "BTG": {"name": "Bitcoin Gold", "prefix": "G", "length": 34, "example": "G..."},
    "BEAM": {"name": "Beam", "prefix": "", "length": 67, "example": ""},
    "KLS": {"name": "Karlsen", "prefix": "karlsen:", "length": 70, "example": "karlsen:..."},
    "XMR": {"name": "Monero", "prefix": "4", "length": 95, "example": "4..."},
    "ZEPH": {"name": "Zephyr", "prefix": "ZEPHYR", "length": 97, "example": "ZEPHYR..."},
}


class WalletManager:
    """Verwaltet Wallet-Adressen für alle Coins"""
    
    def __init__(self, wallets_file: str = WALLETS_FILE):
        self.wallets_file = Path(wallets_file)
        self.wallets: Dict[str, str] = {}
        self.load()
    
    def load(self) -> bool:
        """Lädt Wallets aus Datei"""
        if self.wallets_file.exists():
            try:
                with open(self.wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.wallets = data.get("wallets", {})
                    logger.info(f"Geladen: {len(self.wallets)} Wallets")
                    return True
            except Exception as e:
                logger.error(f"Fehler beim Laden der Wallets: {e}")
        return False
    
    def save(self) -> bool:
        """Speichert Wallets in Datei"""
        try:
            data = {
                "wallets": self.wallets,
                "version": "1.0"
            }
            with open(self.wallets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Gespeichert: {len(self.wallets)} Wallets")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Wallets: {e}")
            return False
    
    def get_wallet(self, coin: str) -> Optional[str]:
        """Gibt Wallet für Coin zurück"""
        return self.wallets.get(coin.upper())
    
    def set_wallet(self, coin: str, address: str) -> bool:
        """Setzt Wallet für Coin"""
        coin = coin.upper()
        
        # Validierung (optional)
        if not address or len(address) < 10:
            logger.warning(f"Ungültige Wallet-Adresse für {coin}")
            return False
        
        self.wallets[coin] = address.strip()
        self.save()
        logger.info(f"Wallet gesetzt: {coin} = {address[:10]}...")
        return True
    
    def remove_wallet(self, coin: str) -> bool:
        """Entfernt Wallet für Coin"""
        coin = coin.upper()
        if coin in self.wallets:
            del self.wallets[coin]
            self.save()
            return True
        return False
    
    def get_all_wallets(self) -> Dict[str, str]:
        """Gibt alle Wallets zurück"""
        return self.wallets.copy()
    
    def has_wallet(self, coin: str) -> bool:
        """Prüft ob Wallet vorhanden"""
        wallet = self.wallets.get(coin.upper(), "")
        return bool(wallet) and not wallet.startswith("DEINE_")
    
    def get_wallet_info(self, coin: str) -> Optional[Dict]:
        """Gibt Wallet-Format-Info zurück"""
        return COIN_WALLET_INFO.get(coin.upper())
    
    def validate_wallet(self, coin: str, address: str) -> bool:
        """Validiert Wallet-Format (einfache Prüfung)"""
        if not address or len(address) < 10:
            return False
        
        info = COIN_WALLET_INFO.get(coin.upper())
        if info:
            # Prefix prüfen
            if info.get("prefix") and not address.startswith(info["prefix"]):
                # Warnung aber nicht blockieren
                logger.warning(f"{coin} Wallet sollte mit '{info['prefix']}' beginnen")
            
            # Länge prüfen (mit Toleranz)
            expected_len = info.get("length", 0)
            if expected_len > 0 and abs(len(address) - expected_len) > 5:
                logger.warning(f"{coin} Wallet-Länge sollte ~{expected_len} sein, ist {len(address)}")
        
        return True
    
    def sync_from_coinex(self) -> tuple:
        """
        Synchronisiert Wallets von CoinEx Exchange.
        
        Returns:
            (neue_wallets, aktualisierte_wallets, fehler_msg)
        """
        try:
            from coinex_api import CoinExAPI
            
            api = CoinExAPI()
            
            if not api.is_configured():
                return 0, 0, "CoinEx API nicht konfiguriert"
            
            # Verbindung testen
            success, msg = api.test_connection()
            if not success:
                return 0, 0, f"CoinEx Verbindung fehlgeschlagen: {msg}"
            
            # Wallets abrufen
            coinex_wallets = api.get_all_mining_wallets()
            
            new_count = 0
            updated_count = 0
            
            for coin, wallet_data in coinex_wallets.items():
                address = wallet_data.get('address', '')
                if not address:
                    continue
                
                existing = self.wallets.get(coin)
                
                if not existing or existing.startswith("DEINE_"):
                    new_count += 1
                    self.wallets[coin] = address
                    logger.info(f"Neue CoinEx Wallet: {coin} = {address[:20]}...")
                elif existing != address:
                    # Nur aktualisieren wenn alte Adresse nicht manuell war
                    if existing.startswith("DEINE_"):
                        updated_count += 1
                        self.wallets[coin] = address
            
            self.save()
            
            logger.info(f"CoinEx Sync: {new_count} neue, {updated_count} aktualisierte Wallets")
            return new_count, updated_count, None
            
        except ImportError:
            return 0, 0, "CoinEx API Modul nicht gefunden"
        except Exception as e:
            logger.error(f"CoinEx Sync Fehler: {e}")
            return 0, 0, str(e)
    
    def get_coinex_balances(self) -> dict:
        """Holt Mining-Balances von CoinEx"""
        try:
            from coinex_api import CoinExAPI
            api = CoinExAPI()
            if api.is_configured():
                return api.get_mining_balances()
        except:
            pass
        return {}


# Globale Instanz
_wallet_manager = None

def get_wallet_manager() -> WalletManager:
    """Gibt globale WalletManager-Instanz zurück"""
    global _wallet_manager
    if _wallet_manager is None:
        _wallet_manager = WalletManager()
    return _wallet_manager


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    wm = WalletManager("test_wallets.json")
    
    # Test: Wallets setzen
    wm.set_wallet("RVN", "RUVuL3CG2c9qTX3bCr32AfCZ5DJEfdJUTR")
    wm.set_wallet("ERG", "9gXA8UYPGvh4FMy5K1JQRqhp7rSUzZ3Y4kz4BfQhRnwJEuvYmqX")
    
    print("\n=== WALLETS ===")
    for coin, addr in wm.get_all_wallets().items():
        print(f"  {coin}: {addr}")
    
    print("\n=== WALLET INFO ===")
    for coin, info in COIN_WALLET_INFO.items():
        print(f"  {coin}: {info['name']} (Prefix: {info.get('prefix', '-')})")
