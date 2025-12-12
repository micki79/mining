#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-GPU Profit Calculator - Individuelle Profit-Berechnung pro GPU
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Erkennt jede GPU separat (RTX 3090, 3080, 3070, etc.)
- Berechnet Profit PRO GPU basierend auf GPU-spezifischen Hashrates
- Jede GPU mined den für SIE profitabelsten Coin
- Kombinierter Gesamt-Profit über alle GPUs
- Unterstützt 1-9 GPUs gleichzeitig
- Laptop vs Desktop GPU Unterscheidung

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import json
import logging
import time
import threading
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


# ============================================================================
# GPU HASHRATE DATABASE - Echte Hashrates pro GPU-Modell und Algorithmus
# ============================================================================

GPU_HASHRATES = {
    # ========== NVIDIA RTX 40 Series ==========
    "RTX 4090": {
        "kawpow": 75.0,        # MH/s - RVN
        "autolykos2": 380.0,   # MH/s - ERG
        "etchash": 130.0,      # MH/s - ETC
        "ethash": 130.0,       # MH/s
        "cuckatoo32": 4.5,     # G/s - GRIN
        "kheavyhash": 3.2,     # GH/s - KAS
        "blake3": 5.5,         # GH/s - ALPH, IRON
        "equihash125": 95.0,   # Sol/s - FLUX
        "beamhashiii": 70.0,   # Sol/s - BEAM
        "octopus": 85.0,       # MH/s - CFX
        "nexapow": 320.0,      # MH/s - NEXA
        "dynexsolve": 800.0,   # H/s - DNX
        "firopow": 70.0,       # MH/s - FIRO
        "power_tdp": 450,      # Watt TDP
    },
    "RTX 4080": {
        "kawpow": 58.0,
        "autolykos2": 290.0,
        "etchash": 98.0,
        "ethash": 98.0,
        "cuckatoo32": 3.2,
        "kheavyhash": 2.4,
        "blake3": 4.2,
        "equihash125": 75.0,
        "beamhashiii": 55.0,
        "octopus": 68.0,
        "nexapow": 250.0,
        "dynexsolve": 620.0,
        "firopow": 55.0,
        "power_tdp": 320,
    },
    "RTX 4070 Ti": {
        "kawpow": 48.0,
        "autolykos2": 240.0,
        "etchash": 82.0,
        "ethash": 82.0,
        "cuckatoo32": 2.6,
        "kheavyhash": 2.0,
        "blake3": 3.5,
        "equihash125": 62.0,
        "beamhashiii": 48.0,
        "octopus": 55.0,
        "nexapow": 200.0,
        "dynexsolve": 520.0,
        "firopow": 45.0,
        "power_tdp": 285,
    },
    "RTX 4070": {
        "kawpow": 38.0,
        "autolykos2": 195.0,
        "etchash": 65.0,
        "ethash": 65.0,
        "cuckatoo32": 2.0,
        "kheavyhash": 1.6,
        "blake3": 2.8,
        "equihash125": 50.0,
        "beamhashiii": 38.0,
        "octopus": 45.0,
        "nexapow": 160.0,
        "dynexsolve": 420.0,
        "firopow": 36.0,
        "power_tdp": 200,
    },
    "RTX 4060 Ti": {
        "kawpow": 32.0,
        "autolykos2": 165.0,
        "etchash": 55.0,
        "ethash": 55.0,
        "cuckatoo32": 1.7,
        "kheavyhash": 1.3,
        "blake3": 2.3,
        "equihash125": 42.0,
        "beamhashiii": 32.0,
        "octopus": 38.0,
        "nexapow": 135.0,
        "dynexsolve": 350.0,
        "firopow": 30.0,
        "power_tdp": 160,
    },
    "RTX 4060": {
        "kawpow": 26.0,
        "autolykos2": 135.0,
        "etchash": 45.0,
        "ethash": 45.0,
        "cuckatoo32": 1.4,
        "kheavyhash": 1.1,
        "blake3": 1.9,
        "equihash125": 35.0,
        "beamhashiii": 26.0,
        "octopus": 32.0,
        "nexapow": 110.0,
        "dynexsolve": 290.0,
        "firopow": 25.0,
        "power_tdp": 115,
    },
    
    # ========== NVIDIA RTX 30 Series Desktop ==========
    "RTX 3090 Ti": {
        "kawpow": 62.0,
        "autolykos2": 320.0,
        "etchash": 125.0,
        "ethash": 125.0,
        "cuckatoo32": 3.0,
        "kheavyhash": 2.3,
        "blake3": 4.0,
        "equihash125": 80.0,
        "beamhashiii": 60.0,
        "octopus": 72.0,
        "nexapow": 270.0,
        "dynexsolve": 680.0,
        "firopow": 58.0,
        "power_tdp": 450,
    },
    "RTX 3090": {
        "kawpow": 60.0,
        "autolykos2": 300.0,
        "etchash": 120.0,
        "ethash": 120.0,
        "cuckatoo32": 2.8,
        "kheavyhash": 2.2,
        "blake3": 3.8,
        "equihash125": 78.0,
        "beamhashiii": 58.0,
        "octopus": 70.0,
        "nexapow": 260.0,
        "dynexsolve": 650.0,
        "firopow": 56.0,
        "power_tdp": 350,
    },
    "RTX 3080 Ti": {
        "kawpow": 55.0,
        "autolykos2": 280.0,
        "etchash": 110.0,
        "ethash": 110.0,
        "cuckatoo32": 2.5,
        "kheavyhash": 2.0,
        "blake3": 3.5,
        "equihash125": 72.0,
        "beamhashiii": 52.0,
        "octopus": 65.0,
        "nexapow": 240.0,
        "dynexsolve": 600.0,
        "firopow": 52.0,
        "power_tdp": 350,
    },
    "RTX 3080": {
        "kawpow": 50.0,
        "autolykos2": 260.0,
        "etchash": 98.0,
        "ethash": 98.0,
        "cuckatoo32": 2.2,
        "kheavyhash": 1.8,
        "blake3": 3.2,
        "equihash125": 65.0,
        "beamhashiii": 48.0,
        "octopus": 58.0,
        "nexapow": 220.0,
        "dynexsolve": 550.0,
        "firopow": 48.0,
        "power_tdp": 320,
    },
    "RTX 3070 Ti": {
        "kawpow": 35.0,
        "autolykos2": 190.0,
        "etchash": 68.0,
        "ethash": 68.0,
        "cuckatoo32": 1.7,
        "kheavyhash": 1.4,
        "blake3": 2.4,
        "equihash125": 52.0,
        "beamhashiii": 38.0,
        "octopus": 46.0,
        "nexapow": 175.0,
        "dynexsolve": 440.0,
        "firopow": 38.0,
        "power_tdp": 290,
    },
    "RTX 3070": {
        "kawpow": 30.0,
        "autolykos2": 170.0,
        "etchash": 62.0,
        "ethash": 62.0,
        "cuckatoo32": 1.5,
        "kheavyhash": 1.2,
        "blake3": 2.1,
        "equihash125": 48.0,
        "beamhashiii": 35.0,
        "octopus": 42.0,
        "nexapow": 155.0,
        "dynexsolve": 400.0,
        "firopow": 35.0,
        "power_tdp": 220,
    },
    "RTX 3060 Ti": {
        "kawpow": 28.0,
        "autolykos2": 155.0,
        "etchash": 60.0,
        "ethash": 60.0,
        "cuckatoo32": 1.4,
        "kheavyhash": 1.1,
        "blake3": 1.9,
        "equihash125": 45.0,
        "beamhashiii": 32.0,
        "octopus": 38.0,
        "nexapow": 140.0,
        "dynexsolve": 360.0,
        "firopow": 32.0,
        "power_tdp": 200,
    },
    "RTX 3060": {
        "kawpow": 24.0,
        "autolykos2": 125.0,
        "etchash": 48.0,
        "ethash": 48.0,
        "cuckatoo32": 1.2,
        "kheavyhash": 0.9,
        "blake3": 1.6,
        "equihash125": 38.0,
        "beamhashiii": 28.0,
        "octopus": 32.0,
        "nexapow": 115.0,
        "dynexsolve": 300.0,
        "firopow": 28.0,
        "power_tdp": 170,
    },
    
    # ========== NVIDIA RTX 30 Series Laptop ==========
    "RTX 3080 Laptop": {
        "kawpow": 42.0,
        "autolykos2": 200.0,
        "etchash": 82.0,
        "ethash": 82.0,
        "cuckatoo32": 1.8,
        "kheavyhash": 1.5,
        "blake3": 2.6,
        "equihash125": 52.0,
        "beamhashiii": 38.0,
        "octopus": 48.0,
        "nexapow": 180.0,
        "dynexsolve": 450.0,
        "firopow": 40.0,
        "power_tdp": 150,  # Laptop TDP
    },
    "RTX 3070 Laptop": {
        "kawpow": 28.0,
        "autolykos2": 145.0,
        "etchash": 55.0,
        "ethash": 55.0,
        "cuckatoo32": 1.3,
        "kheavyhash": 1.0,
        "blake3": 1.8,
        "equihash125": 42.0,
        "beamhashiii": 30.0,
        "octopus": 36.0,
        "nexapow": 135.0,
        "dynexsolve": 340.0,
        "firopow": 32.0,
        "power_tdp": 125,
    },
    "RTX 3060 Laptop": {
        "kawpow": 22.0,
        "autolykos2": 110.0,
        "etchash": 42.0,
        "ethash": 42.0,
        "cuckatoo32": 1.0,
        "kheavyhash": 0.8,
        "blake3": 1.4,
        "equihash125": 32.0,
        "beamhashiii": 24.0,
        "octopus": 28.0,
        "nexapow": 100.0,
        "dynexsolve": 260.0,
        "firopow": 26.0,
        "power_tdp": 115,
    },
    
    # ========== NVIDIA RTX 20 Series ==========
    "RTX 2080 Ti": {
        "kawpow": 38.0,
        "autolykos2": 180.0,
        "etchash": 58.0,
        "ethash": 58.0,
        "cuckatoo32": 1.6,
        "kheavyhash": 1.3,
        "blake3": 2.2,
        "equihash125": 55.0,
        "beamhashiii": 40.0,
        "octopus": 48.0,
        "nexapow": 165.0,
        "dynexsolve": 420.0,
        "firopow": 36.0,
        "power_tdp": 250,
    },
    "RTX 2080 Super": {
        "kawpow": 32.0,
        "autolykos2": 150.0,
        "etchash": 48.0,
        "ethash": 48.0,
        "cuckatoo32": 1.4,
        "kheavyhash": 1.1,
        "blake3": 1.9,
        "equihash125": 48.0,
        "beamhashiii": 35.0,
        "octopus": 42.0,
        "nexapow": 140.0,
        "dynexsolve": 360.0,
        "firopow": 30.0,
        "power_tdp": 250,
    },
    "RTX 2080": {
        "kawpow": 28.0,
        "autolykos2": 135.0,
        "etchash": 44.0,
        "ethash": 44.0,
        "cuckatoo32": 1.2,
        "kheavyhash": 1.0,
        "blake3": 1.7,
        "equihash125": 45.0,
        "beamhashiii": 32.0,
        "octopus": 38.0,
        "nexapow": 125.0,
        "dynexsolve": 320.0,
        "firopow": 27.0,
        "power_tdp": 215,
    },
    "RTX 2070 Super": {
        "kawpow": 26.0,
        "autolykos2": 125.0,
        "etchash": 42.0,
        "ethash": 42.0,
        "cuckatoo32": 1.1,
        "kheavyhash": 0.9,
        "blake3": 1.5,
        "equihash125": 42.0,
        "beamhashiii": 30.0,
        "octopus": 35.0,
        "nexapow": 115.0,
        "dynexsolve": 300.0,
        "firopow": 25.0,
        "power_tdp": 215,
    },
    "RTX 2070": {
        "kawpow": 24.0,
        "autolykos2": 115.0,
        "etchash": 40.0,
        "ethash": 40.0,
        "cuckatoo32": 1.0,
        "kheavyhash": 0.8,
        "blake3": 1.4,
        "equihash125": 40.0,
        "beamhashiii": 28.0,
        "octopus": 32.0,
        "nexapow": 105.0,
        "dynexsolve": 280.0,
        "firopow": 23.0,
        "power_tdp": 175,
    },
    "RTX 2060 Super": {
        "kawpow": 22.0,
        "autolykos2": 105.0,
        "etchash": 38.0,
        "ethash": 38.0,
        "cuckatoo32": 0.9,
        "kheavyhash": 0.7,
        "blake3": 1.2,
        "equihash125": 38.0,
        "beamhashiii": 26.0,
        "octopus": 30.0,
        "nexapow": 95.0,
        "dynexsolve": 260.0,
        "firopow": 21.0,
        "power_tdp": 175,
    },
    "RTX 2060": {
        "kawpow": 20.0,
        "autolykos2": 95.0,
        "etchash": 32.0,
        "ethash": 32.0,
        "cuckatoo32": 0.8,
        "kheavyhash": 0.6,
        "blake3": 1.1,
        "equihash125": 35.0,
        "beamhashiii": 24.0,
        "octopus": 28.0,
        "nexapow": 85.0,
        "dynexsolve": 240.0,
        "firopow": 19.0,
        "power_tdp": 160,
    },
    
    # ========== NVIDIA GTX 16 Series ==========
    "GTX 1660 Ti": {
        "kawpow": 15.0,
        "autolykos2": 75.0,
        "etchash": 30.0,
        "ethash": 30.0,
        "cuckatoo32": 0.6,
        "kheavyhash": 0.5,
        "blake3": 0.9,
        "equihash125": 28.0,
        "beamhashiii": 18.0,
        "octopus": 22.0,
        "nexapow": 65.0,
        "dynexsolve": 180.0,
        "firopow": 14.0,
        "power_tdp": 120,
    },
    "GTX 1660 Super": {
        "kawpow": 14.0,
        "autolykos2": 70.0,
        "etchash": 31.0,
        "ethash": 31.0,
        "cuckatoo32": 0.55,
        "kheavyhash": 0.45,
        "blake3": 0.85,
        "equihash125": 26.0,
        "beamhashiii": 17.0,
        "octopus": 20.0,
        "nexapow": 60.0,
        "dynexsolve": 170.0,
        "firopow": 13.0,
        "power_tdp": 125,
    },
    "GTX 1660": {
        "kawpow": 12.0,
        "autolykos2": 60.0,
        "etchash": 25.0,
        "ethash": 25.0,
        "cuckatoo32": 0.5,
        "kheavyhash": 0.4,
        "blake3": 0.75,
        "equihash125": 24.0,
        "beamhashiii": 15.0,
        "octopus": 18.0,
        "nexapow": 52.0,
        "dynexsolve": 150.0,
        "firopow": 11.0,
        "power_tdp": 120,
    },
    
    # ========== AMD RX 7000 Series ==========
    "RX 7900 XTX": {
        "kawpow": 58.0,
        "autolykos2": 280.0,
        "etchash": 95.0,
        "ethash": 95.0,
        "cuckatoo32": 0.0,  # AMD unterstützt Cuckatoo nicht gut
        "kheavyhash": 2.0,
        "blake3": 3.5,
        "equihash125": 70.0,
        "beamhashiii": 52.0,
        "octopus": 62.0,
        "nexapow": 200.0,
        "dynexsolve": 0.0,  # DNX nicht AMD-optimiert
        "firopow": 52.0,
        "power_tdp": 355,
    },
    "RX 7900 XT": {
        "kawpow": 50.0,
        "autolykos2": 240.0,
        "etchash": 82.0,
        "ethash": 82.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 1.7,
        "blake3": 3.0,
        "equihash125": 60.0,
        "beamhashiii": 45.0,
        "octopus": 55.0,
        "nexapow": 175.0,
        "dynexsolve": 0.0,
        "firopow": 45.0,
        "power_tdp": 315,
    },
    
    # ========== AMD RX 6000 Series ==========
    "RX 6950 XT": {
        "kawpow": 35.0,
        "autolykos2": 160.0,
        "etchash": 62.0,
        "ethash": 62.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 1.3,
        "blake3": 2.2,
        "equihash125": 48.0,
        "beamhashiii": 35.0,
        "octopus": 45.0,
        "nexapow": 140.0,
        "dynexsolve": 0.0,
        "firopow": 34.0,
        "power_tdp": 335,
    },
    "RX 6900 XT": {
        "kawpow": 32.0,
        "autolykos2": 145.0,
        "etchash": 58.0,
        "ethash": 58.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 1.2,
        "blake3": 2.0,
        "equihash125": 45.0,
        "beamhashiii": 32.0,
        "octopus": 42.0,
        "nexapow": 130.0,
        "dynexsolve": 0.0,
        "firopow": 31.0,
        "power_tdp": 300,
    },
    "RX 6800 XT": {
        "kawpow": 28.0,
        "autolykos2": 130.0,
        "etchash": 52.0,
        "ethash": 52.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 1.0,
        "blake3": 1.8,
        "equihash125": 40.0,
        "beamhashiii": 28.0,
        "octopus": 38.0,
        "nexapow": 115.0,
        "dynexsolve": 0.0,
        "firopow": 27.0,
        "power_tdp": 300,
    },
    "RX 6800": {
        "kawpow": 25.0,
        "autolykos2": 115.0,
        "etchash": 48.0,
        "ethash": 48.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 0.9,
        "blake3": 1.6,
        "equihash125": 36.0,
        "beamhashiii": 25.0,
        "octopus": 34.0,
        "nexapow": 100.0,
        "dynexsolve": 0.0,
        "firopow": 24.0,
        "power_tdp": 250,
    },
    "RX 6700 XT": {
        "kawpow": 20.0,
        "autolykos2": 90.0,
        "etchash": 38.0,
        "ethash": 38.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 0.7,
        "blake3": 1.3,
        "equihash125": 30.0,
        "beamhashiii": 20.0,
        "octopus": 28.0,
        "nexapow": 80.0,
        "dynexsolve": 0.0,
        "firopow": 19.0,
        "power_tdp": 230,
    },
    "RX 6600 XT": {
        "kawpow": 15.0,
        "autolykos2": 68.0,
        "etchash": 30.0,
        "ethash": 30.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 0.5,
        "blake3": 1.0,
        "equihash125": 24.0,
        "beamhashiii": 16.0,
        "octopus": 22.0,
        "nexapow": 60.0,
        "dynexsolve": 0.0,
        "firopow": 14.0,
        "power_tdp": 160,
    },
    "RX 6600": {
        "kawpow": 13.0,
        "autolykos2": 58.0,
        "etchash": 28.0,
        "ethash": 28.0,
        "cuckatoo32": 0.0,
        "kheavyhash": 0.45,
        "blake3": 0.9,
        "equihash125": 22.0,
        "beamhashiii": 14.0,
        "octopus": 20.0,
        "nexapow": 52.0,
        "dynexsolve": 0.0,
        "firopow": 12.0,
        "power_tdp": 132,
    },
}


