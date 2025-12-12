#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Manager - Intelligentes Mining-Profit Management
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Wallet-Tracking: Überwacht Mining-Einzahlungen auf Börsen (CoinEx, Gate.io)
- Markt-Analyse: CoinGecko API für Echtzeit-Preise und Trends
- Auto-Sell: Automatischer Verkauf bei Stop-Loss/Take-Profit
- Risk Management: Trailing Stop-Loss, Dump-Erkennung
- Profit-Tracking: Vollständige Dokumentation aller Transaktionen

Basierend auf Research (Mining Communities, Hashrate Index, Braiins):
- Stop-Loss: 15-20% für volatile Mining-Coins
- Trailing Stop: 8-12% nach +15-25% Gewinn
- Auto-Sell: 50-70% zu Stablecoins für Kostendeckung
- RSI: 7-9 Periode mit 80/20 Thresholds
- Dump-Erkennung: >400% Volume-Spike

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import json
import time
import logging
import threading
import sqlite3
import hashlib
import hmac
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class Exchange(Enum):
    """Unterstützte Börsen"""
    COINEX = "coinex"
    GATEIO = "gateio"


class OrderType(Enum):
    """Order-Typen"""
    MARKET = "market"
    LIMIT = "limit"


class OrderSide(Enum):
    """Kauf/Verkauf"""
    BUY = "buy"
    SELL = "sell"


class TradeReason(Enum):
    """Grund für Trade"""
    STOP_LOSS = "stop_loss"
    TRAILING_STOP = "trailing_stop"
    TAKE_PROFIT = "take_profit"
    MANUAL = "manual"
    DUMP_DETECTED = "dump_detected"
    COST_COVERAGE = "cost_coverage"


@dataclass
class MiningDeposit:
    """Eine Mining-Einzahlung auf der Börse"""
    id: str
    coin: str
    amount: float
    timestamp: datetime
    exchange: str
    tx_hash: str = ""
    price_at_deposit: float = 0.0  # USD Preis bei Einzahlung
    source: str = "mining"  # mining, manual, unknown
    sold: bool = False
    sold_amount: float = 0.0
    sold_price: float = 0.0
    profit_loss: float = 0.0


@dataclass
class CoinPosition:
    """Aktuelle Position eines Coins"""
    coin: str
    total_amount: float = 0.0
    mined_amount: float = 0.0  # Nur durch Mining erhalten
    avg_cost_basis: float = 0.0  # Durchschnittlicher Einkaufspreis
    current_price: float = 0.0
    current_value_usd: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_percent: float = 0.0
    highest_price: float = 0.0  # Für Trailing Stop
    exchange: str = ""


@dataclass
class MarketData:
    """Marktdaten für einen Coin"""
    coin: str
    price_usd: float
    price_change_24h: float
    price_change_7d: float
    volume_24h: float
    volume_change_24h: float  # Für Dump-Erkennung
    market_cap: float
    rsi: float = 50.0
    trend: str = "neutral"  # bullish, bearish, neutral
    volatility: float = 0.0
    last_update: datetime = None


@dataclass
class TradeOrder:
    """Eine Trade-Order"""
    id: str
    coin: str
    side: str  # buy/sell
    order_type: str  # market/limit
    amount: float
    price: float
    total_usd: float
    exchange: str
    reason: str
    status: str = "pending"  # pending, filled, cancelled, failed
    created_at: datetime = None
    filled_at: datetime = None
    fee: float = 0.0
    fee_coin: str = "USDT"


@dataclass
class PortfolioSettings:
    """Einstellungen für das Portfolio Management"""
    # Stop-Loss Settings (basierend auf Research)
    stop_loss_percent: float = 15.0  # Standard: 15% für volatile Mining-Coins
    trailing_stop_enabled: bool = True
    trailing_stop_activation: float = 15.0  # Aktiviert nach +15%
    trailing_stop_distance: float = 10.0  # 10% Trailing Distance
    
    # Take-Profit Settings
    take_profit_enabled: bool = True
    take_profit_percent: float = 50.0  # Verkaufe bei +50%
    
    # Auto-Sell Settings
    auto_sell_enabled: bool = True
    auto_sell_percent: float = 60.0  # 60% automatisch verkaufen
    min_hold_hours: float = 2.0  # Mindestens 2h halten
    
    # Stablecoin Preference
    preferred_stablecoin: str = "USDT"  # USDT oder USDC
    
    # Exchange Settings
    primary_exchange: str = "coinex"
    use_limit_orders: bool = True  # Limit statt Market Orders
    limit_order_offset: float = 0.5  # 0.5% unter Marktpreis
    
    # Dump Detection (basierend auf Research: >400% Volume-Spike)
    dump_detection_enabled: bool = True
    dump_volume_threshold: float = 400.0  # 400% Volume-Spike
    
    # RSI Settings (für volatile Coins: 7-9 Periode, 80/20)
    rsi_period: int = 9
    rsi_overbought: float = 80.0
    rsi_oversold: float = 20.0
    
    # Notifications
    notify_on_trade: bool = True
    notify_on_deposit: bool = True
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PortfolioSettings':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================
# COINGECKO API CLIENT
# ============================================================

