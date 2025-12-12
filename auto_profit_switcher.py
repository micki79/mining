#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Profit Switcher - Automatischer Coin-Wechsel basierend auf Profit
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Echtzeit Profit-Vergleich ALLER Coins (ohne Stromkosten = reiner Gewinn)
- Automatische Pool-Auswahl (beste Pools pro Coin)
- Automatisches Wechseln zum profitabelsten Coin
- Kontinuierliches Testen im Hintergrund
"""

import json
import logging
import requests
import time
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# WhatToMine API
WHATTOMINE_GPU_URL = "https://whattomine.com/coins.json"
WHATTOMINE_ASIC_URL = "https://whattomine.com/asic.json"

# Backup APIs
MINERSTAT_API = "https://api.minerstat.com/v2/coins"
HASHRATE_NO_API = "https://api.hashrate.no/v1/coins"

# Cache
CACHE_FILE = "profit_switcher_cache.json"
CACHE_DURATION = 180  # 3 Minuten


@dataclass
class CoinProfit:
    """Profit-Daten für einen Coin"""
    coin: str
    algorithm: str
    revenue_usd_24h: float  # Reiner Gewinn ohne Stromkosten!
    revenue_btc_24h: float
    price_usd: float
    difficulty: float
    network_hashrate: float
    block_reward: float
    block_time: float
    last_block: int = 0
    exchange_rate: float = 0.0
    estimated_rewards: float = 0.0
    pool_fee: float = 1.0  # Standard 1%
    
    def __lt__(self, other):
        return self.revenue_usd_24h < other.revenue_usd_24h


@dataclass 
class PoolInfo:
    """Pool-Informationen"""
    name: str
    url: str
    port: int
    ssl_port: int = 0
    fee: float = 1.0
    region: str = "EU"
    reliability: float = 99.0  # Uptime %
    min_payout: float = 0.0
    payout_scheme: str = "PPLNS"  # PPLNS, PPS, PPS+, FPPS
    
    @property
    def stratum_url(self) -> str:
        return f"stratum+tcp://{self.url}:{self.port}"
    
    @property
    def ssl_url(self) -> str:
        if self.ssl_port:
            return f"stratum+ssl://{self.url}:{self.ssl_port}"
        return self.stratum_url


# === BESTE POOLS PRO COIN ===
# Sortiert nach Zuverlässigkeit und Gebühren
BEST_POOLS = {
    "RVN": [
        PoolInfo("2Miners", "rvn.2miners.com", 6060, 16060, 1.0, "EU", 99.9, 10),
        PoolInfo("Flypool", "stratum-ravencoin.flypool.org", 3333, 3443, 1.0, "EU", 99.5, 10),
        PoolInfo("HeroMiners", "ravencoin.herominers.com", 1140, 1141, 0.9, "EU", 99.0, 5),
        PoolInfo("Nanopool", "rvn-eu1.nanopool.org", 12222, 12433, 1.0, "EU", 99.0, 10),
        PoolInfo("MiningPoolHub", "europe.ravenminer.com", 4567, 0, 0.9, "EU", 98.0, 0.01),
    ],
    "ERG": [
        PoolInfo("2Miners", "erg.2miners.com", 8888, 18888, 1.0, "EU", 99.9, 0.5),
        PoolInfo("Flypool", "stratum-ergo.flypool.org", 3333, 3443, 1.0, "EU", 99.5, 0.5),
        PoolInfo("HeroMiners", "ergo.herominers.com", 1180, 1181, 0.9, "EU", 99.0, 0.1),
        PoolInfo("Nanopool", "ergo-eu1.nanopool.org", 11111, 11433, 1.0, "EU", 99.0, 0.5),
        PoolInfo("WoolyPooly", "erg.woolypooly.com", 3100, 3166, 0.9, "EU", 98.5, 0.5),
    ],
    "ETC": [
        PoolInfo("2Miners", "etc.2miners.com", 1010, 11010, 1.0, "EU", 99.9, 0.1),
        PoolInfo("Ethermine", "etc.ethermine.org", 4444, 5555, 1.0, "EU", 99.9, 0.01),
        PoolInfo("F2Pool", "etc.f2pool.com", 8118, 0, 2.0, "Global", 99.5, 0.1),
        PoolInfo("Poolin", "etc.ss.poolin.me", 443, 1883, 2.0, "Global", 99.0, 0.1),
        PoolInfo("HeroMiners", "etc.herominers.com", 1147, 1148, 0.9, "EU", 99.0, 0.01),
    ],
    "FLUX": [
        PoolInfo("2Miners", "flux.2miners.com", 9090, 19090, 1.0, "EU", 99.9, 0.01),
        PoolInfo("MinerPool", "flux.minerpool.org", 2020, 2022, 0.5, "EU", 99.0, 0.001),
        PoolInfo("HeroMiners", "flux.herominers.com", 1200, 1201, 0.9, "EU", 99.0, 0.001),
        PoolInfo("SoloPool", "flux.solopool.org", 8888, 0, 0.0, "EU", 98.0, 0.0),
    ],
    "KAS": [
        PoolInfo("2Miners", "kas.2miners.com", 2020, 12020, 1.0, "EU", 99.9, 1.0),
        PoolInfo("HeroMiners", "kaspa.herominers.com", 1206, 1207, 0.9, "EU", 99.0, 0.5),
        PoolInfo("WoolyPooly", "kas.woolypooly.com", 3112, 3166, 0.9, "EU", 98.5, 1.0),
        PoolInfo("ACC-Pool", "kas.acc-pool.pw", 16061, 0, 1.0, "EU", 98.0, 0.5),
    ],
    "ALPH": [
        PoolInfo("2Miners", "alph.2miners.com", 2020, 0, 1.0, "EU", 99.9, 0.1),
        PoolInfo("HeroMiners", "alephium.herominers.com", 1199, 1198, 0.9, "EU", 99.0, 0.05),
        PoolInfo("WoolyPooly", "alph.woolypooly.com", 3106, 0, 0.9, "EU", 98.5, 0.1),
    ],
    "NEXA": [
        PoolInfo("2Miners", "nexa.2miners.com", 3030, 0, 1.0, "EU", 99.9, 100),
        PoolInfo("HeroMiners", "nexa.herominers.com", 1213, 1214, 0.9, "EU", 99.0, 50),
        PoolInfo("WoolyPooly", "nexa.woolypooly.com", 3124, 0, 0.9, "EU", 98.5, 100),
    ],
    "XMR": [
        PoolInfo("2Miners", "xmr.2miners.com", 2222, 12222, 1.0, "EU", 99.9, 0.001),
        PoolInfo("Nanopool", "xmr-eu1.nanopool.org", 14433, 14444, 1.0, "EU", 99.0, 0.1),
        PoolInfo("SupportXMR", "pool.supportxmr.com", 3333, 0, 0.6, "Global", 99.0, 0.1),
        PoolInfo("MoneroOcean", "gulf.moneroocean.stream", 10128, 20128, 0.0, "Global", 99.0, 0.003),
    ],
    "ZEPH": [
        PoolInfo("HeroMiners", "zephyr.herominers.com", 1123, 1124, 0.9, "EU", 99.0, 0.1),
        PoolInfo("2Miners", "zeph.2miners.com", 2020, 0, 1.0, "EU", 99.9, 0.01),
    ],
    "CFX": [
        PoolInfo("2Miners", "cfx.2miners.com", 2020, 0, 1.0, "EU", 99.9, 0.1),
        PoolInfo("F2Pool", "cfx.f2pool.com", 6800, 0, 2.0, "Global", 99.5, 0.1),
        PoolInfo("Nanopool", "cfx-eu1.nanopool.org", 17777, 17433, 1.0, "EU", 99.0, 0.1),
    ],
    "CLORE": [
        PoolInfo("WoolyPooly", "clore.woolypooly.com", 3122, 0, 0.9, "EU", 98.5, 1.0),
        PoolInfo("HeroMiners", "clore.herominers.com", 1211, 1212, 0.9, "EU", 99.0, 0.5),
    ],
    "DNX": [
        PoolInfo("HeroMiners", "dynex.herominers.com", 1120, 1121, 0.9, "EU", 99.0, 0.1),
        PoolInfo("K1Pool", "dnx.k1pool.com", 5555, 0, 1.0, "EU", 98.0, 0.1),
    ],
    "RXD": [
        PoolInfo("2Miners", "rxd.2miners.com", 6060, 0, 1.0, "EU", 99.9, 50),
        PoolInfo("WoolyPooly", "rxd.woolypooly.com", 3128, 0, 0.9, "EU", 98.5, 50),
    ],
    "BEAM": [
        PoolInfo("2Miners", "beam.2miners.com", 5252, 15252, 1.0, "EU", 99.9, 0.1),
        PoolInfo("Flypool", "stratum-beam.flypool.org", 3333, 3443, 1.0, "EU", 99.5, 0.1),
        PoolInfo("HeroMiners", "beam.herominers.com", 1130, 1131, 0.9, "EU", 99.0, 0.05),
    ],
    "ZEC": [
        PoolInfo("2Miners", "zec.2miners.com", 1010, 11010, 1.0, "EU", 99.9, 0.001),
        PoolInfo("Flypool", "zec.flypool.org", 3333, 3443, 1.0, "EU", 99.5, 0.01),
        PoolInfo("Nanopool", "zec-eu1.nanopool.org", 6666, 6633, 1.0, "EU", 99.0, 0.01),
    ],
    "FIRO": [
        PoolInfo("2Miners", "firo.2miners.com", 8181, 0, 1.0, "EU", 99.9, 0.1),
        PoolInfo("MintPond", "firo.mintpond.com", 3000, 3001, 1.0, "Global", 99.0, 0.01),
        PoolInfo("HeroMiners", "firo.herominers.com", 1169, 1170, 0.9, "EU", 99.0, 0.05),
    ],
    "RTM": [
        PoolInfo("Suprnova", "rtm.suprnova.cc", 6273, 0, 1.0, "Global", 99.0, 1.0),
        PoolInfo("Rplant", "stratum-eu.rplant.xyz", 7068, 17068, 0.5, "EU", 98.5, 0.5),
    ],
    # NEUE COINS:
    "GRIN": [
        PoolInfo("2Miners", "grin.2miners.com", 3030, 13030, 1.0, "EU", 99.9, 0.1),
        PoolInfo("F2Pool", "grin.f2pool.com", 13654, 0, 2.0, "Global", 99.5, 0.1),
        PoolInfo("GrinMint", "stratum.grinmint.com", 3416, 4416, 2.0, "EU", 99.0, 0.1),
    ],
    "EPIC": [
        PoolInfo("51Pool", "epic.51pool.online", 4416, 0, 1.0, "EU", 98.0, 0.1),
        PoolInfo("IcePool", "epic.icemining.ca", 4000, 0, 1.0, "NA", 98.0, 0.1),
    ],
    "XNA": [
        PoolInfo("WoolyPooly", "xna.woolypooly.com", 3130, 0, 0.9, "EU", 98.5, 10),
        PoolInfo("HeroMiners", "neurai.herominers.com", 1215, 1216, 0.9, "EU", 99.0, 5),
    ],
    "NEOX": [
        PoolInfo("WoolyPooly", "neox.woolypooly.com", 3126, 0, 0.9, "EU", 98.5, 10),
        PoolInfo("HeroMiners", "neoxa.herominers.com", 1217, 1218, 0.9, "EU", 99.0, 5),
    ],
    "ETHW": [
        PoolInfo("2Miners", "ethw.2miners.com", 2020, 12020, 1.0, "EU", 99.9, 0.01),
        PoolInfo("F2Pool", "ethw.f2pool.com", 6688, 0, 2.0, "Global", 99.5, 0.01),
        PoolInfo("WoolyPooly", "ethw.woolypooly.com", 3096, 0, 0.9, "EU", 98.5, 0.01),
    ],
    "IRON": [
        PoolInfo("HeroMiners", "ironfish.herominers.com", 1145, 1146, 0.9, "EU", 99.0, 0.1),
        PoolInfo("KuKuPool", "iron.kuko.io", 5555, 0, 1.0, "EU", 98.0, 0.1),
    ],
}

# Algorithmus zu Miner Mapping
ALGO_MINER_MAP = {
    "kawpow": ["T-Rex", "NBMiner", "GMiner", "Rigel"],
    "autolykos2": ["T-Rex", "NBMiner", "lolMiner", "Rigel"],
    "etchash": ["T-Rex", "NBMiner", "GMiner", "lolMiner"],
    "ethash": ["T-Rex", "NBMiner", "GMiner", "lolMiner"],
    "kheavyhash": ["lolMiner", "BzMiner", "Rigel"],
    "blake3": ["lolMiner", "BzMiner", "Rigel"],
    "equihash125": ["lolMiner", "GMiner"],
    "equihash144": ["lolMiner", "GMiner"],
    "equihash": ["lolMiner", "GMiner"],
    "beamhashiii": ["lolMiner", "GMiner"],
    "randomx": ["XMRig", "SRBMiner"],
    "ghostrider": ["SRBMiner"],
    "sha512256d": ["lolMiner", "BzMiner", "Rigel"],
    "nexapow": ["lolMiner", "BzMiner"],
    "dynexsolve": ["SRBMiner"],
    # NEUE ALGORITHMEN:
    "cuckatoo32": ["lolMiner", "GMiner"],  # GRIN
    "cuckatoo31": ["lolMiner", "GMiner"],
    "cuckoo29": ["lolMiner", "GMiner"],
    "firopow": ["T-Rex", "NBMiner"],  # FIRO
    "progpow": ["T-Rex", "NBMiner"],  # EPIC, SERO
    "octopus": ["T-Rex", "NBMiner"],  # CFX
    "zelhash": ["lolMiner", "GMiner"],  # FLUX
    "zhash": ["lolMiner", "GMiner"],
    "karlsenhash": ["BzMiner", "lolMiner"],  # KLS
    "pyrinhash": ["BzMiner", "Rigel"],  # PYI
    "cryptonight": ["XMRig", "SRBMiner"],  # XMR
    "cryptonightv8": ["XMRig", "SRBMiner"],
    "verthash": ["Rigel"],  # VTC
}

# Referenz-Hashraten für RTX 3080 (Basis für Berechnungen)
REFERENCE_HASHRATES = {
    "kawpow": {"hashrate": 50.0, "unit": "MH/s"},
    "autolykos2": {"hashrate": 260.0, "unit": "MH/s"},
    "etchash": {"hashrate": 98.0, "unit": "MH/s"},
    "ethash": {"hashrate": 98.0, "unit": "MH/s"},
    "kheavyhash": {"hashrate": 1.8, "unit": "GH/s"},
    "blake3": {"hashrate": 3.5, "unit": "GH/s"},
    "equihash125": {"hashrate": 75.0, "unit": "Sol/s"},
    "equihash144": {"hashrate": 75.0, "unit": "Sol/s"},
    "equihash": {"hashrate": 75.0, "unit": "Sol/s"},
    "beamhashiii": {"hashrate": 45.0, "unit": "Sol/s"},
    "randomx": {"hashrate": 1.5, "unit": "kH/s"},  # CPU
    "ghostrider": {"hashrate": 2.0, "unit": "kH/s"},  # CPU
    "sha512256d": {"hashrate": 3.0, "unit": "GH/s"},
    "nexapow": {"hashrate": 200.0, "unit": "MH/s"},
    # NEUE ALGORITHMEN:
    "cuckatoo32": {"hashrate": 2.2, "unit": "G/s"},  # GRIN
    "cuckatoo31": {"hashrate": 2.5, "unit": "G/s"},
    "cuckoo29": {"hashrate": 8.0, "unit": "G/s"},
    "firopow": {"hashrate": 45.0, "unit": "MH/s"},  # FIRO
    "progpow": {"hashrate": 30.0, "unit": "MH/s"},  # EPIC
    "octopus": {"hashrate": 55.0, "unit": "MH/s"},  # CFX
    "zelhash": {"hashrate": 65.0, "unit": "Sol/s"},  # FLUX
    "zhash": {"hashrate": 120.0, "unit": "Sol/s"},
    "karlsenhash": {"hashrate": 1.5, "unit": "GH/s"},  # KLS
    "pyrinhash": {"hashrate": 1.2, "unit": "GH/s"},
    "cryptonight": {"hashrate": 2.0, "unit": "kH/s"},  # CPU
    "cryptonightv8": {"hashrate": 2.0, "unit": "kH/s"},
    "verthash": {"hashrate": 1.0, "unit": "MH/s"},  # VTC
    "dynexsolve": {"hashrate": 500.0, "unit": "H/s"},
}


class AutoProfitSwitcher:
    """
    Automatischer Profit-Switcher
    
    - Holt aktuelle Preise von WhatToMine
    - Berechnet REINEN GEWINN (ohne Stromkosten!)
    - Findet automatisch den besten Pool
    - Wechselt automatisch zum profitabelsten Coin
    """
    
    def __init__(self, gpu_hashrate_factor: float = 1.0):
        """
        Args:
            gpu_hashrate_factor: Faktor für deine GPU vs RTX 3080
                                 z.B. 0.5 für RTX 3070, 1.5 für RTX 4080
        """
        self.gpu_factor = gpu_hashrate_factor
        self.cache_path = Path(CACHE_FILE)
        self.coins_data: Dict[str, CoinProfit] = {}
        self.last_update = None
        self._lock = threading.Lock()
        
        # Callbacks
        self.on_update: Optional[callable] = None
        self.on_switch: Optional[callable] = None
        
        # Auto-Switch Settings
        self.min_profit_diff = 5.0  # Mindestens 5% mehr Profit zum Wechseln
        self.check_interval = 180   # Alle 3 Minuten prüfen
        self.current_coin = ""
        
        # Background Thread
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def fetch_whattomine(self) -> Dict[str, CoinProfit]:
        """Holt aktuelle Daten von WhatToMine"""
        coins = {}
        
        try:
            response = requests.get(WHATTOMINE_GPU_URL, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                for coin_id, coin_data in data.get("coins", {}).items():
                    tag = coin_data.get("tag", "").upper()
                    if not tag:
                        continue
                    
                    algo = coin_data.get("algorithm", "").lower()
                    
                    # Revenue berechnen (OHNE Stromkosten!)
                    btc_revenue = coin_data.get("btc_revenue", 0)
                    
                    # Skalieren auf deine GPU
                    ref_hr = REFERENCE_HASHRATES.get(algo, {}).get("hashrate", 30.0)
                    # WhatToMine gibt Revenue für ihre Referenz-Hashrate
                    # Wir skalieren auf unsere GPU
                    scaled_btc = btc_revenue * self.gpu_factor
                    
                    # BTC zu USD
                    btc_price = data.get("btc_rate", 97000)
                    usd_revenue = scaled_btc * btc_price
                    
                    coins[tag] = CoinProfit(
                        coin=tag,
                        algorithm=algo,
                        revenue_usd_24h=usd_revenue,
                        revenue_btc_24h=scaled_btc,
                        price_usd=coin_data.get("exchange_rate", 0),
                        difficulty=coin_data.get("difficulty", 0),
                        network_hashrate=coin_data.get("nethash", 0),
                        block_reward=coin_data.get("block_reward", 0),
                        block_time=coin_data.get("block_time", 0),
                        last_block=coin_data.get("last_block", 0),
                        exchange_rate=coin_data.get("exchange_rate", 0),
                        estimated_rewards=coin_data.get("estimated_rewards", 0),
                    )
                
                logger.info(f"WhatToMine: {len(coins)} Coins geladen")
                
        except Exception as e:
            logger.error(f"WhatToMine Fehler: {e}")
        
        return coins
    
    def fetch_minerstat_backup(self) -> Dict[str, CoinProfit]:
        """Backup: minerstat API"""
        coins = {}
        
        try:
            response = requests.get(MINERSTAT_API, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                for coin_data in data:
                    tag = coin_data.get("coin", "").upper()
                    algo = coin_data.get("algorithm", "").lower()
                    
                    if not tag or not algo:
                        continue
                    
                    # Revenue aus reward_unit berechnen
                    reward = coin_data.get("reward_unit", 0)
                    price = coin_data.get("price", 0)
                    usd_revenue = reward * price * self.gpu_factor
                    
                    coins[tag] = CoinProfit(
                        coin=tag,
                        algorithm=algo,
                        revenue_usd_24h=usd_revenue,
                        revenue_btc_24h=0,
                        price_usd=price,
                        difficulty=coin_data.get("difficulty", 0),
                        network_hashrate=coin_data.get("network_hashrate", 0),
                        block_reward=coin_data.get("reward_block", 0),
                        block_time=0,
                    )
                    
        except Exception as e:
            logger.error(f"Minerstat Fehler: {e}")
        
        return coins
    
    def update_prices(self) -> bool:
        """Aktualisiert alle Coin-Preise"""
        with self._lock:
            # Primär: WhatToMine
            coins = self.fetch_whattomine()
            
            # Backup: minerstat wenn WhatToMine leer
            if not coins:
                coins = self.fetch_minerstat_backup()
            
            if coins:
                self.coins_data = coins
                self.last_update = datetime.now()
                self._save_cache()
                
                if self.on_update:
                    self.on_update(coins)
                
                return True
        
        return False
    
    def _save_cache(self):
        """Speichert Cache"""
        try:
            cache = {
                "timestamp": self.last_update.isoformat() if self.last_update else "",
                "coins": {
                    tag: {
                        "coin": c.coin,
                        "algorithm": c.algorithm,
                        "revenue_usd_24h": c.revenue_usd_24h,
                        "revenue_btc_24h": c.revenue_btc_24h,
                        "price_usd": c.price_usd,
                    }
                    for tag, c in self.coins_data.items()
                }
            }
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2)
        except Exception as e:
            logger.error(f"Cache Speicherfehler: {e}")
    
    def _load_cache(self) -> bool:
        """Lädt Cache"""
        if not self.cache_path.exists():
            return False
        
        try:
            with open(self.cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            
            ts = cache.get("timestamp")
            if ts:
                self.last_update = datetime.fromisoformat(ts)
                
                # Cache zu alt?
                age = (datetime.now() - self.last_update).total_seconds()
                if age > CACHE_DURATION:
                    return False
            
            for tag, data in cache.get("coins", {}).items():
                self.coins_data[tag] = CoinProfit(
                    coin=data["coin"],
                    algorithm=data["algorithm"],
                    revenue_usd_24h=data["revenue_usd_24h"],
                    revenue_btc_24h=data.get("revenue_btc_24h", 0),
                    price_usd=data.get("price_usd", 0),
                    difficulty=0,
                    network_hashrate=0,
                    block_reward=0,
                    block_time=0,
                )
            
            return len(self.coins_data) > 0
            
        except Exception as e:
            logger.error(f"Cache Ladefehler: {e}")
            return False
    
    def get_top_coins(self, limit: int = 10, algorithms: List[str] = None) -> List[CoinProfit]:
        """
        Gibt die profitabelsten Coins zurück
        
        Args:
            limit: Anzahl der Coins
            algorithms: Filter auf bestimmte Algorithmen
            
        Returns:
            Liste sortiert nach Profit (höchster zuerst)
        """
        # Aktualisieren wenn nötig
        if not self.coins_data or not self.last_update:
            if not self._load_cache():
                self.update_prices()
        elif (datetime.now() - self.last_update).total_seconds() > CACHE_DURATION:
            self.update_prices()
        
        coins = list(self.coins_data.values())
        
        # Filter nach Algorithmen
        if algorithms:
            algos_lower = [a.lower() for a in algorithms]
            coins = [c for c in coins if c.algorithm in algos_lower]
        
        # Nur Coins mit Pools
        coins = [c for c in coins if c.coin in BEST_POOLS]
        
        # Sortieren nach Revenue (höchster zuerst)
        coins.sort(key=lambda c: c.revenue_usd_24h, reverse=True)
        
        return coins[:limit]
    
    def get_best_coin(self, algorithms: List[str] = None) -> Optional[CoinProfit]:
        """Gibt den aktuell profitabelsten Coin zurück"""
        top = self.get_top_coins(1, algorithms)
        return top[0] if top else None
    
    def get_best_pool(self, coin: str) -> Optional[PoolInfo]:
        """Gibt den besten Pool für einen Coin zurück"""
        pools = BEST_POOLS.get(coin.upper(), [])
        if pools:
            # Sortiert nach Reliability, dann Fee
            sorted_pools = sorted(pools, key=lambda p: (-p.reliability, p.fee))
            return sorted_pools[0]
        return None
    
    def get_all_pools(self, coin: str) -> List[PoolInfo]:
        """Gibt alle Pools für einen Coin zurück"""
        return BEST_POOLS.get(coin.upper(), [])
    
    def get_best_miner(self, algorithm: str) -> Optional[str]:
        """Gibt den besten Miner für einen Algorithmus zurück"""
        miners = ALGO_MINER_MAP.get(algorithm.lower(), [])
        return miners[0] if miners else None
    
    def should_switch(self, current_coin: str) -> Tuple[bool, Optional[CoinProfit]]:
        """
        Prüft ob gewechselt werden soll
        
        Returns:
            (should_switch, new_coin) oder (False, None)
        """
        if not current_coin:
            best = self.get_best_coin()
            return (True, best) if best else (False, None)
        
        current_profit = self.coins_data.get(current_coin.upper())
        if not current_profit:
            best = self.get_best_coin()
            return (True, best) if best else (False, None)
        
        best = self.get_best_coin()
        if not best:
            return False, None
        
        # Gleicher Coin?
        if best.coin == current_coin.upper():
            return False, None
        
        # Profit-Differenz berechnen
        if current_profit.revenue_usd_24h > 0:
            diff_percent = ((best.revenue_usd_24h - current_profit.revenue_usd_24h) 
                          / current_profit.revenue_usd_24h * 100)
        else:
            diff_percent = 100
        
        if diff_percent >= self.min_profit_diff:
            logger.info(f"Wechsel empfohlen: {current_coin} → {best.coin} (+{diff_percent:.1f}%)")
            return True, best
        
        return False, None
    
    def get_mining_config(self, coin: str) -> Optional[Dict]:
        """
        Gibt komplette Mining-Konfiguration für einen Coin zurück
        
        Returns:
            Dict mit coin, algorithm, pool, miner, etc.
        """
        coin = coin.upper()
        
        if coin not in self.coins_data:
            return None
        
        coin_data = self.coins_data[coin]
        pool = self.get_best_pool(coin)
        miner = self.get_best_miner(coin_data.algorithm)
        
        if not pool:
            logger.warning(f"Kein Pool für {coin} gefunden")
            return None
        
        return {
            "coin": coin,
            "algorithm": coin_data.algorithm,
            "pool_name": pool.name,
            "pool_url": pool.stratum_url,
            "pool_ssl": pool.ssl_url,
            "pool_fee": pool.fee,
            "miner": miner,
            "revenue_usd_24h": coin_data.revenue_usd_24h,
            "price_usd": coin_data.price_usd,
        }
    
    def start_auto_switch(self, callback: callable = None):
        """
        Startet automatisches Switching im Hintergrund
        
        Args:
            callback: Wird aufgerufen wenn gewechselt werden soll
                      callback(new_coin_config: Dict)
        """
        self.on_switch = callback
        self._running = True
        self._thread = threading.Thread(target=self._auto_switch_loop, daemon=True)
        self._thread.start()
        logger.info("Auto-Switcher gestartet")
    
    def stop_auto_switch(self):
        """Stoppt automatisches Switching"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-Switcher gestoppt")
    
    def _auto_switch_loop(self):
        """Background-Thread für Auto-Switching"""
        while self._running:
            try:
                # Preise aktualisieren
                self.update_prices()
                
                # Prüfen ob wechseln
                should, new_coin = self.should_switch(self.current_coin)
                
                if should and new_coin and self.on_switch:
                    config = self.get_mining_config(new_coin.coin)
                    if config:
                        self.on_switch(config)
                        self.current_coin = new_coin.coin
                
            except Exception as e:
                logger.error(f"Auto-Switch Fehler: {e}")
            
            # Warten
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def get_profit_summary(self) -> str:
        """Gibt formatierte Profit-Übersicht zurück"""
        top_coins = self.get_top_coins(10)
        
        if not top_coins:
            return "Keine Daten verfügbar"
        
        lines = [
            "═══════════════════════════════════════════════════",
            "  TOP 10 PROFITABELSTE COINS (Reiner Gewinn/Tag)",
            "═══════════════════════════════════════════════════",
            f"  {'#':<3} {'Coin':<8} {'Algo':<12} {'$/Tag':<10} {'Pool'}",
            "───────────────────────────────────────────────────",
        ]
        
        for i, coin in enumerate(top_coins, 1):
            pool = self.get_best_pool(coin.coin)
            pool_name = pool.name if pool else "N/A"
            lines.append(
                f"  {i:<3} {coin.coin:<8} {coin.algorithm:<12} "
                f"${coin.revenue_usd_24h:<9.2f} {pool_name}"
            )
        
        lines.append("═══════════════════════════════════════════════════")
        
        return "\n".join(lines)


# Singleton Instance
_switcher_instance: Optional[AutoProfitSwitcher] = None

def get_profit_switcher(gpu_factor: float = 1.0) -> AutoProfitSwitcher:
    """Gibt Singleton-Instanz zurück"""
    global _switcher_instance
    if _switcher_instance is None:
        _switcher_instance = AutoProfitSwitcher(gpu_factor)
    return _switcher_instance


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    switcher = AutoProfitSwitcher(gpu_hashrate_factor=0.85)  # RTX 3080 Laptop ~85%
    
    print("\n🔄 Lade aktuelle Preise...")
    switcher.update_prices()
    
    print(switcher.get_profit_summary())
    
    print("\n📊 Beste Mining-Config:")
    best = switcher.get_best_coin()
    if best:
        config = switcher.get_mining_config(best.coin)
        print(json.dumps(config, indent=2))
