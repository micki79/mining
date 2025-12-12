#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Monitor - NVML basiertes GPU Monitoring System
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Echtzeit GPU-Monitoring via NVIDIA NVML
- AMD GPU Support via pyamdgpuinfo (optional)
- CPU Monitoring via psutil
- Temperatur, Power, Fan, Clocks, Utilization
- Thread-safe mit Historie
- Unterstützung für Multi-GPU Systeme
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging

# NVML Import mit Fallback
try:
    from pynvml import *
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False
    print("⚠️ nvidia-ml-py nicht installiert. Installiere mit: pip install nvidia-ml-py")

# AMD GPU Support (optional)
try:
    import pyamdgpuinfo
    AMD_AVAILABLE = True
except ImportError:
    AMD_AVAILABLE = False

# CPU Monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Datenklasse für GPU-Informationen"""
    index: int
    name: str = ""
    uuid: str = ""
    temperature: int = 0
    temperature_limit: int = 83
    fan_speed: int = 0
    power_watts: float = 0.0
    power_limit_watts: float = 0.0
    power_default_watts: float = 0.0
    power_min_watts: float = 0.0
    power_max_watts: float = 0.0
    gpu_utilization: int = 0
    memory_utilization: int = 0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    core_clock_mhz: int = 0
    memory_clock_mhz: int = 0
    core_clock_max_mhz: int = 0
    memory_clock_max_mhz: int = 0
    pcie_gen: int = 0
    pcie_width: int = 0
    driver_version: str = ""
    vbios_version: str = ""
    # Mining-spezifisch
    hashrate: float = 0.0
    efficiency: float = 0.0  # MH/s per Watt
    gpu_type: str = "NVIDIA"  # NVIDIA, AMD, Intel
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'index': self.index,
            'name': self.name,
            'uuid': self.uuid,
            'temperature': self.temperature,
            'temperature_limit': self.temperature_limit,
            'fan_speed': self.fan_speed,
            'power_watts': self.power_watts,
            'power_limit_watts': self.power_limit_watts,
            'power_default_watts': self.power_default_watts,
            'gpu_utilization': self.gpu_utilization,
            'memory_utilization': self.memory_utilization,
            'memory_used_mb': self.memory_used_mb,
            'memory_total_mb': self.memory_total_mb,
            'core_clock_mhz': self.core_clock_mhz,
            'memory_clock_mhz': self.memory_clock_mhz,
            'hashrate': self.hashrate,
            'efficiency': self.efficiency,
            'gpu_type': self.gpu_type,
        }


@dataclass
class CPUInfo:
    """Datenklasse für CPU-Informationen"""
    name: str = ""
    cores: int = 0
    threads: int = 0
    usage_percent: float = 0.0
    temperature: int = 0
    frequency_mhz: int = 0
    hashrate: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'cores': self.cores,
            'threads': self.threads,
            'usage_percent': self.usage_percent,
            'temperature': self.temperature,
            'frequency_mhz': self.frequency_mhz,
            'hashrate': self.hashrate,
        }


