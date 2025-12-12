#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Pool Fetcher - Holt Mining-Pools automatisch von miningpoolstats.stream

Features:
- Automatisches Laden der besten Pools für jeden Coin
- Caching um API-Limits zu vermeiden
- Fallback auf bekannte Pools
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# Cache-Datei für Pools
POOLS_CACHE_FILE = "pools_cache.json"
CACHE_MAX_AGE = 3600 * 6  # 6 Stunden

# Bekannte gute Pools als Fallback
KNOWN_POOLS = {
    "RVN": [
        {"name": "2Miners", "url": "stratum+tcp://rvn.2miners.com:6060", "fee": 1.0},
        {"name": "Flypool", "url": "stratum+tcp://stratum-ravencoin.flypool.org:3333", "fee": 1.0},
        {"name": "HeroMiners", "url": "stratum+tcp://rvn.herominers.com:1140", "fee": 0.9},
    ],
    "ERG": [
        {"name": "2Miners", "url": "stratum+tcp://erg.2miners.com:8888", "fee": 1.0},
        {"name": "Flypool", "url": "stratum+tcp://stratum-ergo.flypool.org:3333", "fee": 1.0},
        {"name": "HeroMiners", "url": "stratum+tcp://ergo.herominers.com:1180", "fee": 0.9},
    ],
    "ETC": [
        {"name": "2Miners", "url": "stratum+tcp://etc.2miners.com:1010", "fee": 1.0},
        {"name": "Ethermine", "url": "stratum+tcp://etc.ethermine.org:4444", "fee": 1.0},
        {"name": "F2Pool", "url": "stratum+tcp://etc.f2pool.com:8118", "fee": 2.0},
    ],
    "FLUX": [
        {"name": "2Miners", "url": "stratum+tcp://flux.2miners.com:9090", "fee": 1.0},
        {"name": "MinerPool", "url": "stratum+tcp://flux.minerpool.org:2032", "fee": 0.5},
    ],
    "KAS": [
        {"name": "Acc-Pool", "url": "stratum+tcp://kas.acc-pool.pw:16061", "fee": 0.5},
        {"name": "HeroMiners", "url": "stratum+tcp://kaspa.herominers.com:1206", "fee": 0.9},
        {"name": "WoolyPooly", "url": "stratum+tcp://kas.woolypooly.com:3112", "fee": 0.9},
    ],
    "ALPH": [
        {"name": "HeroMiners", "url": "stratum+tcp://alephium.herominers.com:1199", "fee": 0.9},
        {"name": "WoolyPooly", "url": "stratum+tcp://alph.woolypooly.com:3106", "fee": 0.9},
    ],
    "NEXA": [
        {"name": "HeroMiners", "url": "stratum+tcp://nexa.herominers.com:1213", "fee": 0.9},
        {"name": "Acc-Pool", "url": "stratum+tcp://nexa.acc-pool.pw:16200", "fee": 0.5},
    ],
    "GRIN": [
        {"name": "2Miners", "url": "stratum+tcp://grin.2miners.com:3030", "fee": 1.0},
        {"name": "F2Pool", "url": "stratum+tcp://grin.f2pool.com:13654", "fee": 2.0},
    ],
    "BEAM": [
        {"name": "2Miners", "url": "stratum+tcp://beam.2miners.com:5252", "fee": 1.0},
        {"name": "Flypool", "url": "stratum+tcp://stratum-beam.flypool.org:3333", "fee": 1.0},
    ],
    "FIRO": [
        {"name": "2Miners", "url": "stratum+tcp://firo.2miners.com:8181", "fee": 1.0},
        {"name": "MintPond", "url": "stratum+tcp://firo.mintpond.com:3000", "fee": 1.0},
    ],
    "XNA": [
        {"name": "WoolyPooly", "url": "stratum+tcp://xna.woolypooly.com:3102", "fee": 0.9},
        {"name": "HeroMiners", "url": "stratum+tcp://neurai.herominers.com:1231", "fee": 0.9},
    ],
    "CLORE": [
        {"name": "WoolyPooly", "url": "stratum+tcp://clore.woolypooly.com:3122", "fee": 0.9},
        {"name": "HeroMiners", "url": "stratum+tcp://clore.herominers.com:1214", "fee": 0.9},
    ],
    "DNX": [
        {"name": "HeroMiners", "url": "stratum+tcp://dynex.herominers.com:1120", "fee": 0.9},
    ],
    "ZEPH": [
        {"name": "HeroMiners", "url": "stratum+tcp://zephyr.herominers.com:1123", "fee": 0.9},
    ],
    "CFX": [
        {"name": "2Miners", "url": "stratum+tcp://cfx.2miners.com:2020", "fee": 1.0},
        {"name": "F2Pool", "url": "stratum+tcp://cfx.f2pool.com:6800", "fee": 2.0},
    ],
    "XMR": [
        {"name": "2Miners", "url": "stratum+tcp://xmr.2miners.com:2222", "fee": 1.0},
        {"name": "MoneroOcean", "url": "stratum+tcp://gulf.moneroocean.stream:10128", "fee": 0.0},
        {"name": "SupportXMR", "url": "stratum+tcp://pool.supportxmr.com:3333", "fee": 0.6},
    ],
    "ETHW": [
        {"name": "2Miners", "url": "stratum+tcp://ethw.2miners.com:2020", "fee": 1.0},
        {"name": "F2Pool", "url": "stratum+tcp://ethw.f2pool.com:6688", "fee": 2.0},
    ],
    "ZEC": [
        {"name": "2Miners", "url": "stratum+tcp://zec.2miners.com:1010", "fee": 1.0},
        {"name": "Flypool", "url": "stratum+tcp://stratum-zcash.flypool.org:3333", "fee": 1.0},
    ],
    "BTG": [
        {"name": "2Miners", "url": "stratum+tcp://btg.2miners.com:4040", "fee": 1.0},
    ],
    "CTXC": [
        {"name": "2Miners", "url": "stratum+tcp://ctxc.2miners.com:2222", "fee": 1.0},
    ],
    "IRON": [
        {"name": "HeroMiners", "url": "stratum+tcp://ironfish.herominers.com:1145", "fee": 0.9},
        {"name": "Kryptex", "url": "stratum+tcp://iron.kryptex.network:7777", "fee": 1.0},
    ],
    "RTM": [
        {"name": "Flockpool", "url": "stratum+tcp://stratum-na.raptoreum.com:3333", "fee": 0.5},
        {"name": "MinerPool", "url": "stratum+tcp://rtm.minerpool.org:3032", "fee": 0.5},
    ],
    "DERO": [
        {"name": "HeroMiners", "url": "stratum+tcp://dero.herominers.com:1117", "fee": 0.9},
    ],
    "HNS": [
        {"name": "6Block", "url": "stratum+tcp://hns.6block.com:7701", "fee": 2.0},
    ],
    "CKB": [
        {"name": "2Miners", "url": "stratum+tcp://ckb.2miners.com:6464", "fee": 1.0},
        {"name": "F2Pool", "url": "stratum+tcp://ckb.f2pool.com:4300", "fee": 2.0},
    ],
    "EPIC": [
        {"name": "51Pool", "url": "stratum+tcp://epic.51pool.online:4416", "fee": 1.0},
        {"name": "Icemining", "url": "stratum+tcp://epic.icemining.ca:4000", "fee": 1.0},
    ],
    "NEOX": [
        {"name": "WoolyPooly", "url": "stratum+tcp://neox.woolypooly.com:3124", "fee": 0.9},
    ],
    "QUAI": [
        {"name": "HeroMiners", "url": "stratum+tcp://quai.herominers.com:1148", "fee": 0.9},
    ],
    # NEUE COINS:
    "VTC": [
        {"name": "2Miners", "url": "stratum+tcp://vtc.2miners.com:5050", "fee": 1.0},
    ],
    "DGB": [
        {"name": "2Miners", "url": "stratum+tcp://dgb.2miners.com:2020", "fee": 1.0},
        {"name": "ZPool", "url": "stratum+tcp://dgb.zpool.ca:5190", "fee": 2.0},
    ],
    "LTC": [
        {"name": "F2Pool", "url": "stratum+tcp://ltc.f2pool.com:8888", "fee": 2.0},
        {"name": "ViaBTC", "url": "stratum+tcp://ltc.viabtc.io:3333", "fee": 2.0},
    ],
    "DASH": [
        {"name": "F2Pool", "url": "stratum+tcp://dash.f2pool.com:5588", "fee": 2.0},
        {"name": "ViaBTC", "url": "stratum+tcp://dash.viabtc.io:443", "fee": 2.0},
    ],
    "DOGE": [
        {"name": "ViaBTC", "url": "stratum+tcp://doge.viabtc.io:3333", "fee": 2.0},
    ],
    "BCH": [
        {"name": "ViaBTC", "url": "stratum+tcp://bch.viabtc.io:443", "fee": 2.0},
    ],
    "ARRR": [
        {"name": "ZPool", "url": "stratum+tcp://arrr.zpool.ca:5756", "fee": 2.0},
    ],
    "ALEO": [
        {"name": "HeroMiners", "url": "stratum+tcp://aleo.herominers.com:1160", "fee": 0.9},
        {"name": "ZKPool", "url": "stratum+tcp://aleo.zkpool.io:3333", "fee": 1.0},
    ],
    "KDA": [
        {"name": "Poolflare", "url": "stratum+tcp://kda.poolflare.com:443", "fee": 1.0},
    ],
    "PYI": [
        {"name": "WoolyPooly", "url": "stratum+tcp://pyrin.woolypooly.com:3124", "fee": 0.9},
    ],
    "KLS": [
        {"name": "Acc-Pool", "url": "stratum+tcp://kls.acc-pool.pw:16062", "fee": 0.5},
    ],
}


