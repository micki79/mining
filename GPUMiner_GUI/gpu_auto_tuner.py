#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Auto-Tuner - Intelligentes Leistungs- und Temperatur-Management
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Automatische Profile-Anpassung basierend auf Temperatur UND Hashrate
- Live-Performance-Tracking (Hashrate pro Watt = Effizienz)
- Smart-Mode: Findet automatisch optimale Settings
- Benchmark-System für jeden Coin
- Multi-GPU Support mit individuellen Einstellungen
"""

import json
import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATACLASSES
# ============================================================================

class TuningMode(Enum):
    """Auto-Tuning Modi"""
    MANUAL = "manual"           # User wählt Profile manuell
    TEMP_SAFE = "temp_safe"     # Nur Temperatur-Schutz (runterschalten wenn heiß)
    EFFICIENCY = "efficiency"   # Beste Hashrate pro Watt
    MAX_HASH = "max_hash"       # Maximale Hashrate (ignoriert Effizienz)
    SMART = "smart"             # Intelligent: Balance aus Temp, Hashrate, Effizienz


class OCProfile(Enum):
    """OC-Profile Stufen"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GPUHealth(Enum):
    """GPU Gesundheitsstatus"""
    EXCELLENT = "excellent"     # Kühl, stabil, effizient  🟢
    GOOD = "good"               # Normal                   🟢
    WARNING = "warning"         # Wird warm               🟡
    CRITICAL = "critical"       # Zu heiß                 🔴
    THERMAL_LIMIT = "thermal"   # Thermal Throttling!     🔴


@dataclass
class OCSettings:
    """Overclock-Einstellungen"""
    core_clock: int = 0
    mem_clock: int = 0
    power_limit: int = 100
    fan_speed: int = 70
    expected_hashrate: float = 0.0
    expected_power: int = 100
    expected_temp: int = 65
    hashrate_unit: str = "MH/s"


@dataclass
class PerformanceSnapshot:
    """Ein Moment der GPU-Performance"""
    timestamp: datetime
    hashrate: float
    hashrate_unit: str
    temperature: int
    power_watts: int
    fan_speed: int
    efficiency: float  # Hashrate pro Watt
    profile: str       # low/medium/high
    coin: str
    stable: bool = True


@dataclass 
class BenchmarkResult:
    """Ergebnis eines Benchmarks"""
    coin: str
    algorithm: str
    profile: str
    gpu_index: int
    duration_seconds: int
    avg_hashrate: float
    min_hashrate: float
    max_hashrate: float
    hashrate_unit: str
    avg_temp: int
    max_temp: int
    avg_power: int
    efficiency: float  # H/W
    stability: float   # 0-100%
    timestamp: str
    recommended: bool = False  # Ist dies das empfohlene Profile?


@dataclass
class GPUState:
    """Aktueller Zustand einer GPU"""
    index: int
    name: str
    temperature: int = 0
    power_watts: int = 0
    fan_speed: int = 0
    hashrate: float = 0.0
    hashrate_unit: str = "MH/s"
    current_coin: str = ""
    current_profile: OCProfile = OCProfile.MEDIUM
    health: GPUHealth = GPUHealth.GOOD
    tuning_mode: TuningMode = TuningMode.SMART
    enabled: bool = True
    
    # Temperatur-Grenzen
    target_temp: int = 70
    warning_temp: int = 75
    max_temp: int = 83
    
    # Performance History (letzte 60 Snapshots = 10 Minuten bei 10s Intervall)
    history: deque = field(default_factory=lambda: deque(maxlen=60))
    
    # Benchmark Ergebnisse pro Coin
    benchmarks: Dict[str, Dict[str, BenchmarkResult]] = field(default_factory=dict)
    
    # OC Settings pro Coin und Profile
    oc_settings: Dict[str, Dict[str, OCSettings]] = field(default_factory=dict)


# ============================================================================
# GPU AUTO-TUNER
# ============================================================================