class GPUMonitor:
    """
    Thread-sicherer GPU Monitor mit NVML.
    
    Verwendung:
        monitor = GPUMonitor(poll_interval=1.0)
        monitor.start()
        
        # Aktuelle Daten abrufen
        data = monitor.get_current()
        
        # Historie abrufen (letzte 5 Minuten bei 1s Intervall)
        history = monitor.get_history()
        
        monitor.stop()
    """
    
    def __init__(self, poll_interval: float = 1.0, history_size: int = 300):
        """
        Initialisiert den GPU Monitor.
        
        Args:
            poll_interval: Abfrage-Intervall in Sekunden
            history_size: Anzahl der Historie-Einträge (default: 300 = 5 Min bei 1s)
        """
        self.poll_interval = poll_interval
        self.history_size = history_size
        
        self._lock = threading.Lock()
        self._stopped = True
        self._initialized = False
        self._thread: Optional[threading.Thread] = None
        
        self._gpu_count = 0
        self._driver_version = ""
        self._current_data: Dict[str, Any] = {}
        self._history: deque = deque(maxlen=history_size)
        self._gpu_handles: List[Any] = []
        
        # AMD/Intel GPUs (cached beim Start)
        self._other_gpus: List[GPUInfo] = []
        
        # Callbacks für Events
        self._callbacks: Dict[str, List[callable]] = {
            'update': [],
            'alert': [],
            'error': [],
        }
        
        # Alert Thresholds
        self.temp_warning = 75
        self.temp_critical = 85
        self.power_warning_percent = 95
    
    def add_callback(self, event: str, callback: callable):
        """Fügt einen Callback für Events hinzu"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def remove_callback(self, event: str, callback: callable):
        """Entfernt einen Callback"""
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)
    
    def _trigger_callbacks(self, event: str, data: Any):
        """Triggert alle Callbacks für ein Event"""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback Fehler: {e}")
    
    def initialize(self) -> bool:
        """
        Initialisiert NVML und erkennt alle GPUs.
        
        Returns:
            True wenn erfolgreich, False bei Fehler
        """
        success = False
        
        # 1. NVIDIA via NVML
        if NVML_AVAILABLE:
            try:
                nvmlInit()
                self._gpu_count = nvmlDeviceGetCount()
                self._driver_version = nvmlSystemGetDriverVersion()
                
                # Handles für alle GPUs speichern
                self._gpu_handles = []
                for i in range(self._gpu_count):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    self._gpu_handles.append(handle)
                
                self._initialized = True
                logger.info(f"NVML initialisiert: {self._gpu_count} NVIDIA GPU(s), Driver {self._driver_version}")
                success = True
                
            except NVMLError as e:
                logger.error(f"NVML Initialisierung fehlgeschlagen: {e}")
        else:
            logger.warning("NVML nicht verfügbar - nur AMD/Intel GPUs werden erkannt")
        
        # 2. AMD/Intel GPUs via wmic erkennen (cached)
        self._other_gpus = self._collect_gpus_via_wmic()
        if self._other_gpus:
            logger.info(f"Weitere GPUs erkannt: {len(self._other_gpus)} (AMD/Intel)")
            success = True
        
        # 3. CPU Info
        cpu = self._collect_cpu_info()
        if cpu:
            logger.info(f"CPU erkannt: {cpu.name} ({cpu.cores} Cores, {cpu.threads} Threads)")
        
        return success
    
    def shutdown(self):
        """Beendet NVML sauber"""
        if self._initialized and NVML_AVAILABLE:
            try:
                nvmlShutdown()
                self._initialized = False
                logger.info("NVML heruntergefahren")
            except NVMLError as e:
                logger.error(f"NVML Shutdown Fehler: {e}")
    
    def start(self):
        """Startet das Monitoring in einem Background-Thread"""
        if not self._initialized:
            if not self.initialize():
                return False
        
        self._stopped = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="GPUMonitor")
        self._thread.start()
        logger.info("GPU Monitoring gestartet")
        return True
    
    def stop(self):
        """Stoppt das Monitoring"""
        self._stopped = True
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        self.shutdown()
        logger.info("GPU Monitoring gestoppt")
    
    def _collect_gpu_data(self, gpu_index: int) -> GPUInfo:
        """Sammelt alle Daten für eine GPU"""
        gpu = GPUInfo(index=gpu_index)
        
        if gpu_index >= len(self._gpu_handles):
            return gpu
        
        handle = self._gpu_handles[gpu_index]
        
        # Name und UUID
        try:
            gpu.name = nvmlDeviceGetName(handle)
            if isinstance(gpu.name, bytes):
                gpu.name = gpu.name.decode('utf-8')
        except NVMLError:
            gpu.name = f"GPU {gpu_index}"
        
        try:
            gpu.uuid = nvmlDeviceGetUUID(handle)
            if isinstance(gpu.uuid, bytes):
                gpu.uuid = gpu.uuid.decode('utf-8')
        except NVMLError:
            pass
        
        # Temperatur
        try:
            gpu.temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        except NVMLError:
            pass
        
        try:
            gpu.temperature_limit = nvmlDeviceGetTemperatureThreshold(handle, NVML_TEMPERATURE_THRESHOLD_SHUTDOWN)
        except NVMLError:
            gpu.temperature_limit = 83
        
        # Fan Speed
        try:
            gpu.fan_speed = nvmlDeviceGetFanSpeed(handle)
        except NVMLError:
            pass
        
        # Power
        try:
            gpu.power_watts = nvmlDeviceGetPowerUsage(handle) / 1000.0
        except NVMLError:
            pass
        
        try:
            gpu.power_limit_watts = nvmlDeviceGetPowerManagementLimit(handle) / 1000.0
        except NVMLError:
            pass
        
        try:
            gpu.power_default_watts = nvmlDeviceGetPowerManagementDefaultLimit(handle) / 1000.0
        except NVMLError:
            pass
        
        try:
            min_limit, max_limit = nvmlDeviceGetPowerManagementLimitConstraints(handle)
            gpu.power_min_watts = min_limit / 1000.0
            gpu.power_max_watts = max_limit / 1000.0
        except NVMLError:
            pass
        
        # Utilization
        try:
            util = nvmlDeviceGetUtilizationRates(handle)
            gpu.gpu_utilization = util.gpu
            gpu.memory_utilization = util.memory
        except NVMLError:
            pass
        
        # Memory
        try:
            mem = nvmlDeviceGetMemoryInfo(handle)
            gpu.memory_used_mb = mem.used / (1024 * 1024)
            gpu.memory_total_mb = mem.total / (1024 * 1024)
        except NVMLError:
            pass
        
        # Clocks
        try:
            gpu.core_clock_mhz = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
        except NVMLError:
            pass
        
        try:
            gpu.memory_clock_mhz = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM)
        except NVMLError:
            pass
        
        try:
            gpu.core_clock_max_mhz = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_GRAPHICS)
        except NVMLError:
            pass
        
        try:
            gpu.memory_clock_max_mhz = nvmlDeviceGetMaxClockInfo(handle, NVML_CLOCK_MEM)
        except NVMLError:
            pass
        
        # PCIe
        try:
            gpu.pcie_gen = nvmlDeviceGetCurrPcieLinkGeneration(handle)
            gpu.pcie_width = nvmlDeviceGetCurrPcieLinkWidth(handle)
        except NVMLError:
            pass
        
        # VBIOS
        try:
            gpu.vbios_version = nvmlDeviceGetVbiosVersion(handle)
            if isinstance(gpu.vbios_version, bytes):
                gpu.vbios_version = gpu.vbios_version.decode('utf-8')
        except NVMLError:
            pass
        
        gpu.driver_version = self._driver_version
        
        # Effizienz berechnen (wenn Hashrate gesetzt)
        if gpu.hashrate > 0 and gpu.power_watts > 0:
            gpu.efficiency = gpu.hashrate / gpu.power_watts
        
        return gpu
    
    def _check_alerts(self, gpu: GPUInfo):
        """Prüft auf Alerts und triggert Callbacks"""
        alerts = []
        
        # Temperatur-Warnung
        if gpu.temperature >= self.temp_critical:
            alerts.append({
                'type': 'critical',
                'gpu': gpu.index,
                'message': f'GPU {gpu.index} KRITISCHE Temperatur: {gpu.temperature}°C',
                'value': gpu.temperature,
            })
        elif gpu.temperature >= self.temp_warning:
            alerts.append({
                'type': 'warning',
                'gpu': gpu.index,
                'message': f'GPU {gpu.index} hohe Temperatur: {gpu.temperature}°C',
                'value': gpu.temperature,
            })
        
        # Power-Warnung
        if gpu.power_limit_watts > 0:
            power_percent = (gpu.power_watts / gpu.power_limit_watts) * 100
            if power_percent >= self.power_warning_percent:
                alerts.append({
                    'type': 'warning',
                    'gpu': gpu.index,
                    'message': f'GPU {gpu.index} hohe Power: {gpu.power_watts:.0f}W ({power_percent:.0f}%)',
                    'value': gpu.power_watts,
                })
        
        for alert in alerts:
            self._trigger_callbacks('alert', alert)
    
    def _collect_amd_gpus(self) -> List[GPUInfo]:
        """Sammelt AMD GPU Daten (mit wmic Fallback)"""
        amd_gpus = []
        
        # 1. Versuch: pyamdgpuinfo (detaillierte Daten)
        if AMD_AVAILABLE:
            try:
                num_amd = pyamdgpuinfo.detect_gpus()
                for i in range(num_amd):
                    try:
                        amd = pyamdgpuinfo.get_gpu(i)
                        gpu = GPUInfo(
                            index=self._gpu_count + i,  # Nach NVIDIA GPUs
                            name=amd.name if hasattr(amd, 'name') else f"AMD GPU {i}",
                            gpu_type="AMD",
                            temperature=int(amd.query_temperature()) if hasattr(amd, 'query_temperature') else 0,
                            power_watts=amd.query_power() if hasattr(amd, 'query_power') else 0,
                            gpu_utilization=int(amd.query_load() * 100) if hasattr(amd, 'query_load') else 0,
                            memory_total_mb=amd.memory_info.get('vram_size', 0) / (1024*1024) if hasattr(amd, 'memory_info') else 0,
                            core_clock_mhz=int(amd.query_sclk() / 1e6) if hasattr(amd, 'query_sclk') else 0,
                            memory_clock_mhz=int(amd.query_mclk() / 1e6) if hasattr(amd, 'query_mclk') else 0,
                        )
                        amd_gpus.append(gpu)
                    except Exception as e:
                        logger.debug(f"AMD GPU {i} Fehler: {e}")
                
                if amd_gpus:
                    return amd_gpus
            except Exception as e:
                logger.debug(f"pyamdgpuinfo Fehler: {e}")
        
        # 2. Fallback: wmic auf Windows
        amd_gpus = self._collect_gpus_via_wmic()
        return amd_gpus
    
    def _collect_gpus_via_wmic(self) -> List[GPUInfo]:
        """Erkennt AMD/Intel GPUs via Windows wmic (Fallback)"""
        import subprocess
        import re
        
        non_nvidia_gpus = []
        
        try:
            # Hole alle VideoController via wmic
            result = subprocess.run(
                ['wmic', 'path', 'win32_VideoController', 'get', 'Name,AdapterRAM,DriverVersion', '/format:csv'],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode == 0:
                lines = [l.strip() for l in result.stdout.strip().split('\n') if l.strip()]
                
                # Erste Zeile ist Header (Node,AdapterRAM,DriverVersion,Name)
                idx = self._gpu_count  # Starte nach NVIDIA GPUs
                
                for line in lines[1:]:  # Header überspringen
                    parts = line.split(',')
                    if len(parts) >= 4:
                        name = parts[-1].strip()  # Name ist letzte Spalte
                        
                        # Nur nicht-NVIDIA GPUs (die werden schon via NVML erkannt)
                        if 'NVIDIA' not in name.upper() and name:
                            # iGPUs (integrated GPUs) filtern
                            name_upper = name.upper()
                            is_igpu = any([
                                'RADEON(TM)' in name_upper,
                                'RADEON GRAPHICS' in name_upper,
                                'RADEON VEGA' in name_upper and 'RX' not in name_upper,
                                'INTEL UHD' in name_upper,
                                'INTEL HD' in name_upper,
                                'INTEL IRIS' in name_upper,
                                'INTEGRATED' in name_upper,
                                'MICROSOFT BASIC' in name_upper,
                            ])
                            
                            if is_igpu:
                                logger.info(f"iGPU übersprungen: {name}")
                                continue
                            
                            vram_bytes = parts[1].strip() if len(parts) > 1 else '0'
                            driver = parts[2].strip() if len(parts) > 2 else ''
                            
                            # GPU-Typ bestimmen
                            gpu_type = "Unknown"
                            if 'AMD' in name.upper() or 'RADEON' in name.upper():
                                gpu_type = "AMD"
                            elif 'INTEL' in name.upper():
                                gpu_type = "Intel"
                            
                            try:
                                vram_mb = int(vram_bytes) / (1024 * 1024) if vram_bytes.isdigit() else 0
                            except:
                                vram_mb = 0
                            
                            gpu = GPUInfo(
                                index=idx,
                                name=name,
                                gpu_type=gpu_type,
                                memory_total_mb=vram_mb,
                                driver_version=driver,
                            )
                            non_nvidia_gpus.append(gpu)
                            idx += 1
                            logger.info(f"GPU erkannt via wmic: {name} ({gpu_type})")
                            
        except subprocess.TimeoutExpired:
            logger.warning("wmic Timeout")
        except FileNotFoundError:
            logger.debug("wmic nicht gefunden (nicht Windows?)")
        except Exception as e:
            logger.debug(f"wmic Fehler: {e}")
        
        return non_nvidia_gpus
    
    def _collect_cpu_info(self) -> Optional[CPUInfo]:
        """Sammelt CPU Informationen"""
        if not PSUTIL_AVAILABLE:
            return None
        
        try:
            import platform
            cpu = CPUInfo(
                name=platform.processor() or "Unknown CPU",
                cores=psutil.cpu_count(logical=False) or 0,
                threads=psutil.cpu_count(logical=True) or 0,
                usage_percent=psutil.cpu_percent(interval=0.1),
                frequency_mhz=int(psutil.cpu_freq().current) if psutil.cpu_freq() else 0,
            )
            
            # CPU Temperatur (wenn verfügbar)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # Verschiedene Namen je nach System
                    for name in ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal']:
                        if name in temps and temps[name]:
                            cpu.temperature = int(temps[name][0].current)
                            break
            except Exception:
                pass
            
            return cpu
        except Exception as e:
            logger.debug(f"CPU Info Fehler: {e}")
            return None
    
    def _collect_all_metrics(self) -> Dict[str, Any]:
        """Sammelt Metriken von allen GPUs und CPU"""
        metrics = {
            'timestamp': time.time(),
            'gpu_count': self._gpu_count,
            'driver_version': self._driver_version,
            'gpus': [],
            'cpu': None,
            'totals': {
                'power_watts': 0.0,
                'hashrate': 0.0,
            }
        }
        
        # NVIDIA GPUs sammeln (Echtzeit-Daten via NVML)
        for i in range(self._gpu_count):
            try:
                gpu = self._collect_gpu_data(i)
                gpu.gpu_type = "NVIDIA"
                metrics['gpus'].append(gpu)
                metrics['totals']['power_watts'] += gpu.power_watts
                metrics['totals']['hashrate'] += gpu.hashrate
                
                # Alerts prüfen
                self._check_alerts(gpu)
                
            except Exception as e:
                logger.error(f"Fehler beim Sammeln von GPU {i} Daten: {e}")
                metrics['gpus'].append(GPUInfo(index=i))
        
        # AMD/Intel GPUs hinzufügen (gecached beim Start)
        # Diese GPUs haben keine Echtzeit-Daten (nur Name/VRAM)
        for gpu in self._other_gpus:
            metrics['gpus'].append(gpu)
            metrics['totals']['power_watts'] += gpu.power_watts
            metrics['totals']['hashrate'] += gpu.hashrate
        
        # GPU Count aktualisieren
        metrics['gpu_count'] = len(metrics['gpus'])
        
        # CPU Info sammeln
        cpu_info = self._collect_cpu_info()
        if cpu_info:
            metrics['cpu'] = cpu_info
        
        return metrics
    
    def _monitor_loop(self):
        """Haupt-Monitoring-Schleife"""
        while not self._stopped:
            try:
                metrics = self._collect_all_metrics()
                
                with self._lock:
                    self._current_data = metrics
                    self._history.append(metrics)
                
                # Update-Callback triggern
                self._trigger_callbacks('update', metrics)
                
            except Exception as e:
                logger.error(f"Monitor Loop Fehler: {e}")
                self._trigger_callbacks('error', {'message': str(e)})
            
            time.sleep(self.poll_interval)
    
    def get_current(self) -> Dict[str, Any]:
        """Gibt die aktuellen Metriken zurück"""
        with self._lock:
            return self._current_data.copy() if self._current_data else {}
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Gibt die Historie zurück"""
        with self._lock:
            return list(self._history)
    
    def get_gpu(self, index: int) -> Optional[GPUInfo]:
        """Gibt Informationen zu einer spezifischen GPU zurück"""
        with self._lock:
            if self._current_data and 'gpus' in self._current_data:
                gpus = self._current_data['gpus']
                if 0 <= index < len(gpus):
                    return gpus[index]
        return None
    
    def get_gpu_count(self) -> int:
        """Gibt die Anzahl der GPUs zurück"""
        return self._gpu_count
    
    def update_hashrate(self, gpu_index: int, hashrate: float):
        """
        Aktualisiert die Hashrate für eine GPU (von Miner API).
        
        Args:
            gpu_index: GPU Index
            hashrate: Hashrate in MH/s
        """
        with self._lock:
            if self._current_data and 'gpus' in self._current_data:
                gpus = self._current_data['gpus']
                if 0 <= gpu_index < len(gpus):
                    gpus[gpu_index].hashrate = hashrate
                    # Effizienz neu berechnen
                    if gpus[gpu_index].power_watts > 0:
                        gpus[gpu_index].efficiency = hashrate / gpus[gpu_index].power_watts
    
    def update_hashrates(self, hashrates: Dict[int, float]):
        """
        Aktualisiert Hashrates für mehrere GPUs.
        
        Args:
            hashrates: Dict mit {gpu_index: hashrate}
        """
        for gpu_index, hashrate in hashrates.items():
            self.update_hashrate(gpu_index, hashrate)
    
    @staticmethod
    def get_gpu_list() -> List[Dict[str, str]]:
        """
        Statische Methode um eine Liste aller GPUs zu bekommen.
        
        Returns:
            Liste mit {'index': int, 'name': str, 'uuid': str}
        """
        if not NVML_AVAILABLE:
            return []
        
        gpus = []
        try:
            nvmlInit()
            count = nvmlDeviceGetCount()
            
            for i in range(count):
                handle = nvmlDeviceGetHandleByIndex(i)
                name = nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                uuid = nvmlDeviceGetUUID(handle)
                if isinstance(uuid, bytes):
                    uuid = uuid.decode('utf-8')
                
                gpus.append({
                    'index': i,
                    'name': name,
                    'uuid': uuid,
                })
            
            nvmlShutdown()
        except NVMLError as e:
            logger.error(f"Fehler beim Auflisten der GPUs: {e}")
        
        return gpus


