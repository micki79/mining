#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hashrate.no API Client
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Automatisches Abrufen von Overclock-Settings pro GPU/Coin
- Benchmark-Daten für Hashrate/Power Schätzungen
- Caching für API-Rate-Limiting
- Fallback auf lokale Standard-Profile
"""

import json
import time
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None
    print("⚠️ requests nicht installiert. Installiere mit: pip install requests")

logger = logging.getLogger(__name__)


@dataclass
class OCSettings:
    """Overclock-Einstellungen für eine GPU/Algorithmus-Kombination"""
    gpu_name: str
    algorithm: str
    coin: str = ""
    core_clock_offset: int = 0      # MHz Offset (kann negativ sein)
    memory_clock_offset: int = 0    # MHz Offset
    power_limit_watts: int = 0      # Absolute Watts
    power_limit_percent: int = 100  # Prozent vom Default
    fan_speed: int = 0              # 0 = Auto
    hashrate: float = 0.0           # Erwartete Hashrate (MH/s oder entsprechend)
    power_consumption: float = 0.0  # Erwarteter Power-Verbrauch
    efficiency: float = 0.0         # Hash per Watt
    source: str = "default"         # "hashrate.no", "local", "default"
    verified: bool = False          # Von Community verifiziert
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'gpu_name': self.gpu_name,
            'algorithm': self.algorithm,
            'coin': self.coin,
            'core_clock_offset': self.core_clock_offset,
            'memory_clock_offset': self.memory_clock_offset,
            'power_limit_watts': self.power_limit_watts,
            'power_limit_percent': self.power_limit_percent,
            'fan_speed': self.fan_speed,
            'hashrate': self.hashrate,
            'power_consumption': self.power_consumption,
            'efficiency': self.efficiency,
            'source': self.source,
            'verified': self.verified,
        }


# Standard OC-Profile als Fallback
DEFAULT_OC_PROFILES = {
    # Format: "GPU_PATTERN": {"algorithm": OCSettings}
    "RTX 3070": {
        "kawpow": OCSettings(
            gpu_name="RTX 3070",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=70,
            hashrate=30.0,
            power_consumption=140,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 3070",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=65,
            hashrate=170.0,
            power_consumption=120,
        ),
        "equihash125": OCSettings(
            gpu_name="RTX 3070",
            algorithm="equihash125",
            coin="FLUX",
            core_clock_offset=150,
            memory_clock_offset=0,
            power_limit_percent=85,
            fan_speed=70,
            hashrate=55.0,
            power_consumption=150,
        ),
        "etchash": OCSettings(
            gpu_name="RTX 3070",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=1100,
            power_limit_percent=65,
            fan_speed=60,
            hashrate=61.0,
            power_consumption=115,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 3070",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=300,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa!
            power_limit_percent=60,
            fan_speed=65,
            hashrate=596.0,
            power_consumption=95,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 3070",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=100,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=32.0,
            power_consumption=140,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 3070",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=100,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=75,
            hashrate=0.55,
            power_consumption=140,
        ),
    },
    "RTX 3080": {
        "kawpow": OCSettings(
            gpu_name="RTX 3080",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=75,
            hashrate=45.0,
            power_consumption=220,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 3080",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=260.0,
            power_consumption=200,
        ),
        "equihash125": OCSettings(
            gpu_name="RTX 3080",
            algorithm="equihash125",
            coin="FLUX",
            core_clock_offset=150,
            memory_clock_offset=0,
            power_limit_percent=80,
            fan_speed=75,
            hashrate=80.0,
            power_consumption=220,
        ),
        "etchash": OCSettings(
            gpu_name="RTX 3080",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=1100,
            power_limit_percent=65,
            fan_speed=65,
            hashrate=98.0,
            power_consumption=200,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 3080",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=250,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa! --mclk 810
            power_limit_percent=65,
            fan_speed=70,
            hashrate=877.0,
            power_consumption=190,
        ),
        "blake3": OCSettings(
            gpu_name="RTX 3080",
            algorithm="blake3",
            coin="ALPH",
            core_clock_offset=150,
            memory_clock_offset=0,
            power_limit_percent=75,
            fan_speed=70,
            hashrate=2.0,
            power_consumption=200,
        ),
        "octopus": OCSettings(
            gpu_name="RTX 3080",
            algorithm="octopus",
            coin="CFX",
            core_clock_offset=0,
            memory_clock_offset=500,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=75.0,
            power_consumption=190,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 3080",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=150,
            memory_clock_offset=1500,
            power_limit_percent=70,
            fan_speed=75,
            hashrate=48.0,
            power_consumption=260,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 3080",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=150,
            memory_clock_offset=1500,
            power_limit_percent=70,
            fan_speed=80,
            hashrate=0.91,
            power_consumption=260,
        ),
        "firopow": OCSettings(
            gpu_name="RTX 3080",
            algorithm="firopow",
            coin="FIRO",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=75,
            hashrate=42.0,
            power_consumption=220,
        ),
    },
    "RTX 3080 Laptop": {
        "kawpow": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=70,
            hashrate=32.0,
            power_consumption=115,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=800,
            power_limit_percent=70,
            fan_speed=65,
            hashrate=180.0,
            power_consumption=100,
        ),
        "equihash125": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="equihash125",
            coin="FLUX",
            core_clock_offset=150,
            memory_clock_offset=0,
            power_limit_percent=80,
            fan_speed=70,
            hashrate=55.0,
            power_consumption=110,
        ),
        "etchash": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=1000,
            power_limit_percent=65,
            fan_speed=60,
            hashrate=68.0,
            power_consumption=100,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=150,
            memory_clock_offset=-300,  # Memory auf Minimum für Kaspa!
            power_limit_percent=80,
            fan_speed=80,
            hashrate=450.0,
            power_consumption=100,
        ),
        "blake3": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="blake3",
            coin="ALPH",
            core_clock_offset=150,
            memory_clock_offset=0,
            power_limit_percent=75,
            fan_speed=65,
            hashrate=1.4,
            power_consumption=105,
        ),
        "octopus": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="octopus",
            coin="CFX",
            core_clock_offset=0,
            memory_clock_offset=500,
            power_limit_percent=70,
            fan_speed=65,
            hashrate=52.0,
            power_consumption=100,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=85,
            hashrate=25.0,
            power_consumption=115,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=85,
            hashrate=0.45,
            power_consumption=115,
        ),
        "firopow": OCSettings(
            gpu_name="RTX 3080 Laptop",
            algorithm="firopow",
            coin="FIRO",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=70,
            hashrate=28.0,
            power_consumption=115,
        ),
    },
    "RTX 3060 Ti": {
        "kawpow": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=70,
            hashrate=28.0,
            power_consumption=130,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=65,
            hashrate=160.0,
            power_consumption=115,
        ),
        "etchash": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=1100,
            power_limit_percent=65,
            fan_speed=60,
            hashrate=58.0,
            power_consumption=110,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=250,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa!
            power_limit_percent=60,
            fan_speed=65,
            hashrate=490.0,
            power_consumption=85,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=100,
            memory_clock_offset=800,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=28.0,
            power_consumption=125,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 3060 Ti",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=100,
            memory_clock_offset=800,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=0.48,
            power_consumption=125,
        ),
    },
    "RTX 3090": {
        "kawpow": OCSettings(
            gpu_name="RTX 3090",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=80,
            hashrate=55.0,
            power_consumption=290,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 3090",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=75,
            hashrate=320.0,
            power_consumption=280,
        ),
        "etchash": OCSettings(
            gpu_name="RTX 3090",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=1100,
            power_limit_percent=65,
            fan_speed=70,
            hashrate=120.0,
            power_consumption=280,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 3090",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=350,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa! --mclk 807
            power_limit_percent=60,
            fan_speed=75,
            hashrate=1079.0,
            power_consumption=160,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 3090",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=150,
            memory_clock_offset=1200,
            power_limit_percent=70,
            fan_speed=80,
            hashrate=56.0,
            power_consumption=280,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 3090",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=150,
            memory_clock_offset=1200,
            power_limit_percent=70,
            fan_speed=80,
            hashrate=1.1,
            power_consumption=280,
        ),
    },
    "RTX 4070": {
        "kawpow": OCSettings(
            gpu_name="RTX 4070",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=150,
            memory_clock_offset=500,
            power_limit_percent=85,
            fan_speed=65,
            hashrate=35.0,
            power_consumption=130,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 4070",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1200,
            power_limit_percent=70,
            fan_speed=60,
            hashrate=200.0,
            power_consumption=110,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 4070",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=200,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa!
            power_limit_percent=70,
            fan_speed=65,
            hashrate=550.0,
            power_consumption=100,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 4070",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=75,
            fan_speed=65,
            hashrate=38.0,
            power_consumption=120,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 4070",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=75,
            fan_speed=70,
            hashrate=0.7,
            power_consumption=130,
        ),
    },
    "RTX 4080": {
        "kawpow": OCSettings(
            gpu_name="RTX 4080",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=150,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=70,
            hashrate=52.0,
            power_consumption=200,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 4080",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1200,
            power_limit_percent=70,
            fan_speed=65,
            hashrate=300.0,
            power_consumption=180,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 4080",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=200,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa!
            power_limit_percent=70,
            fan_speed=70,
            hashrate=780.0,
            power_consumption=150,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 4080",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=75,
            fan_speed=70,
            hashrate=55.0,
            power_consumption=180,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 4080",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=75,
            fan_speed=75,
            hashrate=1.0,
            power_consumption=200,
        ),
    },
    "RTX 4090": {
        "kawpow": OCSettings(
            gpu_name="RTX 4090",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=150,
            memory_clock_offset=500,
            power_limit_percent=75,
            fan_speed=75,
            hashrate=75.0,
            power_consumption=320,
        ),
        "autolykos2": OCSettings(
            gpu_name="RTX 4090",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=1200,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=400.0,
            power_consumption=300,
        ),
        "kheavyhash": OCSettings(
            gpu_name="RTX 4090",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=200,
            memory_clock_offset=-502,  # Memory auf Minimum für Kaspa!
            power_limit_percent=70,
            fan_speed=70,
            hashrate=1200.0,
            power_consumption=200,
        ),
        "beamhash3": OCSettings(
            gpu_name="RTX 4090",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=75,
            hashrate=72.0,
            power_consumption=320,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="RTX 4090",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=150,
            memory_clock_offset=1000,
            power_limit_percent=70,
            fan_speed=75,
            hashrate=1.5,
            power_consumption=320,
        ),
    },
    "GTX 1080 Ti": {
        "kawpow": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="kawpow",
            coin="RVN",
            core_clock_offset=100,
            memory_clock_offset=400,
            power_limit_percent=80,
            fan_speed=75,
            hashrate=22.0,
            power_consumption=180,
        ),
        "autolykos2": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="autolykos2",
            coin="ERG",
            core_clock_offset=0,
            memory_clock_offset=500,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=95.0,
            power_consumption=150,
        ),
        "etchash": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="etchash",
            coin="ETC",
            core_clock_offset=-200,
            memory_clock_offset=800,
            power_limit_percent=70,
            fan_speed=70,
            hashrate=45.0,
            power_consumption=160,
        ),
        "kheavyhash": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="kheavyhash",
            coin="KAS",
            core_clock_offset=0,
            memory_clock_offset=-300,  # Memory auf Minimum für Kaspa! --mclk 810
            power_limit_percent=70,
            fan_speed=70,
            hashrate=470.0,
            power_consumption=120,
        ),
        "beamhash3": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="beamhash3",
            coin="BEAM",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=75,
            hashrate=20.0,
            power_consumption=180,
        ),
        "cuckatoo32": OCSettings(
            gpu_name="GTX 1080 Ti",
            algorithm="cuckatoo32",
            coin="GRIN",
            core_clock_offset=100,
            memory_clock_offset=500,
            power_limit_percent=80,
            fan_speed=75,
            hashrate=0.38,
            power_consumption=180,
        ),
    },
}

# Algorithmus zu Coin Mapping
ALGORITHM_TO_COIN = {
    "kawpow": "RVN",
    "autolykos2": "ERG",
    "equihash125": "FLUX",
    "equihash1254": "FLUX",
    "zelhash": "FLUX",
    "etchash": "ETC",
    "ethash": "ETC",
    "kheavyhash": "KAS",
    "sha256": "BTC",
    "scrypt": "LTC",
    # Neue Algorithmen
    "cuckatoo32": "GRIN",
    "C32": "GRIN",
    "beamhash3": "BEAM",
    "beamhashiii": "BEAM",
    "BEAM-III": "BEAM",
    "blake3": "ALPH",
    "randomx": "XMR",
}

# Coin zu Algorithmus Mapping
COIN_TO_ALGORITHM = {
    "RVN": "kawpow",
    "ERG": "autolykos2",
    "FLUX": "equihash125",
    "ETC": "etchash",
    "KASPA": "kheavyhash",
    "KAS": "kheavyhash",
    # Neue Coins
    "GRIN": "cuckatoo32",
    "BEAM": "beamhash3",
    "ALPH": "blake3",
    "IRON": "blake3",
    "XMR": "randomx",
    "CLORE": "kawpow",
    "NEOX": "kawpow",
}


class HashrateNoAPI:
    """
    Client für hashrate.no API.
    
    Verwendung:
        api = HashrateNoAPI(api_key="YOUR_KEY")
        
        # OC-Settings für GPU/Coin holen
        oc = api.get_oc_settings("RTX 3070", "RVN")
        
        # Benchmark-Daten holen
        benchmarks = api.get_benchmarks("RVN")
    """
    
    BASE_URL = "https://hashrate.no/api/v2"
    
    def __init__(self, api_key: str = "", cache_dir: str = "cache"):
        """
        Initialisiert den API Client.
        
        Args:
            api_key: hashrate.no API Key (kostenlos nach Registrierung)
            cache_dir: Verzeichnis für Cache-Dateien
        """
        self.api_key = api_key
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Dict[str, float] = {}
        self._cache_duration = 3600  # 1 Stunde
        
        # Lokale Profile laden
        self._local_profiles = self._load_local_profiles()
    
    def _load_local_profiles(self) -> Dict[str, Any]:
        """Lädt lokale OC-Profile aus Datei"""
        profile_path = self.cache_dir / "oc_profiles_local.json"
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden lokaler Profile: {e}")
        return {}
    
    def save_local_profile(self, gpu_name: str, algorithm: str, settings: OCSettings):
        """Speichert ein OC-Profil lokal"""
        key = f"{gpu_name}_{algorithm}"
        self._local_profiles[key] = settings.to_dict()
        
        profile_path = self.cache_dir / "oc_profiles_local.json"
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(self._local_profiles, f, indent=2)
            logger.info(f"Lokales Profil gespeichert: {key}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """Holt Daten aus Cache wenn noch gültig"""
        if key in self._cache:
            if time.time() < self._cache_expiry.get(key, 0):
                return self._cache[key]
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Speichert Daten im Cache"""
        self._cache[key] = data
        self._cache_expiry[key] = time.time() + self._cache_duration
    
    def _api_request(self, endpoint: str, params: Dict[str, str] = None) -> Optional[Dict]:
        """
        Führt einen API-Request durch.
        
        Args:
            endpoint: API Endpoint (z.B. "/benchmarks")
            params: Zusätzliche Query-Parameter
            
        Returns:
            JSON Response oder None bei Fehler
        """
        if not requests:
            logger.error("requests Modul nicht verfügbar")
            return None
        
        if not self.api_key:
            logger.warning("Kein API-Key gesetzt - nutze lokale Profile")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        
        query_params = {"apiKey": self.api_key}
        if params:
            query_params.update(params)
        
        try:
            response = requests.get(url, params=query_params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("Ungültiger API-Key")
            elif response.status_code == 429:
                logger.warning("Rate Limit erreicht - nutze Cache")
            else:
                logger.error(f"API Fehler: {response.status_code}")
                
        except requests.exceptions.Timeout:
            logger.error("API Timeout")
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Fehler: {e}")
        
        return None
    
    def get_benchmarks(self, coin: str = None) -> List[Dict]:
        """
        Holt Benchmark-Daten von hashrate.no.
        
        Args:
            coin: Optionaler Coin-Filter (z.B. "RVN", "ERG")
            
        Returns:
            Liste mit Benchmark-Daten
        """
        cache_key = f"benchmarks_{coin or 'all'}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        params = {}
        if coin:
            params['coin'] = coin
        
        data = self._api_request("/benchmarks", params)
        
        if data:
            self._set_cache(cache_key, data)
            return data
        
        return []
    
    def get_gpu_estimates(self, power_cost: float = 0.10) -> List[Dict]:
        """
        Holt GPU-Schätzungen (Profit etc.) von hashrate.no.
        
        Args:
            power_cost: Stromkosten in $/kWh
            
        Returns:
            Liste mit GPU-Schätzungen
        """
        cache_key = f"gpu_estimates_{power_cost}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        data = self._api_request("/gpuEstimates", {"powerCost": str(power_cost)})
        
        if data:
            self._set_cache(cache_key, data)
            return data
        
        return []
    
    def get_coins(self, coin: str = None) -> List[Dict]:
        """
        Holt Coin-Informationen von hashrate.no.
        
        Args:
            coin: Optionaler einzelner Coin
            
        Returns:
            Liste mit Coin-Daten
        """
        cache_key = f"coins_{coin or 'all'}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        params = {}
        if coin:
            params['coin'] = coin
        
        data = self._api_request("/coins", params)
        
        if data:
            self._set_cache(cache_key, data)
            return data
        
        return []
    
    def _match_gpu_name(self, detected_name: str) -> Optional[str]:
        """Matched einen erkannten GPU-Namen zu den bekannten Profilen"""
        detected_lower = detected_name.lower()
        
        # WICHTIG: Laptop GPUs ZUERST prüfen (vor Desktop)
        if "laptop" in detected_lower or "mobile" in detected_lower:
            laptop_mappings = {
                "3080": "RTX 3080 Laptop",
                "3070": "RTX 3070 Laptop",
                "3060": "RTX 3060 Laptop",
                "4080": "RTX 4080 Laptop",
                "4070": "RTX 4070 Laptop",
                "4060": "RTX 4060 Laptop",
            }
            for pattern, gpu_name in laptop_mappings.items():
                if pattern in detected_lower:
                    # Fallback auf Desktop wenn Laptop-Profil nicht existiert
                    if gpu_name in DEFAULT_OC_PROFILES:
                        return gpu_name
                    # Sonst Desktop-Version
                    return gpu_name.replace(" Laptop", "")
        
        # Direktes Match
        for gpu_pattern in DEFAULT_OC_PROFILES.keys():
            if gpu_pattern.lower() in detected_lower:
                return gpu_pattern
        
        # Spezielle Matches (Desktop GPUs)
        gpu_mappings = {
            "3070": "RTX 3070",
            "3080": "RTX 3080",
            "3060 ti": "RTX 3060 Ti",
            "3060ti": "RTX 3060 Ti",
            "3090": "RTX 3090",
            "4070": "RTX 4070",
            "4080": "RTX 4080",
            "4090": "RTX 4090",
        }
        
        for pattern, gpu_name in gpu_mappings.items():
            if pattern in detected_lower:
                return gpu_name
        
        return None
    
    def get_oc_settings(self, gpu_name: str, coin_or_algo: str) -> OCSettings:
        """
        Holt die optimalen OC-Settings für eine GPU/Coin-Kombination.
        
        Sucht in folgender Reihenfolge:
        1. hashrate.no API (wenn API-Key vorhanden)
        2. Lokale benutzerdefinierte Profile
        3. Default-Profile
        
        Args:
            gpu_name: GPU Name (z.B. "NVIDIA GeForce RTX 3070")
            coin_or_algo: Coin (z.B. "RVN") oder Algorithmus (z.B. "kawpow")
            
        Returns:
            OCSettings Objekt mit OC-Einstellungen
        """
        # Algorithmus bestimmen
        if coin_or_algo.upper() in COIN_TO_ALGORITHM:
            algorithm = COIN_TO_ALGORITHM[coin_or_algo.upper()]
            coin = coin_or_algo.upper()
        elif coin_or_algo.lower() in ALGORITHM_TO_COIN:
            algorithm = coin_or_algo.lower()
            coin = ALGORITHM_TO_COIN[algorithm]
        else:
            algorithm = coin_or_algo.lower()
            coin = ""
        
        # GPU Name matchen
        matched_gpu = self._match_gpu_name(gpu_name)
        
        # 1. Versuche hashrate.no API
        if self.api_key and coin:
            benchmarks = self.get_benchmarks(coin)
            oc_settings = self._parse_benchmarks_for_gpu(benchmarks, gpu_name, algorithm, coin)
            if oc_settings:
                return oc_settings
        
        # 2. Lokale Profile prüfen
        if matched_gpu:
            local_key = f"{matched_gpu}_{algorithm}"
            if local_key in self._local_profiles:
                profile = self._local_profiles[local_key]
                return OCSettings(
                    gpu_name=matched_gpu,
                    algorithm=algorithm,
                    coin=coin,
                    core_clock_offset=profile.get('core_clock_offset', 0),
                    memory_clock_offset=profile.get('memory_clock_offset', 0),
                    power_limit_watts=profile.get('power_limit_watts', 0),
                    power_limit_percent=profile.get('power_limit_percent', 100),
                    fan_speed=profile.get('fan_speed', 0),
                    hashrate=profile.get('hashrate', 0),
                    power_consumption=profile.get('power_consumption', 0),
                    source="local",
                    verified=profile.get('verified', False),
                )
        
        # 3. Default-Profile
        if matched_gpu and matched_gpu in DEFAULT_OC_PROFILES:
            gpu_profiles = DEFAULT_OC_PROFILES[matched_gpu]
            if algorithm in gpu_profiles:
                default = gpu_profiles[algorithm]
                return OCSettings(
                    gpu_name=matched_gpu,
                    algorithm=algorithm,
                    coin=coin,
                    core_clock_offset=default.core_clock_offset,
                    memory_clock_offset=default.memory_clock_offset,
                    power_limit_watts=default.power_limit_watts,
                    power_limit_percent=default.power_limit_percent,
                    fan_speed=default.fan_speed,
                    hashrate=default.hashrate,
                    power_consumption=default.power_consumption,
                    source="default",
                    verified=False,
                )
        
        # 4. Fallback - konservative Einstellungen
        logger.warning(f"Keine OC-Profile für {gpu_name}/{algorithm} gefunden - nutze konservative Defaults")
        return OCSettings(
            gpu_name=gpu_name,
            algorithm=algorithm,
            coin=coin,
            core_clock_offset=0,
            memory_clock_offset=0,
            power_limit_percent=100,
            fan_speed=0,  # Auto
            source="fallback",
        )
    
    def _parse_benchmarks_for_gpu(
        self, 
        benchmarks: List[Dict], 
        gpu_name: str,
        algorithm: str,
        coin: str
    ) -> Optional[OCSettings]:
        """Parst Benchmark-Daten und extrahiert OC-Settings"""
        if not benchmarks:
            return None
        
        matched_gpu = self._match_gpu_name(gpu_name)
        if not matched_gpu:
            return None
        
        # Suche passende Benchmarks
        for benchmark in benchmarks:
            bench_gpu = benchmark.get('gpu', '').lower()
            bench_algo = benchmark.get('algorithm', '').lower()
            
            if matched_gpu.lower() in bench_gpu and algorithm in bench_algo:
                # Gefunden!
                return OCSettings(
                    gpu_name=matched_gpu,
                    algorithm=algorithm,
                    coin=coin,
                    core_clock_offset=benchmark.get('coreOffset', 0),
                    memory_clock_offset=benchmark.get('memOffset', 0),
                    power_limit_watts=benchmark.get('powerLimit', 0),
                    power_limit_percent=benchmark.get('powerLimitPercent', 100),
                    fan_speed=benchmark.get('fanSpeed', 0),
                    hashrate=benchmark.get('hashrate', 0),
                    power_consumption=benchmark.get('power', 0),
                    efficiency=benchmark.get('efficiency', 0),
                    source="hashrate.no",
                    verified=benchmark.get('verified', False),
                )
        
        return None
    
    def get_all_oc_for_gpu(self, gpu_name: str) -> Dict[str, OCSettings]:
        """
        Holt alle verfügbaren OC-Profile für eine GPU.
        
        Args:
            gpu_name: GPU Name
            
        Returns:
            Dict mit {algorithm: OCSettings}
        """
        matched_gpu = self._match_gpu_name(gpu_name)
        profiles = {}
        
        # Coins die wir unterstützen
        supported_coins = ["RVN", "ERG", "FLUX", "ETC"]
        
        for coin in supported_coins:
            oc = self.get_oc_settings(gpu_name, coin)
            if oc.source != "fallback":
                profiles[oc.algorithm] = oc
        
        return profiles
    
    def get_gpu_hashrates(self, gpu_name: str) -> Dict[str, Dict[str, float]]:
        """
        Holt erwartete Hashrates für alle Algorithmen einer GPU.
        
        Diese Methode wird vom Benchmark Manager genutzt um
        die erwarteten vs. gemessenen Hashrates zu vergleichen.
        
        Args:
            gpu_name: GPU Name (z.B. "NVIDIA GeForce RTX 3080")
            
        Returns:
            Dict mit {algorithm: {"hashrate": float, "power": float, "efficiency": float}}
        """
        result = {}
        matched_gpu = self._match_gpu_name(gpu_name)
        
        if not matched_gpu:
            logger.debug(f"GPU nicht erkannt: {gpu_name}")
            return result
        
        # Alle unterstützten Algorithmen durchgehen
        all_algos = [
            "kawpow", "autolykos2", "etchash", "equihash125",
            "beamhash3", "kheavyhash", "octopus", "blake3",
            "nexapow", "cuckatoo32", "firopow", "randomx"
        ]
        
        for algo in all_algos:
            oc = self.get_oc_settings(gpu_name, algo)
            
            if oc.hashrate > 0:
                result[algo] = {
                    "hashrate": oc.hashrate,
                    "power": oc.power_consumption,
                    "efficiency": oc.efficiency if oc.efficiency > 0 else (
                        oc.hashrate / oc.power_consumption if oc.power_consumption > 0 else 0
                    )
                }
        
        logger.info(f"GPU-Hashrates geladen für {matched_gpu}: {len(result)} Algorithmen")
        return result
    
    def get_expected_hashrate(self, gpu_name: str, algorithm: str) -> float:
        """
        Holt die erwartete Hashrate für GPU + Algorithmus.
        
        Args:
            gpu_name: GPU Name
            algorithm: Algorithmus Name
            
        Returns:
            Erwartete Hashrate (0.0 wenn unbekannt)
        """
        hashrates = self.get_gpu_hashrates(gpu_name)
        
        if algorithm in hashrates:
            return hashrates[algorithm].get("hashrate", 0.0)
        
        return 0.0


# Standalone Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("hashrate.no API Client Test")
    print("=" * 60)
    
    # Ohne API-Key (nutzt Default-Profile)
    api = HashrateNoAPI()
    
    # Test: OC-Settings für RTX 3070 + RVN
    print("\n📊 OC-Settings für RTX 3070 + RVN:")
    oc = api.get_oc_settings("NVIDIA GeForce RTX 3070", "RVN")
    print(f"   Core Offset: {oc.core_clock_offset} MHz")
    print(f"   Memory Offset: {oc.memory_clock_offset} MHz")
    print(f"   Power Limit: {oc.power_limit_percent}%")
    print(f"   Fan Speed: {oc.fan_speed}%")
    print(f"   Expected Hashrate: {oc.hashrate} MH/s")
    print(f"   Expected Power: {oc.power_consumption}W")
    print(f"   Source: {oc.source}")
    
    # Test: Alle Profile für RTX 3080
    print("\n📊 Alle OC-Profile für RTX 3080:")
    all_oc = api.get_all_oc_for_gpu("RTX 3080")
    for algo, settings in all_oc.items():
        print(f"   {algo}: Core {settings.core_clock_offset:+d}, "
              f"Mem {settings.memory_clock_offset:+d}, "
              f"PL {settings.power_limit_percent}%, "
              f"Hash {settings.hashrate}")
    
    print("\n✅ Test beendet")
    print("\n💡 Für Live-Daten: Registriere dich auf hashrate.no und hole einen API-Key")
