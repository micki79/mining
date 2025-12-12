#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Overclock Manager - GPU Overclocking via NVML
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Automatisches Overclocking via NVML
- Integration mit hashrate.no für optimale Settings
- Per-Algorithmus Profile
- Sichere Limits und Validierung
- Backup und Restore von Default-Settings
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# NVML Import
try:
    from pynvml import *
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    print("⚠️ nvidia-ml-py nicht installiert. Installiere mit: pip install nvidia-ml-py")

# Lokale Imports
try:
    from hashrateno_api import HashrateNoAPI, OCSettings
except ImportError:
    HashrateNoAPI = None
    OCSettings = None

logger = logging.getLogger(__name__)


@dataclass
class GPUDefaults:
    """Standard-Einstellungen einer GPU (für Restore)"""
    index: int
    name: str
    power_limit_default: int  # mW
    power_limit_min: int
    power_limit_max: int
    core_clock_max: int
    memory_clock_max: int


class OverclockManager:
    """
    Verwaltet GPU Overclocking via NVML.
    
    Verwendung:
        oc_manager = OverclockManager()
        oc_manager.initialize()
        
        # Automatisches OC für einen Coin
        oc_manager.apply_auto_oc(0, "RVN")  # GPU 0, RVN Mining
        
        # Manuelles OC
        oc_manager.set_power_limit(0, 150)  # 150W
        oc_manager.set_clock_offset(0, core=100, memory=500)
        
        # Reset
        oc_manager.reset_gpu(0)
        
        oc_manager.shutdown()
    
    WICHTIG: Erfordert Administrator-Rechte für Overclocking!
    """
    
    def __init__(self, hashrate_api_key: str = "", profiles_path: str = "oc_profiles.json"):
        """
        Initialisiert den Overclock Manager.
        
        Args:
            hashrate_api_key: hashrate.no API Key für Auto-OC
            profiles_path: Pfad zur Profile-Datei
        """
        self.profiles_path = Path(profiles_path)
        self._initialized = False
        self._gpu_count = 0
        self._gpu_handles: List[Any] = []
        self._gpu_defaults: Dict[int, GPUDefaults] = {}
        self._current_profiles: Dict[int, str] = {}  # GPU -> aktiver Algorithmus
        
        # hashrate.no API Client
        if HashrateNoAPI:
            self._api = HashrateNoAPI(api_key=hashrate_api_key)
        else:
            self._api = None
            logger.warning("hashrateno_api nicht verfügbar")
        
        # Benutzerdefinierte Profile laden
        self._profiles = self._load_profiles()
    
    def _load_profiles(self) -> Dict[str, Any]:
        """Lädt benutzerdefinierte OC-Profile"""
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Fehler beim Laden der Profile: {e}")
        return {}
    
    def save_profiles(self):
        """Speichert OC-Profile"""
        try:
            with open(self.profiles_path, 'w', encoding='utf-8') as f:
                json.dump(self._profiles, f, indent=2)
            logger.info(f"Profile gespeichert: {self.profiles_path}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Profile: {e}")
    
    def initialize(self) -> bool:
        """
        Initialisiert NVML und liest GPU-Defaults.
        
        Returns:
            True wenn erfolgreich
        """
        if not NVML_AVAILABLE:
            logger.error("NVML nicht verfügbar")
            return False
        
        try:
            nvmlInit()
            self._gpu_count = nvmlDeviceGetCount()
            
            # Handles und Defaults für alle GPUs
            for i in range(self._gpu_count):
                handle = nvmlDeviceGetHandleByIndex(i)
                self._gpu_handles.append(handle)
                
                # Defaults speichern
                name = nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                
                defaults = GPUDefaults(
                    index=i,
                    name=name,
                    power_limit_default=0,
                    power_limit_min=0,
                    power_limit_max=0,
                    core_clock_max=0,
                    memory_clock_max=0,
                )
                
                try:
                    defaults.power_limit_default = nvmlDeviceGetPowerManagementDefaultLimit(handle)
                except NVMLError:
                    pass
                
                try:
                    min_limit, max_limit = nvmlDeviceGetPowerManagementLimitConstraints(handle)
                    defaults.power_limit_min = min_limit
                    defaults.power_limit_max = max_limit
                except NVMLError:
                    pass
                
                try:
                    defaults.core_clock_max = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS)
                except NVMLError:
                    pass
                
                try:
                    defaults.memory_clock_max = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM)
                except NVMLError:
                    pass
                
                self._gpu_defaults[i] = defaults
            
            self._initialized = True
            logger.info(f"OverclockManager initialisiert: {self._gpu_count} GPU(s)")
            return True
            
        except NVMLError as e:
            logger.error(f"NVML Initialisierung fehlgeschlagen: {e}")
            return False
    
    def shutdown(self):
        """Beendet NVML"""
        if self._initialized and NVML_AVAILABLE:
            try:
                nvmlShutdown()
                self._initialized = False
                logger.info("OverclockManager heruntergefahren")
            except NVMLError as e:
                logger.error(f"NVML Shutdown Fehler: {e}")
    
    def get_gpu_count(self) -> int:
        """Gibt die Anzahl der GPUs zurück"""
        return self._gpu_count
    
    def get_gpu_info(self, gpu_index: int) -> Optional[GPUDefaults]:
        """Gibt die Default-Infos einer GPU zurück"""
        return self._gpu_defaults.get(gpu_index)
    
    def set_power_limit(self, gpu_index: int, power_watts: int) -> bool:
        """
        Setzt das Power Limit einer GPU.
        
        Args:
            gpu_index: GPU Index
            power_watts: Power Limit in Watt
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        handle = self._gpu_handles[gpu_index]
        defaults = self._gpu_defaults.get(gpu_index)
        
        # In Milliwatt konvertieren
        power_mw = power_watts * 1000
        
        # Validierung
        if defaults:
            if power_mw < defaults.power_limit_min:
                power_mw = defaults.power_limit_min
                logger.warning(f"GPU {gpu_index}: Power Limit auf Minimum angepasst: {power_mw/1000}W")
            elif power_mw > defaults.power_limit_max:
                power_mw = defaults.power_limit_max
                logger.warning(f"GPU {gpu_index}: Power Limit auf Maximum angepasst: {power_mw/1000}W")
        
        try:
            nvmlDeviceSetPowerManagementLimit(handle, power_mw)
            logger.info(f"GPU {gpu_index}: Power Limit gesetzt auf {power_watts}W")
            return True
        except NVMLError as e:
            logger.error(f"GPU {gpu_index}: Fehler beim Setzen des Power Limits: {e}")
            return False
    
    def set_power_limit_percent(self, gpu_index: int, percent: int) -> bool:
        """
        Setzt das Power Limit als Prozent vom Default.
        
        Args:
            gpu_index: GPU Index
            percent: Prozent (z.B. 70 für 70%)
            
        Returns:
            True wenn erfolgreich
        """
        defaults = self._gpu_defaults.get(gpu_index)
        if not defaults or defaults.power_limit_default == 0:
            logger.error(f"GPU {gpu_index}: Keine Default-Werte verfügbar")
            return False
        
        power_watts = int((defaults.power_limit_default / 1000) * (percent / 100))
        return self.set_power_limit(gpu_index, power_watts)
    
    def set_clock_offset(self, gpu_index: int, core_offset: int = 0, memory_offset: int = 0) -> bool:
        """
        Setzt Clock Offsets für Core und Memory.
        
        WICHTIG: Erfordert Admin-Rechte und unterstützte GPU!
        
        Args:
            gpu_index: GPU Index
            core_offset: Core Clock Offset in MHz (kann negativ sein)
            memory_offset: Memory Clock Offset in MHz
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        handle = self._gpu_handles[gpu_index]
        success = True
        
        # Core Clock Offset
        try:
            # NVML verwendet nvmlDeviceSetGpcClkVfOffset für neuere GPUs
            nvmlDeviceSetGpcClkVfOffset(handle, core_offset)
            logger.info(f"GPU {gpu_index}: Core Offset gesetzt auf {core_offset:+d} MHz")
        except NVMLError as e:
            # Fallback für ältere Methode oder nicht unterstützt
            logger.warning(f"GPU {gpu_index}: Core Offset nicht unterstützt: {e}")
            success = False
        except AttributeError:
            logger.warning(f"GPU {gpu_index}: nvmlDeviceSetGpcClkVfOffset nicht verfügbar")
            success = False
        
        # Memory Clock Offset
        # WICHTIG: NVML verdoppelt den Memory Offset intern bei einigen GPUs
        try:
            nvmlDeviceSetMemClkVfOffset(handle, memory_offset)
            logger.info(f"GPU {gpu_index}: Memory Offset gesetzt auf {memory_offset:+d} MHz")
        except NVMLError as e:
            logger.warning(f"GPU {gpu_index}: Memory Offset nicht unterstützt: {e}")
            success = False
        except AttributeError:
            logger.warning(f"GPU {gpu_index}: nvmlDeviceSetMemClkVfOffset nicht verfügbar")
            success = False
        
        return success
    
    def set_locked_clocks(self, gpu_index: int, core_clock: int, memory_clock: int) -> bool:
        """
        Setzt feste Clock-Speeds (locked clocks).
        
        Args:
            gpu_index: GPU Index
            core_clock: Fester Core Clock in MHz
            memory_clock: Fester Memory Clock in MHz
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        handle = self._gpu_handles[gpu_index]
        
        try:
            # GPU Clocks locken
            nvmlDeviceSetGpuLockedClocks(handle, core_clock, core_clock)
            logger.info(f"GPU {gpu_index}: Core Clock gelockt auf {core_clock} MHz")
        except NVMLError as e:
            logger.warning(f"GPU {gpu_index}: Clock Locking nicht unterstützt: {e}")
            return False
        except AttributeError:
            logger.warning(f"GPU {gpu_index}: nvmlDeviceSetGpuLockedClocks nicht verfügbar")
            return False
        
        return True
    
    def reset_clocks(self, gpu_index: int) -> bool:
        """
        Setzt Clocks auf Default zurück.
        
        Args:
            gpu_index: GPU Index
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        handle = self._gpu_handles[gpu_index]
        
        try:
            # Clock Offsets zurücksetzen
            try:
                nvmlDeviceSetGpcClkVfOffset(handle, 0)
            except:
                pass
            
            try:
                nvmlDeviceSetMemClkVfOffset(handle, 0)
            except:
                pass
            
            # Locked Clocks aufheben
            try:
                nvmlDeviceResetGpuLockedClocks(handle)
            except:
                pass
            
            logger.info(f"GPU {gpu_index}: Clocks zurückgesetzt")
            return True
            
        except NVMLError as e:
            logger.error(f"GPU {gpu_index}: Fehler beim Zurücksetzen der Clocks: {e}")
            return False
    
    def reset_gpu(self, gpu_index: int) -> bool:
        """
        Setzt alle Einstellungen einer GPU auf Default zurück.
        
        Args:
            gpu_index: GPU Index
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        defaults = self._gpu_defaults.get(gpu_index)
        if not defaults:
            return False
        
        success = True
        
        # Power Limit zurücksetzen
        if defaults.power_limit_default > 0:
            if not self.set_power_limit(gpu_index, defaults.power_limit_default // 1000):
                success = False
        
        # Clocks zurücksetzen
        if not self.reset_clocks(gpu_index):
            success = False
        
        # Aktives Profil entfernen
        if gpu_index in self._current_profiles:
            del self._current_profiles[gpu_index]
        
        logger.info(f"GPU {gpu_index}: Alle Einstellungen zurückgesetzt")
        return success
    
    def reset_all_gpus(self) -> bool:
        """Setzt alle GPUs auf Default zurück"""
        success = True
        for i in range(self._gpu_count):
            if not self.reset_gpu(i):
                success = False
        return success
    
    def apply_auto_oc(self, gpu_index: int, coin_or_algo: str) -> bool:
        """
        Wendet automatisches Overclocking basierend auf hashrate.no Daten an.
        
        Args:
            gpu_index: GPU Index
            coin_or_algo: Coin (z.B. "RVN") oder Algorithmus (z.B. "kawpow")
            
        Returns:
            True wenn erfolgreich
        """
        if not self._initialized or gpu_index >= len(self._gpu_handles):
            return False
        
        defaults = self._gpu_defaults.get(gpu_index)
        if not defaults:
            return False
        
        # OC-Settings von hashrate.no holen
        if self._api:
            oc_settings = self._api.get_oc_settings(defaults.name, coin_or_algo)
        else:
            logger.error("hashrate.no API nicht verfügbar")
            return False
        
        logger.info(f"GPU {gpu_index}: Auto-OC für {coin_or_algo} ({oc_settings.source})")
        logger.info(f"   Core: {oc_settings.core_clock_offset:+d} MHz")
        logger.info(f"   Memory: {oc_settings.memory_clock_offset:+d} MHz")
        logger.info(f"   Power: {oc_settings.power_limit_percent}%")
        
        # Anwenden
        success = True
        
        # Power Limit
        if oc_settings.power_limit_watts > 0:
            if not self.set_power_limit(gpu_index, oc_settings.power_limit_watts):
                success = False
        elif oc_settings.power_limit_percent > 0:
            if not self.set_power_limit_percent(gpu_index, oc_settings.power_limit_percent):
                success = False
        
        # Clock Offsets
        if oc_settings.core_clock_offset != 0 or oc_settings.memory_clock_offset != 0:
            if not self.set_clock_offset(gpu_index, oc_settings.core_clock_offset, oc_settings.memory_clock_offset):
                # Bei Fehler trotzdem fortfahren (nicht alle GPUs unterstützen Offsets via NVML)
                pass
        
        # Aktives Profil merken
        self._current_profiles[gpu_index] = oc_settings.algorithm
        
        return success
    
    def apply_auto_oc_all(self, coin_or_algo: str) -> bool:
        """
        Wendet Auto-OC auf alle GPUs an.
        
        Args:
            coin_or_algo: Coin oder Algorithmus
            
        Returns:
            True wenn alle erfolgreich
        """
        success = True
        for i in range(self._gpu_count):
            if not self.apply_auto_oc(i, coin_or_algo):
                success = False
        return success
    
    def get_current_profile(self, gpu_index: int) -> Optional[str]:
        """Gibt den aktuell aktiven Algorithmus für eine GPU zurück"""
        return self._current_profiles.get(gpu_index)
    
    def save_custom_profile(
        self, 
        name: str, 
        gpu_name: str,
        algorithm: str,
        core_offset: int,
        memory_offset: int,
        power_limit_percent: int,
        fan_speed: int = 0
    ):
        """
        Speichert ein benutzerdefiniertes OC-Profil.
        
        Args:
            name: Profilname
            gpu_name: GPU Bezeichnung
            algorithm: Algorithmus
            core_offset: Core Clock Offset
            memory_offset: Memory Clock Offset
            power_limit_percent: Power Limit in Prozent
            fan_speed: Lüfter-Geschwindigkeit (0 = Auto)
        """
        key = f"{gpu_name}_{algorithm}"
        
        self._profiles[key] = {
            'name': name,
            'gpu_name': gpu_name,
            'algorithm': algorithm,
            'core_clock_offset': core_offset,
            'memory_clock_offset': memory_offset,
            'power_limit_percent': power_limit_percent,
            'fan_speed': fan_speed,
            'created': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        self.save_profiles()
        logger.info(f"Profil gespeichert: {name}")
    
    def apply_custom_profile(self, gpu_index: int, profile_key: str) -> bool:
        """
        Wendet ein benutzerdefiniertes Profil an.
        
        Args:
            gpu_index: GPU Index
            profile_key: Profil-Key (gpu_name_algorithm)
            
        Returns:
            True wenn erfolgreich
        """
        if profile_key not in self._profiles:
            logger.error(f"Profil nicht gefunden: {profile_key}")
            return False
        
        profile = self._profiles[profile_key]
        
        success = True
        
        if profile.get('power_limit_percent'):
            if not self.set_power_limit_percent(gpu_index, profile['power_limit_percent']):
                success = False
        
        core_offset = profile.get('core_clock_offset', 0)
        memory_offset = profile.get('memory_clock_offset', 0)
        if core_offset != 0 or memory_offset != 0:
            self.set_clock_offset(gpu_index, core_offset, memory_offset)
        
        self._current_profiles[gpu_index] = profile.get('algorithm', 'custom')
        
        return success
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """Gibt alle gespeicherten Profile zurück"""
        return [
            {'key': key, **profile}
            for key, profile in self._profiles.items()
        ]


# Standalone Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Overclock Manager Test")
    print("=" * 60)
    
    oc = OverclockManager()
    
    if not oc.initialize():
        print("❌ Initialisierung fehlgeschlagen")
        exit(1)
    
    print(f"\n✅ {oc.get_gpu_count()} GPU(s) gefunden")
    
    for i in range(oc.get_gpu_count()):
        info = oc.get_gpu_info(i)
        if info:
            print(f"\n   GPU {i}: {info.name}")
            print(f"   Power Default: {info.power_limit_default/1000}W")
            print(f"   Power Range: {info.power_limit_min/1000}W - {info.power_limit_max/1000}W")
    
    # Test Auto-OC (nur anzeigen, nicht anwenden im Test)
    print("\n📊 Auto-OC Preview für RVN:")
    if oc._api:
        for i in range(oc.get_gpu_count()):
            info = oc.get_gpu_info(i)
            if info:
                settings = oc._api.get_oc_settings(info.name, "RVN")
                print(f"   GPU {i}: Core {settings.core_clock_offset:+d}, "
                      f"Mem {settings.memory_clock_offset:+d}, "
                      f"PL {settings.power_limit_percent}%")
    
    print("\n⚠️ Auto-OC wird im Test-Modus NICHT angewendet!")
    print("   Führe mit --apply aus um OC anzuwenden")
    
    oc.shutdown()
    print("\n✅ Test beendet")