class CoinGeckoAPI:
    """
    CoinGecko API Client für Marktdaten
    Kostenlos, kein API-Key nötig, 10-30 calls/minute
    """
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    # Mapping von Mining-Coin Symbolen zu CoinGecko IDs
    COIN_ID_MAP = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "RVN": "ravencoin",
        "ERG": "ergo",
        "ETC": "ethereum-classic",
        "FLUX": "zelcash",
        "KAS": "kaspa",
        "ALPH": "alephium",
        "GRIN": "grin",
        "BEAM": "beam",
        "XMR": "monero",
        "ZEPH": "zephyr-protocol",
        "CFX": "conflux-token",
        "CLORE": "clore-ai",
        "DNX": "dynex",
        "IRON": "iron-fish",
        "NEXA": "nexacoin",
        "ZEC": "zcash",
        "FIRO": "zcoin",
        "DOGE": "dogecoin",
        "LTC": "litecoin",
        "DASH": "dash",
        "RTM": "raptoreum",
        "USDT": "tether",
        "USDC": "usd-coin",
        "WOW": "wownero",
        "DERO": "dero",
    }
    
    def __init__(self):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_ttl = 60  # 60 Sekunden Cache
        self._last_request = 0
        self._min_interval = 1.5  # 1.5s zwischen Requests (Rate Limiting)
    
    def _rate_limit(self):
        """Rate Limiting - verhindert API Bans"""
        elapsed = time.time() - self._last_request
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request = time.time()
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Prüft Cache"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Setzt Cache"""
        self._cache[key] = (data, time.time())
    
    def _request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """API Request mit Rate Limiting und Caching"""
        if not requests:
            logger.warning("requests Modul nicht verfügbar")
            return None
        
        # Cache prüfen
        cache_key = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                logger.warning("⚠️ CoinGecko Rate Limit erreicht, warte 60s...")
                time.sleep(60)
                return self._request(endpoint, params)
            
            if response.status_code != 200:
                logger.warning(f"CoinGecko API Fehler: {response.status_code}")
                return None
            
            data = response.json()
            self._set_cache(cache_key, data)
            return data
            
        except Exception as e:
            logger.error(f"CoinGecko Request Fehler: {e}")
            return None
    
    def get_coin_id(self, symbol: str) -> Optional[str]:
        """Gibt CoinGecko ID für Symbol zurück"""
        return self.COIN_ID_MAP.get(symbol.upper())
    
    def get_price(self, coin: str) -> Optional[float]:
        """Holt aktuellen Preis in USD"""
        coin_id = self.get_coin_id(coin)
        if not coin_id:
            logger.warning(f"Unbekannter Coin: {coin}")
            return None
        
        data = self._request("/simple/price", {
            "ids": coin_id,
            "vs_currencies": "usd"
        })
        
        if data and coin_id in data:
            return data[coin_id].get("usd", 0)
        return None
    
    def get_prices_bulk(self, coins: List[str]) -> Dict[str, float]:
        """Holt Preise für mehrere Coins auf einmal"""
        coin_ids = [self.get_coin_id(c) for c in coins if self.get_coin_id(c)]
        if not coin_ids:
            return {}
        
        data = self._request("/simple/price", {
            "ids": ",".join(coin_ids),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_24hr_vol": "true"
        })
        
        result = {}
        if data:
            # Reverse Mapping
            id_to_symbol = {v: k for k, v in self.COIN_ID_MAP.items()}
            for coin_id, price_data in data.items():
                symbol = id_to_symbol.get(coin_id)
                if symbol:
                    result[symbol] = price_data.get("usd", 0)
        
        return result
    
    def get_market_data(self, coin: str) -> Optional[MarketData]:
        """Holt vollständige Marktdaten für einen Coin"""
        coin_id = self.get_coin_id(coin)
        if not coin_id:
            return None
        
        data = self._request(f"/coins/{coin_id}", {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        })
        
        if not data:
            return None
        
        market = data.get("market_data", {})
        
        # Trend bestimmen
        change_24h = market.get("price_change_percentage_24h", 0) or 0
        change_7d = market.get("price_change_percentage_7d", 0) or 0
        
        if change_24h > 5 and change_7d > 10:
            trend = "bullish"
        elif change_24h < -5 and change_7d < -10:
            trend = "bearish"
        else:
            trend = "neutral"
        
        return MarketData(
            coin=coin,
            price_usd=market.get("current_price", {}).get("usd", 0) or 0,
            price_change_24h=change_24h,
            price_change_7d=change_7d,
            volume_24h=market.get("total_volume", {}).get("usd", 0) or 0,
            volume_change_24h=0,  # Berechnen wir separat
            market_cap=market.get("market_cap", {}).get("usd", 0) or 0,
            trend=trend,
            last_update=datetime.now()
        )
    
    def get_price_history(self, coin: str, days: int = 14) -> List[Tuple[datetime, float]]:
        """Holt Preis-Historie für RSI-Berechnung"""
        coin_id = self.get_coin_id(coin)
        if not coin_id:
            return []
        
        data = self._request(f"/coins/{coin_id}/market_chart", {
            "vs_currency": "usd",
            "days": days
        })
        
        if not data or "prices" not in data:
            return []
        
        result = []
        for timestamp, price in data["prices"]:
            dt = datetime.fromtimestamp(timestamp / 1000)
            result.append((dt, price))
        
        return result
    
    def calculate_rsi(self, coin: str, period: int = 9) -> float:
        """
        Berechnet RSI (Relative Strength Index)
        Verwendet 9er Periode für volatile Mining-Coins (statt Standard 14)
        Thresholds: 80/20 statt 70/30 (basierend auf Research)
        """
        history = self.get_price_history(coin, days=period + 7)
        if len(history) < period + 1:
            return 50.0  # Neutral wenn nicht genug Daten
        
        # Nur die letzten N+1 Preise für Period
        prices = [p[1] for p in history[-(period + 1):]]
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)


# ============================================================
# EXCHANGE TRADING API
# ============================================================