class GPUAutoTuner:
    """
    Intelligentes GPU Auto-Tuning System
    
    Überwacht GPUs kontinuierlich und passt OC-Settings automatisch an für:
    - Optimale Temperatur (unter Target bleiben)
    - Maximale Hashrate (im sicheren Bereich)
    - Beste Effizienz (Hashrate pro Watt)
    """
    
    UPDATE_INTERVAL = 10  # Sekunden zwischen Updates
    STABILIZE_TIME = 30   # Sekunden warten nach OC-Änderung
    
    def __init__(self, config_path: str = "gpu_tuner_config.json"):
        self.config_path = Path(config_path)
        self.gpus: Dict[int, GPUState] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._callbacks: List[Callable] = []
        self._last_oc_change: Dict[int, datetime] = {}
        
        # MSI Afterburner / OC Manager
        self._oc_manager = None
        
        # Miner API für Hashrate
        self._miner_api = None
        
        self._load_config()
    
    def _load_config(self):
        """Lädt gespeicherte Konfiguration"""
        if not self.config_path.exists():
            return
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for idx_str, gpu_data in data.get("gpus", {}).items():
                idx = int(idx_str)
                state = GPUState(
                    index=idx,
                    name=gpu_data.get("name", f"GPU {idx}"),
                    target_temp=gpu_data.get("target_temp", 70),
                    warning_temp=gpu_data.get("warning_temp", 75),
                    max_temp=gpu_data.get("max_temp", 83),
                    current_profile=OCProfile(gpu_data.get("current_profile", "medium")),
                    tuning_mode=TuningMode(gpu_data.get("tuning_mode", "smart")),
                    enabled=gpu_data.get("enabled", True),
                )
                
                # OC Settings laden
                for coin, profiles in gpu_data.get("oc_settings", {}).items():
                    state.oc_settings[coin] = {}
                    for profile_name, settings in profiles.items():
                        state.oc_settings[coin][profile_name] = OCSettings(**settings)
                
                # Benchmarks laden
                for coin, profiles in gpu_data.get("benchmarks", {}).items():
                    state.benchmarks[coin] = {}
                    for profile_name, result in profiles.items():
                        state.benchmarks[coin][profile_name] = BenchmarkResult(**result)
                
                self.gpus[idx] = state
            
            logger.info(f"Auto-Tuner Config geladen: {len(self.gpus)} GPUs")
        except Exception as e:
            logger.error(f"Fehler beim Laden der Tuner Config: {e}")
    
    def _save_config(self):
        """Speichert Konfiguration"""
        try:
            data = {"gpus": {}}
            
            for idx, gpu in self.gpus.items():
                gpu_data = {
                    "name": gpu.name,
                    "target_temp": gpu.target_temp,
                    "warning_temp": gpu.warning_temp,
                    "max_temp": gpu.max_temp,
                    "current_profile": gpu.current_profile.value,
                    "tuning_mode": gpu.tuning_mode.value,
                    "enabled": gpu.enabled,
                    "oc_settings": {},
                    "benchmarks": {},
                }
                
                # OC Settings
                for coin, profiles in gpu.oc_settings.items():
                    gpu_data["oc_settings"][coin] = {}
                    for profile_name, settings in profiles.items():
                        gpu_data["oc_settings"][coin][profile_name] = asdict(settings)
                
                # Benchmarks
                for coin, profiles in gpu.benchmarks.items():
                    gpu_data["benchmarks"][coin] = {}
                    for profile_name, result in profiles.items():
                        gpu_data["benchmarks"][coin][profile_name] = asdict(result)
                
                data["gpus"][str(idx)] = gpu_data
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Tuner Config: {e}")
    
    # =========================================================================
    # GPU ERKENNUNG & STATUS
    # =========================================================================
    
    def detect_gpus(self) -> List[GPUState]:
        """Erkennt alle GPUs"""
        try:
            import pynvml
            pynvml.nvmlInit()
            count = pynvml.nvmlDeviceGetDeviceCount()
            
            for i in range(count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                if i not in self.gpus:
                    self.gpus[i] = GPUState(index=i, name=name)
                else:
                    self.gpus[i].name = name
            
            pynvml.nvmlShutdown()
            logger.info(f"Auto-Tuner: {len(self.gpus)} GPUs erkannt")
        except Exception as e:
            logger.error(f"GPU-Erkennung Fehler: {e}")
        
        return list(self.gpus.values())
    
    def update_gpu_stats(self, gpu_index: int) -> Optional[GPUState]:
        """Aktualisiert GPU-Statistiken von NVML"""
        if gpu_index not in self.gpus:
            return None
        
        gpu = self.gpus[gpu_index]
        
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_index)
            
            # Temperatur
            gpu.temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            
            # Power
            try:
                gpu.power_watts = pynvml.nvmlDeviceGetPowerUsage(handle) // 1000
            except:
                gpu.power_watts = 0
            
            # Fan
            try:
                gpu.fan_speed = pynvml.nvmlDeviceGetFanSpeed(handle)
            except:
                gpu.fan_speed = 0
            
            pynvml.nvmlShutdown()
            
            # Health Status bestimmen
            gpu.health = self._determine_health(gpu)
            
        except Exception as e:
            logger.error(f"GPU {gpu_index} Stats Fehler: {e}")
        
        return gpu
    
    def _determine_health(self, gpu: GPUState) -> GPUHealth:
        """Bestimmt den Gesundheitsstatus basierend auf Temperatur"""
        temp = gpu.temperature
        
        if temp >= gpu.max_temp:
            return GPUHealth.THERMAL_LIMIT
        elif temp >= gpu.warning_temp:
            return GPUHealth.CRITICAL
        elif temp >= gpu.target_temp:
            return GPUHealth.WARNING
        elif temp >= gpu.target_temp - 10:
            return GPUHealth.GOOD
        else:
            return GPUHealth.EXCELLENT
    
    def get_health_color(self, gpu: GPUState) -> Tuple[int, int, int]:
        """Gibt RGB Farbe für Health Status zurück"""
        colors = {
            GPUHealth.EXCELLENT: (0, 200, 0),    # Grün
            GPUHealth.GOOD: (100, 200, 0),       # Hellgrün
            GPUHealth.WARNING: (255, 200, 0),    # Gelb
            GPUHealth.CRITICAL: (255, 100, 0),   # Orange
            GPUHealth.THERMAL_LIMIT: (255, 0, 0), # Rot
        }
        return colors.get(gpu.health, (128, 128, 128))
    
    def get_health_emoji(self, gpu: GPUState) -> str:
        """Gibt Emoji für Health Status zurück"""
        emojis = {
            GPUHealth.EXCELLENT: "🟢",
            GPUHealth.GOOD: "🟢",
            GPUHealth.WARNING: "🟡",
            GPUHealth.CRITICAL: "🔴",
            GPUHealth.THERMAL_LIMIT: "🔥",
        }
        return emojis.get(gpu.health, "⚪")
    
    def get_temp_color(self, temp: int, gpu: GPUState = None) -> Tuple[int, int, int]:
        """Gibt RGB Farbe für Temperatur zurück"""
        if gpu:
            if temp >= gpu.max_temp:
                return (255, 0, 0)      # Rot
            elif temp >= gpu.warning_temp:
                return (255, 100, 0)    # Orange
            elif temp >= gpu.target_temp:
                return (255, 200, 0)    # Gelb
            elif temp >= 60:
                return (100, 200, 0)    # Hellgrün
            else:
                return (0, 200, 0)      # Grün
        else:
            # Default Grenzen
            if temp >= 80:
                return (255, 0, 0)
            elif temp >= 75:
                return (255, 100, 0)
            elif temp >= 70:
                return (255, 200, 0)
            elif temp >= 60:
                return (100, 200, 0)
            else:
                return (0, 200, 0)
    
    # =========================================================================
    # OC PROFILE MANAGEMENT
    # =========================================================================
    
    def set_profile(self, gpu_index: int, profile: OCProfile, coin: str = None):
        """Setzt OC-Profile für eine GPU"""
        if gpu_index not in self.gpus:
            return
        
        gpu = self.gpus[gpu_index]
        old_profile = gpu.current_profile
        gpu.current_profile = profile
        
        # OC-Settings anwenden wenn Coin bekannt
        coin = coin or gpu.current_coin
        if coin and coin in gpu.oc_settings:
            settings = gpu.oc_settings[coin].get(profile.value)
            if settings:
                self._apply_oc_settings(gpu_index, settings)
        
        self._last_oc_change[gpu_index] = datetime.now()
        logger.info(f"GPU {gpu_index}: Profile {old_profile.value} -> {profile.value}")
        self._save_config()
        self._notify_callbacks()
    
    def set_tuning_mode(self, gpu_index: int, mode: TuningMode):
        """Setzt den Tuning-Modus für eine GPU"""
        if gpu_index not in self.gpus:
            return
        
        self.gpus[gpu_index].tuning_mode = mode
        logger.info(f"GPU {gpu_index}: Tuning Mode = {mode.value}")
        self._save_config()
    
    def _apply_oc_settings(self, gpu_index: int, settings: OCSettings):
        """Wendet OC-Settings an (via MSI Afterburner)"""
        if not self._oc_manager:
            try:
                from msi_afterburner import MSIAfterburner
                self._oc_manager = MSIAfterburner()
            except:
                logger.warning("MSI Afterburner nicht verfügbar")
                return
        
        try:
            self._oc_manager.set_gpu_settings(
                gpu_index=gpu_index,
                core_clock=settings.core_clock,
                mem_clock=settings.mem_clock,
                power_limit=settings.power_limit,
                fan_speed=settings.fan_speed
            )
            logger.info(f"GPU {gpu_index}: OC angewendet - Core {settings.core_clock:+d}, "
                       f"Mem {settings.mem_clock:+d}, PL {settings.power_limit}%")
        except Exception as e:
            logger.error(f"OC-Fehler GPU {gpu_index}: {e}")
    
    def load_oc_profiles_for_coin(self, gpu_index: int, coin: str, 
                                   base_settings: Dict = None) -> bool:
        """
        Lädt/Generiert OC-Profile für einen Coin
        
        Args:
            gpu_index: GPU Index
            coin: Coin Ticker
            base_settings: Basis-Settings (Medium) von hashrate.no
        """
        if gpu_index not in self.gpus:
            return False
        
        gpu = self.gpus[gpu_index]
        
        if not base_settings:
            # Versuche von GPU Profit Manager zu laden
            try:
                from gpu_profit_manager import get_gpu_profit_manager
                manager = get_gpu_profit_manager()
                manager.load_oc_profiles_from_hashrate_no(gpu_index, coin)
                # TODO: Sync mit diesem System
            except:
                pass
            return False
        
        # Generiere LOW/MEDIUM/HIGH Profile
        base_core = base_settings.get("core", 0)
        base_mem = base_settings.get("mem", 0)
        base_pl = base_settings.get("pl", 100)
        base_fan = base_settings.get("fan", 70)
        base_hash = base_settings.get("hashrate", 0)
        base_power = base_settings.get("power", 100)
        unit = base_settings.get("unit", "MH/s")
        
        gpu.oc_settings[coin] = {
            "low": OCSettings(
                core_clock=int(base_core * 0.5),
                mem_clock=int(base_mem * 0.7),
                power_limit=max(50, base_pl - 15),
                fan_speed=min(100, base_fan + 10),
                expected_hashrate=base_hash * 0.80,
                expected_power=int(base_power * 0.70),
                expected_temp=55,
                hashrate_unit=unit
            ),
            "medium": OCSettings(
                core_clock=base_core,
                mem_clock=base_mem,
                power_limit=base_pl,
                fan_speed=base_fan,
                expected_hashrate=base_hash,
                expected_power=base_power,
                expected_temp=65,
                hashrate_unit=unit
            ),
            "high": OCSettings(
                core_clock=int(base_core * 1.2) if base_core > 0 else 50,
                mem_clock=int(base_mem * 1.15),
                power_limit=min(100, base_pl + 10),
                fan_speed=min(100, base_fan + 15),
                expected_hashrate=base_hash * 1.05,
                expected_power=int(base_power * 1.15),
                expected_temp=75,
                hashrate_unit=unit
            ),
        }
        
        self._save_config()
        logger.info(f"GPU {gpu_index}: OC-Profile für {coin} generiert")
        return True
    
    # =========================================================================
    # AUTO-TUNING LOGIK
    # =========================================================================
    
    def auto_tune(self, gpu_index: int) -> Optional[OCProfile]:
        """
        Führt Auto-Tuning für eine GPU durch
        
        Returns:
            Neues Profile oder None wenn keine Änderung
        """
        if gpu_index not in self.gpus:
            return None
        
        gpu = self.gpus[gpu_index]
        
        if not gpu.enabled:
            return None
        
        if gpu.tuning_mode == TuningMode.MANUAL:
            return None
        
        # Nicht zu schnell wechseln (Stabilisierungszeit)
        if gpu_index in self._last_oc_change:
            elapsed = (datetime.now() - self._last_oc_change[gpu_index]).total_seconds()
            if elapsed < self.STABILIZE_TIME:
                return None
        
        # Aktuellen Status holen
        self.update_gpu_stats(gpu_index)
        
        current_profile = gpu.current_profile
        new_profile = current_profile
        
        # =====================================================================
        # TUNING LOGIK
        # =====================================================================
        
        if gpu.tuning_mode == TuningMode.TEMP_SAFE:
            # Nur Temperatur-basiert
            new_profile = self._tune_for_temp(gpu)
        
        elif gpu.tuning_mode == TuningMode.EFFICIENCY:
            # Beste Effizienz (mit Temp-Limit)
            new_profile = self._tune_for_efficiency(gpu)
        
        elif gpu.tuning_mode == TuningMode.MAX_HASH:
            # Maximale Hashrate (mit Temp-Limit)
            new_profile = self._tune_for_max_hash(gpu)
        
        elif gpu.tuning_mode == TuningMode.SMART:
            # Intelligente Balance
            new_profile = self._tune_smart(gpu)
        
        # Profile wechseln wenn nötig
        if new_profile != current_profile:
            self.set_profile(gpu_index, new_profile)
            return new_profile
        
        return None
    
    def _tune_for_temp(self, gpu: GPUState) -> OCProfile:
        """Tuning nur basierend auf Temperatur"""
        temp = gpu.temperature
        current = gpu.current_profile
        
        # KRITISCH: Sofort runter!
        if temp >= gpu.max_temp:
            return OCProfile.LOW
        
        # Zu warm -> runterschalten
        if temp >= gpu.warning_temp:
            if current == OCProfile.HIGH:
                return OCProfile.MEDIUM
            elif current == OCProfile.MEDIUM:
                return OCProfile.LOW
        
        # Warm aber OK -> Medium halten
        if temp >= gpu.target_temp:
            if current == OCProfile.HIGH:
                return OCProfile.MEDIUM
            return current
        
        # Kühl -> kann hoch
        if temp <= gpu.target_temp - 10:
            if current == OCProfile.LOW:
                return OCProfile.MEDIUM
            elif current == OCProfile.MEDIUM:
                return OCProfile.HIGH
        
        return current
    
    def _tune_for_efficiency(self, gpu: GPUState) -> OCProfile:
        """Tuning für beste Effizienz (H/W)"""
        # Erst Temperatur checken
        temp_profile = self._tune_for_temp(gpu)
        
        # Wenn Temp kritisch, das hat Vorrang
        if gpu.temperature >= gpu.warning_temp:
            return temp_profile
        
        # Effizienz aus Benchmarks vergleichen
        coin = gpu.current_coin
        if coin in gpu.benchmarks:
            best_efficiency = 0
            best_profile = gpu.current_profile
            
            for profile_name, result in gpu.benchmarks[coin].items():
                if result.efficiency > best_efficiency:
                    # Aber nur wenn Temp OK war
                    if result.max_temp < gpu.warning_temp:
                        best_efficiency = result.efficiency
                        best_profile = OCProfile(profile_name)
            
            return best_profile
        
        # Ohne Benchmarks: LOW ist meist effizienter
        return OCProfile.LOW if gpu.temperature < gpu.target_temp else temp_profile
    
    def _tune_for_max_hash(self, gpu: GPUState) -> OCProfile:
        """Tuning für maximale Hashrate"""
        # Erst Temperatur checken
        if gpu.temperature >= gpu.max_temp:
            return OCProfile.LOW  # Notfall!
        
        if gpu.temperature >= gpu.warning_temp:
            return OCProfile.MEDIUM
        
        # Sonst: HIGH wenn möglich
        return OCProfile.HIGH
    
    def _tune_smart(self, gpu: GPUState) -> OCProfile:
        """
        Intelligentes Tuning - Balance aus:
        - Temperatur (Sicherheit)
        - Hashrate (Performance)
        - Effizienz (Stromkosten)
        - Stabilität (keine Crashes)
        """
        temp = gpu.temperature
        current = gpu.current_profile
        coin = gpu.current_coin
        
        # PRIORITÄT 1: Temperatur-Sicherheit
        if temp >= gpu.max_temp:
            logger.warning(f"GPU {gpu.index}: THERMAL LIMIT! -> LOW")
            return OCProfile.LOW
        
        if temp >= gpu.warning_temp:
            if current == OCProfile.HIGH:
                logger.info(f"GPU {gpu.index}: Zu warm ({temp}°C) -> MEDIUM")
                return OCProfile.MEDIUM
            elif current == OCProfile.MEDIUM and temp >= gpu.max_temp - 3:
                logger.info(f"GPU {gpu.index}: Sehr warm ({temp}°C) -> LOW")
                return OCProfile.LOW
        
        # PRIORITÄT 2: Benchmark-Daten nutzen wenn vorhanden
        if coin in gpu.benchmarks:
            benchmarks = gpu.benchmarks[coin]
            
            # Finde bestes Profile basierend auf Score
            best_score = 0
            best_profile = current
            
            for profile_name, result in benchmarks.items():
                # Score = Hashrate * Stabilität * Temp-Factor
                temp_factor = 1.0
                if result.max_temp >= gpu.warning_temp:
                    temp_factor = 0.5  # Penalty für heiße Profile
                elif result.max_temp >= gpu.target_temp:
                    temp_factor = 0.8
                
                score = result.avg_hashrate * (result.stability / 100) * temp_factor
                
                if score > best_score:
                    best_score = score
                    best_profile = OCProfile(profile_name)
            
            # Nur wechseln wenn aktuelles Profile deutlich schlechter
            if best_profile != current:
                current_score = 0
                if current.value in benchmarks:
                    r = benchmarks[current.value]
                    current_score = r.avg_hashrate * (r.stability / 100)
                
                # Nur wechseln wenn >5% besser
                if best_score > current_score * 1.05:
                    return best_profile
        
        # PRIORITÄT 3: Temperatur-Raum nutzen
        if temp <= gpu.target_temp - 15:
            # Sehr kühl -> HIGH probieren
            if current != OCProfile.HIGH:
                logger.info(f"GPU {gpu.index}: Kühl ({temp}°C) -> HIGH testen")
                return OCProfile.HIGH
        
        elif temp <= gpu.target_temp - 5:
            # Kühl -> mindestens MEDIUM
            if current == OCProfile.LOW:
                return OCProfile.MEDIUM
        
        return current
    
    # =========================================================================
    # BENCHMARK SYSTEM
    # =========================================================================
    
    def run_benchmark(self, gpu_index: int, coin: str, profile: OCProfile,
                     duration: int = 60, callback: Callable = None) -> Optional[BenchmarkResult]:
        """
        Führt einen Benchmark für ein bestimmtes Profile durch
        
        Args:
            gpu_index: GPU Index
            coin: Coin zu benchmarken
            profile: OC-Profile zu testen
            duration: Benchmark-Dauer in Sekunden
            callback: Callback für Fortschritt (progress: float, message: str)
        
        Returns:
            BenchmarkResult oder None bei Fehler
        """
        if gpu_index not in self.gpus:
            return None
        
        gpu = self.gpus[gpu_index]
        
        logger.info(f"Benchmark Start: GPU {gpu_index}, {coin}, Profile {profile.value}, {duration}s")
        
        if callback:
            callback(0.0, f"Setze Profile {profile.value}...")
        
        # 1. Profile setzen
        old_profile = gpu.current_profile
        self.set_profile(gpu_index, profile, coin)
        
        # 2. Warten bis stabil (30s)
        if callback:
            callback(0.1, "Warte auf Stabilisierung...")
        time.sleep(self.STABILIZE_TIME)
        
        # 3. Samples sammeln
        samples: List[PerformanceSnapshot] = []
        start_time = time.time()
        sample_interval = 5  # Alle 5 Sekunden
        
        while time.time() - start_time < duration:
            # GPU Stats aktualisieren
            self.update_gpu_stats(gpu_index)
            
            # Hashrate vom Miner holen
            hashrate = self._get_miner_hashrate(gpu_index)
            
            # Effizienz berechnen
            efficiency = hashrate / gpu.power_watts if gpu.power_watts > 0 else 0
            
            snapshot = PerformanceSnapshot(
                timestamp=datetime.now(),
                hashrate=hashrate,
                hashrate_unit=gpu.hashrate_unit,
                temperature=gpu.temperature,
                power_watts=gpu.power_watts,
                fan_speed=gpu.fan_speed,
                efficiency=efficiency,
                profile=profile.value,
                coin=coin,
                stable=True
            )
            samples.append(snapshot)
            
            progress = (time.time() - start_time) / duration
            if callback:
                callback(0.1 + progress * 0.8, f"Benchmark... {hashrate:.1f} {gpu.hashrate_unit}, {gpu.temperature}°C")
            
            time.sleep(sample_interval)
        
        # 4. Ergebnis berechnen
        if callback:
            callback(0.95, "Berechne Ergebnis...")
        
        if not samples:
            logger.error("Keine Samples gesammelt!")
            return None
        
        hashrates = [s.hashrate for s in samples]
        temps = [s.temperature for s in samples]
        powers = [s.power_watts for s in samples]
        efficiencies = [s.efficiency for s in samples]
        
        # Stabilität = wie konstant war die Hashrate?
        if len(hashrates) > 1:
            hashrate_std = statistics.stdev(hashrates)
            avg_hash = statistics.mean(hashrates)
            stability = max(0, 100 - (hashrate_std / avg_hash * 100)) if avg_hash > 0 else 0
        else:
            stability = 100
        
        result = BenchmarkResult(
            coin=coin,
            algorithm=gpu.oc_settings.get(coin, {}).get(profile.value, OCSettings()).hashrate_unit,
            profile=profile.value,
            gpu_index=gpu_index,
            duration_seconds=duration,
            avg_hashrate=statistics.mean(hashrates),
            min_hashrate=min(hashrates),
            max_hashrate=max(hashrates),
            hashrate_unit=gpu.hashrate_unit,
            avg_temp=int(statistics.mean(temps)),
            max_temp=max(temps),
            avg_power=int(statistics.mean(powers)),
            efficiency=statistics.mean(efficiencies),
            stability=round(stability, 1),
            timestamp=datetime.now().isoformat(),
            recommended=False
        )
        
        # 5. Ergebnis speichern
        if coin not in gpu.benchmarks:
            gpu.benchmarks[coin] = {}
        gpu.benchmarks[coin][profile.value] = result
        
        # 6. Bestes Profile markieren
        self._update_recommended_profile(gpu_index, coin)
        
        self._save_config()
        
        if callback:
            callback(1.0, f"Fertig: {result.avg_hashrate:.1f} {result.hashrate_unit}")
        
        logger.info(f"Benchmark Ergebnis: {result.avg_hashrate:.1f} {result.hashrate_unit}, "
                   f"{result.avg_temp}°C, Effizienz: {result.efficiency:.2f} H/W")
        
        return result
    
    def run_full_benchmark(self, gpu_index: int, coin: str, 
                          duration_per_profile: int = 60,
                          callback: Callable = None) -> Dict[str, BenchmarkResult]:
        """
        Führt Benchmark für ALLE Profile durch (LOW, MEDIUM, HIGH)
        
        Returns:
            Dict mit allen Ergebnissen
        """
        results = {}
        
        for i, profile in enumerate([OCProfile.LOW, OCProfile.MEDIUM, OCProfile.HIGH]):
            if callback:
                callback(i / 3, f"Teste {profile.value.upper()}...")
            
            result = self.run_benchmark(
                gpu_index, coin, profile, duration_per_profile,
                callback=lambda p, m: callback((i + p) / 3, m) if callback else None
            )
            
            if result:
                results[profile.value] = result
        
        return results
    
    def _update_recommended_profile(self, gpu_index: int, coin: str):
        """Aktualisiert das empfohlene Profile basierend auf Benchmarks"""
        if gpu_index not in self.gpus:
            return
        
        gpu = self.gpus[gpu_index]
        
        if coin not in gpu.benchmarks:
            return
        
        benchmarks = gpu.benchmarks[coin]
        
        # Reset alle recommended flags
        for result in benchmarks.values():
            result.recommended = False
        
        # Finde bestes: Höchste Hashrate mit Temp < warning und Stability > 90%
        best_profile = None
        best_hashrate = 0
        
        for profile_name, result in benchmarks.items():
            if result.max_temp < gpu.warning_temp and result.stability >= 90:
                if result.avg_hashrate > best_hashrate:
                    best_hashrate = result.avg_hashrate
                    best_profile = profile_name
        
        if best_profile:
            benchmarks[best_profile].recommended = True
            logger.info(f"GPU {gpu_index} {coin}: Empfohlenes Profile = {best_profile}")
    
    def _get_miner_hashrate(self, gpu_index: int) -> float:
        """Holt aktuelle Hashrate vom Miner"""
        # Versuche Miner API
        if self._miner_api:
            try:
                stats = self._miner_api.get_gpu_stats(gpu_index)
                if stats:
                    return stats.get("hashrate", 0)
            except:
                pass
        
        # Fallback: Aus GPU State
        if gpu_index in self.gpus:
            return self.gpus[gpu_index].hashrate
        
        return 0.0
    
    # =========================================================================
    # MONITORING THREAD
    # =========================================================================
    
    def start(self):
        """Startet den Auto-Tuner Thread"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Auto-Tuner gestartet")
    
    def stop(self):
        """Stoppt den Auto-Tuner Thread"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-Tuner gestoppt")
    
    def _monitor_loop(self):
        """Haupt-Monitoring Loop"""
        while self._running:
            try:
                for gpu_index in list(self.gpus.keys()):
                    # Stats aktualisieren
                    self.update_gpu_stats(gpu_index)
                    
                    # Auto-Tuning
                    self.auto_tune(gpu_index)
                    
                    # Snapshot für History
                    gpu = self.gpus[gpu_index]
                    if gpu.hashrate > 0:
                        efficiency = gpu.hashrate / gpu.power_watts if gpu.power_watts > 0 else 0
                        snapshot = PerformanceSnapshot(
                            timestamp=datetime.now(),
                            hashrate=gpu.hashrate,
                            hashrate_unit=gpu.hashrate_unit,
                            temperature=gpu.temperature,
                            power_watts=gpu.power_watts,
                            fan_speed=gpu.fan_speed,
                            efficiency=efficiency,
                            profile=gpu.current_profile.value,
                            coin=gpu.current_coin
                        )
                        gpu.history.append(snapshot)
                
                self._notify_callbacks()
                
            except Exception as e:
                logger.error(f"Monitor Loop Fehler: {e}")
            
            time.sleep(self.UPDATE_INTERVAL)
    
    # =========================================================================
    # CALLBACKS
    # =========================================================================
    
    def add_callback(self, callback: Callable):
        """Fügt Callback für Updates hinzu"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable):
        """Entfernt Callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_callbacks(self):
        """Benachrichtigt alle Callbacks"""
        for callback in self._callbacks:
            try:
                callback(self.gpus)
            except Exception as e:
                logger.error(f"Callback Fehler: {e}")


# ============================================================================
# SINGLETON
# ============================================================================

_auto_tuner: Optional[GPUAutoTuner] = None

def get_auto_tuner() -> GPUAutoTuner:
    """Gibt globale Auto-Tuner Instanz zurück"""
    global _auto_tuner
    if _auto_tuner is None:
        _auto_tuner = GPUAutoTuner()
    return _auto_tuner


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    tuner = GPUAutoTuner()
    gpus = tuner.detect_gpus()
    
    print(f"\n{'='*60}")
    print(f"GPU AUTO-TUNER TEST")
    print(f"{'='*60}")
    
    for gpu in gpus:
        tuner.update_gpu_stats(gpu.index)
        print(f"\nGPU {gpu.index}: {gpu.name}")
        print(f"  Temperatur: {gpu.temperature}°C {tuner.get_health_emoji(gpu)}")
        print(f"  Power: {gpu.power_watts}W")
        print(f"  Fan: {gpu.fan_speed}%")
        print(f"  Health: {gpu.health.value}")
        print(f"  Profile: {gpu.current_profile.value}")
        print(f"  Tuning Mode: {gpu.tuning_mode.value}")
