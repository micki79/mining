#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Exchange Manager - Automatisches Wallet-Loading von allen Börsen

Features:
- Automatisches Laden beim Start
- Erweiterbar für neue Börsen
- Zentrale Wallet-Verwaltung
- Rate-Limiting und Fehlerbehandlung

Unterstützte Börsen:
- CoinEx (implementiert)
- Binance (vorbereitet)
- Kraken (vorbereitet)
- KuCoin (vorbereitet)
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

class ExchangeStatus(Enum):
    """Status einer Börse"""
    NOT_CONFIGURED = "not_configured"
    CONNECTED = "connected"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    SYNCING = "syncing"


@dataclass
class WalletInfo:
    """Wallet-Informationen"""
    coin: str
    address: str
    chain: str = ""
    memo: str = ""
    source: str = ""  # coinex, binance, manual, etc.
    last_sync: str = ""
    
    def to_dict(self) -> dict:
        return {
            'coin': self.coin,
            'address': self.address,
            'chain': self.chain,
            'memo': self.memo,
            'source': self.source,
            'last_sync': self.last_sync
        }


@dataclass
class ExchangeInfo:
    """Börsen-Informationen"""
    name: str
    status: ExchangeStatus = ExchangeStatus.NOT_CONFIGURED
    wallet_count: int = 0
    last_sync: str = ""
    error_message: str = ""


# =============================================================================
# ABSTRACT EXCHANGE BASE
# =============================================================================

class ExchangeBase(ABC):
    """Basis-Klasse für alle Börsen"""
    
    NAME = "Unknown"
    CONFIG_FILE = "exchange_config.json"
    
    def __init__(self):
        self.api_key = ""
        self.api_secret = ""
        self.status = ExchangeStatus.NOT_CONFIGURED
        self.last_error = ""
        self._load_config()
    
    def _load_config(self):
        """Lädt API-Credentials aus Config"""
        try:
            config_path = Path(self.CONFIG_FILE)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    exchange_config = config.get(self.NAME.lower(), {})
                    self.api_key = exchange_config.get('api_key', '')
                    self.api_secret = exchange_config.get('api_secret', '')
        except Exception as e:
            logger.debug(f"{self.NAME} Config laden: {e}")
    
    def is_configured(self) -> bool:
        """Prüft ob API konfiguriert ist"""
        return bool(self.api_key and self.api_secret)
    
    @abstractmethod
    def test_connection(self) -> Tuple[bool, str]:
        """Testet die Verbindung"""
        pass
    
    @abstractmethod
    def get_deposit_addresses(self) -> Dict[str, WalletInfo]:
        """Holt alle Deposit-Adressen"""
        pass
    
    @abstractmethod
    def get_balances(self) -> Dict[str, float]:
        """Holt alle Kontostände"""
        pass


# =============================================================================
# COINEX EXCHANGE
# =============================================================================