# Coin zu Algorithmus Mapping
COIN_ALGORITHMS = {
    "RVN": "kawpow",
    "ERG": "autolykos2",
    "ETC": "etchash",
    "FLUX": "equihash125",
    "KAS": "kheavyhash",
    "ALPH": "blake3",
    "IRON": "blake3",
    "GRIN": "cuckatoo32",
    "BEAM": "beamhashiii",
    "CFX": "octopus",
    "NEXA": "nexapow",
    "DNX": "dynexsolve",
    "FIRO": "firopow",
    "ZEC": "equihash",
    "CLORE": "kawpow",
    "AIPG": "kawpow",
    "ZEPH": "randomx",  # CPU
    "XMR": "randomx",   # CPU
}


@dataclass
class GPUProfitInfo:
    """Profit-Information für eine einzelne GPU"""
    gpu_index: int
    gpu_name: str
    gpu_model: str  # Erkanntes Modell (z.B. "RTX 3080")
    
    # Bester Coin für diese GPU
    best_coin: str = ""
    best_algorithm: str = ""
    best_profit_usd: float = 0.0
    best_hashrate: float = 0.0
    best_hashrate_unit: str = "MH/s"
    
    # Pool Info
    best_pool_url: str = ""
    best_pool_name: str = ""
    best_miner: str = ""
    
    # OC Settings
    oc_core: int = 0
    oc_memory: int = 0
    oc_power_limit: int = 100
    
    # Status
    is_mining: bool = False
    current_hashrate: float = 0.0
    current_profit_usd: float = 0.0
    
    # Alle Profit-Optionen für diese GPU
    all_profits: Dict[str, float] = field(default_factory=dict)


