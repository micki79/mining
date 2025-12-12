#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Coin Konfiguration - ALLE minebaren Coins mit Pools
Teil des GPU Mining Profit Switcher V11.0 Ultimate
"""

from typing import Dict, List, Optional
from dataclasses import dataclass

# ============================================================================
# ALLE VERFÜGBAREN COINS
# ============================================================================

COIN_CONFIGS = {
    # === KAWPOW COINS ===
    "RVN": {
        "name": "Ravencoin",
        "algorithm": "kawpow",
        "ticker": "RVN",
        "website": "https://ravencoin.org",
        "explorer": "https://ravencoin.network",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://rvn.2miners.com:6060", "fee": 1.0},
            {"name": "HeroMiners", "url": "stratum+tcp://rvn.herominers.com:1140", "fee": 0.9},
            {"name": "Flypool", "url": "stratum+tcp://stratum-ravencoin.flypool.org:3333", "fee": 1.0},
            {"name": "WoolyPooly", "url": "stratum+tcp://rvn.woolypooly.com:55555", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://rvn.k1pool.com:7861", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer", "teamredminer", "srbminer", "wildrig"]
    },
    "CLORE": {
        "name": "Clore.ai",
        "algorithm": "kawpow",
        "ticker": "CLORE",
        "website": "https://clore.ai",
        "explorer": "https://explorer.clore.ai",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://clore.woolypooly.com:3122", "fee": 0.9},
            {"name": "HeroMiners", "url": "stratum+tcp://clore.herominers.com:1199", "fee": 0.9},
            {"name": "ACC-Pool", "url": "stratum+tcp://clore.acc-pool.pw:33100", "fee": 0.5},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer", "teamredminer", "srbminer"]
    },
    "XNA": {
        "name": "Neurai",
        "algorithm": "kawpow",
        "ticker": "XNA",
        "website": "https://neurai.org",
        "explorer": "https://explorer.neurai.org",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://xna.woolypooly.com:3128", "fee": 0.9},
            {"name": "ACC-Pool", "url": "stratum+tcp://xna.acc-pool.pw:33200", "fee": 0.5},
            {"name": "K1Pool", "url": "stratum+tcp://xna.k1pool.com:7871", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer", "rigel"]
    },
    "MEOWCOIN": {
        "name": "MeowCoin",
        "algorithm": "kawpow",
        "ticker": "MEWC",
        "website": "https://meowcoin.com",
        "explorer": "https://explorer.meowcoin.com",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://mewc.woolypooly.com:3129", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://mewc.k1pool.com:7872", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer"]
    },
    "NEOXA": {
        "name": "Neoxa",
        "algorithm": "kawpow",
        "ticker": "NEOX",
        "website": "https://neoxa.net",
        "explorer": "https://explorer.neoxa.net",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://neox.woolypooly.com:3127", "fee": 0.9},
            {"name": "ACC-Pool", "url": "stratum+tcp://neox.acc-pool.pw:33040", "fee": 0.5},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer"]
    },
    "AIPG": {
        "name": "AI Power Grid",
        "algorithm": "kawpow",
        "ticker": "AIPG",
        "website": "https://aipowergrid.io",
        "explorer": "https://explorer.aipowergrid.io",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://aipg.woolypooly.com:3130", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer", "bzminer"]
    },
    
    # === AUTOLYKOS2 (ERGO) ===
    "ERG": {
        "name": "Ergo",
        "algorithm": "autolykos2",
        "ticker": "ERG",
        "website": "https://ergoplatform.org",
        "explorer": "https://explorer.ergoplatform.com",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://ergo.herominers.com:1180", "fee": 0.9},
            {"name": "2miners", "url": "stratum+tcp://erg.2miners.com:8888", "fee": 1.0},
            {"name": "WoolyPooly", "url": "stratum+tcp://erg.woolypooly.com:3100", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://erg.k1pool.com:3100", "fee": 0.9},
            {"name": "Nanopool", "url": "stratum+tcp://ergo-eu1.nanopool.org:11111", "fee": 1.0},
        ],
        "miners": ["trex", "nbminer", "gminer", "lolminer", "bzminer", "rigel", "teamredminer", "srbminer"]
    },
    
    # === ETCHASH (ETC) ===
    "ETC": {
        "name": "Ethereum Classic",
        "algorithm": "etchash",
        "ticker": "ETC",
        "website": "https://ethereumclassic.org",
        "explorer": "https://blockscout.com/etc/mainnet",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://etc.2miners.com:1010", "fee": 1.0},
            {"name": "Ethermine", "url": "stratum+tcp://eu1-etc.ethermine.org:4444", "fee": 1.0},
            {"name": "F2Pool", "url": "stratum+tcp://etc.f2pool.com:8118", "fee": 2.0},
            {"name": "Nanopool", "url": "stratum+tcp://etc-eu1.nanopool.org:19999", "fee": 1.0},
            {"name": "HeroMiners", "url": "stratum+tcp://etc.herominers.com:1147", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer", "lolminer", "bzminer", "rigel", "phoenixminer", "teamredminer", "srbminer"]
    },
    
    # === EQUIHASH (FLUX, BTG) ===
    "FLUX": {
        "name": "Flux",
        "algorithm": "equihash125",
        "ticker": "FLUX",
        "website": "https://runonflux.io",
        "explorer": "https://explorer.runonflux.io",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://flux.2miners.com:9090", "fee": 1.0},
            {"name": "HeroMiners", "url": "stratum+tcp://flux.herominers.com:1200", "fee": 0.9},
            {"name": "MinerPool", "url": "stratum+tcp://flux-eu.minerpool.org:6060", "fee": 0.5},
            {"name": "K1Pool", "url": "stratum+tcp://flux.k1pool.com:4422", "fee": 0.9},
        ],
        "miners": ["gminer", "lolminer"]
    },
    "BTG": {
        "name": "Bitcoin Gold",
        "algorithm": "equihash144",
        "ticker": "BTG",
        "website": "https://bitcoingold.org",
        "explorer": "https://explorer.bitcoingold.org",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://btg.2miners.com:4040", "fee": 1.0},
            {"name": "HeroMiners", "url": "stratum+tcp://btg.herominers.com:1186", "fee": 0.9},
        ],
        "miners": ["gminer", "lolminer"]
    },
    
    # === KHEAVYHASH (KASPA) ===
    "KAS": {
        "name": "Kaspa",
        "algorithm": "kheavyhash",
        "ticker": "KAS",
        "website": "https://kaspa.org",
        "explorer": "https://explorer.kaspa.org",
        "enabled": True,
        "pools": [
            {"name": "ACC-Pool", "url": "stratum+tcp://kas.acc-pool.pw:16061", "fee": 0.5},
            {"name": "HeroMiners", "url": "stratum+tcp://kas.herominers.com:1206", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://kas.k1pool.com:7777", "fee": 0.9},
            {"name": "WoolyPooly", "url": "stratum+tcp://kas.woolypooly.com:3112", "fee": 0.9},
        ],
        "miners": ["gminer", "lolminer", "bzminer", "rigel", "teamredminer", "srbminer"]
    },
    "KLS": {
        "name": "Karlsen",
        "algorithm": "karlsenhash",
        "ticker": "KLS",
        "website": "https://karlsencoin.com",
        "explorer": "https://explorer.karlsencoin.com",
        "enabled": True,
        "pools": [
            {"name": "ACC-Pool", "url": "stratum+tcp://kls.acc-pool.pw:16081", "fee": 0.5},
            {"name": "WoolyPooly", "url": "stratum+tcp://kls.woolypooly.com:3132", "fee": 0.9},
        ],
        "miners": ["bzminer", "rigel"]
    },
    
    # === BLAKE3 (ALEPHIUM, IRON FISH) ===
    "ALPH": {
        "name": "Alephium",
        "algorithm": "blake3",
        "ticker": "ALPH",
        "website": "https://alephium.org",
        "explorer": "https://explorer.alephium.org",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://alph.herominers.com:1199", "fee": 0.9},
            {"name": "WoolyPooly", "url": "stratum+tcp://alph.woolypooly.com:3106", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://alph.k1pool.com:3300", "fee": 0.9},
        ],
        "miners": ["trex", "gminer", "bzminer", "srbminer"]
    },
    "IRON": {
        "name": "Iron Fish",
        "algorithm": "blake3",
        "ticker": "IRON",
        "website": "https://ironfish.network",
        "explorer": "https://explorer.ironfish.network",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://ironfish.herominers.com:1145", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://iron.k1pool.com:4500", "fee": 0.9},
        ],
        "miners": ["bzminer", "rigel"]
    },
    
    # === SHA512256D (RADIANT) ===
    "RXD": {
        "name": "Radiant",
        "algorithm": "sha512256d",
        "ticker": "RXD",
        "website": "https://radiantblockchain.org",
        "explorer": "https://explorer.radiantblockchain.org",
        "enabled": True,
        "pools": [
            {"name": "WoolyPooly", "url": "stratum+tcp://rxd.woolypooly.com:3124", "fee": 0.9},
            {"name": "ACC-Pool", "url": "stratum+tcp://rxd.acc-pool.pw:14461", "fee": 0.5},
        ],
        "miners": ["bzminer", "rigel"]
    },
    
    # === NEXAPOW ===
    "NEXA": {
        "name": "Nexa",
        "algorithm": "nexapow",
        "ticker": "NEXA",
        "website": "https://nexa.org",
        "explorer": "https://explorer.nexa.org",
        "enabled": True,
        "pools": [
            {"name": "ACC-Pool", "url": "stratum+tcp://nexa.acc-pool.pw:16011", "fee": 0.5},
            {"name": "WoolyPooly", "url": "stratum+tcp://nexa.woolypooly.com:3120", "fee": 0.9},
        ],
        "miners": ["lolminer", "rigel", "wildrig"]
    },
    
    # === DYNEXSOLVE ===
    "DNX": {
        "name": "Dynex",
        "algorithm": "dynexsolve",
        "ticker": "DNX",
        "website": "https://dynexcoin.org",
        "explorer": "https://explorer.dynexcoin.org",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://dnx.herominers.com:1120", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://dnx.k1pool.com:9200", "fee": 0.9},
        ],
        "miners": ["bzminer", "onezerominer"]
    },
    
    # === OCTOPUS (CONFLUX) ===
    "CFX": {
        "name": "Conflux",
        "algorithm": "octopus",
        "ticker": "CFX",
        "website": "https://confluxnetwork.org",
        "explorer": "https://confluxscan.io",
        "enabled": True,
        "pools": [
            {"name": "F2Pool", "url": "stratum+tcp://cfx.f2pool.com:6800", "fee": 2.0},
            {"name": "WoolyPooly", "url": "stratum+tcp://cfx.woolypooly.com:3094", "fee": 0.9},
            {"name": "HeroMiners", "url": "stratum+tcp://conflux.herominers.com:1170", "fee": 0.9},
        ],
        "miners": ["trex", "nbminer", "gminer"]
    },
    
    # === FIROPOW ===
    "FIRO": {
        "name": "Firo",
        "algorithm": "firopow",
        "ticker": "FIRO",
        "website": "https://firo.org",
        "explorer": "https://explorer.firo.org",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://firo.2miners.com:8181", "fee": 1.0},
            {"name": "MintPond", "url": "stratum+tcp://firo.mintpond.com:3000", "fee": 1.0},
            {"name": "WoolyPooly", "url": "stratum+tcp://firo.woolypooly.com:3104", "fee": 0.9},
        ],
        "miners": ["trex", "teamredminer", "wildrig"]
    },
    
    # === ZEPHYR (RANDOMX) ===
    "ZEPH": {
        "name": "Zephyr",
        "algorithm": "randomx",
        "ticker": "ZEPH",
        "website": "https://zephyrprotocol.com",
        "explorer": "https://explorer.zephyrprotocol.com",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://zephyr.herominers.com:1123", "fee": 0.9},
            {"name": "K1Pool", "url": "stratum+tcp://zeph.k1pool.com:7800", "fee": 0.9},
        ],
        "miners": ["srbminer", "xmrig"]
    },
    
    # === MONERO (RANDOMX - CPU MINING!) ===
    "XMR": {
        "name": "Monero",
        "algorithm": "randomx",
        "ticker": "XMR",
        "website": "https://getmonero.org",
        "explorer": "https://xmrchain.net",
        "enabled": True,
        "mining_type": "cpu",  # CPU Mining!
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://xmr.2miners.com:2222", "fee": 1.0},
            {"name": "HeroMiners", "url": "stratum+tcp://monero.herominers.com:1111", "fee": 0.9},
            {"name": "MoneroOcean", "url": "stratum+tcp://gulf.moneroocean.stream:10128", "fee": 0.0},
            {"name": "SupportXMR", "url": "stratum+tcp://pool.supportxmr.com:3333", "fee": 0.6},
            {"name": "Nanopool", "url": "stratum+tcp://xmr-eu1.nanopool.org:14433", "fee": 1.0},
            {"name": "P2Pool", "url": "stratum+tcp://p2pool.io:3333", "fee": 0.0},
        ],
        "miners": ["xmrig", "srbminer"],
        "hashrate_unit": "H/s",
        "notes": "CPU Mining empfohlen! Ryzen 9 5900HX: ~8-12 kH/s"
    },
    
    # === BEAMHASH ===
    "BEAM": {
        "name": "Beam",
        "algorithm": "beamhash3",
        "ticker": "BEAM",
        "website": "https://beam.mw",
        "explorer": "https://explorer.beam.mw",
        "enabled": True,
        "pools": [
            {"name": "HeroMiners", "url": "stratum+tcp://beam.herominers.com:1130", "fee": 0.9},
            {"name": "2miners", "url": "stratum+tcp://beam.2miners.com:5252", "fee": 1.0},
        ],
        "miners": ["lolminer", "gminer"]
    },
    
    # === CUCKATOO (GRIN) ===
    "GRIN": {
        "name": "Grin",
        "algorithm": "cuckatoo32",
        "ticker": "GRIN",
        "website": "https://grin.mw",
        "explorer": "https://grinscan.net",
        "enabled": True,
        "pools": [
            {"name": "2miners", "url": "stratum+tcp://grin.2miners.com:3030", "fee": 1.0},
            {"name": "F2Pool", "url": "stratum+tcp://grin.f2pool.com:13654", "fee": 2.5},
            {"name": "HeroMiners", "url": "stratum+tcp://grin.herominers.com:1165", "fee": 0.9},
        ],
        "miners": ["lolminer", "gminer"]
    },
}

# ============================================================================
# ALGORITHMEN MAPPING
# ============================================================================

ALGORITHM_CONFIGS = {
    "kawpow": {
        "name": "KawPow",
        "coins": ["RVN", "CLORE", "XNA", "MEOWCOIN", "NEOXA", "AIPG"],
        "memory_intensive": True,
        "description": "ASIC-resistant PoW (Ravencoin)"
    },
    "autolykos2": {
        "name": "Autolykos2",
        "coins": ["ERG"],
        "memory_intensive": True,
        "description": "Ergo's memory-hard PoW"
    },
    "etchash": {
        "name": "Etchash",
        "coins": ["ETC"],
        "memory_intensive": True,
        "description": "Ethereum Classic DAG-based"
    },
    "equihash125": {
        "name": "Equihash 125,4",
        "coins": ["FLUX"],
        "memory_intensive": False,
        "description": "ZelHash for Flux"
    },
    "equihash144": {
        "name": "Equihash 144,5",
        "coins": ["BTG"],
        "memory_intensive": False,
        "description": "Zhash for Bitcoin Gold"
    },
    "kheavyhash": {
        "name": "kHeavyHash",
        "coins": ["KAS"],
        "memory_intensive": False,
        "description": "Kaspa's GPU-friendly PoW"
    },
    "karlsenhash": {
        "name": "KarlsenHash",
        "coins": ["KLS"],
        "memory_intensive": False,
        "description": "Karlsen's kHeavyHash variant"
    },
    "blake3": {
        "name": "Blake3",
        "coins": ["ALPH", "IRON"],
        "memory_intensive": False,
        "description": "Fast hashing for Alephium"
    },
    "sha512256d": {
        "name": "SHA512256d",
        "coins": ["RXD"],
        "memory_intensive": False,
        "description": "Radiant blockchain"
    },
    "nexapow": {
        "name": "NexaPow",
        "coins": ["NEXA"],
        "memory_intensive": False,
        "description": "Nexa's custom PoW"
    },
    "dynexsolve": {
        "name": "DynexSolve",
        "coins": ["DNX"],
        "memory_intensive": True,
        "description": "Dynex neuromorphic computing"
    },
    "octopus": {
        "name": "Octopus",
        "coins": ["CFX"],
        "memory_intensive": True,
        "description": "Conflux's ASIC-resistant"
    },
    "firopow": {
        "name": "FiroPow",
        "coins": ["FIRO"],
        "memory_intensive": True,
        "description": "Firo's ProgPow variant"
    },
    "randomx": {
        "name": "RandomX",
        "coins": ["ZEPH"],
        "memory_intensive": True,
        "description": "CPU-optimized (Monero-based)"
    },
    "beamhash3": {
        "name": "BeamHash III",
        "coins": ["BEAM"],
        "memory_intensive": True,
        "description": "Beam's Equihash variant"
    },
    "cuckatoo32": {
        "name": "Cuckatoo32",
        "coins": ["GRIN"],
        "memory_intensive": True,
        "description": "Grin's memory-hard Cuckoo Cycle"
    },
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_coins() -> List[str]:
    """Gibt alle verfügbaren Coins zurück"""
    return list(COIN_CONFIGS.keys())


def get_enabled_coins() -> List[str]:
    """Gibt alle aktivierten Coins zurück"""
    return [coin for coin, config in COIN_CONFIGS.items() if config.get('enabled', False)]


def get_coin_config(coin: str) -> Optional[Dict]:
    """Gibt die Konfiguration für einen Coin zurück"""
    return COIN_CONFIGS.get(coin.upper())


def get_pools_for_coin(coin: str) -> List[Dict]:
    """Gibt alle Pools für einen Coin zurück"""
    config = COIN_CONFIGS.get(coin.upper())
    if config:
        return config.get('pools', [])
    return []


def get_algorithm_for_coin(coin: str) -> Optional[str]:
    """Gibt den Algorithmus für einen Coin zurück"""
    config = COIN_CONFIGS.get(coin.upper())
    if config:
        return config.get('algorithm')
    return None


def get_coins_by_algorithm(algorithm: str) -> List[str]:
    """Gibt alle Coins für einen Algorithmus zurück"""
    return [coin for coin, config in COIN_CONFIGS.items() 
            if config.get('algorithm', '').lower() == algorithm.lower()]


def get_miners_for_coin(coin: str) -> List[str]:
    """Gibt alle Miner für einen Coin zurück"""
    config = COIN_CONFIGS.get(coin.upper())
    if config:
        return config.get('miners', [])
    return []


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("\n=== ALLE COINS ===")
    for coin, config in COIN_CONFIGS.items():
        pools = len(config.get('pools', []))
        miners = len(config.get('miners', []))
        algo = config.get('algorithm', '?')
        print(f"  {coin:10} | {config['name']:20} | {algo:15} | {pools} Pools | {miners} Miner")
    
    print(f"\n=== STATISTIK ===")
    print(f"  Coins: {len(COIN_CONFIGS)}")
    print(f"  Algorithmen: {len(ALGORITHM_CONFIGS)}")
    total_pools = sum(len(c.get('pools', [])) for c in COIN_CONFIGS.values())
    print(f"  Pools gesamt: {total_pools}")
