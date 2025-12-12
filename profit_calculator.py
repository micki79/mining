#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Profit Calculator - Berechnet USD/Tag für alle Coins
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Datenquellen: WhatToMine, minerstat
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# API Konfiguration
WHATTOMINE_API = "https://whattomine.com/coins.json"
MINERSTAT_API = "https://api.minerstat.com/v2/coins"

# Cache-Einstellungen
CACHE_FILE = "profit_cache.json"
CACHE_DURATION = 300  # 5 Minuten


@dataclass
class CoinProfit:
    """Profit-Daten für einen Coin"""
    coin: str
    algorithm: str
    hashrate: float  # Hashrate für Berechnung
    hashrate_unit: str  # MH/s, GH/s, etc.
    btc_revenue_24h: float
    usd_revenue_24h: float
    difficulty: float
    block_reward: float
    price_usd: float
    last_update: datetime


class ProfitCalculator:
    """Berechnet Mining-Profit für verschiedene Coins - GPU-SPEZIFISCH!"""
    
    # WhatToMine Referenz-Hashrates (was WTM für ihre Berechnungen verwendet)
    # Diese werden genutzt um auf die TATSÄCHLICHE GPU-Hashrate zu skalieren
    WTM_REFERENCE_HASHRATES = {
        "kawpow":       {"hash": 30.0,  "unit": "MH/s"},   # RVN
        "autolykos2":   {"hash": 170.0, "unit": "MH/s"},   # ERG
        "etchash":      {"hash": 60.0,  "unit": "MH/s"},   # ETC
        "ethash":       {"hash": 60.0,  "unit": "MH/s"},   # Legacy
        "kheavyhash":   {"hash": 350.0, "unit": "MH/s"},   # KAS
        "equihash125":  {"hash": 55.0,  "unit": "Sol/s"},  # FLUX
        "equihash144":  {"hash": 55.0,  "unit": "Sol/s"},  # ZEC
        "blake3":       {"hash": 2.2,   "unit": "GH/s"},   # ALPH
        "octopus":      {"hash": 58.0,  "unit": "MH/s"},   # CFX
        "randomx":      {"hash": 1.0,   "unit": "kH/s"},   # XMR (CPU)
        "progpow":      {"hash": 30.0,  "unit": "MH/s"},   
        "firopow":      {"hash": 25.0,  "unit": "MH/s"},   # FIRO
        "beamhashiii":  {"hash": 30.0,  "unit": "Sol/s"},  # BEAM
        "zelhash":      {"hash": 55.0,  "unit": "Sol/s"},  # FLUX
        "zhash":        {"hash": 55.0,  "unit": "Sol/s"},
        "cuckoo":       {"hash": 5.0,   "unit": "G/s"},    # GRIN
        "cuckatoo32":   {"hash": 2.0,   "unit": "G/s"},
        "sha256":       {"hash": 100.0, "unit": "TH/s"},   # BTC (ASIC)
        "scrypt":       {"hash": 1.0,   "unit": "GH/s"},   # LTC (ASIC)
        "x11":          {"hash": 1.0,   "unit": "TH/s"},   # DASH
    }
    
    # Algorithmus zu Coin Mapping
    ALGO_TO_COINS = {
        "kawpow": ["RVN", "CLORE", "NEOX", "MEWC"],
        "autolykos2": ["ERG"],
        "etchash": ["ETC", "ETHW"],
        "kheavyhash": ["KAS"],
        "equihash125": ["FLUX"],
        "equihash144": ["ZEC", "ZEN"],
        "blake3": ["ALPH", "IRON"],
        "octopus": ["CFX"],
        "beamhashiii": ["BEAM"],
        "firopow": ["FIRO"],
        "randomx": ["XMR", "ZEPH"],
        "ghostrider": ["RTM"],
        "dynex": ["DNX"],
    }
    
    def __init__(self, cache_dir: str = ".", gpu_name: str = None):
        self.cache_path = Path(cache_dir) / CACHE_FILE
        self.cache: Dict[str, CoinProfit] = {}
        self.last_fetch = None
        self.gpu_name = gpu_name  # z.B. "RTX 3080 Laptop GPU"
        self.gpu_hashrates = {}   # Hashrates für diese GPU pro Algo
        self._load_cache()
        
        if gpu_name:
            self._load_gpu_hashrates(gpu_name)
    
    def set_gpu(self, gpu_name: str):
        """Setzt die GPU für Profit-Berechnungen"""
        self.gpu_name = gpu_name
        self._load_gpu_hashrates(gpu_name)
        logger.info(f"ProfitCalculator: GPU gesetzt auf {gpu_name}")
    
    def _load_gpu_hashrates(self, gpu_name: str):
        """Lädt GPU-spezifische Hashrates aus der Datenbank"""
        try:
            from gpu_database import GPU_OC_DATABASE, get_oc_settings
            
            gpu_lower = gpu_name.lower()
            matched_gpu = None
            
            # WICHTIG: Spezifischere Matches (Laptop) ZUERST prüfen!
            # Sortiere DB-Keys nach Länge (längere = spezifischer zuerst)
            sorted_gpus = sorted(GPU_OC_DATABASE.keys(), key=len, reverse=True)
            
            for db_gpu in sorted_gpus:
                db_lower = db_gpu.lower()
                # Prüfe ob der DB-Name im erkannten Namen enthalten ist
                if db_lower in gpu_lower:
                    matched_gpu = db_gpu
                    break
            
            # Spezielles Matching für Laptop GPUs falls nicht gefunden
            if not matched_gpu:
                laptop_patterns = [
                    ("3080 laptop", "RTX 3080 Laptop"),
                    ("3070 laptop", "RTX 3070 Laptop"),
                    ("3060 laptop", "RTX 3060 Laptop"),
                    ("4090 laptop", "RTX 4090 Laptop"),
                    ("4080 laptop", "RTX 4080 Laptop"),
                ]
                for pattern, db_name in laptop_patterns:
                    if pattern in gpu_lower:
                        if db_name in GPU_OC_DATABASE:
                            matched_gpu = db_name
                            break
            
            # Fallback: Generische GPU-Matches
            if not matched_gpu:
                gpu_patterns = [
                    ("3090", "RTX 3090"),
                    ("3080 ti", "RTX 3080 Ti"),
                    ("3080", "RTX 3080"),
                    ("3070 ti", "RTX 3070 Ti"),
                    ("3070", "RTX 3070"),
                    ("3060 ti", "RTX 3060 Ti"),
                    ("3060", "RTX 3060"),
                    ("4090", "RTX 4090"),
                    ("4080", "RTX 4080"),
                    ("4070 ti", "RTX 4070 Ti"),
                    ("4070", "RTX 4070"),
                    ("4060 ti", "RTX 4060 Ti"),
                    ("4060", "RTX 4060"),
                    ("6900 xt", "RX 6900 XT"),
                    ("6800 xt", "RX 6800 XT"),
                    ("6700 xt", "RX 6700 XT"),
                    ("6600 xt", "RX 6600 XT"),
                ]
                for pattern, db_name in gpu_patterns:
                    if pattern in gpu_lower:
                        if db_name in GPU_OC_DATABASE:
                            matched_gpu = db_name
                            break
            
            if matched_gpu and matched_gpu in GPU_OC_DATABASE:
                gpu_data = GPU_OC_DATABASE[matched_gpu]
                for algo, settings in gpu_data.items():
                    self.gpu_hashrates[algo] = {
                        "hashrate": settings.get("hash", 0),
                        "power": settings.get("power", 100),
                        "unit": settings.get("unit", "MH/s")
                    }
                logger.info(f"GPU-Hashrates geladen für {matched_gpu}: {len(self.gpu_hashrates)} Algorithmen")
            else:
                logger.warning(f"GPU {gpu_name} nicht in Datenbank gefunden - nutze Referenz-Werte")
                
        except ImportError:
            logger.warning("gpu_database nicht verfügbar")
        except Exception as e:
            logger.error(f"Fehler beim Laden der GPU-Hashrates: {e}")
    
    def get_gpu_hashrate(self, algorithm: str) -> Optional[Dict]:
        """Gibt Hashrate für diese GPU und diesen Algorithmus zurück"""
        algo_lower = algorithm.lower()
        
        # Direkt aus GPU-Daten
        if algo_lower in self.gpu_hashrates:
            return self.gpu_hashrates[algo_lower]
        
        # Aliase prüfen
        algo_aliases = {
            "equihash_125_4": "equihash125",
            "equihash_144_5": "equihash144",
            "ethash": "etchash",
            "zelhash": "equihash125",
            "zhash": "equihash144",
        }
        if algo_lower in algo_aliases:
            alias = algo_aliases[algo_lower]
            if alias in self.gpu_hashrates:
                return self.gpu_hashrates[alias]
        
        return None
    
    def _load_cache(self):
        """Lädt Cache von Datei"""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_fetch = datetime.fromisoformat(data.get("last_fetch", "2000-01-01"))
            except:
                pass
    
    def _save_cache(self, coins_data: Dict):
        """Speichert Cache in Datei"""
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "last_fetch": datetime.now().isoformat(),
                    "coins": coins_data
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Cache-Speichern fehlgeschlagen: {e}")
    
    def _should_refresh(self) -> bool:
        """Prüft ob Cache aktualisiert werden sollte"""
        if not self.last_fetch:
            return True
        return datetime.now() - self.last_fetch > timedelta(seconds=CACHE_DURATION)
    
    def fetch_whattomine(self) -> Dict[str, Dict]:
        """Holt Coin-Daten von WhatToMine"""
        try:
            response = requests.get(WHATTOMINE_API, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            coins = {}
            
            # Mapping für alternative Namen
            TAG_ALIASES = {
                "RAVEN": "RVN",
                "RAVENCOIN": "RVN", 
                "ERG": "ERGO",
                "ERGO": "ERG",
                "ETHEREUMCLASSIC": "ETC",
                "FLUX": "FLUX",
            }
            
            for coin_id, coin_data in data.get("coins", {}).items():
                tag = coin_data.get("tag", "").upper()
                name = coin_data.get("name", "").upper()
                
                if tag:
                    coin_info = {
                        "name": coin_data.get("name", ""),
                        "algorithm": coin_data.get("algorithm", "").lower(),
                        "nethash": coin_data.get("nethash", 0),
                        "difficulty": coin_data.get("difficulty", 0),
                        "block_reward": coin_data.get("block_reward", 0),
                        "btc_revenue": float(coin_data.get("btc_revenue", 0) or 0),
                        "exchange_rate": float(coin_data.get("exchange_rate", 0) or 0),
                        "exchange_rate_curr": coin_data.get("exchange_rate_curr", "BTC"),
                        "profitability": float(coin_data.get("profitability", 0) or 0),
                        "profitability24": float(coin_data.get("profitability24", 0) or 0),
                    }
                    
                    # Unter Tag speichern
                    coins[tag] = coin_info
                    
                    # Auch unter Alias speichern
                    if tag in TAG_ALIASES:
                        coins[TAG_ALIASES[tag]] = coin_info
                    if name in TAG_ALIASES:
                        coins[TAG_ALIASES[name]] = coin_info
                    
                    # Spezialfall: Name ohne Spaces
                    name_clean = name.replace(" ", "")
                    if name_clean != tag:
                        coins[name_clean] = coin_info
            
            self.last_fetch = datetime.now()
            self._save_cache(coins)
            logger.info(f"WhatToMine: {len(coins)} Coins geladen (Tags: {list(coins.keys())[:10]}...)")
            return coins
            
        except Exception as e:
            logger.error(f"WhatToMine API Fehler: {e}")
            return {}
    
    def get_btc_price(self) -> float:
        """Holt aktuellen BTC Preis in USD"""
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin", "vs_currencies": "usd"},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("bitcoin", {}).get("usd", 0)
        except:
            pass
        return 97000  # Fallback
    
    def calculate_profit(self, coin: str, hashrate: float = None, power_watts: float = 0, 
                        power_cost: float = 0.0) -> Optional[Dict]:
        """
        Berechnet Revenue für einen Coin - OHNE Stromkosten!
        
        Args:
            coin: Coin-Ticker (z.B. "RVN")
            hashrate: Hashrate (None = GPU-spezifisch aus Datenbank)
            power_watts: Stromverbrauch (nur für Info, NICHT abgezogen)
            power_cost: IGNORIERT - Wir zeigen NUR Revenue!
        
        Returns:
            Dict mit revenue pro Tag (KEIN Stromabzug!)
        """
        # Daten abrufen wenn nötig
        if self._should_refresh():
            coins = self.fetch_whattomine()
        else:
            # Aus Cache laden
            if self.cache_path.exists():
                try:
                    with open(self.cache_path, 'r', encoding='utf-8') as f:
                        coins = json.load(f).get("coins", {})
                except:
                    coins = self.fetch_whattomine()
            else:
                coins = self.fetch_whattomine()
        
        # Coin-Daten suchen (mit Fallbacks)
        coin_upper = coin.upper()
        coin_data = coins.get(coin_upper)
        
        # Fallback: Alternative Tags suchen
        if not coin_data:
            alternatives = {
                "RVN": ["RAVEN", "RAVENCOIN"],
                "ERG": ["ERGO"],
                "ETC": ["ETHEREUMCLASSIC", "ETHCLASSIC"],
                "FLUX": ["ZEL"],
            }
            for alt in alternatives.get(coin_upper, []):
                coin_data = coins.get(alt)
                if coin_data:
                    break
        
        # Fallback: Durchsuche alle Coins nach Namen
        if not coin_data:
            for tag, data in coins.items():
                if coin_upper in data.get("name", "").upper():
                    coin_data = data
                    break
        
        if not coin_data:
            return None
        
        # BTC-Preis holen
        btc_price = self.get_btc_price()
        algo = coin_data.get("algorithm", "").lower()
        
        # GPU-SPEZIFISCHE Hashrate und Power holen!
        gpu_stats = self.get_gpu_hashrate(algo)
        
        if gpu_stats and hashrate is None:
            # Nutze GPU-spezifische Werte
            hashrate = gpu_stats["hashrate"]
            if power_watts == 0:
                power_watts = gpu_stats.get("power", 100)
        elif hashrate is None:
            # Fallback auf WTM Referenz
            ref_data = self.WTM_REFERENCE_HASHRATES.get(algo, {"hash": 30.0})
            hashrate = ref_data["hash"]
            if power_watts == 0:
                power_watts = 150  # Default
        
        # WTM Referenz für Skalierung
        wtm_ref = self.WTM_REFERENCE_HASHRATES.get(algo, {"hash": 30.0})
        wtm_hashrate = wtm_ref["hash"]
        
        # Skalieren auf tatsächliche Hashrate
        if wtm_hashrate > 0:
            hashrate_factor = hashrate / wtm_hashrate
        else:
            hashrate_factor = 1.0
        
        # Revenue berechnen
        btc_revenue_raw = coin_data.get("btc_revenue", 0)
        btc_revenue_24h = btc_revenue_raw * hashrate_factor
        usd_revenue_24h = btc_revenue_24h * btc_price
        
        # Stromverbrauch nur für Info (NICHT abgezogen!)
        kwh_per_day = (power_watts * 24) / 1000
        
        # NUR Revenue zeigen - KEIN Stromabzug!
        return {
            "coin": coin.upper(),
            "algorithm": algo,
            "hashrate": hashrate,
            "hashrate_unit": gpu_stats["unit"] if gpu_stats else "MH/s",
            "power_watts": power_watts,
            "btc_revenue_24h": btc_revenue_24h,
            "usd_revenue_24h": round(usd_revenue_24h, 4),
            "kwh_per_day": round(kwh_per_day, 2),
            "usd_profit_24h": round(usd_revenue_24h, 4),  # = Revenue (KEIN Stromabzug!)
            "exchange_rate": coin_data.get("exchange_rate", 0),
            "btc_price": btc_price,
            "difficulty": coin_data.get("difficulty", 0),
        }
    
    def get_most_profitable(self, coins: List[str] = None,
                               limit: int = 20) -> List[Dict]:
        """
        Findet die profitabelsten Coins FÜR DIESE GPU!
        
        Args:
            coins: Liste von Coins zu prüfen (None = alle)
            limit: Max Anzahl Ergebnisse
        
        Returns:
            Sortierte Liste der Coins nach REVENUE (KEIN Stromabzug!)
        """
        results = []
        
        # Daten abrufen
        if self._should_refresh():
            coin_data = self.fetch_whattomine()
        else:
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    coin_data = json.load(f).get("coins", {})
            except:
                coin_data = self.fetch_whattomine()
        
        btc_price = self.get_btc_price()
        
        for coin, data in coin_data.items():
            if coins and coin not in coins:
                continue
            
            algo = data.get("algorithm", "").lower()
            
            # GPU-SPEZIFISCHE Hashrate und Power!
            gpu_stats = self.get_gpu_hashrate(algo)
            
            if gpu_stats:
                hashrate = gpu_stats["hashrate"]
                power_watts = gpu_stats.get("power", 100)
                unit = gpu_stats.get("unit", "MH/s")
            else:
                # Fallback auf WTM Referenz
                wtm_ref = self.WTM_REFERENCE_HASHRATES.get(algo)
                if not wtm_ref:
                    continue  # Algorithmus nicht unterstützt
                hashrate = wtm_ref["hash"]
                power_watts = 150  # Default
                unit = wtm_ref.get("unit", "MH/s")
            
            if hashrate <= 0:
                continue
            
            # Skalierung auf WTM-Referenz
            wtm_ref = self.WTM_REFERENCE_HASHRATES.get(algo, {"hash": hashrate})
            wtm_hashrate = wtm_ref["hash"]
            hashrate_factor = hashrate / wtm_hashrate if wtm_hashrate > 0 else 1.0
            
            # Revenue berechnen (KEIN Stromabzug!)
            btc_revenue = data.get("btc_revenue", 0) * hashrate_factor
            usd_revenue = btc_revenue * btc_price
            kwh_per_day = (power_watts * 24) / 1000
            
            results.append({
                "coin": coin,
                "algorithm": algo,
                "hashrate": hashrate,
                "hashrate_unit": unit,
                "power_watts": power_watts,
                "usd_revenue_24h": round(usd_revenue, 4),
                "kwh_per_day": round(kwh_per_day, 2),
                "usd_profit_24h": round(usd_revenue, 4),  # = Revenue (KEIN Stromabzug!)
                "profitability": data.get("profitability", 0),
                "exchange_rate": data.get("exchange_rate", 0),
            })
        
        # Nach REVENUE sortieren (NICHT Profit!)
        results.sort(key=lambda x: x["usd_revenue_24h"], reverse=True)
        return results[:limit]
    
    def get_best_coin_for_gpu(self) -> Optional[Dict]:
        """
        Findet den BESTEN Coin für diese GPU!
        
        Returns:
            Dict mit dem profitabelsten Coin oder None
        """
        results = self.get_most_profitable(limit=1)
        return results[0] if results else None
    
    def get_supported_algorithms(self) -> List[str]:
        """Gibt Liste aller Algorithmen zurück die diese GPU unterstützt"""
        if self.gpu_hashrates:
            return list(self.gpu_hashrates.keys())
        return list(self.WTM_REFERENCE_HASHRATES.keys())
    
    def print_profitability_report(self, top_n: int = 10):
        """Druckt einen Revenue-Report für diese GPU (OHNE Stromkosten)"""
        print(f"\n{'='*70}")
        print(f"REVENUE-REPORT für: {self.gpu_name or 'Unbekannte GPU'}")
        print(f"(Stromkosten werden NICHT abgezogen)")
        print(f"{'='*70}")
        
        results = self.get_most_profitable(limit=top_n)
        
        if not results:
            print("Keine Daten verfügbar!")
            return
        
        print(f"\n{'Rank':<5} {'Coin':<8} {'Algo':<15} {'Hashrate':<15} {'Power':<8} {'Revenue/Tag':<12}")
        print("-" * 70)
        
        for i, coin in enumerate(results, 1):
            hashrate_str = f"{coin['hashrate']:.1f} {coin['hashrate_unit']}"
            print(f"{i:<5} {coin['coin']:<8} {coin['algorithm']:<15} {hashrate_str:<15} "
                  f"{coin['power_watts']:<8.0f}W ${coin['usd_revenue_24h']:<10.2f}")
        
        print("-" * 70)
        best = results[0]
        print(f"\n🏆 BESTER COIN: {best['coin']} ({best['algorithm']}) = ${best['usd_revenue_24h']:.2f}/Tag")
        print(f"   Hashrate: {best['hashrate']:.1f} {best['hashrate_unit']} @ {best['power_watts']:.0f}W")


# Globale Instanz
_profit_calc = None

def get_profit_calculator(gpu_name: str = None) -> ProfitCalculator:
    """Gibt globale ProfitCalculator-Instanz zurück"""
    global _profit_calc
    if _profit_calc is None:
        _profit_calc = ProfitCalculator(gpu_name=gpu_name)
    elif gpu_name and _profit_calc.gpu_name != gpu_name:
        _profit_calc.set_gpu(gpu_name)
    return _profit_calc


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test mit RTX 3080 Laptop
    calc = ProfitCalculator(gpu_name="RTX 3080 Laptop GPU")
    
    print("\nGPU-Hashrates geladen:")
    for algo, stats in calc.gpu_hashrates.items():
        print(f"  {algo}: {stats['hashrate']} {stats['unit']} @ {stats['power']}W")
    
    # Revenue-Report (OHNE Stromkosten!)
    calc.print_profitability_report(top_n=15)
    
    # Test: Einzelner Coin
    print("\n=== RVN REVENUE ===")
    result = calc.calculate_profit("RVN")
    if result:
        print(f"  Revenue: ${result['usd_revenue_24h']:.4f}/Tag")
        print(f"  Stromkosten: ${result['power_cost_24h']:.4f}/Tag")
        print(f"  Profit: ${result['usd_profit_24h']:.4f}/Tag")
    
    # Test: Profitabelste Coins
    print("\n=== TOP 5 PROFITABEL ===")
    hashrates = {
        "kawpow": 30.0,
        "autolykos2": 170.0,
        "etchash": 60.0,
        "kheavyhash": 350.0,
    }
    top = calc.get_most_profitable(hashrates, power_watts=140, power_cost=0.10)[:5]
    for i, coin in enumerate(top, 1):
        print(f"  {i}. {coin['coin']:6} ({coin['algorithm']:12}): ${coin['usd_profit_24h']:.4f}/Tag")