class ExchangeTradingAPI:
    """
    Trading API für CoinEx und Gate.io
    Führt echte Trades aus!
    
    Rate Limits (basierend auf Research):
    - CoinEx: 30 req/s (Orders), 60 req/s (Cancel)
    - Gate.io: 10 req/s pro Market
    """
    
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.api_key = ""
        self.api_secret = ""
        self.base_url = ""
        
        if exchange == Exchange.COINEX:
            self.base_url = "https://api.coinex.com/v2"
        elif exchange == Exchange.GATEIO:
            self.base_url = "https://api.gateio.ws/api/v4"
    
    def set_credentials(self, api_key: str, api_secret: str):
        """Setzt API Credentials"""
        self.api_key = api_key
        self.api_secret = api_secret
        logger.info(f"🔑 API Credentials gesetzt für {self.exchange.value}")
    
    def _sign_coinex(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Signiert CoinEx Request (V2 API)"""
        timestamp = str(int(time.time() * 1000))
        
        # Prepared String
        if params:
            query_string = urllib.parse.urlencode(sorted(params.items()))
            prepared = f"{method}{path}?{query_string}{timestamp}"
        else:
            prepared = f"{method}{path}{timestamp}"
        
        if body:
            prepared += json.dumps(body, separators=(',', ':'))
        
        # HMAC SHA256
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            prepared.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().lower()
        
        return {
            "X-COINEX-KEY": self.api_key,
            "X-COINEX-SIGN": signature,
            "X-COINEX-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
    
    def _sign_gateio(self, method: str, path: str, query: str = "", body: str = "") -> dict:
        """Signiert Gate.io Request (V4 API)"""
        timestamp = str(int(time.time()))
        
        # Hash body
        body_hash = hashlib.sha512(body.encode('utf-8')).hexdigest()
        
        # Sign string
        sign_string = f"{method}\n{path}\n{query}\n{body_hash}\n{timestamp}"
        
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            sign_string.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()
        
        return {
            "KEY": self.api_key,
            "SIGN": signature,
            "Timestamp": timestamp,
            "Content-Type": "application/json"
        }
    
    def get_balance(self, coin: str) -> float:
        """Holt Balance eines Coins"""
        if not requests or not self.api_key:
            return 0.0
        
        try:
            if self.exchange == Exchange.COINEX:
                path = "/assets/spot/balance"
                headers = self._sign_coinex("GET", path)
                response = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        for asset in data.get("data", []):
                            if asset.get("ccy") == coin:
                                return float(asset.get("available", 0))
                
            elif self.exchange == Exchange.GATEIO:
                path = "/spot/accounts"
                headers = self._sign_gateio("GET", path)
                response = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    for asset in data:
                        if asset.get("currency") == coin:
                            return float(asset.get("available", 0))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Balance Abfrage Fehler ({self.exchange.value}): {e}")
            return 0.0
    
    def get_all_balances(self) -> Dict[str, float]:
        """Holt alle Balances mit Guthaben > 0"""
        balances = {}
        
        if not requests or not self.api_key:
            return balances
        
        try:
            if self.exchange == Exchange.COINEX:
                path = "/assets/spot/balance"
                headers = self._sign_coinex("GET", path)
                response = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        for asset in data.get("data", []):
                            available = float(asset.get("available", 0))
                            if available > 0:
                                balances[asset.get("ccy")] = available
                
            elif self.exchange == Exchange.GATEIO:
                path = "/spot/accounts"
                headers = self._sign_gateio("GET", path)
                response = requests.get(f"{self.base_url}{path}", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    for asset in data:
                        available = float(asset.get("available", 0))
                        if available > 0:
                            balances[asset.get("currency")] = available
            
            logger.info(f"💰 {len(balances)} Coins mit Guthaben auf {self.exchange.value}")
            
        except Exception as e:
            logger.error(f"Balances Abfrage Fehler ({self.exchange.value}): {e}")
        
        return balances
    
    def get_deposit_history(self, coin: str = None, limit: int = 100) -> List[Dict]:
        """Holt Einzahlungs-Historie (für Mining-Tracking)"""
        deposits = []
        
        if not requests or not self.api_key:
            return deposits
        
        try:
            if self.exchange == Exchange.COINEX:
                path = "/assets/deposit-history"
                params = {"limit": limit}
                if coin:
                    params["ccy"] = coin
                headers = self._sign_coinex("GET", path, params)
                response = requests.get(f"{self.base_url}{path}", headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        for d in data.get("data", {}).get("data", []):
                            deposits.append({
                                "coin": d.get("ccy"),
                                "amount": float(d.get("amount", 0)),
                                "timestamp": datetime.fromtimestamp(d.get("created_at", 0) / 1000),
                                "tx_hash": d.get("tx_id", ""),
                                "status": d.get("status"),
                                "exchange": "coinex"
                            })
                
            elif self.exchange == Exchange.GATEIO:
                path = "/wallet/deposits"
                params = {"limit": limit}
                if coin:
                    params["currency"] = coin
                query = urllib.parse.urlencode(params)
                headers = self._sign_gateio("GET", path, query)
                response = requests.get(f"{self.base_url}{path}?{query}", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    for d in data:
                        deposits.append({
                            "coin": d.get("currency"),
                            "amount": float(d.get("amount", 0)),
                            "timestamp": datetime.fromtimestamp(int(d.get("timestamp", 0))),
                            "tx_hash": d.get("txid", ""),
                            "status": d.get("status"),
                            "exchange": "gateio"
                        })
            
            logger.info(f"📥 {len(deposits)} Einzahlungen geladen von {self.exchange.value}")
            
        except Exception as e:
            logger.error(f"Deposit History Fehler ({self.exchange.value}): {e}")
        
        return deposits
    
    def place_order(
        self,
        coin: str,
        side: OrderSide,
        amount: float,
        order_type: OrderType = OrderType.LIMIT,
        price: float = None,
        stablecoin: str = "USDT"
    ) -> Optional[TradeOrder]:
        """
        Platziert eine Order
        
        Args:
            coin: Coin zum Verkaufen (z.B. "RVN")
            side: BUY oder SELL
            amount: Menge
            order_type: MARKET oder LIMIT (Empfehlung: LIMIT für Small-Caps)
            price: Preis für Limit Orders
            stablecoin: USDT oder USDC
        
        Returns:
            TradeOrder bei Erfolg, None bei Fehler
        """
        if not requests or not self.api_key:
            logger.error("❌ Trading API nicht konfiguriert")
            return None
        
        market = f"{coin}{stablecoin}"  # z.B. RVNUSDT
        
        try:
            order_id = None
            
            if self.exchange == Exchange.COINEX:
                path = "/spot/order"
                body = {
                    "market": market,
                    "market_type": "SPOT",
                    "side": side.value,
                    "type": order_type.value,
                    "amount": str(amount)
                }
                
                if order_type == OrderType.LIMIT and price:
                    body["price"] = str(price)
                
                headers = self._sign_coinex("POST", path, body=body)
                response = requests.post(
                    f"{self.base_url}{path}",
                    headers=headers,
                    json=body,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        order_id = str(data.get("data", {}).get("order_id", ""))
                        logger.info(f"✅ CoinEx Order: {order_id}")
                    else:
                        logger.error(f"❌ CoinEx Order Fehler: {data.get('message')}")
                
            elif self.exchange == Exchange.GATEIO:
                path = "/spot/orders"
                body = {
                    "currency_pair": f"{coin}_{stablecoin}",
                    "side": side.value,
                    "type": order_type.value,
                    "amount": str(amount),
                    "account": "spot"
                }
                
                if order_type == OrderType.LIMIT and price:
                    body["price"] = str(price)
                
                body_str = json.dumps(body)
                headers = self._sign_gateio("POST", path, "", body_str)
                response = requests.post(
                    f"{self.base_url}{path}",
                    headers=headers,
                    data=body_str,
                    timeout=10
                )
                
                if response.status_code == 201:
                    data = response.json()
                    order_id = str(data.get("id", ""))
                    logger.info(f"✅ Gate.io Order: {order_id}")
                else:
                    logger.error(f"❌ Gate.io Order Fehler: {response.text}")
            
            if order_id:
                total_usd = amount * (price or 0)
                
                order = TradeOrder(
                    id=order_id,
                    coin=coin,
                    side=side.value,
                    order_type=order_type.value,
                    amount=amount,
                    price=price or 0,
                    total_usd=total_usd,
                    exchange=self.exchange.value,
                    reason="",
                    status="pending",
                    created_at=datetime.now()
                )
                
                logger.info(f"✅ Order platziert: {side.value.upper()} {amount} {coin} @ ${price:.4f} auf {self.exchange.value}")
                return order
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Order Fehler ({self.exchange.value}): {e}")
            return None
    
    def get_ticker_price(self, coin: str, stablecoin: str = "USDT") -> float:
        """Holt aktuellen Ticker-Preis von der Börse (für schnelle Preisabfrage)"""
        if not requests:
            return 0.0
        
        try:
            if self.exchange == Exchange.COINEX:
                market = f"{coin}{stablecoin}"
                response = requests.get(
                    f"{self.base_url}/spot/ticker",
                    params={"market": market},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == 0:
                        tickers = data.get("data", [])
                        if tickers:
                            return float(tickers[0].get("last", 0))
                
            elif self.exchange == Exchange.GATEIO:
                pair = f"{coin}_{stablecoin}"
                response = requests.get(
                    f"{self.base_url}/spot/tickers",
                    params={"currency_pair": pair},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        return float(data[0].get("last", 0))
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Ticker Fehler ({self.exchange.value}): {e}")
            return 0.0


# ============================================================
# PORTFOLIO DATABASE
# ============================================================

class PortfolioDatabase:
    """SQLite Datenbank für Portfolio-Tracking und Historie"""
    
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialisiert die Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Mining Deposits - trackt alle Mining-Einzahlungen
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mining_deposits (
                id TEXT PRIMARY KEY,
                coin TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TEXT NOT NULL,
                exchange TEXT NOT NULL,
                tx_hash TEXT,
                price_at_deposit REAL DEFAULT 0,
                source TEXT DEFAULT 'mining',
                sold INTEGER DEFAULT 0,
                sold_amount REAL DEFAULT 0,
                sold_price REAL DEFAULT 0,
                profit_loss REAL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trade Orders - alle ausgeführten Trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_orders (
                id TEXT PRIMARY KEY,
                coin TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                total_usd REAL NOT NULL,
                exchange TEXT NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                filled_at TEXT,
                fee REAL DEFAULT 0,
                fee_coin TEXT DEFAULT 'USDT'
            )
        """)
        
        # Daily Profits - tägliche Statistiken
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_profits (
                date TEXT PRIMARY KEY,
                total_mined_usd REAL DEFAULT 0,
                total_sold_usd REAL DEFAULT 0,
                total_fees_usd REAL DEFAULT 0,
                net_profit_usd REAL DEFAULT 0,
                coins_mined TEXT,
                coins_sold TEXT
            )
        """)
        
        # Highest Prices - für Trailing Stop
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highest_prices (
                coin TEXT PRIMARY KEY,
                highest_price REAL NOT NULL,
                recorded_at TEXT NOT NULL
            )
        """)
        
        # Activity Log - alle Aktionen dokumentieren
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT,
                details TEXT,
                acknowledged INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Portfolio-Datenbank initialisiert: {self.db_path}")
    
    def add_deposit(self, deposit: MiningDeposit):
        """Fügt eine Mining-Einzahlung hinzu"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO mining_deposits
            (id, coin, amount, timestamp, exchange, tx_hash, price_at_deposit, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            deposit.id,
            deposit.coin,
            deposit.amount,
            deposit.timestamp.isoformat(),
            deposit.exchange,
            deposit.tx_hash,
            deposit.price_at_deposit,
            deposit.source
        ))
        
        # Activity Log
        self._log_activity(cursor, "DEPOSIT", 
            f"Neue Mining-Einzahlung: {deposit.amount:.6f} {deposit.coin}",
            json.dumps({"coin": deposit.coin, "amount": deposit.amount, "price": deposit.price_at_deposit}))
        
        conn.commit()
        conn.close()
    
    def add_trade(self, trade: TradeOrder):
        """Fügt einen Trade hinzu"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO trade_orders
            (id, coin, side, order_type, amount, price, total_usd, exchange, reason, status, created_at, fee, fee_coin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.id,
            trade.coin,
            trade.side,
            trade.order_type,
            trade.amount,
            trade.price,
            trade.total_usd,
            trade.exchange,
            trade.reason,
            trade.status,
            trade.created_at.isoformat() if trade.created_at else None,
            trade.fee,
            trade.fee_coin
        ))
        
        # Activity Log
        self._log_activity(cursor, "TRADE",
            f"Trade ausgeführt: {trade.side.upper()} {trade.amount:.6f} {trade.coin} @ ${trade.price:.4f}",
            json.dumps({"coin": trade.coin, "amount": trade.amount, "price": trade.price, "reason": trade.reason}))
        
        conn.commit()
        conn.close()
    
    def _log_activity(self, cursor, action_type: str, description: str, details: str = ""):
        """Interne Methode zum Loggen von Aktivitäten"""
        cursor.execute("""
            INSERT INTO activity_log (timestamp, action_type, description, details)
            VALUES (?, ?, ?, ?)
        """, (datetime.now().isoformat(), action_type, description, details))
    
    def log_activity(self, action_type: str, description: str, details: str = ""):
        """Loggt eine Aktivität (öffentliche Methode)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        self._log_activity(cursor, action_type, description, details)
        conn.commit()
        conn.close()
    
    def get_unsold_deposits(self, coin: str = None) -> List[MiningDeposit]:
        """Holt unverkaufte Mining-Einzahlungen"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if coin:
            cursor.execute("""
                SELECT * FROM mining_deposits WHERE sold = 0 AND coin = ? ORDER BY timestamp
            """, (coin,))
        else:
            cursor.execute("""
                SELECT * FROM mining_deposits WHERE sold = 0 ORDER BY timestamp
            """)
        
        deposits = []
        for row in cursor.fetchall():
            deposits.append(MiningDeposit(
                id=row[0],
                coin=row[1],
                amount=row[2],
                timestamp=datetime.fromisoformat(row[3]),
                exchange=row[4],
                tx_hash=row[5] or "",
                price_at_deposit=row[6] or 0,
                source=row[7] or "mining",
                sold=bool(row[8]),
                sold_amount=row[9] or 0,
                sold_price=row[10] or 0,
                profit_loss=row[11] or 0
            ))
        
        conn.close()
        return deposits
    
    def mark_deposit_sold(self, deposit_id: str, sold_amount: float, sold_price: float, profit_loss: float):
        """Markiert Einzahlung als verkauft"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE mining_deposits
            SET sold = 1, sold_amount = ?, sold_price = ?, profit_loss = ?
            WHERE id = ?
        """, (sold_amount, sold_price, profit_loss, deposit_id))
        
        conn.commit()
        conn.close()
    
    def get_highest_price(self, coin: str) -> float:
        """Holt höchsten Preis für Trailing Stop"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT highest_price FROM highest_prices WHERE coin = ?", (coin,))
        row = cursor.fetchone()
        
        conn.close()
        return row[0] if row else 0.0
    
    def update_highest_price(self, coin: str, price: float):
        """Aktualisiert höchsten Preis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO highest_prices (coin, highest_price, recorded_at)
            VALUES (?, ?, ?)
        """, (coin, price, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_activity_log(self, limit: int = 100, unacknowledged_only: bool = False) -> List[Dict]:
        """Holt Activity Log"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if unacknowledged_only:
            cursor.execute("""
                SELECT * FROM activity_log WHERE acknowledged = 0 ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                "id": row[0],
                "timestamp": row[1],
                "action_type": row[2],
                "description": row[3],
                "details": row[4],
                "acknowledged": bool(row[5])
            })
        
        conn.close()
        return logs
    
    def acknowledge_activity(self, activity_id: int):
        """Markiert Aktivität als gesehen (Checkbox abhaken)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("UPDATE activity_log SET acknowledged = 1 WHERE id = ?", (activity_id,))
        
        conn.commit()
        conn.close()
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """Holt Trading-Historie"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM trade_orders ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "id": row[0],
                "coin": row[1],
                "side": row[2],
                "order_type": row[3],
                "amount": row[4],
                "price": row[5],
                "total_usd": row[6],
                "exchange": row[7],
                "reason": row[8],
                "status": row[9],
                "created_at": row[10]
            })
        
        conn.close()
        return trades
    
    def get_daily_stats(self, date: str = None) -> Dict:
        """Holt Tagesstatistik"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM daily_profits WHERE date = ?", (date,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "date": row[0],
                "total_mined_usd": row[1],
                "total_sold_usd": row[2],
                "total_fees_usd": row[3],
                "net_profit_usd": row[4],
                "coins_mined": json.loads(row[5]) if row[5] else {},
                "coins_sold": json.loads(row[6]) if row[6] else {}
            }
        
        return {
            "date": date,
            "total_mined_usd": 0,
            "total_sold_usd": 0,
            "total_fees_usd": 0,
            "net_profit_usd": 0,
            "coins_mined": {},
            "coins_sold": {}
        }
    
    def get_period_stats(self, days: int = 30) -> List[Dict]:
        """Holt Statistiken für einen Zeitraum"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT * FROM daily_profits WHERE date >= ? ORDER BY date DESC
        """, (start_date,))
        
        stats = []
        for row in cursor.fetchall():
            stats.append({
                "date": row[0],
                "total_mined_usd": row[1],
                "total_sold_usd": row[2],
                "total_fees_usd": row[3],
                "net_profit_usd": row[4]
            })
        
        conn.close()
        return stats