@dataclass
class MultiGPUProfitResult:
    """Gesamt-Ergebnis für alle GPUs"""
    timestamp: datetime
    gpu_count: int
    total_profit_usd: float
    gpus: List[GPUProfitInfo]
    
    # Kombinierte Stats
    total_power_watts: float = 0.0
    efficiency: float = 0.0  # $/Watt


class MultiGPUProfitCalculator:
    """
    Berechnet den optimalen Coin für JEDE GPU individuell
    
    Features:
    - Erkennt GPU-Modell automatisch
    - Berechnet Profit basierend auf GPU-spezifischen Hashrates
    - Holt aktuelle Preise von WhatToMine/CoinGecko
    - Wählt besten Coin pro GPU
    """
    
    # WhatToMine API
    WHATTOMINE_URL = "https://whattomine.com/coins.json"
    
    # Pool Konfiguration pro Coin
    POOLS = {
        "RVN": {"name": "2Miners", "url": "stratum+tcp://rvn.2miners.com:6060", "miner": "T-Rex"},
        "ERG": {"name": "2Miners", "url": "stratum+tcp://erg.2miners.com:8888", "miner": "T-Rex"},
        "ETC": {"name": "2Miners", "url": "stratum+tcp://etc.2miners.com:1010", "miner": "T-Rex"},
        "FLUX": {"name": "2Miners", "url": "stratum+tcp://flux.2miners.com:9090", "miner": "lolMiner"},
        "KAS": {"name": "2Miners", "url": "stratum+tcp://kas.2miners.com:2020", "miner": "lolMiner"},
        "ALPH": {"name": "2Miners", "url": "stratum+tcp://alph.2miners.com:2020", "miner": "lolMiner"},
        "IRON": {"name": "HeroMiners", "url": "stratum+tcp://de.ironfish.herominers.com:1145", "miner": "lolMiner"},
        "GRIN": {"name": "2Miners", "url": "stratum+tcp://grin.2miners.com:3030", "miner": "lolMiner"},
        "BEAM": {"name": "2Miners", "url": "stratum+tcp://beam.2miners.com:5252", "miner": "lolMiner"},
        "CFX": {"name": "2Miners", "url": "stratum+tcp://cfx.2miners.com:4040", "miner": "T-Rex"},
        "NEXA": {"name": "2Miners", "url": "stratum+tcp://nexa.2miners.com:2020", "miner": "lolMiner"},
        "DNX": {"name": "HeroMiners", "url": "stratum+tcp://de.dynex.herominers.com:1120", "miner": "DynexSolve"},
        "FIRO": {"name": "2Miners", "url": "stratum+tcp://firo.2miners.com:8181", "miner": "T-Rex"},
        "CLORE": {"name": "Unmineable", "url": "stratum+tcp://rx.unmineable.com:3333", "miner": "T-Rex"},
    }
    
    def __init__(self):
        self._coin_prices: Dict[str, float] = {}
        self._coin_btc_revenue: Dict[str, float] = {}
        self._last_price_update = 0
        self._price_cache_ttl = 180  # 3 Minuten
        self._lock = threading.Lock()
    
    def match_gpu_model(self, gpu_name: str) -> str:
        """
        Matched GPU-Namen zu bekanntem Modell
        
        Args:
            gpu_name: Voller GPU Name (z.B. "NVIDIA GeForce RTX 3080 Laptop GPU")
            
        Returns:
            Erkanntes Modell (z.B. "RTX 3080 Laptop") oder "Unknown"
        """
        gpu_upper = gpu_name.upper()
        
        # Laptop-Erkennung (muss vor Desktop kommen!)
        laptop_keywords = ["LAPTOP", "MOBILE", "MAX-Q", "MAX Q"]
        is_laptop = any(kw in gpu_upper for kw in laptop_keywords)
        
        # RTX 40 Series
        if "4090" in gpu_upper:
            return "RTX 4090"
        if "4080" in gpu_upper:
            return "RTX 4080"
        if "4070 TI" in gpu_upper or "4070TI" in gpu_upper:
            return "RTX 4070 Ti"
        if "4070" in gpu_upper:
            return "RTX 4070"
        if "4060 TI" in gpu_upper or "4060TI" in gpu_upper:
            return "RTX 4060 Ti"
        if "4060" in gpu_upper:
            return "RTX 4060"
        
        # RTX 30 Series
        if "3090 TI" in gpu_upper or "3090TI" in gpu_upper:
            return "RTX 3090 Ti"
        if "3090" in gpu_upper:
            return "RTX 3090"
        if "3080 TI" in gpu_upper or "3080TI" in gpu_upper:
            return "RTX 3080 Ti"
        if "3080" in gpu_upper:
            return "RTX 3080 Laptop" if is_laptop else "RTX 3080"
        if "3070 TI" in gpu_upper or "3070TI" in gpu_upper:
            return "RTX 3070 Ti"
        if "3070" in gpu_upper:
            return "RTX 3070 Laptop" if is_laptop else "RTX 3070"
        if "3060 TI" in gpu_upper or "3060TI" in gpu_upper:
            return "RTX 3060 Ti"
        if "3060" in gpu_upper:
            return "RTX 3060 Laptop" if is_laptop else "RTX 3060"
        
        # RTX 20 Series
        if "2080 TI" in gpu_upper or "2080TI" in gpu_upper:
            return "RTX 2080 Ti"
        if "2080 SUPER" in gpu_upper:
            return "RTX 2080 Super"
        if "2080" in gpu_upper:
            return "RTX 2080"
        if "2070 SUPER" in gpu_upper:
            return "RTX 2070 Super"
        if "2070" in gpu_upper:
            return "RTX 2070"
        if "2060 SUPER" in gpu_upper:
            return "RTX 2060 Super"
        if "2060" in gpu_upper:
            return "RTX 2060"
        
        # GTX 16 Series
        if "1660 TI" in gpu_upper or "1660TI" in gpu_upper:
            return "GTX 1660 Ti"
        if "1660 SUPER" in gpu_upper:
            return "GTX 1660 Super"
        if "1660" in gpu_upper:
            return "GTX 1660"
        
        # AMD RX 7000
        if "7900 XTX" in gpu_upper:
            return "RX 7900 XTX"
        if "7900 XT" in gpu_upper:
            return "RX 7900 XT"
        
        # AMD RX 6000
        if "6950 XT" in gpu_upper:
            return "RX 6950 XT"
        if "6900 XT" in gpu_upper:
            return "RX 6900 XT"
        if "6800 XT" in gpu_upper:
            return "RX 6800 XT"
        if "6800" in gpu_upper:
            return "RX 6800"
        if "6700 XT" in gpu_upper:
            return "RX 6700 XT"
        if "6600 XT" in gpu_upper:
            return "RX 6600 XT"
        if "6600" in gpu_upper:
            return "RX 6600"
        
        return "Unknown"
    
    def get_gpu_hashrate(self, gpu_model: str, algorithm: str) -> float:
        """
        Gibt die Hashrate für ein GPU-Modell und Algorithmus zurück
        
        Args:
            gpu_model: Erkanntes GPU-Modell (z.B. "RTX 3080")
            algorithm: Algorithmus (z.B. "kawpow")
            
        Returns:
            Hashrate oder 0.0 wenn nicht bekannt
        """
        if gpu_model not in GPU_HASHRATES:
            logger.warning(f"GPU-Modell nicht in DB: {gpu_model}")
            return 0.0
        
        return GPU_HASHRATES[gpu_model].get(algorithm, 0.0)
    
    def fetch_coin_prices(self) -> bool:
        """Holt aktuelle Coin-Preise von WhatToMine"""
        if not requests:
            return False
        
        # Cache prüfen
        if time.time() - self._last_price_update < self._price_cache_ttl:
            return True
        
        try:
            response = requests.get(self.WHATTOMINE_URL, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"WhatToMine API Fehler: {response.status_code}")
                return False
            
            data = response.json()
            coins = data.get("coins", {})
            
            with self._lock:
                for coin_name, coin_data in coins.items():
                    tag = coin_data.get("tag", "")
                    if tag:
                        self._coin_prices[tag] = coin_data.get("exchange_rate", 0)
                        # BTC Revenue pro 1 Unit Hashrate
                        self._coin_btc_revenue[tag] = coin_data.get("btc_revenue", 0)
            
            self._last_price_update = time.time()
            logger.info(f"✅ {len(self._coin_prices)} Coin-Preise aktualisiert")
            return True
            
        except Exception as e:
            logger.error(f"Coin-Preise abrufen fehlgeschlagen: {e}")
            return False
    
    def calculate_profit_for_gpu(self, gpu_model: str, coin: str) -> float:
        """
        Berechnet den täglichen Profit für eine GPU und einen Coin
        
        Args:
            gpu_model: GPU-Modell (z.B. "RTX 3080")
            coin: Coin-Symbol (z.B. "RVN")
            
        Returns:
            Täglicher Profit in USD
        """
        algorithm = COIN_ALGORITHMS.get(coin, "")
        if not algorithm:
            return 0.0
        
        # CPU-Algorithmen überspringen für GPU
        if algorithm in ["randomx", "ghostrider"]:
            return 0.0
        
        hashrate = self.get_gpu_hashrate(gpu_model, algorithm)
        if hashrate <= 0:
            return 0.0
        
        # BTC Revenue für Standard-Hashrate (1 MH/s, 1 GH/s, etc.)
        btc_revenue = self._coin_btc_revenue.get(coin, 0)
        if btc_revenue <= 0:
            return 0.0
        
        # Skalierung basierend auf unserer Hashrate
        # WhatToMine gibt Revenue für Standard-Einheiten (meist 1 MH/s)
        # Wir müssen basierend auf unserer echten Hashrate skalieren
        
        # BTC Preis
        btc_price = self._coin_prices.get("BTC", 40000)
        
        # Profit berechnen
        daily_btc = btc_revenue * hashrate
        daily_usd = daily_btc * btc_price
        
        return daily_usd
    
    def calculate_best_coin_for_gpu(self, gpu_index: int, gpu_name: str) -> GPUProfitInfo:
        """
        Berechnet den besten Coin für eine spezifische GPU
        
        Args:
            gpu_index: GPU Index (0, 1, 2, ...)
            gpu_name: Voller GPU-Name
            
        Returns:
            GPUProfitInfo mit bestem Coin und allen Optionen
        """
        # GPU-Modell erkennen
        gpu_model = self.match_gpu_model(gpu_name)
        
        result = GPUProfitInfo(
            gpu_index=gpu_index,
            gpu_name=gpu_name,
            gpu_model=gpu_model
        )
        
        if gpu_model == "Unknown":
            logger.warning(f"GPU {gpu_index}: Unbekanntes Modell '{gpu_name}'")
            return result
        
        # Preise aktualisieren wenn nötig
        self.fetch_coin_prices()
        
        # Profit für jeden Coin berechnen
        best_profit = 0.0
        best_coin = ""
        
        for coin, algorithm in COIN_ALGORITHMS.items():
            # CPU-Coins überspringen
            if algorithm in ["randomx", "ghostrider"]:
                continue
            
            profit = self.calculate_profit_for_gpu(gpu_model, coin)
            result.all_profits[coin] = profit
            
            if profit > best_profit:
                best_profit = profit
                best_coin = coin
        
        if best_coin:
            algorithm = COIN_ALGORITHMS[best_coin]
            hashrate = self.get_gpu_hashrate(gpu_model, algorithm)
            pool_info = self.POOLS.get(best_coin, {})
            
            result.best_coin = best_coin
            result.best_algorithm = algorithm
            result.best_profit_usd = best_profit
            result.best_hashrate = hashrate
            result.best_hashrate_unit = self._get_hashrate_unit(algorithm)
            result.best_pool_url = pool_info.get("url", "")
            result.best_pool_name = pool_info.get("name", "")
            result.best_miner = pool_info.get("miner", "T-Rex")
            
            logger.info(f"GPU {gpu_index} ({gpu_model}): Bester Coin = {best_coin} (${best_profit:.2f}/Tag)")
        
        return result
    
    def _get_hashrate_unit(self, algorithm: str) -> str:
        """Gibt die Hashrate-Einheit für einen Algorithmus zurück"""
        units = {
            "kawpow": "MH/s",
            "autolykos2": "MH/s",
            "etchash": "MH/s",
            "ethash": "MH/s",
            "cuckatoo32": "G/s",
            "kheavyhash": "GH/s",
            "blake3": "GH/s",
            "equihash125": "Sol/s",
            "equihash": "Sol/s",
            "beamhashiii": "Sol/s",
            "octopus": "MH/s",
            "nexapow": "MH/s",
            "dynexsolve": "H/s",
            "firopow": "MH/s",
        }
        return units.get(algorithm, "H/s")
    
    def calculate_all_gpus(self, gpus: List[Tuple[int, str]]) -> MultiGPUProfitResult:
        """
        Berechnet beste Coins für ALLE GPUs
        
        Args:
            gpus: Liste von (gpu_index, gpu_name) Tupeln
            
        Returns:
            MultiGPUProfitResult mit allen GPU-Infos und Gesamt-Profit
        """
        gpu_results = []
        total_profit = 0.0
        total_power = 0.0
        
        for gpu_index, gpu_name in gpus:
            gpu_info = self.calculate_best_coin_for_gpu(gpu_index, gpu_name)
            gpu_results.append(gpu_info)
            total_profit += gpu_info.best_profit_usd
            
            # Power-Verbrauch schätzen
            if gpu_info.gpu_model in GPU_HASHRATES:
                tdp = GPU_HASHRATES[gpu_info.gpu_model].get("power_tdp", 200)
                # Mining typischerweise bei 70-80% TDP
                total_power += tdp * 0.75
        
        result = MultiGPUProfitResult(
            timestamp=datetime.now(),
            gpu_count=len(gpus),
            total_profit_usd=total_profit,
            gpus=gpu_results,
            total_power_watts=total_power,
            efficiency=total_profit / (total_power / 1000 * 24) if total_power > 0 else 0  # $/kWh
        )
        
        logger.info(f"📊 Multi-GPU Profit: {len(gpus)} GPUs, ${total_profit:.2f}/Tag, {total_power:.0f}W")
        
        return result
    
    def get_top_coins_for_gpu(self, gpu_model: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Gibt die Top N profitabelsten Coins für ein GPU-Modell zurück
        
        Args:
            gpu_model: GPU-Modell (z.B. "RTX 3080")
            top_n: Anzahl der Coins
            
        Returns:
            Liste von (coin, profit_usd) Tupeln, sortiert nach Profit
        """
        self.fetch_coin_prices()
        
        profits = []
        for coin, algorithm in COIN_ALGORITHMS.items():
            if algorithm in ["randomx", "ghostrider"]:
                continue
            profit = self.calculate_profit_for_gpu(gpu_model, coin)
            if profit > 0:
                profits.append((coin, profit))
        
        profits.sort(key=lambda x: x[1], reverse=True)
        return profits[:top_n]


# ============================================================================
# SINGLETON
# ============================================================================

_calculator: Optional[MultiGPUProfitCalculator] = None

def get_multi_gpu_calculator() -> MultiGPUProfitCalculator:
    """Gibt Singleton-Instanz zurück"""
    global _calculator
    if _calculator is None:
        _calculator = MultiGPUProfitCalculator()
    return _calculator


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 70)
    print("🎮 Multi-GPU Profit Calculator Test")
    print("=" * 70)
    
    calc = get_multi_gpu_calculator()
    
    # Test GPU-Erkennung
    test_gpus = [
        "NVIDIA GeForce RTX 3080 Laptop GPU",
        "NVIDIA GeForce RTX 3070",
        "NVIDIA GeForce RTX 4090",
        "AMD Radeon RX 6800 XT",
    ]
    
    print("\n📊 GPU-Modell Erkennung:")
    for gpu in test_gpus:
        model = calc.match_gpu_model(gpu)
        print(f"  {gpu} → {model}")
    
    # Test Profit-Berechnung
    print("\n💰 Top Coins pro GPU:")
    for gpu in ["RTX 3080", "RTX 3070", "RTX 3080 Laptop"]:
        print(f"\n  {gpu}:")
        top = calc.get_top_coins_for_gpu(gpu, top_n=5)
        for coin, profit in top:
            print(f"    {coin}: ${profit:.2f}/Tag")
    
    # Test Multi-GPU
    print("\n🎮 Multi-GPU Berechnung:")
    gpus = [
        (0, "NVIDIA GeForce RTX 3080"),
        (1, "NVIDIA GeForce RTX 3070"),
    ]
    result = calc.calculate_all_gpus(gpus)
    print(f"  Gesamt-Profit: ${result.total_profit_usd:.2f}/Tag")
    print(f"  Gesamt-Power: {result.total_power_watts:.0f}W")
    for gpu in result.gpus:
        print(f"  GPU {gpu.gpu_index} ({gpu.gpu_model}): {gpu.best_coin} = ${gpu.best_profit_usd:.2f}/Tag")
    
    print("\n" + "=" * 70)
    print("✅ Test abgeschlossen!")
    print("=" * 70)
