#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate.io API Client
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- API v4 Authentifizierung (HMAC-SHA512)
- Deposit-Adressen abrufen
- Wallet-Balances abfragen
- Automatische Wallet-Synchronisierung
"""

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    import requests
except ImportError:
    requests = None
    print("⚠️ requests nicht installiert")

logger = logging.getLogger(__name__)


@dataclass
class GateIOWallet:
    """Gate.io Wallet-Adresse"""
    coin: str
    address: str
    chain: str = ""
    memo: str = ""
    
    def to_dict(self) -> dict:
        return {
            "coin": self.coin,
            "address": self.address,
            "chain": self.chain,
            "memo": self.memo
        }


class GateIOAPI:
    """
    Gate.io API v4 Client
    
    Verwendung:
        api = GateIOAPI(api_key="...", api_secret="...")
        
        # Deposit-Adresse holen
        wallet = api.get_deposit_address("BTC")
        
        # Alle Wallets synchronisieren
        wallets = api.get_all_deposit_addresses()
    """
    
    BASE_URL = "https://api.gateio.ws"
    PREFIX = "/api/v4"
    CONFIG_FILE = "gateio_config.json"
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        """
        Initialisiert den Gate.io API Client.
        
        Args:
            api_key: Gate.io API Key
            api_secret: Gate.io API Secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Versuche Config zu laden wenn keine Keys übergeben
        if not api_key or not api_secret:
            self._load_config()
        
        if self.api_key and self.api_secret:
            logger.info("Gate.io API initialisiert")
    
    def _load_config(self):
        """Lädt API-Keys aus Config-Datei"""
        config_path = Path(self.CONFIG_FILE)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_key = config.get("api_key", "")
                    self.api_secret = config.get("api_secret", "")
                    if self.api_key:
                        logger.info("Gate.io Config geladen")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Gate.io Config: {e}")
    
    def save_config(self, api_key: str, api_secret: str):
        """Speichert API-Keys in Config-Datei"""
        self.api_key = api_key
        self.api_secret = api_secret
        
        config = {
            "api_key": api_key,
            "api_secret": api_secret,
            "created": datetime.now().isoformat()
        }
        
        try:
            with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            logger.info("Gate.io Config gespeichert")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Prüft ob API konfiguriert ist"""
        return bool(self.api_key and self.api_secret)
    
    def _generate_signature(self, method: str, url: str, query_string: str = "", 
                           payload: str = "") -> Dict[str, str]:
        """
        Generiert die API v4 Signatur.
        
        Gate.io API v4 Signatur-Format:
        - signature_string = METHOD\n/api/v4/endpoint\nquery\nSHA512(body)\ntimestamp
        - Sign: HMAC-SHA512(secret, signature_string)
        """
        # Timestamp als float (wie im offiziellen Beispiel)
        t = time.time()
        
        # Body Hash (SHA512 des Payloads)
        m = hashlib.sha512()
        m.update((payload or "").encode('utf-8'))
        hashed_payload = m.hexdigest()
        
        # Signatur-String erstellen (WICHTIG: url muss /api/v4/... sein!)
        s = '%s\n%s\n%s\n%s\n%s' % (method, url, query_string or "", hashed_payload, t)
        
        # HMAC-SHA512 Signatur
        sign = hmac.new(
            self.api_secret.encode('utf-8'),
            s.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return {
            "KEY": self.api_key,
            "Timestamp": str(t),
            "SIGN": sign,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, params: Dict = None, 
                 data: Dict = None) -> Optional[Any]:
        """
        Führt einen API-Request durch.
        
        Args:
            method: HTTP Methode (GET, POST)
            endpoint: API Endpoint (z.B. "/wallet/deposit_address")
            params: Query-Parameter
            data: Request Body (für POST)
            
        Returns:
            JSON Response oder None bei Fehler
        """
        if not requests:
            logger.error("requests Modul nicht verfügbar")
            return None
        
        if not self.is_configured():
            logger.error("Gate.io API nicht konfiguriert")
            return None
        
        # Volle URL mit Prefix
        full_url_path = self.PREFIX + endpoint
        url = self.BASE_URL + full_url_path
        
        # Query String
        query_string = ""
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        
        # Body
        payload = ""
        if data:
            payload = json.dumps(data)
        
        # Headers mit Signatur (WICHTIG: voller Pfad mit /api/v4!)
        headers = self._generate_signature(method, full_url_path, query_string, payload)
        
        try:
            if method == "GET":
                full_url = f"{url}?{query_string}" if query_string else url
                response = requests.get(full_url, headers=headers, timeout=30)
            else:
                full_url = f"{url}?{query_string}" if query_string else url
                response = requests.post(full_url, headers=headers, data=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", response.text[:100])
                logger.error(f"Gate.io API Fehler ({response.status_code}): {error_msg}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Gate.io Request Fehler: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Gate.io JSON Fehler: {e}")
            return None
    
    def get_deposit_address(self, currency: str, chain: str = "") -> Optional[GateIOWallet]:
        """
        Holt die Deposit-Adresse für eine Währung.
        
        Args:
            currency: Währung (z.B. "BTC", "ETH", "RVN")
            chain: Optional - Blockchain-Netzwerk
            
        Returns:
            GateIOWallet oder None bei Fehler
        """
        params = {"currency": currency.upper()}
        
        result = self._request("GET", "/wallet/deposit_address", params)
        
        if result:
            # Gate.io gibt ein Array zurück
            if isinstance(result, list) and len(result) > 0:
                # Wenn chain angegeben, suche passende
                for addr in result:
                    if chain and addr.get("chain", "").upper() != chain.upper():
                        continue
                    
                    return GateIOWallet(
                        coin=currency.upper(),
                        address=addr.get("address", ""),
                        chain=addr.get("chain", ""),
                        memo=addr.get("payment_id", "") or addr.get("memo", "")
                    )
                
                # Sonst erste Adresse
                first = result[0]
                return GateIOWallet(
                    coin=currency.upper(),
                    address=first.get("address", ""),
                    chain=first.get("chain", ""),
                    memo=first.get("payment_id", "") or first.get("memo", "")
                )
            
            # Einzelnes Objekt
            elif isinstance(result, dict):
                return GateIOWallet(
                    coin=currency.upper(),
                    address=result.get("address", ""),
                    chain=result.get("chain", ""),
                    memo=result.get("payment_id", "") or result.get("memo", "")
                )
        
        return None
    
    def get_all_deposit_addresses(self, coins: List[str] = None) -> Dict[str, GateIOWallet]:
        """
        Holt alle Deposit-Adressen für die angegebenen Coins.
        
        Args:
            coins: Liste der Coins (wenn None, werden Mining-Coins verwendet)
            
        Returns:
            Dict mit {coin: GateIOWallet}
        """
        if coins is None:
            # Standard Mining-Coins
            coins = [
                "BTC", "ETH", "RVN", "ERG", "ETC", "FLUX", "KAS", "ALPH",
                "CFX", "DOGE", "LTC", "BCH", "DASH", "ZEC", "XMR",
                "NEXA", "KDA", "CKB", "HNS", "FIRO", "BEAM", "GRIN",
                "CLORE", "DNX", "ZEPH", "RTM", "XNA", "NEOX", "IRON",
                "MONA", "DGB", "VTC", "GRS", "ARRR", "DERO", "QTC"
            ]
        
        wallets = {}
        total = len(coins)
        
        logger.info(f"Gate.io: Lade {total} Wallet-Adressen...")
        
        for i, coin in enumerate(coins):
            if i > 0 and i % 10 == 0:
                logger.info(f"Gate.io Wallet-Scan: {i}/{total} ({coin}...)")
            
            try:
                wallet = self.get_deposit_address(coin)
                if wallet and wallet.address:
                    wallets[coin] = wallet
                    logger.info(f"  ✓ {coin}: {wallet.address[:20]}...")
                
                # Rate Limiting (Gate.io: 900/min)
                time.sleep(0.1)
                
            except Exception as e:
                logger.debug(f"  ✗ {coin}: {e}")
        
        logger.info(f"Gate.io: {len(wallets)} Wallets von {total} Coins geladen")
        return wallets
    
    def get_spot_balances(self) -> Dict[str, float]:
        """
        Holt alle Spot-Balances.
        
        Returns:
            Dict mit {currency: available_balance}
        """
        result = self._request("GET", "/spot/accounts")
        
        if result and isinstance(result, list):
            balances = {}
            for item in result:
                currency = item.get("currency", "")
                available = float(item.get("available", 0))
                if available > 0:
                    balances[currency] = available
            return balances
        
        return {}
    
    def get_total_balance_usd(self) -> float:
        """
        Holt den Gesamt-Balance in USD.
        
        Returns:
            Gesamt-Wert in USD
        """
        result = self._request("GET", "/wallet/total_balance")
        
        if result:
            return float(result.get("total", {}).get("amount", 0))
        
        return 0.0
    
    def get_currencies(self) -> List[Dict]:
        """
        Holt alle verfügbaren Währungen.
        
        Returns:
            Liste mit Währungs-Informationen
        """
        result = self._request("GET", "/spot/currencies")
        
        if result and isinstance(result, list):
            return result
        
        return []


# =============================================================================
# GATE.IO WALLET SYNC (wie CoinEx)
# =============================================================================

class GateIOWalletSync:
    """
    Synchronisiert Gate.io Wallets mit der lokalen Wallet-Datei
    """
    
    WALLETS_FILE = "wallets.json"
    
    def __init__(self, api: GateIOAPI = None):
        """
        Args:
            api: GateIOAPI Instanz (optional, wird sonst erstellt)
        """
        self.api = api or GateIOAPI()
        self.wallets: Dict[str, str] = {}
        self.wallet_sources: Dict[str, str] = {}  # NEU: Speichert Quelle pro Coin
        self._load_wallets()
    
    def _load_wallets(self):
        """Lädt existierende Wallets"""
        try:
            if Path(self.WALLETS_FILE).exists():
                with open(self.WALLETS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.wallets = data.get("wallets", {})
                    self.wallet_sources = data.get("wallet_sources", {})
        except Exception as e:
            logger.error(f"Fehler beim Laden der Wallets: {e}")
    
    def _save_wallets(self, gateio_coins: List[str] = None):
        """Speichert Wallets mit Quellenangabe"""
        try:
            # Existierende Daten laden
            data = {}
            if Path(self.WALLETS_FILE).exists():
                with open(self.WALLETS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Wallets aktualisieren
            if "wallets" not in data:
                data["wallets"] = {}
            data["wallets"].update(self.wallets)
            
            # Wallet-Quellen aktualisieren
            if "wallet_sources" not in data:
                data["wallet_sources"] = {}
            
            # Gate.io als Quelle für die synchronisierten Coins setzen
            if gateio_coins:
                for coin in gateio_coins:
                    data["wallet_sources"][coin.upper()] = "Gate.io"
            
            data["wallet_sources"].update(self.wallet_sources)
            data["last_gateio_sync"] = datetime.now().isoformat()
            
            # Speichern
            with open(self.WALLETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Wallets gespeichert: {len(self.wallets)} Wallets")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
    
    def _update_exchange_manager(self, gateio_wallets: Dict[str, 'GateIOWallet']):
        """Aktualisiert auch den ExchangeManager mit Quellenangabe"""
        try:
            from exchange_api import ExchangeManager, WalletAddress
            
            em = ExchangeManager()
            
            for coin, wallet in gateio_wallets.items():
                if not wallet.address or wallet.address.startswith("New address"):
                    continue
                
                coin_upper = coin.upper()
                
                # WalletAddress mit Gate.io als Quelle erstellen
                wallet_obj = WalletAddress(
                    coin=coin_upper,
                    network=wallet.chain or coin_upper,
                    address=wallet.address,
                    memo=wallet.memo or "",
                    exchange="Gate.io",
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
    
    def sync_all(self, coins: List[str] = None) -> Dict[str, int]:
        """
        Synchronisiert alle Gate.io Wallets.
        
        Args:
            coins: Liste der zu synchronisierenden Coins
            
        Returns:
            Dict mit {"new": int, "updated": int, "total": int}
        """
        if not self.api.is_configured():
            logger.error("Gate.io API nicht konfiguriert!")
            return {"new": 0, "updated": 0, "total": 0}
        
        logger.info("=== Gate.io Wallet Sync ===")
        
        # Wallets von Gate.io holen
        gateio_wallets = self.api.get_all_deposit_addresses(coins)
        
        new_count = 0
        updated_count = 0
        synced_coins = []
        
        for coin, wallet in gateio_wallets.items():
            if not wallet.address or wallet.address.startswith("New address"):
                continue
            
            coin_upper = coin.upper()
            synced_coins.append(coin_upper)
            
            if coin_upper not in self.wallets:
                self.wallets[coin_upper] = wallet.address
                self.wallet_sources[coin_upper] = "Gate.io"
                new_count += 1
                logger.info(f"Neue Wallet: {coin_upper}")
            elif self.wallets[coin_upper] != wallet.address:
                self.wallets[coin_upper] = wallet.address
                self.wallet_sources[coin_upper] = "Gate.io"
                updated_count += 1
                logger.info(f"Wallet aktualisiert: {coin_upper}")
            else:
                # Auch bei gleichbleibender Adresse - Quelle aktualisieren
                self.wallet_sources[coin_upper] = "Gate.io"
        
        # Speichern in wallets.json
        if new_count > 0 or updated_count > 0:
            self._save_wallets(synced_coins)
        
        # ExchangeManager aktualisieren
        self._update_exchange_manager(gateio_wallets)
        
        result = {
            "new": new_count,
            "updated": updated_count,
            "total": len(gateio_wallets)
        }
        
        logger.info(f"Gate.io Sync: {new_count} neu, {updated_count} aktualisiert, {result['total']} total")
        
        return result


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Gate.io API Test")
    print("=" * 60)
    
    # API initialisieren
    api = GateIOAPI()
    
    if not api.is_configured():
        print("\n⚠️ Gate.io API nicht konfiguriert!")
        print("Erstelle gateio_config.json mit:")
        print(json.dumps({
            "api_key": "DEIN_API_KEY",
            "api_secret": "DEIN_API_SECRET"
        }, indent=2))
    else:
        print("\n✓ Gate.io API konfiguriert")
        
        # Test: Deposit-Adresse
        print("\n📍 Teste Deposit-Adresse für BTC...")
        wallet = api.get_deposit_address("BTC")
        if wallet:
            print(f"   Adresse: {wallet.address}")
            print(f"   Chain: {wallet.chain}")
        
        # Test: Balances
        print("\n💰 Teste Spot-Balances...")
        balances = api.get_spot_balances()
        if balances:
            for coin, amount in list(balances.items())[:5]:
                print(f"   {coin}: {amount}")
        
        # Test: Wallet Sync
        print("\n🔄 Teste Wallet-Sync...")
        sync = GateIOWalletSync(api)
        result = sync.sync_all(["BTC", "ETH", "RVN", "ERG"])
        print(f"   Neu: {result['new']}, Aktualisiert: {result['updated']}")
    
    print("\n✅ Test beendet")