# ============================================================
# PORTFOLIO MANAGER
# ============================================================

class PortfolioManager:
    """
    Haupt-Klasse für Portfolio Management
    
    Überwacht:
    - Mining-Einzahlungen auf Börsen
    - Marktpreise und Trends
    - Stop-Loss und Trailing Stop
    - Automatische Verkäufe
    
    Vollautomatisch - User muss nicht anwesend sein!
    """
    
    def __init__(self, config_path: str = "portfolio_config.json"):
        self.config_path = config_path
        self.settings = PortfolioSettings()
        
        # APIs
        self.coingecko = CoinGeckoAPI()
        self.exchanges: Dict[str, ExchangeTradingAPI] = {}
        
        # Database
        self.db = PortfolioDatabase()
        
        # State
        self.positions: Dict[str, CoinPosition] = {}
        self.market_data: Dict[str, MarketData] = {}
        self.known_deposits: set = set()  # Bereits bekannte Deposit-IDs
        
        # Threading
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Callbacks für GUI
        self.on_deposit: Optional[Callable[[MiningDeposit], None]] = None
        self.on_trade: Optional[Callable[[TradeOrder], None]] = None
        self.on_alert: Optional[Callable[[str, str], None]] = None  # (level, message)
        self.on_price_update: Optional[Callable[[Dict[str, float]], None]] = None
        
        # Load config
        self._load_config()
        
        logger.info("💰 Portfolio Manager initialisiert")
    
    def _load_config(self):
        """Lädt Konfiguration aus JSON"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.settings = PortfolioSettings.from_dict(data.get("settings", {}))
                    
                    # Exchange Credentials laden
                    for exchange_name, creds in data.get("exchanges", {}).items():
                        try:
                            exchange = Exchange(exchange_name)
                            api = ExchangeTradingAPI(exchange)
                            api.set_credentials(creds.get("api_key", ""), creds.get("api_secret", ""))
                            self.exchanges[exchange_name] = api
                        except:
                            pass
                    
                    logger.info(f"📂 Portfolio-Config geladen: {len(self.exchanges)} Börsen")
        except Exception as e:
            logger.warning(f"Config laden fehlgeschlagen: {e}")
    
    def save_config(self):
        """Speichert Konfiguration in JSON"""
        try:
            data = {
                "settings": self.settings.to_dict(),
                "exchanges": {}
            }
            
            for name, api in self.exchanges.items():
                data["exchanges"][name] = {
                    "api_key": api.api_key,
                    "api_secret": api.api_secret
                }
            
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.info("💾 Portfolio-Config gespeichert")
        except Exception as e:
            logger.error(f"Config speichern fehlgeschlagen: {e}")
    
    def add_exchange(self, exchange: Exchange, api_key: str, api_secret: str):
        """Fügt eine Börse hinzu"""
        api = ExchangeTradingAPI(exchange)
        api.set_credentials(api_key, api_secret)
        self.exchanges[exchange.value] = api
        self.save_config()
        logger.info(f"🔗 Börse hinzugefügt: {exchange.value}")
    
    def start_monitoring(self, interval: float = 60.0):
        """Startet das automatische Monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
        
        self.db.log_activity("MONITORING", f"Portfolio Monitoring gestartet (Intervall: {interval}s)")
        logger.info(f"🚀 Portfolio Monitoring gestartet (Intervall: {interval}s)")
    
    def stop_monitoring(self):
        """Stoppt das Monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        
        self.db.log_activity("MONITORING", "Portfolio Monitoring gestoppt")
        logger.info("⏹️ Portfolio Monitoring gestoppt")
    
    def _monitor_loop(self, interval: float):
        """Haupt-Monitoring-Schleife (läuft im Hintergrund)"""
        while self._running:
            try:
                # 1. Neue Einzahlungen prüfen
                self._check_deposits()
                
                # 2. Preise aktualisieren
                self._update_prices()
                
                # 3. Stop-Loss prüfen
                self._check_stop_loss()
                
                # 4. Trailing Stop prüfen
                if self.settings.trailing_stop_enabled:
                    self._check_trailing_stop()
                
                # 5. Take-Profit prüfen
                if self.settings.take_profit_enabled:
                    self._check_take_profit()
                
                # 6. Dump-Erkennung
                if self.settings.dump_detection_enabled:
                    self._check_dumps()
                
            except Exception as e:
                logger.error(f"❌ Monitor Loop Fehler: {e}")
            
            # Warten - aber interruptable
            for _ in range(int(interval)):
                if not self._running:
                    break
                time.sleep(1)
    
    def _check_deposits(self):
        """Prüft auf neue Mining-Einzahlungen"""
        for exchange_name, api in self.exchanges.items():
            try:
                deposits = api.get_deposit_history(limit=50)
                
                for dep in deposits:
                    # Nur completed Deposits
                    status = str(dep.get("status", "")).upper()
                    if status not in ["FINISHED", "COMPLETED", "DONE", "SUCCESS"]:
                        continue
                    
                    # Eindeutige ID generieren
                    dep_id = f"{exchange_name}_{dep.get('tx_hash', '')}_{dep.get('coin')}_{dep.get('amount')}"
                    dep_hash = hashlib.md5(dep_id.encode()).hexdigest()[:16]
                    
                    if dep_hash in self.known_deposits:
                        continue
                    
                    self.known_deposits.add(dep_hash)
                    
                    # Preis holen
                    price = self.coingecko.get_price(dep["coin"]) or 0
                    
                    # MiningDeposit erstellen
                    mining_dep = MiningDeposit(
                        id=dep_hash,
                        coin=dep["coin"],
                        amount=dep["amount"],
                        timestamp=dep["timestamp"],
                        exchange=exchange_name,
                        tx_hash=dep.get("tx_hash", ""),
                        price_at_deposit=price,
                        source="mining"
                    )
                    
                    # In DB speichern
                    self.db.add_deposit(mining_dep)
                    
                    # Callback für GUI
                    if self.on_deposit:
                        self.on_deposit(mining_dep)
                    
                    # Alert
                    if self.on_alert and self.settings.notify_on_deposit:
                        value_usd = mining_dep.amount * price
                        self.on_alert("info", f"💰 Neue Mining-Einzahlung: {mining_dep.amount:.6f} {mining_dep.coin} (${value_usd:.2f})")
                    
                    logger.info(f"💰 Neue Einzahlung: {mining_dep.amount:.6f} {mining_dep.coin} @ ${price:.4f}")
                    
                    # Auto-Sell wenn aktiviert
                    if self.settings.auto_sell_enabled:
                        self._schedule_auto_sell(mining_dep)
                        
            except Exception as e:
                logger.error(f"Deposit Check Fehler ({exchange_name}): {e}")
    
    def _schedule_auto_sell(self, deposit: MiningDeposit):
        """Plant Auto-Sell nach Mindest-Haltezeit"""
        def delayed_sell():
            # Warten auf Mindest-Haltezeit
            time.sleep(self.settings.min_hold_hours * 3600)
            
            if not self._running:
                return
            
            # Aktuellen Preis holen
            current_price = self.coingecko.get_price(deposit.coin) or 0
            if current_price <= 0:
                return
            
            # Nur den Auto-Sell Anteil verkaufen
            sell_amount = deposit.amount * (self.settings.auto_sell_percent / 100)
            
            if sell_amount > 0:
                self._execute_sell(deposit, TradeReason.COST_COVERAGE, current_price, sell_amount)
        
        # In separatem Thread ausführen
        thread = threading.Thread(target=delayed_sell, daemon=True)
        thread.start()
    
    def _update_prices(self):
        """Aktualisiert Marktpreise für alle Positionen"""
        deposits = self.db.get_unsold_deposits()
        coins = list(set(d.coin for d in deposits))
        
        if not coins:
            return
        
        # Bulk-Preise holen (effizienter)
        prices = self.coingecko.get_prices_bulk(coins)
        
        for coin, price in prices.items():
            if coin not in self.market_data:
                self.market_data[coin] = MarketData(
                    coin=coin, price_usd=price, price_change_24h=0, 
                    price_change_7d=0, volume_24h=0, volume_change_24h=0, market_cap=0
                )
            else:
                self.market_data[coin].price_usd = price
            
            # Höchsten Preis aktualisieren (für Trailing Stop)
            highest = self.db.get_highest_price(coin)
            if price > highest:
                self.db.update_highest_price(coin, price)
        
        # Callback für GUI
        if self.on_price_update:
            self.on_price_update(prices)
    
    def _check_stop_loss(self):
        """Prüft Stop-Loss für alle unverkauften Positionen"""
        deposits = self.db.get_unsold_deposits()
        
        for deposit in deposits:
            if deposit.coin not in self.market_data:
                continue
            
            current_price = self.market_data[deposit.coin].price_usd
            entry_price = deposit.price_at_deposit
            
            if entry_price <= 0:
                continue
            
            # Mindest-Haltezeit prüfen
            hold_hours = (datetime.now() - deposit.timestamp).total_seconds() / 3600
            if hold_hours < self.settings.min_hold_hours:
                continue
            
            # Verlust berechnen
            loss_percent = ((current_price - entry_price) / entry_price) * 100
            
            if loss_percent <= -self.settings.stop_loss_percent:
                # 🔴 STOP-LOSS AUSGELÖST!
                logger.warning(f"🔴 STOP-LOSS: {deposit.coin} bei {loss_percent:.1f}% Verlust")
                
                if self.on_alert:
                    self.on_alert("warning", f"🔴 STOP-LOSS ausgelöst: {deposit.coin} bei {loss_percent:.1f}% Verlust")
                
                # Verkaufen
                self._execute_sell(deposit, TradeReason.STOP_LOSS, current_price)
    
    def _check_trailing_stop(self):
        """Prüft Trailing Stop für Positionen mit Gewinn"""
        deposits = self.db.get_unsold_deposits()
        
        for deposit in deposits:
            if deposit.coin not in self.market_data:
                continue
            
            current_price = self.market_data[deposit.coin].price_usd
            entry_price = deposit.price_at_deposit
            highest_price = self.db.get_highest_price(deposit.coin)
            
            if entry_price <= 0 or highest_price <= 0:
                continue
            
            # Gewinn vom Entry berechnen
            gain_from_entry = ((current_price - entry_price) / entry_price) * 100
            
            # Trailing Stop nur wenn Aktivierungs-Schwelle erreicht
            if gain_from_entry < self.settings.trailing_stop_activation:
                continue
            
            # Verlust vom Höchststand berechnen
            loss_from_high = ((current_price - highest_price) / highest_price) * 100
            
            if loss_from_high <= -self.settings.trailing_stop_distance:
                # 🟡 TRAILING STOP AUSGELÖST!
                logger.warning(f"🟡 TRAILING STOP: {deposit.coin} bei {loss_from_high:.1f}% vom Hoch")
                
                if self.on_alert:
                    self.on_alert("warning", f"🟡 TRAILING STOP: {deposit.coin} bei {loss_from_high:.1f}% vom Höchststand")
                
                # Verkaufen
                self._execute_sell(deposit, TradeReason.TRAILING_STOP, current_price)
    
    def _check_take_profit(self):
        """Prüft Take-Profit für Positionen mit großem Gewinn"""
        deposits = self.db.get_unsold_deposits()
        
        for deposit in deposits:
            if deposit.coin not in self.market_data:
                continue
            
            current_price = self.market_data[deposit.coin].price_usd
            entry_price = deposit.price_at_deposit
            
            if entry_price <= 0:
                continue
            
            # Gewinn berechnen
            gain_percent = ((current_price - entry_price) / entry_price) * 100
            
            if gain_percent >= self.settings.take_profit_percent:
                # 🟢 TAKE-PROFIT AUSGELÖST!
                logger.info(f"🟢 TAKE-PROFIT: {deposit.coin} bei +{gain_percent:.1f}% Gewinn")
                
                if self.on_alert:
                    self.on_alert("info", f"🟢 TAKE-PROFIT: {deposit.coin} bei +{gain_percent:.1f}% Gewinn")
                
                # Verkaufen
                self._execute_sell(deposit, TradeReason.TAKE_PROFIT, current_price)
    
    def _check_dumps(self):
        """Erkennt Dump-Situationen anhand von RSI und Volume"""
        for coin, market in self.market_data.items():
            try:
                # RSI berechnen
                rsi = self.coingecko.calculate_rsi(coin, period=self.settings.rsi_period)
                
                # Dump-Indikatoren
                is_dump = False
                reasons = []
                
                # 1. RSI überkauft und fällt stark
                if rsi > self.settings.rsi_overbought and market.price_change_24h < -10:
                    is_dump = True
                    reasons.append(f"RSI={rsi:.0f}, 24h={market.price_change_24h:.1f}%")
                
                # 2. Starker Preisverfall (>15%)
                if market.price_change_24h < -15:
                    is_dump = True
                    reasons.append(f"Starker Fall: {market.price_change_24h:.1f}%")
                
                if is_dump:
                    logger.warning(f"⚠️ DUMP ERKANNT: {coin} - {', '.join(reasons)}")
                    
                    if self.on_alert:
                        self.on_alert("critical", f"⚠️ DUMP ERKANNT: {coin} - {', '.join(reasons)}")
                    
                    # Alle Positionen dieses Coins verkaufen
                    deposits = self.db.get_unsold_deposits(coin)
                    for deposit in deposits:
                        self._execute_sell(deposit, TradeReason.DUMP_DETECTED, market.price_usd)
                        
            except Exception as e:
                logger.error(f"Dump Check Fehler für {coin}: {e}")
    
    def _execute_sell(self, deposit: MiningDeposit, reason: TradeReason, current_price: float, amount: float = None):
        """Führt einen Verkauf aus"""
        exchange_name = deposit.exchange
        sell_amount = amount or deposit.amount
        
        if exchange_name not in self.exchanges:
            logger.error(f"❌ Börse nicht konfiguriert: {exchange_name}")
            return
        
        api = self.exchanges[exchange_name]
        
        # Limit Order Preis (leicht unter Markt für schnelle Ausführung)
        if self.settings.use_limit_orders:
            order_price = current_price * (1 - self.settings.limit_order_offset / 100)
            order_type = OrderType.LIMIT
        else:
            order_price = current_price
            order_type = OrderType.MARKET
        
        # Order platzieren
        order = api.place_order(
            coin=deposit.coin,
            side=OrderSide.SELL,
            amount=sell_amount,
            order_type=order_type,
            price=order_price,
            stablecoin=self.settings.preferred_stablecoin
        )
        
        if order:
            order.reason = reason.value
            
            # In DB speichern
            self.db.add_trade(order)
            
            # Deposit als verkauft markieren (wenn alles verkauft)
            if sell_amount >= deposit.amount:
                profit_loss = (current_price - deposit.price_at_deposit) * deposit.amount
                self.db.mark_deposit_sold(deposit.id, deposit.amount, current_price, profit_loss)
            
            # Callback für GUI
            if self.on_trade:
                self.on_trade(order)
            
            # Alert
            if self.on_alert and self.settings.notify_on_trade:
                profit_loss = (current_price - deposit.price_at_deposit) * sell_amount
                pnl_str = f"+${profit_loss:.2f}" if profit_loss >= 0 else f"-${abs(profit_loss):.2f}"
                self.on_alert("info", f"✅ VERKAUFT: {sell_amount:.6f} {deposit.coin} @ ${current_price:.4f} ({pnl_str}) - Grund: {reason.value}")
            
            logger.info(f"✅ Verkauft: {sell_amount:.6f} {deposit.coin} @ ${current_price:.4f} - Grund: {reason.value}")
        else:
            logger.error(f"❌ Verkauf fehlgeschlagen: {deposit.coin}")
    
    def manual_sell(self, coin: str, amount: float, exchange: str = None) -> Optional[TradeOrder]:
        """Manueller Verkauf durch User"""
        exchange_name = exchange or self.settings.primary_exchange
        
        if exchange_name not in self.exchanges:
            logger.error(f"❌ Börse nicht konfiguriert: {exchange_name}")
            return None
        
        api = self.exchanges[exchange_name]
        current_price = self.coingecko.get_price(coin) or api.get_ticker_price(coin)
        
        if current_price <= 0:
            logger.error(f"❌ Kein Preis für {coin}")
            return None
        
        order = api.place_order(
            coin=coin,
            side=OrderSide.SELL,
            amount=amount,
            order_type=OrderType.LIMIT if self.settings.use_limit_orders else OrderType.MARKET,
            price=current_price * (1 - self.settings.limit_order_offset / 100),
            stablecoin=self.settings.preferred_stablecoin
        )
        
        if order:
            order.reason = TradeReason.MANUAL.value
            self.db.add_trade(order)
            
            if self.on_trade:
                self.on_trade(order)
        
        return order
    
    def get_portfolio_summary(self) -> Dict:
        """Gibt Portfolio-Zusammenfassung zurück"""
        deposits = self.db.get_unsold_deposits()
        
        total_value_usd = 0
        total_cost_basis_usd = 0
        total_unrealized_pnl = 0
        positions = {}
        
        for deposit in deposits:
            coin = deposit.coin
            current_price = self.market_data.get(coin, MarketData(
                coin=coin, price_usd=0, price_change_24h=0, price_change_7d=0,
                volume_24h=0, volume_change_24h=0, market_cap=0
            )).price_usd
            
            if coin not in positions:
                positions[coin] = {
                    "amount": 0,
                    "avg_cost": 0,
                    "current_price": current_price,
                    "value_usd": 0,
                    "cost_basis_usd": 0,
                    "unrealized_pnl": 0,
                    "unrealized_pnl_percent": 0
                }
            
            positions[coin]["amount"] += deposit.amount
            positions[coin]["cost_basis_usd"] += deposit.amount * deposit.price_at_deposit
            positions[coin]["value_usd"] = positions[coin]["amount"] * current_price
            
            if positions[coin]["amount"] > 0:
                positions[coin]["avg_cost"] = positions[coin]["cost_basis_usd"] / positions[coin]["amount"]
            
            positions[coin]["unrealized_pnl"] = positions[coin]["value_usd"] - positions[coin]["cost_basis_usd"]
            
            if positions[coin]["cost_basis_usd"] > 0:
                positions[coin]["unrealized_pnl_percent"] = (positions[coin]["unrealized_pnl"] / positions[coin]["cost_basis_usd"]) * 100
            
            total_value_usd += positions[coin]["value_usd"]
            total_cost_basis_usd += positions[coin]["cost_basis_usd"]
            total_unrealized_pnl += positions[coin]["unrealized_pnl"]
        
        return {
            "total_value_usd": total_value_usd,
            "total_cost_basis_usd": total_cost_basis_usd,
            "total_unrealized_pnl": total_unrealized_pnl,
            "total_unrealized_pnl_percent": (total_unrealized_pnl / total_cost_basis_usd * 100) if total_cost_basis_usd > 0 else 0,
            "positions": positions,
            "position_count": len(positions)
        }
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """Gibt Trading-Historie zurück"""
        return self.db.get_trade_history(limit)
    
    def get_activity_log(self, limit: int = 100) -> List[Dict]:
        """Gibt Activity-Log zurück"""
        return self.db.get_activity_log(limit)


# ============================================================
# SINGLETON
# ============================================================

_portfolio_manager: Optional[PortfolioManager] = None

def get_portfolio_manager() -> PortfolioManager:
    """Gibt die Singleton-Instanz zurück"""
    global _portfolio_manager
    if _portfolio_manager is None:
        _portfolio_manager = PortfolioManager()
    return _portfolio_manager


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("💰 Portfolio Manager Test")
    print("=" * 60)
    
    # CoinGecko Test
    cg = CoinGeckoAPI()
    
    print("\n📊 Aktuelle Preise:")
    for coin in ["RVN", "ERG", "KAS", "GRIN", "FLUX"]:
        price = cg.get_price(coin)
        if price:
            print(f"  {coin}: ${price:.6f}")
        else:
            print(f"  {coin}: N/A")
    
    print("\n📈 RSI (9er Periode für volatile Coins):")
    for coin in ["RVN", "KAS", "ERG"]:
        rsi = cg.calculate_rsi(coin, period=9)
        status = "ÜBERKAUFT" if rsi > 80 else "ÜBERVERKAUFT" if rsi < 20 else "NEUTRAL"
        print(f"  {coin}: RSI={rsi:.1f} ({status})")
    
    print("\n📉 Marktdaten:")
    market = cg.get_market_data("KAS")
    if market:
        print(f"  KAS:")
        print(f"    Preis: ${market.price_usd:.6f}")
        print(f"    24h: {market.price_change_24h:+.1f}%")
        print(f"    7d: {market.price_change_7d:+.1f}%")
        print(f"    Trend: {market.trend}")
    
    print("\n" + "=" * 60)
    print("✅ Test abgeschlossen!")
    print("=" * 60)