class CoinExExchange(ExchangeBase):
    """CoinEx Börsen-Integration"""
    
    NAME = "CoinEx"
    CONFIG_FILE = "coinex_config.json"
    
    def __init__(self):
        super().__init__()
        self._api = None
    
    def _get_api(self):
        """Lazy-Loading der CoinEx API"""
        if self._api is None:
            try:
                from coinex_api import CoinExAPI
                self._api = CoinExAPI()
            except ImportError:
                logger.error("CoinEx API nicht verfügbar")
        return self._api
    
    def _load_config(self):
        """CoinEx hat eigene Config-Datei"""
        try:
            config_path = Path(self.CONFIG_FILE)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
                    self.api_secret = config.get('api_secret', '')
                    if self.api_key:
                        self.status = ExchangeStatus.CONNECTED
        except Exception as e:
            logger.debug(f"CoinEx Config: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Testet CoinEx Verbindung"""
        api = self._get_api()
        if not api:
            return False, "API nicht verfügbar"
        
        if not api.is_configured():
            return False, "Nicht konfiguriert"
        
        try:
            success, msg = api.test_connection()
            if success:
                self.status = ExchangeStatus.CONNECTED
            else:
                self.status = ExchangeStatus.ERROR
                self.last_error = msg
            return success, msg
        except Exception as e:
            self.status = ExchangeStatus.ERROR
            self.last_error = str(e)
            return False, str(e)
    
    def get_deposit_addresses(self) -> Dict[str, WalletInfo]:
        """Holt alle CoinEx Deposit-Adressen"""
        api = self._get_api()
        if not api or not api.is_configured():
            return {}
        
        try:
            self.status = ExchangeStatus.SYNCING
            wallets_raw = api.get_all_mining_wallets()
            
            wallets = {}
            for coin, data in wallets_raw.items():
                wallets[coin] = WalletInfo(
                    coin=coin,
                    address=data.get('address', ''),
                    chain=data.get('chain', coin),
                    memo=data.get('memo', ''),
                    source='coinex',
                    last_sync=time.strftime('%Y-%m-%d %H:%M:%S')
                )
            
            self.status = ExchangeStatus.CONNECTED
            return wallets
            
        except Exception as e:
            self.status = ExchangeStatus.ERROR
            self.last_error = str(e)
            logger.error(f"CoinEx Wallets Fehler: {e}")
            return {}
    
    def get_balances(self) -> Dict[str, float]:
        """Holt CoinEx Balances"""
        api = self._get_api()
        if not api or not api.is_configured():
            return {}
        
        try:
            return api.get_mining_balances()
        except Exception as e:
            logger.error(f"CoinEx Balances Fehler: {e}")
            return {}


# =============================================================================
# BINANCE EXCHANGE (VORBEREITET)
# =============================================================================

class BinanceExchange(ExchangeBase):
    """Binance Börsen-Integration (Template für Erweiterung)"""
    
    NAME = "Binance"
    
    def test_connection(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Nicht konfiguriert"
        # TODO: Binance API implementieren
        return False, "Noch nicht implementiert"
    
    def get_deposit_addresses(self) -> Dict[str, WalletInfo]:
        # TODO: Binance API implementieren
        return {}
    
    def get_balances(self) -> Dict[str, float]:
        # TODO: Binance API implementieren
        return {}


# =============================================================================
# KRAKEN EXCHANGE (VORBEREITET)
# =============================================================================

class KrakenExchange(ExchangeBase):
    """Kraken Börsen-Integration (Template für Erweiterung)"""
    
    NAME = "Kraken"
    
    def test_connection(self) -> Tuple[bool, str]:
        if not self.is_configured():
            return False, "Nicht konfiguriert"
        # TODO: Kraken API implementieren
        return False, "Noch nicht implementiert"
    
    def get_deposit_addresses(self) -> Dict[str, WalletInfo]:
        return {}
    
    def get_balances(self) -> Dict[str, float]:
        return {}


# =============================================================================
# GATE.IO EXCHANGE
# =============================================================================

class GateIOExchange(ExchangeBase):
    """Gate.io Börsen-Integration"""
    
    NAME = "Gate.io"
    CONFIG_FILE = "gateio_config.json"
    
    def __init__(self):
        super().__init__()
        self._api = None
    
    def _get_api(self):
        """Lazy-Loading der Gate.io API"""
        if self._api is None:
            try:
                from gateio_api import GateIOAPI
                self._api = GateIOAPI()
            except ImportError:
                logger.error("Gate.io API nicht verfügbar")
        return self._api
    
    def _load_config(self):
        """Gate.io hat eigene Config-Datei"""
        try:
            config_path = Path(self.CONFIG_FILE)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.api_key = config.get('api_key', '')
                    self.api_secret = config.get('api_secret', '')
                    if self.api_key:
                        self.status = ExchangeStatus.CONNECTED
                        logger.info("Gate.io Config geladen")
        except Exception as e:
            logger.debug(f"Gate.io Config: {e}")
    
    def test_connection(self) -> Tuple[bool, str]:
        """Testet Gate.io Verbindung"""
        api = self._get_api()
        if not api:
            return False, "API nicht verfügbar"
        
        if not api.is_configured():
            return False, "Nicht konfiguriert"
        
        try:
            # Einfacher Test: Hole Spot Balances
            balances = api.get_spot_balances()
            if balances is not None:  # Auch leere Liste ist OK
                self.status = ExchangeStatus.CONNECTED
                return True, f"Verbunden ({len(balances)} Currencies)"
            else:
                self.status = ExchangeStatus.ERROR
                self.last_error = "Keine Antwort"
                return False, "Keine Antwort"
        except Exception as e:
            self.status = ExchangeStatus.ERROR
            self.last_error = str(e)
            return False, str(e)
    
    def get_deposit_addresses(self) -> Dict[str, WalletInfo]:
        """Holt alle Gate.io Deposit-Adressen"""
        api = self._get_api()
        if not api or not api.is_configured():
            return {}
        
        try:
            self.status = ExchangeStatus.SYNCING
            wallets_raw = api.get_all_deposit_addresses()
            
            wallets = {}
            for coin, wallet in wallets_raw.items():
                wallets[coin] = WalletInfo(
                    coin=coin,
                    address=wallet.address,
                    chain=wallet.chain,
                    memo=wallet.memo,
                    source='gateio',
                    last_sync=time.strftime('%Y-%m-%d %H:%M:%S')
                )
            
            self.status = ExchangeStatus.CONNECTED
            return wallets
            
        except Exception as e:
            self.status = ExchangeStatus.ERROR
            self.last_error = str(e)
            logger.error(f"Gate.io Wallets Fehler: {e}")
            return {}
    
    def get_balances(self) -> Dict[str, float]:
        """Holt Gate.io Balances"""
        api = self._get_api()
        if not api or not api.is_configured():
            return {}
        
        try:
            return api.get_spot_balances()
        except Exception as e:
            logger.error(f"Gate.io Balances Fehler: {e}")
            return {}


# =============================================================================
# UNIVERSAL EXCHANGE MANAGER
# =============================================================================

class UniversalExchangeManager:
    """
    Zentraler Manager für alle Börsen.
    
    Features:
    - Automatisches Laden aller Wallets beim Start
    - Zentrale Wallet-Speicherung in wallets.json
    - Erweiterbar für neue Börsen
    - Fehlerbehandlung und Retry
    """
    
    WALLETS_FILE = "wallets.json"
    
    # Alle verfügbaren Börsen
    EXCHANGES = {
        'coinex': CoinExExchange,
        'gateio': GateIOExchange,
        'binance': BinanceExchange,
        'kraken': KrakenExchange,
    }
    
    def __init__(self, auto_sync: bool = True):
        """
        Initialisiert den Exchange Manager.
        
        Args:
            auto_sync: Automatisch beim Start synchronisieren
        """
        self.exchanges: Dict[str, ExchangeBase] = {}
        self.wallets: Dict[str, WalletInfo] = {}
        self._wallets_file = Path(self.WALLETS_FILE)
        
        # Börsen initialisieren
        self._init_exchanges()
        
        # Wallets laden
        self._load_wallets()
        
        # Automatisch synchronisieren
        if auto_sync:
            self.sync_all()
    
    def _init_exchanges(self):
        """Initialisiert alle Börsen"""
        for name, exchange_class in self.EXCHANGES.items():
            try:
                self.exchanges[name] = exchange_class()
                logger.debug(f"Exchange initialisiert: {name}")
            except Exception as e:
                logger.error(f"Exchange {name} Fehler: {e}")
    
    def _load_wallets(self):
        """Lädt gespeicherte Wallets"""
        if self._wallets_file.exists():
            try:
                with open(self._wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Einfaches Format: {"wallets": {"RVN": "address"}}
                    if 'wallets' in data and isinstance(data['wallets'], dict):
                        for coin, value in data['wallets'].items():
                            if isinstance(value, str):
                                # Altes Format: nur Adresse
                                self.wallets[coin] = WalletInfo(
                                    coin=coin,
                                    address=value,
                                    source='manual'
                                )
                            elif isinstance(value, dict):
                                # Neues Format: komplette Info
                                self.wallets[coin] = WalletInfo(
                                    coin=value.get('coin', coin),
                                    address=value.get('address', ''),
                                    chain=value.get('chain', ''),
                                    memo=value.get('memo', ''),
                                    source=value.get('source', 'unknown'),
                                    last_sync=value.get('last_sync', '')
                                )
                    
                    logger.info(f"Geladen: {len(self.wallets)} Wallets")
            except Exception as e:
                logger.error(f"Wallets laden Fehler: {e}")
    
    def _save_wallets(self):
        """Speichert alle Wallets"""
        try:
            # Einfaches Format für Kompatibilität
            simple_wallets = {coin: w.address for coin, w in self.wallets.items()}
            
            # Erweitertes Format
            detailed_wallets = {coin: w.to_dict() for coin, w in self.wallets.items()}
            
            data = {
                'wallets': simple_wallets,  # Für Kompatibilität
                'wallets_detailed': detailed_wallets,  # Für Details
                'version': '2.0',
                'last_sync': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            with open(self._wallets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Gespeichert: {len(self.wallets)} Wallets")
            return True
        except Exception as e:
            logger.error(f"Wallets speichern Fehler: {e}")
            return False
    
    def sync_all(self) -> Dict[str, Tuple[int, int, str]]:
        """
        Synchronisiert alle konfigurierten Börsen.
        
        Returns:
            Dict mit {exchange: (neue, aktualisierte, fehler)}
        """
        results = {}
        
        for name, exchange in self.exchanges.items():
            if not exchange.is_configured():
                results[name] = (0, 0, "Nicht konfiguriert")
                continue
            
            try:
                logger.info(f"Synchronisiere {name}...")
                new, updated, error = self.sync_exchange(name)
                results[name] = (new, updated, error or "OK")
            except Exception as e:
                results[name] = (0, 0, str(e))
                logger.error(f"{name} Sync Fehler: {e}")
        
        return results
    
    def sync_exchange(self, exchange_name: str) -> Tuple[int, int, Optional[str]]:
        """
        Synchronisiert eine einzelne Börse.
        
        Returns:
            (neue_wallets, aktualisierte_wallets, fehler_msg)
        """
        exchange = self.exchanges.get(exchange_name.lower())
        if not exchange:
            return 0, 0, f"Börse '{exchange_name}' nicht gefunden"
        
        if not exchange.is_configured():
            return 0, 0, "Nicht konfiguriert"
        
        # Verbindung testen
        success, msg = exchange.test_connection()
        if not success:
            return 0, 0, msg
        
        # Wallets holen
        new_wallets = exchange.get_deposit_addresses()
        
        new_count = 0
        updated_count = 0
        
        for coin, wallet_info in new_wallets.items():
            if not wallet_info.address:
                continue
            
            existing = self.wallets.get(coin)
            
            if not existing:
                # Neue Wallet
                self.wallets[coin] = wallet_info
                new_count += 1
                logger.info(f"CoinEx: Neue Wallet {coin}")
            elif existing.address != wallet_info.address:
                # Nur aktualisieren wenn von gleicher Quelle oder manuell
                if existing.source == wallet_info.source or existing.source == 'manual':
                    self.wallets[coin] = wallet_info
                    updated_count += 1
                    logger.info(f"CoinEx: Wallet aktualisiert {coin}")
        
        self._save_wallets()
        
        return new_count, updated_count, None
    
    def get_wallet(self, coin: str) -> Optional[str]:
        """Gibt Wallet-Adresse für Coin zurück"""
        wallet = self.wallets.get(coin.upper())
        return wallet.address if wallet else None
    
    def get_wallet_info(self, coin: str) -> Optional[WalletInfo]:
        """Gibt vollständige Wallet-Info zurück"""
        return self.wallets.get(coin.upper())
    
    def get_all_wallets(self) -> Dict[str, str]:
        """Gibt alle Wallets als {coin: address} zurück"""
        return {coin: w.address for coin, w in self.wallets.items() if w.address}
    
    def list_wallets(self) -> List[WalletInfo]:
        """Gibt alle Wallets als Liste von WalletInfo zurück - für GUI Tabelle"""
        return list(self.wallets.values())
    
    def get_wallets_by_source(self, source: str) -> Dict[str, str]:
        """Gibt Wallets einer bestimmten Quelle zurück"""
        return {
            coin: w.address 
            for coin, w in self.wallets.items() 
            if w.source == source and w.address
        }
    
    def set_wallet(self, coin: str, address: str, source: str = 'manual') -> bool:
        """Setzt eine Wallet manuell"""
        coin = coin.upper()
        
        if not address or len(address) < 10:
            return False
        
        self.wallets[coin] = WalletInfo(
            coin=coin,
            address=address.strip(),
            source=source,
            last_sync=time.strftime('%Y-%m-%d %H:%M:%S')
        )
        
        return self._save_wallets()
    
    def remove_wallet(self, coin: str) -> bool:
        """Entfernt eine Wallet"""
        coin = coin.upper()
        if coin in self.wallets:
            del self.wallets[coin]
            return self._save_wallets()
        return False
    
    def get_exchange_status(self) -> Dict[str, ExchangeInfo]:
        """Gibt Status aller Börsen zurück"""
        status = {}
        for name, exchange in self.exchanges.items():
            wallet_count = len([
                w for w in self.wallets.values() 
                if w.source == name.lower()
            ])
            status[name] = ExchangeInfo(
                name=exchange.NAME,
                status=exchange.status,
                wallet_count=wallet_count,
                error_message=exchange.last_error
            )
        return status
    
    def has_wallet(self, coin: str) -> bool:
        """Prüft ob Wallet vorhanden und gültig ist"""
        wallet = self.wallets.get(coin.upper())
        return bool(wallet and wallet.address and len(wallet.address) > 10)
    
    def fetch_all_wallets(self) -> int:
        """
        Holt alle Wallets von allen konfigurierten Börsen.
        
        Returns:
            Anzahl der geladenen Wallets
        """
        count = 0
        
        for name, exchange in self.exchanges.items():
            if not exchange.is_configured():
                continue
            
            try:
                wallets = exchange.get_deposit_addresses()
                for coin, wallet_info in wallets.items():
                    self.wallets[coin.upper()] = wallet_info
                    count += 1
                logger.info(f"{name}: {len(wallets)} Wallets geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden von {name}: {e}")
        
        if count > 0:
            self._save_wallets()
        
        return count


# =============================================================================
# GLOBALE INSTANZ
# =============================================================================

_manager: Optional[UniversalExchangeManager] = None

def get_exchange_manager(auto_sync: bool = True) -> UniversalExchangeManager:
    """Gibt globale Manager-Instanz zurück"""
    global _manager
    if _manager is None:
        _manager = UniversalExchangeManager(auto_sync=auto_sync)
    return _manager


def auto_sync_wallets() -> Dict[str, Tuple[int, int, str]]:
    """Convenience-Funktion für automatische Wallet-Synchronisierung"""
    manager = get_exchange_manager()
    return manager.sync_all()


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "="*60)
    print("  Universal Exchange Manager - Test")
    print("="*60 + "\n")
    
    # Manager erstellen (auto_sync=True)
    manager = get_exchange_manager()
    
    # Status anzeigen
    print("\n--- Börsen Status ---")
    for name, info in manager.get_exchange_status().items():
        status_emoji = "✅" if info.status == ExchangeStatus.CONNECTED else "❌"
        print(f"  {status_emoji} {info.name}: {info.status.value} ({info.wallet_count} Wallets)")
        if info.error_message:
            print(f"      Fehler: {info.error_message}")
    
    # Wallets anzeigen
    print("\n--- Geladene Wallets ---")
    wallets = manager.get_all_wallets()
    print(f"  Total: {len(wallets)} Wallets")
    
    for coin, address in sorted(wallets.items()):
        wallet_info = manager.get_wallet_info(coin)
        source = wallet_info.source if wallet_info else "?"
        print(f"  {coin:6} [{source:8}] → {address[:35]}...")
    
    # Wallets nach Quelle
    print("\n--- Wallets nach Quelle ---")
    for source in ['coinex', 'manual']:
        source_wallets = manager.get_wallets_by_source(source)
        print(f"  {source}: {len(source_wallets)} Wallets")
    
    print("\n" + "="*60)
