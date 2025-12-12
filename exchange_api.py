#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exchange API - Automatische Wallet-Adressen von ALLEN Börsen
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Unterstützte Börsen:
- Binance
- Kraken  
- Coinbase
- KuCoin
- Bybit
- OKX
- Gate.io
- Bitget
- MEXC
- HTX (Huobi)
- Crypto.com
- Bitstamp
- Gemini
- Bitfinex
- Poloniex

HINWEIS: Für die API-Zugriffe werden API Keys benötigt!
"""

import hashlib
import hmac
import time
import logging
import requests
import base64
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path
from urllib.parse import urlencode
from datetime import datetime

logger = logging.getLogger(__name__)

# Konfigurationsdatei
CONFIG_FILE = "exchange_config.json"

# Liste aller unterstützten Börsen
SUPPORTED_EXCHANGES = [
    {"id": "coinex", "name": "CoinEx", "url": "https://www.coinex.com"},  # NEU - Vorinstalliert!
    {"id": "binance", "name": "Binance", "url": "https://www.binance.com"},
    {"id": "kraken", "name": "Kraken", "url": "https://www.kraken.com"},
    {"id": "coinbase", "name": "Coinbase", "url": "https://www.coinbase.com"},
    {"id": "kucoin", "name": "KuCoin", "url": "https://www.kucoin.com"},
    {"id": "bybit", "name": "Bybit", "url": "https://www.bybit.com"},
    {"id": "okx", "name": "OKX", "url": "https://www.okx.com"},
    {"id": "gateio", "name": "Gate.io", "url": "https://www.gate.io"},
    {"id": "bitget", "name": "Bitget", "url": "https://www.bitget.com"},
    {"id": "mexc", "name": "MEXC", "url": "https://www.mexc.com"},
    {"id": "htx", "name": "HTX (Huobi)", "url": "https://www.htx.com"},
    {"id": "cryptocom", "name": "Crypto.com", "url": "https://crypto.com"},
    {"id": "bitstamp", "name": "Bitstamp", "url": "https://www.bitstamp.net"},
    {"id": "gemini", "name": "Gemini", "url": "https://www.gemini.com"},
    {"id": "bitfinex", "name": "Bitfinex", "url": "https://www.bitfinex.com"},
    {"id": "poloniex", "name": "Poloniex", "url": "https://poloniex.com"},
]

# Mining-relevante Coins (Basis-Liste, wird dynamisch erweitert)
MINING_COINS = [
    # GPU Mining - Hauptcoins
    "RVN", "ERG", "ETC", "FLUX", "KAS", "ALPH", "NEXA", "XMR", 
    "ZEC", "BEAM", "GRIN", "CFX", "CTXC", "RXD", "DNX", "ZEPH",
    "XNA", "CLORE", "AIPG", "OCTA", "NOVO", "RTM", "FIRO",
    # GPU Mining - Weitere
    "KLS", "IRON", "DERO", "HNS", "CKB", "SERO", "TUBE", "NIM",
    "NEOXA", "VTC", "MEWC", "PAPRY", "MEOW", "BTG", "DGB",
    # CPU Mining
    "XMR", "ZEPH", "RTM", "DERO",
    # ASIC
    "BTC", "LTC", "DASH", "ZEN", "GRS", "VIA", "RDD", "LBRY"
]

def get_coins_from_whattomine() -> List[str]:
    """
    Holt ALLE aktuellen Mining-Coins von mehreren Quellen.
    
    Quellen:
    1. WhatToMine (GPU + ASIC)
    2. hashrate.no
    3. minerstat
    """
    import requests
    all_coins = set(MINING_COINS)
    
    # 1. WhatToMine GPU Coins
    try:
        response = requests.get(
            "https://whattomine.com/coins.json",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 MiningTool/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            for coin_data in data.get('coins', {}).values():
                tag = coin_data.get('tag', '').upper()
                if tag and 2 <= len(tag) <= 6:
                    all_coins.add(tag)
    except:
        pass
    
    # 2. WhatToMine ASIC Coins
    try:
        response = requests.get(
            "https://whattomine.com/asic.json",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 MiningTool/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            for coin_data in data.get('coins', {}).values():
                tag = coin_data.get('tag', '').upper()
                if tag and 2 <= len(tag) <= 6:
                    all_coins.add(tag)
    except:
        pass
    
    # 3. hashrate.no Coins
    try:
        from hashrateno_api import HashrateNoAPI
        api = HashrateNoAPI()
        coins_data = api.get_coins()
        if coins_data:
            for coin_info in coins_data:
                if isinstance(coin_info, dict):
                    tag = coin_info.get('ticker', coin_info.get('coin', '')).upper()
                elif isinstance(coin_info, str):
                    tag = coin_info.upper()
                else:
                    continue
                if tag and 2 <= len(tag) <= 6:
                    all_coins.add(tag)
    except:
        pass
    
    # 4. minerstat Coins
    try:
        response = requests.get(
            "https://api.minerstat.com/v2/coins",
            timeout=10,
            headers={'User-Agent': 'Mozilla/5.0 MiningTool/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            for coin_key, coin_data in data.items():
                if isinstance(coin_data, dict):
                    tag = coin_data.get('coin', coin_key).upper()
                else:
                    tag = coin_key.upper()
                if tag and 2 <= len(tag) <= 6:
                    all_coins.add(tag)
    except:
        pass
    
    return sorted(list(all_coins))


@dataclass
class WalletAddress:
    """Wallet-Adresse von einer Börse"""
    coin: str
    network: str
    address: str
    memo: Optional[str] = None
    exchange: str = ""
    last_updated: str = ""


class ExchangeAPI:
    """Basis-Klasse für Börsen-APIs"""
    
    NAME = "Unknown"
    BASE_URL = ""
    
    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase  # Für KuCoin, OKX etc.
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'GPUMiner/1.0'
        })
    
    def is_configured(self) -> bool:
        """Prüft ob API Keys konfiguriert sind"""
        return bool(self.api_key and self.api_secret)
    
    def test_connection(self) -> tuple[bool, str]:
        """Testet die API-Verbindung"""
        return False, "Nicht implementiert"
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        raise NotImplementedError
    
    def get_all_addresses(self) -> List[WalletAddress]:
        """Holt alle Deposit-Adressen für Mining-Coins"""
        addresses = []
        for coin in MINING_COINS:
            try:
                addr = self.get_deposit_address(coin)
                if addr and addr.address:
                    addresses.append(addr)
                    logger.info(f"{self.NAME}: {coin} Adresse geladen")
                time.sleep(0.2)  # Rate limiting
            except Exception as e:
                logger.debug(f"{self.NAME}: {coin} Fehler: {e}")
        return addresses


class BinanceAPI(ExchangeAPI):
    """Binance API"""
    
    NAME = "Binance"
    BASE_URL = "https://api.binance.com"
    
    def _sign(self, params: Dict) -> Dict:
        params['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        return params
    
    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "API Keys nicht konfiguriert"
        try:
            params = self._sign({})
            response = self.session.get(
                f"{self.BASE_URL}/sapi/v1/account/status",
                params=params,
                headers={'X-MBX-APIKEY': self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                return True, "Verbunden"
            return False, f"Fehler: {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            params = {'coin': coin.upper()}
            if network:
                params['network'] = network
            params = self._sign(params)
            
            response = self.session.get(
                f"{self.BASE_URL}/sapi/v1/capital/deposit/address",
                params=params,
                headers={'X-MBX-APIKEY': self.api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return WalletAddress(
                    coin=data.get('coin', coin),
                    network=data.get('network', network),
                    address=data.get('address', ''),
                    memo=data.get('tag') or data.get('memo'),
                    exchange='Binance',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"Binance {coin}: {e}")
        return None


class KrakenAPI(ExchangeAPI):
    """Kraken API"""
    
    NAME = "Kraken"
    BASE_URL = "https://api.kraken.com"
    
    def _sign(self, urlpath: str, data: Dict) -> Dict:
        nonce = str(int(time.time() * 1000))
        data['nonce'] = nonce
        postdata = urlencode(data)
        encoded = (nonce + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        return {
            'API-Key': self.api_key,
            'API-Sign': base64.b64encode(signature.digest()).decode()
        }
    
    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "API Keys nicht konfiguriert"
        try:
            urlpath = '/0/private/Balance'
            data = {}
            headers = self._sign(urlpath, data.copy())
            response = self.session.post(
                f"{self.BASE_URL}{urlpath}",
                data=data,
                headers=headers,
                timeout=10
            )
            result = response.json()
            if not result.get('error'):
                return True, "Verbunden"
            return False, str(result.get('error'))
        except Exception as e:
            return False, str(e)
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        
        # Kraken Asset Mapping
        asset_map = {'BTC': 'XBT', 'DOGE': 'XDG'}
        asset = asset_map.get(coin.upper(), coin.upper())
        
        try:
            urlpath = '/0/private/DepositAddresses'
            data = {'asset': asset}
            headers = self._sign(urlpath, data.copy())
            
            response = self.session.post(
                f"{self.BASE_URL}{urlpath}",
                data=data,
                headers=headers,
                timeout=10
            )
            
            result = response.json()
            if result.get('result') and len(result['result']) > 0:
                addr_data = result['result'][0]
                return WalletAddress(
                    coin=coin.upper(),
                    network=network or coin,
                    address=addr_data.get('address', ''),
                    memo=addr_data.get('tag'),
                    exchange='Kraken',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"Kraken {coin}: {e}")
        return None


class KuCoinAPI(ExchangeAPI):
    """KuCoin API"""
    
    NAME = "KuCoin"
    BASE_URL = "https://api.kucoin.com"
    
    def _sign(self, method: str, endpoint: str, data: str = "") -> Dict:
        timestamp = str(int(time.time() * 1000))
        str_to_sign = timestamp + method + endpoint + data
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode(), str_to_sign.encode(), hashlib.sha256).digest()
        ).decode()
        passphrase = base64.b64encode(
            hmac.new(self.api_secret.encode(), self.passphrase.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            'KC-API-KEY': self.api_key,
            'KC-API-SIGN': signature,
            'KC-API-TIMESTAMP': timestamp,
            'KC-API-PASSPHRASE': passphrase,
            'KC-API-KEY-VERSION': '2'
        }
    
    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "API Keys nicht konfiguriert"
        try:
            endpoint = '/api/v1/accounts'
            headers = self._sign('GET', endpoint)
            response = self.session.get(f"{self.BASE_URL}{endpoint}", headers=headers, timeout=10)
            data = response.json()
            if data.get('code') == '200000':
                return True, "Verbunden"
            return False, data.get('msg', 'Unbekannter Fehler')
        except Exception as e:
            return False, str(e)
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            endpoint = f'/api/v1/deposit-addresses?currency={coin.upper()}'
            headers = self._sign('GET', endpoint)
            response = self.session.get(f"{self.BASE_URL}{endpoint}", headers=headers, timeout=10)
            data = response.json()
            
            if data.get('code') == '200000' and data.get('data'):
                addr_data = data['data']
                return WalletAddress(
                    coin=coin.upper(),
                    network=addr_data.get('chain', ''),
                    address=addr_data.get('address', ''),
                    memo=addr_data.get('memo'),
                    exchange='KuCoin',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"KuCoin {coin}: {e}")
        return None


class BybitAPI(ExchangeAPI):
    """Bybit API"""
    
    NAME = "Bybit"
    BASE_URL = "https://api.bybit.com"
    
    def _sign(self, params: Dict) -> tuple[str, Dict]:
        timestamp = str(int(time.time() * 1000))
        params_str = urlencode(sorted(params.items()))
        sign_str = timestamp + self.api_key + '5000' + params_str
        signature = hmac.new(self.api_secret.encode(), sign_str.encode(), hashlib.sha256).hexdigest()
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': '5000'
        }
        return params_str, headers
    
    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "API Keys nicht konfiguriert"
        try:
            params = {}
            params_str, headers = self._sign(params)
            response = self.session.get(
                f"{self.BASE_URL}/v5/account/wallet-balance?accountType=UNIFIED",
                headers=headers, timeout=10
            )
            data = response.json()
            if data.get('retCode') == 0:
                return True, "Verbunden"
            return False, data.get('retMsg', 'Fehler')
        except Exception as e:
            return False, str(e)
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            params = {'coin': coin.upper()}
            if network:
                params['chainType'] = network
            params_str, headers = self._sign(params)
            
            response = self.session.get(
                f"{self.BASE_URL}/v5/asset/deposit/query-address?{params_str}",
                headers=headers, timeout=10
            )
            data = response.json()
            
            if data.get('retCode') == 0 and data.get('result', {}).get('chains'):
                chain = data['result']['chains'][0]
                return WalletAddress(
                    coin=coin.upper(),
                    network=chain.get('chain', ''),
                    address=chain.get('addressDeposit', ''),
                    memo=chain.get('tagDeposit'),
                    exchange='Bybit',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"Bybit {coin}: {e}")
        return None


class OKXAPI(ExchangeAPI):
    """OKX API"""
    
    NAME = "OKX"
    BASE_URL = "https://www.okx.com"
    
    def _sign(self, method: str, path: str, body: str = "") -> Dict:
        timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
        prehash = timestamp + method + path + body
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def test_connection(self) -> tuple[bool, str]:
        if not self.is_configured():
            return False, "API Keys nicht konfiguriert"
        try:
            path = '/api/v5/account/balance'
            headers = self._sign('GET', path)
            response = self.session.get(f"{self.BASE_URL}{path}", headers=headers, timeout=10)
            data = response.json()
            if data.get('code') == '0':
                return True, "Verbunden"
            return False, data.get('msg', 'Fehler')
        except Exception as e:
            return False, str(e)
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            path = f'/api/v5/asset/deposit-address?ccy={coin.upper()}'
            headers = self._sign('GET', path)
            response = self.session.get(f"{self.BASE_URL}{path}", headers=headers, timeout=10)
            data = response.json()
            
            if data.get('code') == '0' and data.get('data'):
                addr_data = data['data'][0]
                return WalletAddress(
                    coin=coin.upper(),
                    network=addr_data.get('chain', ''),
                    address=addr_data.get('addr', ''),
                    memo=addr_data.get('tag'),
                    exchange='OKX',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"OKX {coin}: {e}")
        return None


class GateIOAPI(ExchangeAPI):
    """Gate.io API"""
    
    NAME = "Gate.io"
    BASE_URL = "https://api.gateio.ws"
    
    def _sign(self, method: str, path: str, query: str = "", body: str = "") -> Dict:
        timestamp = str(int(time.time()))
        hashed_body = hashlib.sha512(body.encode()).hexdigest()
        sign_str = f"{method}\n{path}\n{query}\n{hashed_body}\n{timestamp}"
        signature = hmac.new(self.api_secret.encode(), sign_str.encode(), hashlib.sha512).hexdigest()
        return {
            'KEY': self.api_key,
            'SIGN': signature,
            'Timestamp': timestamp,
            'Content-Type': 'application/json'
        }
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            path = f'/api/v4/wallet/deposit_address'
            query = f'currency={coin.upper()}'
            headers = self._sign('GET', path, query)
            response = self.session.get(f"{self.BASE_URL}{path}?{query}", headers=headers, timeout=10)
            data = response.json()
            
            # Gate.io gibt eine Liste zurück!
            if isinstance(data, list) and len(data) > 0:
                addr_info = data[0]  # Erste Adresse nehmen
                return WalletAddress(
                    coin=coin.upper(),
                    network=addr_info.get('chain', ''),
                    address=addr_info.get('address', ''),
                    memo=addr_info.get('payment_id') or addr_info.get('memo'),
                    exchange='Gate.io',
                    last_updated=datetime.now().isoformat()
                )
            elif isinstance(data, dict) and data.get('address'):
                return WalletAddress(
                    coin=coin.upper(),
                    network=data.get('chain', ''),
                    address=data.get('address', ''),
                    memo=data.get('payment_id'),
                    exchange='Gate.io',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"Gate.io {coin}: {e}")
        return None


class MEXCAPI(ExchangeAPI):
    """MEXC API"""
    
    NAME = "MEXC"
    BASE_URL = "https://api.mexc.com"
    
    def _sign(self, params: Dict) -> Dict:
        params['timestamp'] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()
        params['signature'] = signature
        return params
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            params = {'coin': coin.upper()}
            if network:
                params['network'] = network
            params = self._sign(params)
            
            response = self.session.get(
                f"{self.BASE_URL}/api/v3/capital/deposit/address",
                params=params,
                headers={'X-MEXC-APIKEY': self.api_key},
                timeout=10
            )
            data = response.json()
            
            if data.get('address'):
                return WalletAddress(
                    coin=coin.upper(),
                    network=data.get('network', ''),
                    address=data.get('address', ''),
                    memo=data.get('tag'),
                    exchange='MEXC',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"MEXC {coin}: {e}")
        return None


class BitgetAPI(ExchangeAPI):
    """Bitget API"""
    
    NAME = "Bitget"
    BASE_URL = "https://api.bitget.com"
    
    def _sign(self, method: str, path: str, body: str = "") -> Dict:
        timestamp = str(int(time.time() * 1000))
        prehash = timestamp + method.upper() + path + body
        signature = base64.b64encode(
            hmac.new(self.api_secret.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode()
        return {
            'ACCESS-KEY': self.api_key,
            'ACCESS-SIGN': signature,
            'ACCESS-TIMESTAMP': timestamp,
            'ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        if not self.is_configured():
            return None
        try:
            path = f'/api/spot/v1/wallet/deposit-address?coin={coin.upper()}'
            if network:
                path += f'&chain={network}'
            headers = self._sign('GET', path)
            response = self.session.get(f"{self.BASE_URL}{path}", headers=headers, timeout=10)
            data = response.json()
            
            if data.get('code') == '00000' and data.get('data'):
                addr_data = data['data']
                return WalletAddress(
                    coin=coin.upper(),
                    network=addr_data.get('chain', ''),
                    address=addr_data.get('address', ''),
                    memo=addr_data.get('tag'),
                    exchange='Bitget',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"Bitget {coin}: {e}")
        return None


class CoinExExchangeAPI(ExchangeAPI):
    """
    CoinEx API - Vorinstalliert und automatisch konfiguriert!
    
    Nutzt die separate coinex_api.py für die API-Kommunikation.
    """
    
    NAME = "CoinEx"
    BASE_URL = "https://api.coinex.com/v2"
    
    def __init__(self, api_key: str = "", api_secret: str = "", passphrase: str = ""):
        super().__init__(api_key, api_secret, passphrase)
        self._coinex_api = None
        self._load_from_config()
    
    def _load_from_config(self):
        """Lädt CoinEx Credentials aus coinex_config.json"""
        try:
            from coinex_api import CoinExAPI
            self._coinex_api = CoinExAPI()
            
            if self._coinex_api.is_configured():
                self.api_key = self._coinex_api.api_key
                self.api_secret = self._coinex_api.api_secret
                logger.info("CoinEx API aus Config geladen")
        except ImportError:
            logger.debug("coinex_api.py nicht gefunden")
        except Exception as e:
            logger.debug(f"CoinEx Config Fehler: {e}")
    
    def is_configured(self) -> bool:
        """CoinEx ist vorinstalliert - prüft ob API aktiv"""
        if self._coinex_api:
            return self._coinex_api.is_configured()
        return bool(self.api_key and self.api_secret)
    
    def test_connection(self) -> Tuple[bool, str]:
        """Testet die CoinEx Verbindung"""
        if self._coinex_api:
            return self._coinex_api.test_connection()
        return False, "CoinEx API nicht initialisiert"
    
    def get_deposit_address(self, coin: str, network: str = "") -> Optional[WalletAddress]:
        """Holt Deposit-Adresse von CoinEx"""
        if not self._coinex_api or not self._coinex_api.is_configured():
            return None
        
        try:
            result = self._coinex_api.get_deposit_address(coin, network or None)
            
            if result and result.get('is_valid'):
                return WalletAddress(
                    coin=coin.upper(),
                    network=result.get('chain', coin.upper()),
                    address=result.get('address', ''),
                    memo=result.get('memo'),
                    exchange='CoinEx',
                    last_updated=datetime.now().isoformat()
                )
        except Exception as e:
            logger.debug(f"CoinEx {coin}: {e}")
        
        return None
    
    def get_all_deposit_addresses(self, coins: List[str] = None) -> List[WalletAddress]:
        """Holt ALLE Deposit-Adressen von CoinEx"""
        if not self._coinex_api or not self._coinex_api.is_configured():
            return []
        
        wallets = []
        
        try:
            # Alle Mining-Wallets von CoinEx holen
            coinex_wallets = self._coinex_api.get_all_mining_wallets()
            
            for coin, data in coinex_wallets.items():
                if coins and coin not in coins:
                    continue
                    
                wallets.append(WalletAddress(
                    coin=coin,
                    network=data.get('chain', coin),
                    address=data.get('address', ''),
                    memo=data.get('memo'),
                    exchange='CoinEx',
                    last_updated=datetime.now().isoformat()
                ))
            
            logger.info(f"CoinEx: {len(wallets)} Wallet-Adressen geladen")
            
        except Exception as e:
            logger.error(f"CoinEx get_all_deposit_addresses Fehler: {e}")
        
        return wallets


# Factory für Exchange APIs
EXCHANGE_CLASSES = {
    'coinex': CoinExExchangeAPI,  # NEU - Vorinstalliert!
    'binance': BinanceAPI,
    'kraken': KrakenAPI,
    'kucoin': KuCoinAPI,
    'bybit': BybitAPI,
    'okx': OKXAPI,
    'gateio': GateIOAPI,
    'mexc': MEXCAPI,
    'bitget': BitgetAPI,
}


class ExchangeManager:
    """Verwaltet alle Börsen-APIs"""
    
    def __init__(self, config_path: str = "."):
        self.config_path = Path(config_path) / CONFIG_FILE
        self.exchanges: Dict[str, ExchangeAPI] = {}
        self.wallets: Dict[str, WalletAddress] = {}
        self._load_config()
    
    def _load_config(self):
        """Lädt Börsen-Konfiguration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Alle konfigurierten Börsen laden
                for exchange_id, exchange_cls in EXCHANGE_CLASSES.items():
                    if exchange_id in config:
                        exc_config = config[exchange_id]
                        self.exchanges[exchange_id] = exchange_cls(
                            api_key=exc_config.get('api_key', ''),
                            api_secret=exc_config.get('api_secret', ''),
                            passphrase=exc_config.get('passphrase', '')
                        )
                
                # Gespeicherte Wallets laden
                for addr in config.get('wallets', []):
                    try:
                        wallet = WalletAddress(**addr)
                        self.wallets[wallet.coin] = wallet
                    except:
                        pass
                
                logger.info(f"Exchange Config: {len(self.exchanges)} Börsen, {len(self.wallets)} Wallets")
                
            except Exception as e:
                logger.error(f"Config Ladefehler: {e}")
    
    def save_config(self):
        """Speichert Konfiguration"""
        try:
            # Bestehende Config laden oder neu erstellen
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Wallets aktualisieren - kompatibel mit WalletInfo und WalletAddress
            wallet_list = []
            for w in self.wallets.values():
                wallet_dict = {
                    'coin': w.coin,
                    'address': w.address,
                    'memo': getattr(w, 'memo', ''),
                }
                # Netzwerk - chain oder network
                wallet_dict['network'] = getattr(w, 'network', '') or getattr(w, 'chain', '')
                # Quelle - exchange oder source
                wallet_dict['exchange'] = getattr(w, 'exchange', '') or getattr(w, 'source', '')
                # Zeitstempel
                wallet_dict['last_updated'] = getattr(w, 'last_updated', '') or getattr(w, 'last_sync', '')
                wallet_list.append(wallet_dict)
            
            config['wallets'] = wallet_list
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                
            logger.info(f"Config gespeichert: {len(self.wallets)} Wallets")
            
        except Exception as e:
            logger.error(f"Config Speicherfehler: {e}")
    
    def _save_wallets(self):
        """Alias für save_config - speichert Wallets"""
        self.save_config()
    
    def add_exchange(self, exchange_id: str, api_key: str, api_secret: str, passphrase: str = "") -> tuple[bool, str]:
        """Fügt eine Börse hinzu und testet die Verbindung"""
        exchange_id = exchange_id.lower()
        
        if exchange_id not in EXCHANGE_CLASSES:
            return False, f"Unbekannte Börse: {exchange_id}"
        
        # API erstellen
        exchange = EXCHANGE_CLASSES[exchange_id](api_key, api_secret, passphrase)
        
        # Verbindung testen
        success, message = exchange.test_connection()
        
        if success:
            self.exchanges[exchange_id] = exchange
            
            # In Config speichern
            try:
                config = {}
                if self.config_path.exists():
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                
                config[exchange_id] = {
                    'api_key': api_key,
                    'api_secret': api_secret,
                    'passphrase': passphrase
                }
                
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
                    
            except Exception as e:
                logger.error(f"Config Speicherfehler: {e}")
            
            logger.info(f"Börse hinzugefügt: {exchange_id}")
            return True, f"{exchange_id.upper()} verbunden!"
        
        return False, f"Verbindung fehlgeschlagen: {message}"
    
    def remove_exchange(self, exchange_id: str):
        """Entfernt eine Börse"""
        exchange_id = exchange_id.lower()
        if exchange_id in self.exchanges:
            del self.exchanges[exchange_id]
            
            # Aus Config entfernen
            try:
                if self.config_path.exists():
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    if exchange_id in config:
                        del config[exchange_id]
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2)
            except:
                pass
    
    def get_configured_exchanges(self) -> List[str]:
        """Gibt Liste der konfigurierten Börsen zurück"""
        return [exc_id for exc_id, exc in self.exchanges.items() if exc.is_configured()]
    
    def get_wallet_address(self, coin: str, preferred_exchange: str = "") -> Optional[WalletAddress]:
        """Holt Wallet-Adresse für einen Coin"""
        coin = coin.upper()
        
        # Aus Cache
        if coin in self.wallets:
            return self.wallets[coin]
        
        # NEU: Aus wallets.json laden (wichtig für Gate.io/CoinEx Wallets!)
        try:
            import json
            from pathlib import Path
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallets_data = data.get("wallets", {})
                    wallet_sources = data.get("wallet_sources", {})
                    
                    if coin in wallets_data:
                        # Wallet aus wallets.json erstellen
                        source = wallet_sources.get(coin, "Manual")
                        wallet_obj = WalletAddress(
                            coin=coin,
                            network=coin,
                            address=wallets_data[coin],
                            memo="",
                            exchange=source,
                            last_updated=datetime.now().isoformat()
                        )
                        self.wallets[coin] = wallet_obj
                        logger.info(f"Wallet für {coin} aus wallets.json geladen ({source})")
                        return wallet_obj
        except Exception as e:
            logger.debug(f"wallets.json Fallback: {e}")
        
        # Von Börsen holen (nur wenn nicht in wallets.json)
        exchanges_to_try = []
        if preferred_exchange and preferred_exchange.lower() in self.exchanges:
            exchanges_to_try.append(preferred_exchange.lower())
        exchanges_to_try.extend([e for e in self.exchanges.keys() if e not in exchanges_to_try])
        
        for exchange_name in exchanges_to_try:
            exchange = self.exchanges[exchange_name]
            if not exchange.is_configured():
                continue
            addr = exchange.get_deposit_address(coin)
            if addr and addr.address:
                self.wallets[coin] = addr
                self.save_config()
                return addr
        
        return None
    
    def fetch_all_wallets(self, exchange_id: str = "") -> int:
        """Holt alle Wallets (von einer oder allen Börsen)"""
        count = 0
        
        exchanges_to_use = [exchange_id] if exchange_id else self.exchanges.keys()
        
        for exc_id in exchanges_to_use:
            if exc_id not in self.exchanges:
                continue
            exchange = self.exchanges[exc_id]
            if not exchange.is_configured():
                continue
            
            try:
                addresses = exchange.get_all_addresses()
                for addr in addresses:
                    if addr.coin not in self.wallets:
                        self.wallets[addr.coin] = addr
                        count += 1
            except Exception as e:
                logger.error(f"Fehler bei {exc_id}: {e}")
        
        if count > 0:
            self.save_config()
        
        return count
    
    def list_wallets(self) -> List[WalletAddress]:
        """Gibt Liste aller Wallets zurück"""
        return list(self.wallets.values())
    
    def add_manual_wallet(self, coin: str, address: str, network: str = "", memo: str = ""):
        """Fügt manuell eine Wallet-Adresse hinzu"""
        self.wallets[coin.upper()] = WalletAddress(
            coin=coin.upper(),
            network=network or coin.upper(),
            address=address,
            memo=memo if memo else None,
            exchange="Manual",
            last_updated=datetime.now().isoformat()
        )
        self.save_config()


def get_supported_exchanges() -> List[Dict]:
    """Gibt Liste aller unterstützten Börsen zurück"""
    return SUPPORTED_EXCHANGES


def get_mining_coins() -> List[str]:
    """Gibt Liste der Mining-Coins zurück"""
    return MINING_COINS