class AutoPoolFetcher:
    """Holt und cached Mining-Pools automatisch"""
    
    def __init__(self, cache_file: str = POOLS_CACHE_FILE):
        self.cache_file = Path(cache_file)
        self.pools_cache: Dict[str, List[Dict]] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Lädt Pool-Cache"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.pools_cache = data.get('pools', {})
                    self._cache_time = data.get('timestamp', 0)
            except:
                self.pools_cache = {}
                self._cache_time = 0
        else:
            self.pools_cache = {}
            self._cache_time = 0
    
    def _save_cache(self):
        """Speichert Pool-Cache"""
        try:
            data = {
                'pools': self.pools_cache,
                'timestamp': time.time(),
                'updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Pool-Cache speichern fehlgeschlagen: {e}")
    
    def _is_cache_valid(self) -> bool:
        """Prüft ob Cache noch gültig ist"""
        return (time.time() - self._cache_time) < CACHE_MAX_AGE
    
    def get_pools_for_coin(self, coin: str) -> List[Dict]:
        """
        Holt Pools für einen Coin.
        
        Returns:
            Liste von Pools: [{"name": "...", "url": "...", "fee": ...}, ...]
        """
        coin = coin.upper()
        
        # 1. Aus Cache wenn gültig
        if coin in self.pools_cache and self._is_cache_valid():
            return self.pools_cache[coin]
        
        # 2. Von miningpoolstats.stream versuchen
        fetched_pools = self._fetch_from_miningpoolstats(coin)
        if fetched_pools:
            self.pools_cache[coin] = fetched_pools
            self._save_cache()
            return fetched_pools
        
        # 3. Fallback auf bekannte Pools
        if coin in KNOWN_POOLS:
            return KNOWN_POOLS[coin]
        
        return []
    
    def _fetch_from_miningpoolstats(self, coin: str) -> List[Dict]:
        """Holt Pools von miningpoolstats.stream"""
        if not requests:
            return []
        
        try:
            # miningpoolstats.stream API
            url = f"https://miningpoolstats.stream/api/{coin.lower()}"
            
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 Mining-Tool/1.0'
            })
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            pools = []
            
            # Parse Pool-Daten
            for pool_data in data.get('data', [])[:10]:  # Top 10 Pools
                pool = {
                    'name': pool_data.get('pool', pool_data.get('name', 'Unknown')),
                    'url': pool_data.get('url', ''),
                    'fee': pool_data.get('fee', 1.0),
                    'hashrate': pool_data.get('hashrate', 0),
                    'workers': pool_data.get('workers', 0),
                }
                
                # URL bereinigen
                if pool['url'] and not pool['url'].startswith('stratum'):
                    pool['url'] = f"stratum+tcp://{pool['url']}"
                
                if pool['url']:
                    pools.append(pool)
            
            logger.info(f"MiningPoolStats: {len(pools)} Pools für {coin} geladen")
            return pools
            
        except Exception as e:
            logger.debug(f"MiningPoolStats API Fehler für {coin}: {e}")
            return []
    
    def get_best_pool(self, coin: str) -> Optional[Dict]:
        """Gibt den besten Pool für einen Coin zurück"""
        pools = self.get_pools_for_coin(coin)
        if pools:
            # Sortiere nach Fee (niedrigste zuerst)
            sorted_pools = sorted(pools, key=lambda p: p.get('fee', 99))
            return sorted_pools[0]
        return None
    
    def get_pool_url(self, coin: str) -> Optional[str]:
        """Gibt die URL des besten Pools zurück"""
        pool = self.get_best_pool(coin)
        return pool['url'] if pool else None
    
    def get_pool_name(self, coin: str) -> Optional[str]:
        """Gibt den Namen des besten Pools zurück"""
        pool = self.get_best_pool(coin)
        return pool['name'] if pool else None
    
    def refresh_all_pools(self, coins: List[str] = None):
        """Aktualisiert Pools für alle/angegebene Coins"""
        if coins is None:
            coins = list(KNOWN_POOLS.keys())
        
        for coin in coins:
            self.get_pools_for_coin(coin)
            time.sleep(0.5)  # Rate limiting
        
        self._save_cache()