# Standalone Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("GPU Monitor Test")
    print("=" * 60)
    
    # GPU Liste anzeigen
    gpus = GPUMonitor.get_gpu_list()
    if not gpus:
        print("❌ Keine NVIDIA GPUs gefunden oder NVML nicht verfügbar")
        exit(1)
    
    print(f"\n✅ Gefundene GPUs: {len(gpus)}")
    for gpu in gpus:
        print(f"   [{gpu['index']}] {gpu['name']}")
    
    # Monitor starten
    monitor = GPUMonitor(poll_interval=1.0)
    
    def on_update(data):
        print(f"\n[{time.strftime('%H:%M:%S')}] Update:")
        for gpu in data.get('gpus', []):
            print(f"   GPU {gpu.index}: {gpu.temperature}°C | {gpu.power_watts:.0f}W | "
                  f"Fan {gpu.fan_speed}% | Core {gpu.core_clock_mhz}MHz | Mem {gpu.memory_clock_mhz}MHz")
    
    def on_alert(alert):
        print(f"\n⚠️ ALERT: {alert['message']}")
    
    monitor.add_callback('update', on_update)
    monitor.add_callback('alert', on_alert)
    
    if monitor.start():
        print("\n▶️ Monitoring läuft... (Drücke Ctrl+C zum Beenden)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️ Beende...")
    
    monitor.stop()
    print("✅ Test beendet")
