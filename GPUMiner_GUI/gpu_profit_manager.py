#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Profit Manager - hashrate.no Integration
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Direkte Profitabilitäts-Daten von hashrate.no pro GPU
- Multi-GPU Support (jede GPU eigene Einstellungen)
- OC-Profile: Low/Medium/High basierend auf Temperatur
- Automatischer Benchmark mit optimalen Settings
- Automatische OC-Anpassung pro Coin
"""

import json
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# OC PROFILE SYSTEM
# ============================================================================

class OCProfile(Enum):
    """OC-Profile basierend auf Temperatur/Performance"""
    LOW = "low"           # Kühl, leise, weniger Profit
    MEDIUM = "medium"     # Balanced
    HIGH = "high"         # Max Profit, heißer, lauter


@dataclass
class OCSettings:
    """Overclock-Einstellungen für eine GPU"""
    core_clock: int = 0      # MHz offset
    mem_clock: int = 0       # MHz offset
    power_limit: int = 100   # Prozent
    fan_speed: int = 70      # Prozent
    expected_hashrate: float = 0.0
    expected_power: int = 0   # Watt
    expected_temp: int = 65   # °C
    hashrate_unit: str = "MH/s"


@dataclass
class CoinOCProfiles:
    """OC-Profile für einen Coin (Low/Medium/High)"""
    coin: str
    algorithm: str
    low: OCSettings = field(default_factory=OCSettings)
    medium: OCSettings = field(default_factory=OCSettings)
    high: OCSettings = field(default_factory=OCSettings)


@dataclass 
class GPUConfig:
    """Konfiguration für eine einzelne GPU"""
    index: int                          # GPU Index (0, 1, 2...)
    name: str                           # z.B. "NVIDIA GeForce RTX 3080 Laptop GPU"
    hashrate_no_name: str = ""          # Name wie bei hashrate.no
    current_profile: OCProfile = OCProfile.MEDIUM
    max_temp: int = 80                  # Max erlaubte Temperatur
    target_temp: int = 70               # Ziel-Temperatur
    coin_profiles: Dict[str, CoinOCProfiles] = field(default_factory=dict)
    enabled: bool = True
    last_benchmark: str = ""            # ISO Timestamp
    
    def get_oc_for_coin(self, coin: str, profile: OCProfile = None) -> Optional[OCSettings]:
        """Gibt OC-Settings für einen Coin zurück"""
        if coin not in self.coin_profiles:
            return None
        
        profile = profile or self.current_profile
        coin_oc = self.coin_profiles[coin]
        
        if profile == OCProfile.LOW:
            return coin_oc.low
        elif profile == OCProfile.HIGH:
            return coin_oc.high
        else:
            return coin_oc.medium


@dataclass
class CoinProfit:
    """Profitabilitäts-Daten für einen Coin"""
    coin: str
    algorithm: str
    revenue_usd_24h: float      # NUR Revenue, KEINE Stromkosten!
    hashrate: float
    hashrate_unit: str
    power_watts: int
    difficulty: float = 0
    block_reward: float = 0
    price_usd: float = 0
    pool_fee: float = 0
    

# ============================================================================
# GPU NAME MAPPING (Erkannter Name -> hashrate.no Name)
# ============================================================================

GPU_NAME_MAPPING = {
    # NVIDIA RTX 40 Series
    "rtx 4090": "RTX 4090",
    "rtx 4080 super": "RTX 4080 SUPER",
    "rtx 4080": "RTX 4080",
    "rtx 4070 ti super": "RTX 4070 Ti SUPER",
    "rtx 4070 ti": "RTX 4070 Ti",
    "rtx 4070 super": "RTX 4070 SUPER",
    "rtx 4070": "RTX 4070",
    "rtx 4060 ti": "RTX 4060 Ti",
    "rtx 4060": "RTX 4060",
    
    # NVIDIA RTX 30 Series
    "rtx 3090 ti": "RTX 3090 Ti",
    "rtx 3090": "RTX 3090",
    "rtx 3080 ti": "RTX 3080 Ti",
    "rtx 3080 12gb": "RTX 3080 12GB",
    "rtx 3080 laptop": "RTX 3080 Laptop",
    "rtx 3080": "RTX 3080",
    "rtx 3070 ti": "RTX 3070 Ti",
    "rtx 3070 laptop": "RTX 3070 Laptop",
    "rtx 3070": "RTX 3070",
    "rtx 3060 ti": "RTX 3060 Ti",
    "rtx 3060 laptop": "RTX 3060 Laptop",
    "rtx 3060": "RTX 3060",
    "rtx 3050": "RTX 3050",
    
    # NVIDIA RTX 20 Series
    "rtx 2080 ti": "RTX 2080 Ti",
    "rtx 2080 super": "RTX 2080 SUPER",
    "rtx 2080": "RTX 2080",
    "rtx 2070 super": "RTX 2070 SUPER",
    "rtx 2070": "RTX 2070",
    "rtx 2060 super": "RTX 2060 SUPER",
    "rtx 2060": "RTX 2060",
    
    # NVIDIA GTX Series
    "gtx 1080 ti": "GTX 1080 Ti",
    "gtx 1080": "GTX 1080",
    "gtx 1070 ti": "GTX 1070 Ti",
    "gtx 1070": "GTX 1070",
    "gtx 1660 ti": "GTX 1660 Ti",
    "gtx 1660 super": "GTX 1660 SUPER",
    "gtx 1660": "GTX 1660",
    
    # AMD RX 7000 Series
    "rx 7900 xtx": "RX 7900 XTX",
    "rx 7900 xt": "RX 7900 XT",
    "rx 7800 xt": "RX 7800 XT",
    "rx 7700 xt": "RX 7700 XT",
    "rx 7600": "RX 7600",
    
    # AMD RX 6000 Series
    "rx 6950 xt": "RX 6950 XT",
    "rx 6900 xt": "RX 6900 XT",
    "rx 6800 xt": "RX 6800 XT",
    "rx 6800": "RX 6800",
    "rx 6700 xt": "RX 6700 XT",
    "rx 6700": "RX 6700",
    "rx 6600 xt": "RX 6600 XT",
    "rx 6600": "RX 6600",
    "rx 6500 xt": "RX 6500 XT",
    
    # AMD RX 5000 Series
    "rx 5700 xt": "RX 5700 XT",
    "rx 5700": "RX 5700",
    "rx 5600 xt": "RX 5600 XT",
    "rx 5500 xt": "RX 5500 XT",
}


def match_gpu_name(detected_name: str) -> str:
    """Matched erkannten GPU-Namen zu hashrate.no Namen"""
    detected_lower = detected_name.lower()
    
    # Sortiere nach Länge (längere Matches zuerst für Spezifität)
    for pattern, hashrate_name in sorted(GPU_NAME_MAPPING.items(), key=lambda x: len(x[0]), reverse=True):
        if pattern in detected_lower:
            return hashrate_name
    
    # Fallback: Versuche direkte Extraktion
    # "NVIDIA GeForce RTX 3080 Laptop GPU" -> "RTX 3080 Laptop"
    import re
    match = re.search(r'(RTX|GTX|RX)\s*\d+\s*\w*', detected_name, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    
    return detected_name


# ============================================================================
# OC PROFILE TEMPLATES (Low/Medium/High)
# ============================================================================

def generate_oc_profiles(base_settings: Dict) -> CoinOCProfiles:
    """
    Generiert Low/Medium/High Profile aus Basis-Settings
    
    Beispiel Input (von hashrate.no):
    {
        "coin": "RVN",
        "algorithm": "kawpow", 
        "core": 100,
        "mem": 500,
        "pl": 75,
        "fan": 70,
        "hashrate": 32.0,
        "power": 115,
        "unit": "MH/s"
    }
    """
    coin = base_settings.get("coin", "")
    algo = base_settings.get("algorithm", "")
    
    # Basis-Werte (= Medium)
    base_core = base_settings.get("core", 0)
    base_mem = base_settings.get("mem", 0)
    base_pl = base_settings.get("pl", 100)
    base_fan = base_settings.get("fan", 70)
    base_hash = base_settings.get("hashrate", 0)
    base_power = base_settings.get("power", 100)
    unit = base_settings.get("unit", "MH/s")
    
    # LOW Profile: -20% Performance, -25% Power, kühler
    low = OCSettings(
        core_clock=int(base_core * 0.5),      # Halber Core OC
        mem_clock=int(base_mem * 0.7),        # 70% Mem OC
        power_limit=max(50, base_pl - 15),    # -15% PL
        fan_speed=min(100, base_fan + 10),    # +10% Fan
        expected_hashrate=base_hash * 0.80,   # -20% Hashrate
        expected_power=int(base_power * 0.70),# -30% Power
        expected_temp=55,                      # Kühl
        hashrate_unit=unit
    )
    
    # MEDIUM Profile: Standard (von hashrate.no)
    medium = OCSettings(
        core_clock=base_core,
        mem_clock=base_mem,
        power_limit=base_pl,
        fan_speed=base_fan,
        expected_hashrate=base_hash,
        expected_power=base_power,
        expected_temp=65,
        hashrate_unit=unit
    )
    
    # HIGH Profile: +10% Performance, +15% Power, heißer
    high = OCSettings(
        core_clock=int(base_core * 1.2) if base_core > 0 else 50,
        mem_clock=int(base_mem * 1.15),       # +15% Mem OC
        power_limit=min(100, base_pl + 10),   # +10% PL
        fan_speed=min(100, base_fan + 15),    # +15% Fan
        expected_hashrate=base_hash * 1.05,   # +5% Hashrate (realistisch)
        expected_power=int(base_power * 1.15),# +15% Power
        expected_temp=75,                      # Heißer
        hashrate_unit=unit
    )
    
    return CoinOCProfiles(
        coin=coin,
        algorithm=algo,
        low=low,
        medium=medium,
        high=high
    )


# ============================================================================
# GPU PROFIT MANAGER
# ============================================================================

class GPUProfitManager:
    """
    Verwaltet Profitabilität für mehrere GPUs mit hashrate.no Integration
    """
    
    API_BASE = "https://hashrate.no/api/v2"
    CACHE_DURATION = 300  # 5 Minuten
    
    def __init__(self, api_key: str = None, config_path: str = "gpu_profit_config.json"):
        self.api_key = api_key or self._load_api_key()
        self.config_path = Path(config_path)
        self.gpus: Dict[int, GPUConfig] = {}  # index -> GPUConfig
        self._cache: Dict[str, Tuple[datetime, any]] = {}
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'GPUMiningProfitSwitcher/11.0'
        })
        
        self._load_config()
    
    def _load_api_key(self) -> str:
        """Lädt API Key aus Config"""
        try:
            config_file = Path("hashrateno_config.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f).get("api_key", "")
        except:
            pass
        return ""
    
    def _load_config(self):
        """Lädt GPU-Konfiguration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for idx_str, gpu_data in data.get("gpus", {}).items():
                        idx = int(idx_str)
                        # Rekonstruiere GPUConfig
                        gpu = GPUConfig(
                            index=idx,
                            name=gpu_data.get("name", ""),
                            hashrate_no_name=gpu_data.get("hashrate_no_name", ""),
                            current_profile=OCProfile(gpu_data.get("current_profile", "medium")),
                            max_temp=gpu_data.get("max_temp", 80),
                            target_temp=gpu_data.get("target_temp", 70),
                            enabled=gpu_data.get("enabled", True),
                            last_benchmark=gpu_data.get("last_benchmark", "")
                        )
                        # Coin Profiles laden
                        for coin, profile_data in gpu_data.get("coin_profiles", {}).items():
                            gpu.coin_profiles[coin] = CoinOCProfiles(
                                coin=coin,
                                algorithm=profile_data.get("algorithm", ""),
                                low=OCSettings(**profile_data.get("low", {})),
                                medium=OCSettings(**profile_data.get("medium", {})),
                                high=OCSettings(**profile_data.get("high", {}))
                            )
                        self.gpus[idx] = gpu
                logger.info(f"GPU Config geladen: {len(self.gpus)} GPUs")
            except Exception as e:
                logger.error(f"Fehler beim Laden der GPU Config: {e}")
    
    def _save_config(self):
        """Speichert GPU-Konfiguration"""
        try:
            data = {"gpus": {}}
            for idx, gpu in self.gpus.items():
                gpu_data = {
                    "name": gpu.name,
                    "hashrate_no_name": gpu.hashrate_no_name,
                    "current_profile": gpu.current_profile.value,
                    "max_temp": gpu.max_temp,
                    "target_temp": gpu.target_temp,
                    "enabled": gpu.enabled,
                    "last_benchmark": gpu.last_benchmark,
                    "coin_profiles": {}
                }
                for coin, profiles in gpu.coin_profiles.items():
                    gpu_data["coin_profiles"][coin] = {
                        "algorithm": profiles.algorithm,
                        "low": asdict(profiles.low),
                        "medium": asdict(profiles.medium),
                        "high": asdict(profiles.high)
                    }
                data["gpus"][str(idx)] = gpu_data
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"GPU Config gespeichert: {len(self.gpus)} GPUs")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der GPU Config: {e}")
    
    def _api_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """API Request zu hashrate.no"""
        if not self.api_key:
            logger.warning("Kein hashrate.no API Key konfiguriert")
            return None
        
        params = params or {}
        params["apiKey"] = self.api_key
        
        url = f"{self.API_BASE}{endpoint}"
        
        try:
            response = self._session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"hashrate.no API Fehler: {e}")
            return None
    
    def _get_cached(self, key: str) -> Optional[any]:
        """Holt gecachte Daten"""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.CACHE_DURATION):
                return data
        return None
    
    def _set_cached(self, key: str, data: any):
        """Cached Daten"""
        self._cache[key] = (datetime.now(), data)
    
    # =========================================================================
    # GPU ERKENNUNG
    # =========================================================================
    
    def detect_gpus(self) -> List[GPUConfig]:
        """Erkennt alle GPUs im System"""
        detected = []
        
        # NVIDIA GPUs via NVML
        try:
            import pynvml
            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetDeviceCount()
            
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                hashrate_name = match_gpu_name(name)
                
                # Existierende Config beibehalten oder neue erstellen
                if i in self.gpus:
                    self.gpus[i].name = name
                    self.gpus[i].hashrate_no_name = hashrate_name
                else:
                    self.gpus[i] = GPUConfig(
                        index=i,
                        name=name,
                        hashrate_no_name=hashrate_name
                    )
                
                detected.append(self.gpus[i])
                logger.info(f"GPU {i}: {name} -> {hashrate_name}")
            
            pynvml.nvmlShutdown()
        except ImportError:
            logger.warning("pynvml nicht verfügbar")
        except Exception as e:
            logger.error(f"GPU-Erkennung Fehler: {e}")
        
        # AMD GPUs könnten hier hinzugefügt werden
        
        self._save_config()
        return detected
    
    # =========================================================================
    # PROFITABILITÄT
    # =========================================================================
    
    def get_gpu_profits(self, gpu_index: int = 0) -> List[CoinProfit]:
        """
        Holt Profitabilitäts-Daten für eine GPU von hashrate.no
        
        Returns:
            Liste von CoinProfit sortiert nach Revenue (OHNE Stromkosten!)
        """
        if gpu_index not in self.gpus:
            logger.error(f"GPU {gpu_index} nicht gefunden")
            return []
        
        gpu = self.gpus[gpu_index]
        cache_key = f"profits_{gpu.hashrate_no_name}"
        
        # Cache prüfen
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        # Von hashrate.no holen
        data = self._api_request("/gpuEstimates", {"powerCost": "0"})  # KEINE Stromkosten!
        
        if not data:
            return []
        
        profits = []
        gpu_name_lower = gpu.hashrate_no_name.lower()
        
        # Suche GPU in Daten
        for gpu_data in data:
            if gpu_data.get("gpu", "").lower() == gpu_name_lower:
                # Coins extrahieren
                for coin_data in gpu_data.get("coins", []):
                    profit = CoinProfit(
                        coin=coin_data.get("coin", ""),
                        algorithm=coin_data.get("algorithm", ""),
                        revenue_usd_24h=float(coin_data.get("revenue", 0)),
                        hashrate=float(coin_data.get("hashrate", 0)),
                        hashrate_unit=coin_data.get("unit", "MH/s"),
                        power_watts=int(coin_data.get("power", 0)),
                        price_usd=float(coin_data.get("price", 0)),
                    )
                    profits.append(profit)
                break
        
        # Nach Revenue sortieren (NICHT Profit!)
        profits.sort(key=lambda x: x.revenue_usd_24h, reverse=True)
        
        self._set_cached(cache_key, profits)
        logger.info(f"GPU {gpu_index} ({gpu.hashrate_no_name}): {len(profits)} Coins geladen")
        
        return profits
    
    def get_best_coin(self, gpu_index: int = 0) -> Optional[CoinProfit]:
        """Gibt den profitabelsten Coin für eine GPU zurück"""
        profits = self.get_gpu_profits(gpu_index)
        return profits[0] if profits else None
    
    def get_all_gpu_profits(self) -> Dict[int, List[CoinProfit]]:
        """Holt Profits für ALLE GPUs"""
        result = {}
        for idx in self.gpus:
            result[idx] = self.get_gpu_profits(idx)
        return result
    
    # =========================================================================
    # OC PROFILE MANAGEMENT
    # =========================================================================
    
    def load_oc_profiles_from_hashrate_no(self, gpu_index: int = 0, coin: str = None) -> bool:
        """
        Lädt OC-Settings von hashrate.no und generiert Low/Medium/High Profile
        """
        if gpu_index not in self.gpus:
            return False
        
        gpu = self.gpus[gpu_index]
        
        params = {}
        if coin:
            params["coin"] = coin
        
        data = self._api_request("/benchmarks", params)
        
        if not data:
            return False
        
        gpu_name_lower = gpu.hashrate_no_name.lower()
        count = 0
        
        for benchmark in data:
            if benchmark.get("gpu", "").lower() != gpu_name_lower:
                continue
            
            coin_name = benchmark.get("coin", "")
            if coin and coin_name.upper() != coin.upper():
                continue
            
            # Basis-Settings
            base_settings = {
                "coin": coin_name,
                "algorithm": benchmark.get("algorithm", ""),
                "core": benchmark.get("core", 0),
                "mem": benchmark.get("mem", 0),
                "pl": benchmark.get("pl", 100),
                "fan": benchmark.get("fan", 70),
                "hashrate": benchmark.get("hashrate", 0),
                "power": benchmark.get("power", 100),
                "unit": benchmark.get("unit", "MH/s"),
            }
            
            # Low/Medium/High Profile generieren
            profiles = generate_oc_profiles(base_settings)
            gpu.coin_profiles[coin_name] = profiles
            count += 1
        
        if count > 0:
            self._save_config()
            logger.info(f"GPU {gpu_index}: {count} OC-Profile von hashrate.no geladen")
        
        return count > 0
    
    def set_gpu_profile(self, gpu_index: int, profile: OCProfile):
        """Setzt das aktive OC-Profile für eine GPU"""
        if gpu_index in self.gpus:
            self.gpus[gpu_index].current_profile = profile
            self._save_config()
            logger.info(f"GPU {gpu_index}: Profile auf {profile.value} gesetzt")
    
    def get_oc_for_coin(self, gpu_index: int, coin: str) -> Optional[OCSettings]:
        """Gibt die aktuellen OC-Settings für einen Coin zurück"""
        if gpu_index not in self.gpus:
            return None
        return self.gpus[gpu_index].get_oc_for_coin(coin)
    
    # =========================================================================
    # AUTO-BENCHMARK
    # =========================================================================
    
    def run_benchmark(self, gpu_index: int, coin: str, duration_seconds: int = 60) -> Optional[Dict]:
        """
        Führt einen Benchmark für einen Coin aus
        
        Returns:
            Dict mit gemessenen Werten (hashrate, temp, power, etc.)
        """
        if gpu_index not in self.gpus:
            return None
        
        gpu = self.gpus[gpu_index]
        logger.info(f"Starte Benchmark für GPU {gpu_index} ({gpu.name}) - Coin: {coin}")
        
        # OC-Settings laden falls nicht vorhanden
        if coin not in gpu.coin_profiles:
            self.load_oc_profiles_from_hashrate_no(gpu_index, coin)
        
        # Hier würde der eigentliche Mining-Benchmark laufen
        # TODO: Integration mit Miner-API
        
        # Placeholder für Benchmark-Ergebnis
        result = {
            "coin": coin,
            "gpu_index": gpu_index,
            "duration": duration_seconds,
            "measured_hashrate": 0.0,
            "measured_power": 0,
            "measured_temp": 0,
            "profile_used": gpu.current_profile.value,
            "timestamp": datetime.now().isoformat()
        }
        
        gpu.last_benchmark = datetime.now().isoformat()
        self._save_config()
        
        return result
    
    # =========================================================================
    # TEMPERATUR-BASIERTE PROFILE-AUSWAHL
    # =========================================================================
    
    def auto_adjust_profile(self, gpu_index: int, current_temp: int) -> OCProfile:
        """
        Passt das OC-Profile automatisch basierend auf Temperatur an
        
        Returns:
            Das neue/aktuelle Profile
        """
        if gpu_index not in self.gpus:
            return OCProfile.MEDIUM
        
        gpu = self.gpus[gpu_index]
        old_profile = gpu.current_profile
        
        # Temperatur-Logik
        if current_temp >= gpu.max_temp:
            # ZU HEISS! -> LOW
            new_profile = OCProfile.LOW
            logger.warning(f"GPU {gpu_index}: {current_temp}°C >= {gpu.max_temp}°C -> LOW Profile!")
        elif current_temp >= gpu.target_temp + 5:
            # Etwas zu warm -> MEDIUM
            new_profile = OCProfile.MEDIUM
        elif current_temp <= gpu.target_temp - 10:
            # Schön kühl -> HIGH möglich
            new_profile = OCProfile.HIGH
        else:
            # Im Zielbereich -> behalten
            new_profile = old_profile
        
        if new_profile != old_profile:
            gpu.current_profile = new_profile
            logger.info(f"GPU {gpu_index}: Profile {old_profile.value} -> {new_profile.value} (Temp: {current_temp}°C)")
        
        return new_profile
    
    # =========================================================================
    # REPORT
    # =========================================================================
    
    def print_report(self, gpu_index: int = None):
        """Druckt einen Profitabilitäts-Report"""
        gpus_to_report = [gpu_index] if gpu_index is not None else list(self.gpus.keys())
        
        for idx in gpus_to_report:
            if idx not in self.gpus:
                continue
            
            gpu = self.gpus[idx]
            profits = self.get_gpu_profits(idx)
            
            print(f"\n{'='*70}")
            print(f"GPU {idx}: {gpu.name}")
            print(f"hashrate.no Name: {gpu.hashrate_no_name}")
            print(f"Aktives Profile: {gpu.current_profile.value.upper()}")
            print(f"Max Temp: {gpu.max_temp}°C | Target: {gpu.target_temp}°C")
            print(f"{'='*70}")
            
            if not profits:
                print("Keine Profit-Daten verfügbar (API Key prüfen)")
                continue
            
            print(f"\n{'Rank':<5} {'Coin':<8} {'Algo':<15} {'Hashrate':<15} {'Power':<8} {'Revenue/Tag':<12}")
            print("-" * 70)
            
            for i, p in enumerate(profits[:15], 1):
                hashrate_str = f"{p.hashrate:.1f} {p.hashrate_unit}"
                print(f"{i:<5} {p.coin:<8} {p.algorithm:<15} {hashrate_str:<15} "
                      f"{p.power_watts:<8}W ${p.revenue_usd_24h:<11.2f}")
            
            print("-" * 70)
            if profits:
                best = profits[0]
                print(f"\n🏆 BESTER: {best.coin} = ${best.revenue_usd_24h:.2f}/Tag")
                
                # OC-Profile anzeigen falls vorhanden
                if best.coin in gpu.coin_profiles:
                    profile = gpu.coin_profiles[best.coin]
                    print(f"\n📊 OC-PROFILE für {best.coin}:")
                    print(f"   LOW:    Core {profile.low.core_clock:+d} | Mem {profile.low.mem_clock:+d} | PL {profile.low.power_limit}% | ~{profile.low.expected_hashrate:.1f} {profile.low.hashrate_unit} @ {profile.low.expected_temp}°C")
                    print(f"   MEDIUM: Core {profile.medium.core_clock:+d} | Mem {profile.medium.mem_clock:+d} | PL {profile.medium.power_limit}% | ~{profile.medium.expected_hashrate:.1f} {profile.medium.hashrate_unit} @ {profile.medium.expected_temp}°C")
                    print(f"   HIGH:   Core {profile.high.core_clock:+d} | Mem {profile.high.mem_clock:+d} | PL {profile.high.power_limit}% | ~{profile.high.expected_hashrate:.1f} {profile.high.hashrate_unit} @ {profile.high.expected_temp}°C")


# ============================================================================
# SINGLETON
# ============================================================================

_manager: Optional[GPUProfitManager] = None

def get_gpu_profit_manager(api_key: str = None) -> GPUProfitManager:
    """Gibt die globale GPUProfitManager Instanz zurück"""
    global _manager
    if _manager is None:
        _manager = GPUProfitManager(api_key=api_key)
    return _manager


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = GPUProfitManager()
    
    # GPUs erkennen
    gpus = manager.detect_gpus()
    print(f"\n{len(gpus)} GPU(s) erkannt:")
    for gpu in gpus:
        print(f"  [{gpu.index}] {gpu.name} -> {gpu.hashrate_no_name}")
    
    # Report
    manager.print_report()