# Globale Instanz
_pool_fetcher: Optional[AutoPoolFetcher] = None

def get_pool_fetcher() -> AutoPoolFetcher:
    """Gibt globale Pool-Fetcher Instanz zurück"""
    global _pool_fetcher
    if _pool_fetcher is None:
        _pool_fetcher = AutoPoolFetcher()
    return _pool_fetcher


def get_best_pool_for_coin(coin: str) -> Dict:
    """Convenience-Funktion: Gibt besten Pool für Coin zurück"""
    fetcher = get_pool_fetcher()
    pool = fetcher.get_best_pool(coin)
    if pool:
        return pool
    return {"name": "N/A", "url": "", "fee": 0}


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    print("\n" + "="*60)
    print("  Auto Pool Fetcher Test")
    print("="*60 + "\n")
    
    fetcher = get_pool_fetcher()
    
    # Test verschiedene Coins
    test_coins = ["RVN", "ERG", "ETC", "KAS", "GRIN", "BEAM", "XMR"]
    
    for coin in test_coins:
        pool = fetcher.get_best_pool(coin)
        if pool:
            print(f"{coin:6} → {pool['name']:15} ({pool.get('fee', '?')}% fee)")
            print(f"         {pool['url']}")
        else:
            print(f"{coin:6} → Keine Pools gefunden")
        print()
    
    print("="*60)
