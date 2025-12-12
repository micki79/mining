#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CoinEx API Integration - Automatisches Wallet-Abrufen

Holt Deposit-Adressen für Mining-Coins von CoinEx.
"""

import hashlib
import hmac
import json
import time
import logging
from typing import Dict, Optional, List, Tuple
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# =============================================================================
# COINEX API CLIENT
# =============================================================================

class CoinExAPI:
    """
    CoinEx API Client für Wallet-Management.
    
    Funktionen:
    - Deposit-Adressen abrufen
    - Kontostände prüfen
    - Unterstützte Coins auflisten
    """
    
    BASE_URL = "https://api.coinex.com/v2"
    
    # Mining-relevante Coins auf CoinEx
    # Basis Mining-Coins (Fallback wenn API nicht erreichbar)
    MINING_COINS_BASE = [
        "RVN", "ERG", "ETC", "FLUX", "KAS", "ALPH", "NEXA", 
        "XMR", "ZEPH", "CFX", "FIRO", "DNX", "BEAM", "KLS",
        "RXD", "XNA", "CLORE", "IRON", "DERO", "RTM", "ZEC",
        "GRIN", "CTXC", "AIPG", "OCTA", "NOVO", "HNS", "CKB",
        "SERO", "TUBE", "CAMP", "MEWC", "PAPRY", "MEOW", "NIM",
        "NEOXA", "VTC", "FITA", "GRAM", "BELL", "LBRY", "BTC",
        "LTC", "DASH", "ZEN", "BTG", "DGB", "RDD", "VIA", "GRS"
    ]
    
    @classmethod
    def get_all_coins_dynamic(cls) -> List[str]:
        """
        Holt ALLE Mining-Coins dynamisch von mehreren Quellen!
        
        Quellen:
        1. WhatToMine (GPU + ASIC)
        2. hashrate.no
        3. minerstat
        
        Wird bei jedem Aufruf aktualisiert.
        """
        all_coins = set(cls.MINING_COINS_BASE)
        
        # 1. Von WhatToMine GPU Coins holen
        try:
            response = requests.get(
                "https://whattomine.com/coins.json",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if response.status_code == 200:
                data = response.json()
                for coin_data in data.get('coins', {}).values():
                    tag = coin_data.get('tag', '').upper()
                    if tag and len(tag) <= 6:
                        all_coins.add(tag)
                logger.info(f"WhatToMine: {len(data.get('coins', {}))} GPU Coins geladen")
        except Exception as e:
            logger.debug(f"WhatToMine GPU API: {e}")
        
        # 2. Von WhatToMine ASIC Coins holen
        try:
            response = requests.get(
                "https://whattomine.com/asic.json",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if response.status_code == 200:
                data = response.json()
                for coin_data in data.get('coins', {}).values():
                    tag = coin_data.get('tag', '').upper()
                    if tag and len(tag) <= 6:
                        all_coins.add(tag)
                logger.info(f"WhatToMine: {len(data.get('coins', {}))} ASIC Coins geladen")
        except Exception as e:
            logger.debug(f"WhatToMine ASIC API: {e}")
        
        # 3. Von hashrate.no Coins holen (benötigt API Key)
        try:
            from hashrateno_api import HashrateNoAPI
            hashrate_api = HashrateNoAPI()
            coins_data = hashrate_api.get_coins()
            
            if coins_data:
                for coin_info in coins_data:
                    # Verschiedene mögliche Strukturen
                    if isinstance(coin_info, dict):
                        tag = coin_info.get('ticker', coin_info.get('coin', coin_info.get('symbol', ''))).upper()
                    elif isinstance(coin_info, str):
                        tag = coin_info.upper()
                    else:
                        continue
                    
                    if tag and 2 <= len(tag) <= 6:
                        all_coins.add(tag)
                
                logger.info(f"hashrate.no: {len(coins_data)} Coins geladen")
        except ImportError:
            logger.debug("hashrateno_api nicht verfügbar")
        except Exception as e:
            logger.debug(f"hashrate.no API: {e}")
        
        # 4. Von minerstat Coins holen (öffentliche API)
        try:
            response = requests.get(
                "https://api.minerstat.com/v2/coins",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 MiningTool/1.0'}
            )
            if response.status_code == 200:
                data = response.json()
                count = 0
                for coin_key, coin_data in data.items():
                    if isinstance(coin_data, dict):
                        tag = coin_data.get('coin', coin_key).upper()
                    else:
                        tag = coin_key.upper()
                    
                    if tag and 2 <= len(tag) <= 6:
                        all_coins.add(tag)
                        count += 1
                
                logger.info(f"minerstat: {count} Coins geladen")
        except Exception as e:
            logger.debug(f"minerstat API: {e}")
        
        logger.info(f"Dynamische Coin-Liste: {len(all_coins)} Coins total")
        return sorted(list(all_coins))
    
    # Dynamische Liste (wird beim Import aktualisiert)
    MINING_COINS = MINING_COINS_BASE.copy()
    
    def __init__(self, api_key: str = "", api_secret: str = "", config_file: str = "coinex_config.json"):
        """
        Initialisiert den CoinEx API Client.
        
        Args:
            api_key: CoinEx API Key (Zugangs-ID)
            api_secret: CoinEx API Secret (Geheimer Schlüssel)
            config_file: Pfad zur Config-Datei
        """
        self.config_file = Path(config_file)
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Config laden falls vorhanden
        if not api_key and self.config_file.exists():
            self._load_config()
        
        self._session = requests.Session() if requests else None
        
        if self.api_key:
            logger.info("CoinEx API initialisiert")
    
    def _load_config(self):
        """Lädt API-Credentials aus Config-Datei"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.api_key = config.get('api_key', '')
                self.api_secret = config.get('api_secret', '')
                logger.info("CoinEx Config geladen")
        except Exception as e:
            logger.warning(f"CoinEx Config nicht geladen: {e}")
    
    def save_config(self):
        """Speichert API-Credentials in Config-Datei"""
        try:
            config = {
                'api_key': self.api_key,
                'api_secret': self.api_secret,
                'updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info("CoinEx Config gespeichert")
            return True
        except Exception as e:
            logger.error(f"CoinEx Config Fehler: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Prüft ob API-Credentials konfiguriert sind"""
        return bool(self.api_key and self.api_secret)
    
    def _generate_signature(self, method: str, path: str, params: Dict = None, body: Dict = None) -> Dict:
        """
        Generiert die Signatur für authentifizierte Requests.
        
        CoinEx V2 API Signatur (KORREKT):
        1. prepared_str = method + request_path (inkl. query string) + body + timestamp
        2. signature = HMAC-SHA256(prepared_str, secret) mit latin-1 encoding!
        """
        timestamp = str(int(time.time() * 1000))
        
        # Body als JSON String (nur für POST)
        body_str = ""
        if body:
            body_str = json.dumps(body, separators=(',', ':'))
        
        # Request Path mit Query String
        request_path = path
        if params:
            # Query String OHNE ? am Anfang für Signatur
            query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            request_path = f"{path}?{query_string}"
        
        # Prepared String für Signatur: METHOD + PATH + BODY + TIMESTAMP
        prepared_str = method.upper() + request_path + body_str + timestamp
        
        # HMAC-SHA256 Signatur mit latin-1 encoding (WICHTIG!)
        signature = hmac.new(
            bytes(self.api_secret, 'latin-1'),
            msg=bytes(prepared_str, 'latin-1'),
            digestmod=hashlib.sha256
        ).hexdigest().lower()
        
        return {
            'X-COINEX-KEY': self.api_key,
            'X-COINEX-SIGN': signature,
            'X-COINEX-TIMESTAMP': timestamp,
            'Content-Type': 'application/json; charset=utf-8'
        }
    
    def _request(self, method: str, endpoint: str, params: Dict = None, body: Dict = None) -> Optional[Dict]:
        """Führt einen API Request aus"""
        if not self._session:
            logger.error("requests Modul nicht verfügbar")
            return None
        
        if not self.is_configured():
            logger.error("CoinEx API nicht konfiguriert")
            return None
        
        # WICHTIG: Für die Signatur brauchen wir den VOLLEN Pfad inkl. /v2
        full_path = f"/v2{endpoint}"
        
        # URL bauen (MIT Query-Parametern für GET)
        url = f"{self.BASE_URL}{endpoint}"
        if params and method.upper() == "GET":
            query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            url = f"{url}?{query_string}"
        
        # Signatur mit VOLLEM Pfad (inkl. /v2)
        headers = self._generate_signature(method, full_path, params, body)
        
        try:
            if method.upper() == "GET":
                # WICHTIG: params=None, da sie bereits in der URL sind!
                response = self._session.get(url, headers=headers, timeout=10)
            else:
                response = self._session.post(url, headers=headers, json=body, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0:
                    return data.get('data', {})
                else:
                    logger.error(f"CoinEx API Fehler: {data.get('message', 'Unknown')}")
                    return None
            else:
                logger.error(f"CoinEx HTTP Fehler: {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("CoinEx API Timeout")
        except requests.exceptions.ConnectionError:
            logger.error("CoinEx API Verbindungsfehler")
        except Exception as e:
            logger.error(f"CoinEx API Fehler: {e}")
        
        return None
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Testet die API-Verbindung.
        
        Returns:
            (success, message)
        """
        if not self.is_configured():
            return False, "API nicht konfiguriert"
        
        # Account Info abrufen
        result = self._request("GET", "/assets/spot/balance")
        
        if result is not None:
            return True, "Verbindung erfolgreich!"
        else:
            return False, "Verbindung fehlgeschlagen"
    
    def get_deposit_address(self, coin: str, chain: str = None) -> Optional[Dict]:
        """
        Holt die Deposit-Adresse für einen Coin.
        
        Args:
            coin: Coin Symbol (z.B. "RVN", "ERG")
            chain: Optional: Netzwerk/Chain (z.B. "RVN" für native)
            
        Returns:
            Dict mit 'address' und optional 'memo'
        """
        coin = coin.upper()
        
        # Chain bestimmen (meist gleich wie Coin für native Chains)
        if not chain:
            chain = self._get_default_chain(coin)
        
        params = {
            'ccy': coin,
            'chain': chain
        }
        
        result = self._request("GET", "/assets/deposit-address", params=params)
        
        if result:
            return {
                'coin': coin,
                'chain': chain,
                'address': result.get('address', ''),
                'memo': result.get('memo', ''),
                'is_valid': bool(result.get('address'))
            }
        
        return None
    
    def _get_default_chain(self, coin: str) -> str:
        """Gibt die Standard-Chain für einen Coin zurück"""
        # Die meisten Mining-Coins haben ihre native Chain
        chain_map = {
            'RVN': 'RVN',
            'ERG': 'ERG',
            'ETC': 'ETC',
            'FLUX': 'FLUX',
            'KAS': 'KAS',
            'ALPH': 'ALPH',
            'XMR': 'XMR',
            'ZEPH': 'ZEPH',
            'CFX': 'CFX',
            'FIRO': 'FIRO',
            'BEAM': 'BEAM',
            'DNX': 'DNX',
            'NEXA': 'NEXA',
            'RXD': 'RXD',
            'CLORE': 'CLORE',
            'KLS': 'KLS',
            'IRON': 'IRON',
        }
        return chain_map.get(coin, coin)
    
    def get_all_mining_wallets(self, use_dynamic: bool = True) -> Dict[str, Dict]:
        """
        Holt alle Deposit-Adressen für Mining-relevante Coins.
        
        Args:
            use_dynamic: Wenn True, werden Coins dynamisch von WhatToMine geholt
        
        Returns:
            Dict mit {coin: {address, chain, memo}}
        """
        wallets = {}
        
        # Dynamische oder statische Coin-Liste verwenden
        if use_dynamic:
            try:
                coins_to_check = self.get_all_coins_dynamic()
                logger.info(f"Dynamische Coin-Liste: {len(coins_to_check)} Coins")
            except:
                coins_to_check = self.MINING_COINS_BASE
                logger.info(f"Fallback auf statische Liste: {len(coins_to_check)} Coins")
        else:
            coins_to_check = self.MINING_COINS_BASE
        
        # Fortschritt loggen
        total = len(coins_to_check)
        
        for i, coin in enumerate(coins_to_check):
            if i % 10 == 0:
                logger.info(f"CoinEx Wallet-Scan: {i}/{total} ({coin}...)")
            
            result = self.get_deposit_address(coin)
            
            if result and result.get('is_valid'):
                wallets[coin] = {
                    'address': result['address'],
                    'chain': result['chain'],
                    'memo': result.get('memo', ''),
                    'source': 'coinex'
                }
                logger.info(f"  ✓ {coin}: {result['address'][:20]}...")
            
            # Rate Limiting
            time.sleep(0.15)
        
        logger.info(f"CoinEx: {len(wallets)} Wallets von {total} Coins geladen")
        return wallets
    
    def get_balances(self) -> Dict[str, float]:
        """
        Holt alle Kontostände.
        
        Returns:
            Dict mit {coin: balance}
        """
        result = self._request("GET", "/assets/spot/balance")
        
        if not result:
            return {}
        
        balances = {}
        for item in result:
            coin = item.get('ccy', '')
            available = float(item.get('available', 0))
            frozen = float(item.get('frozen', 0))
            
            total = available + frozen
            if total > 0:
                balances[coin] = {
                    'available': available,
                    'frozen': frozen,
                    'total': total
                }
        
        return balances
    
    def get_mining_balances(self) -> Dict[str, Dict]:
        """Holt nur Balances für Mining-Coins"""
        all_balances = self.get_balances()
        return {coin: bal for coin, bal in all_balances.items() if coin in self.MINING_COINS}


# =============================================================================
# WALLET SYNC MANAGER
# =============================================================================

class CoinExWalletSync:
    """
    Synchronisiert CoinEx Wallets mit dem Mining Tool.
    
    - Lädt Wallets von CoinEx
    - Speichert in wallets.json im EINFACHEN Format: {"wallets": {"RVN": "adresse"}}
    - Aktualisiert Flight Sheets
    - NEU: Aktualisiert auch ExchangeManager mit Quellenangabe
    """
    
    def __init__(self, coinex_api: CoinExAPI, wallets_file: str = "wallets.json"):
        self.api = coinex_api
        self.wallets_file = Path(wallets_file)
        self.wallets = self._load_wallets()
    
    def _load_wallets(self) -> Dict:
        """Lädt existierende Wallets"""
        if self.wallets_file.exists():
            try:
                with open(self.wallets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {'wallets': {}, 'wallet_sources': {}}
    
    def _save_wallets(self, coinex_coins: List[str] = None):
        """Speichert Wallets mit Quellenangabe"""
        try:
            # Wallet-Quellen aktualisieren
            if "wallet_sources" not in self.wallets:
                self.wallets["wallet_sources"] = {}
            
            # CoinEx als Quelle für die synchronisierten Coins setzen
            if coinex_coins:
                for coin in coinex_coins:
                    self.wallets["wallet_sources"][coin.upper()] = "CoinEx"
            
            with open(self.wallets_file, 'w', encoding='utf-8') as f:
                json.dump(self.wallets, f, indent=2, ensure_ascii=False)
            logger.info(f"Wallets gespeichert: {len(self.wallets.get('wallets', {}))} Wallets")
            return True
        except Exception as e:
            logger.error(f"Wallet-Speichern fehlgeschlagen: {e}")
            return False
    
    def _update_exchange_manager(self, coinex_wallets: Dict[str, Dict]):
        """Aktualisiert auch den ExchangeManager mit Quellenangabe"""
        try:
            from exchange_api import ExchangeManager, WalletAddress
            from datetime import datetime
            
            em = ExchangeManager()
            
            for coin, wallet_data in coinex_wallets.items():
                address = wallet_data.get('address', '')
                if not address:
                    continue
                
                coin_upper = coin.upper()
                
                # WalletAddress mit CoinEx als Quelle erstellen
                wallet_obj = WalletAddress(
                    coin=coin_upper,
                    network=wallet_data.get('chain', coin_upper),
                    address=address,
                    memo=wallet_data.get('memo', ''),
                    exchange="CoinEx",
                    last_updated=datetime.now().isoformat()
                )
                
                em.wallets[coin_upper] = wallet_obj
                logger.info(f"Wallet aktualisiert: {coin_upper}")
            
            # Speichern
            em.save_config()
            
        except ImportError:
            logger.debug("ExchangeManager nicht verfügbar")
        except Exception as e:
            logger.debug(f"ExchangeManager Update: {e}")
    
    def sync_from_coinex(self) -> Tuple[int, int]:
        """
        Synchronisiert Wallets von CoinEx.
        SPEICHERT IM EINFACHEN FORMAT: {"wallets": {"RVN": "adresse"}}
        
        Returns:
            (neue_wallets, aktualisierte_wallets)
        """
        if not self.api.is_configured():
            logger.error("CoinEx API nicht konfiguriert")
            return 0, 0
        
        new_count = 0
        updated_count = 0
        synced_coins = []
        
        coinex_wallets = self.api.get_all_mining_wallets()
        
        if 'wallets' not in self.wallets:
            self.wallets['wallets'] = {}
        if 'wallet_sources' not in self.wallets:
            self.wallets['wallet_sources'] = {}
        
        for coin, wallet_data in coinex_wallets.items():
            address = wallet_data.get('address', '')
            if not address:
                continue
            
            synced_coins.append(coin)
            
            # EINFACHES FORMAT: Coin als Key, Adresse als Value
            existing = self.wallets['wallets'].get(coin)
            
            if not existing:
                new_count += 1
                logger.info(f"Neue Wallet: {coin}")
            elif existing != address:
                updated_count += 1
                logger.info(f"Wallet aktualisiert: {coin}")
            
            # Speichere im einfachen Format!
            self.wallets['wallets'][coin] = address
            self.wallets['wallet_sources'][coin] = "CoinEx"
        
        self.wallets['coinex_last_sync'] = time.strftime('%Y-%m-%d %H:%M:%S')
        self.wallets['total_count'] = len(self.wallets['wallets'])
        self._save_wallets(synced_coins)
        
        # ExchangeManager aktualisieren
        self._update_exchange_manager(coinex_wallets)
        
        logger.info(f"CoinEx Sync: {new_count} neu, {updated_count} aktualisiert, {len(self.wallets['wallets'])} total")
        return new_count, updated_count
    
    def get_wallet_for_coin(self, coin: str) -> Optional[str]:
        """Gibt die Wallet-Adresse für einen Coin zurück"""
        return self.wallets.get('wallets', {}).get(coin.upper())
    
    def get_all_coinex_wallets(self) -> Dict[str, str]:
        """Gibt alle Wallets zurück: {coin: address}"""
        return self.wallets.get('wallets', {}).copy()


# =============================================================================
# INITIALISIERUNG MIT VORINSTALLIERTEN CREDENTIALS
# =============================================================================

def create_default_config():
    """Erstellt die Standard-Config mit vorinstallierten Credentials"""
    config = {
        'api_key': '4F5224720D1845839A9E9E9AB1E87DEE',
        'api_secret': '77E433F6E3137524A7C75CD6E1BAC70D2CBE7B2ED05B70DE',
        'updated': time.strftime('%Y-%m-%d %H:%M:%S'),
        'note': 'CoinEx API für automatisches Wallet-Abrufen'
    }
    
    config_file = Path('coinex_config.json')
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        logger.info("CoinEx Config erstellt mit vorinstallierten Credentials")
        return True
    except Exception as e:
        logger.error(f"Config-Erstellung fehlgeschlagen: {e}")
        return False


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("\n" + "="*60)
    print("  CoinEx API Test")
    print("="*60 + "\n")
    
    # Config erstellen falls nicht vorhanden
    if not Path('coinex_config.json').exists():
        print("Erstelle Config mit vorinstallierten Credentials...")
        create_default_config()
    
    # API initialisieren
    api = CoinExAPI()
    
    if not api.is_configured():
        print("❌ API nicht konfiguriert!")
        exit(1)
    
    print(f"API Key: {api.api_key[:10]}...")
    
    # Verbindung testen
    print("\n--- Teste Verbindung ---")
    success, msg = api.test_connection()
    print(f"{'✅' if success else '❌'} {msg}")
    
    if success:
        # Wallets abrufen
        print("\n--- Lade Mining Wallets ---")
        wallets = api.get_all_mining_wallets()
        
        print(f"\nGefunden: {len(wallets)} Wallets")
        for coin, data in wallets.items():
            addr = data['address']
            print(f"  {coin:6} → {addr[:30]}...")
        
        # Balances
        print("\n--- Mining Balances ---")
        balances = api.get_mining_balances()
        
        if balances:
            for coin, bal in balances.items():
                print(f"  {coin:6} → {bal['available']:.8f} (verfügbar)")
        else:
            print("  Keine Mining-Balances gefunden")
        
        # Wallet Sync
        print("\n--- Wallet Sync ---")
        sync = CoinExWalletSync(api)
        new, updated = sync.sync_from_coinex()
        print(f"  Neu: {new}, Aktualisiert: {updated}")
    
    print("\n" + "="*60)
