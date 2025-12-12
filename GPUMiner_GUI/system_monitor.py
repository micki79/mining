#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Monitor - Erkennt ALLE Hardware (NVIDIA, AMD, Intel, CPU)
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- NVIDIA GPUs via NVML
- AMD GPUs via WMI (auch iGPUs!)
- Intel GPUs via WMI
- CPU Monitoring via WMI/psutil
- Automatische Erkennung aller Geräte
"""

import logging
import subprocess
import re
import time
import threading
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from collections import deque

logger = logging.getLogger(__name__)

# Versuche verschiedene Libraries zu importieren
NVML_AVAILABLE = False
PSUTIL_AVAILABLE = False
WMI_AVAILABLE = False

try:
    from pynvml import *
    NVML_AVAILABLE = True
except ImportError:
    pass

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    pass

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    pass


@dataclass
class HardwareInfo:
    """Basis-Klasse für Hardware-Informationen"""
    index: int
    name: str = ""
    hw_type: str = ""  # "NVIDIA", "AMD", "Intel", "CPU"
    temperature: int = 0
    fan_speed: int = 0
    power_watts: float = 0.0
    utilization: int = 0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    core_clock_mhz: int = 0
    memory_clock_mhz: int = 0
    hashrate: float = 0.0
    efficiency: float = 0.0
    driver_version: str = ""
    
    # CPU-spezifisch
    cores: int = 0
    threads: int = 0
    frequency_mhz: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'name': self.name,
            'hw_type': self.hw_type,
            'temperature': self.temperature,
            'fan_speed': self.fan_speed,
            'power_watts': self.power_watts,
            'utilization': self.utilization,
            'memory_used_mb': self.memory_used_mb,
            'memory_total_mb': self.memory_total_mb,
            'core_clock_mhz': self.core_clock_mhz,
            'memory_clock_mhz': self.memory_clock_mhz,
            'hashrate': self.hashrate,
            'efficiency': self.efficiency,
            'cores': self.cores,
            'threads': self.threads,
            'frequency_mhz': self.frequency_mhz,
        }


class SystemMonitor:
    """
    Universeller System Monitor für alle Hardware-Typen
    
    Erkennt automatisch:
    - NVIDIA GPUs (dediziert + Laptop)
    - AMD GPUs (dediziert + iGPU)
    - Intel GPUs (iGPU)
    - CPU
    """
    
    def __init__(self, poll_interval: float = 1.0, history_size: int = 300):
        self.poll_interval = poll_interval
        self.history_size = history_size
        
        self._lock = threading.Lock()
        self._stopped = True
        self._thread = None
        
        self._devices: List[HardwareInfo] = []
        self._history = deque(maxlen=history_size)
        self._current_data = {}
        
        # NVML Handle für NVIDIA
        self._nvml_initialized = False
        self._nvml_handles = []
        self._nvml_driver = ""
        
        # WMI für AMD/Intel/CPU
        self._wmi = None
        
        # Callbacks
        self._callbacks = {
            'update': [],
            'error': [],
        }
    
    def add_callback(self, event: str, callback: callable):
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, data: Any):
        for cb in self._callbacks.get(event, []):
            try:
                cb(data)
            except Exception as e:
                logger.error(f"Callback Fehler: {e}")
    
    def initialize(self) -> bool:
        """Initialisiert alle Hardware-Monitore"""
        success = False
        
        # 1. NVIDIA via NVML
        if NVML_AVAILABLE:
            try:
                nvmlInit()
                count = nvmlDeviceGetCount()
                self._nvml_driver = nvmlSystemGetDriverVersion()
                
                for i in range(count):
                    handle = nvmlDeviceGetHandleByIndex(i)
                    self._nvml_handles.append(handle)
                
                self._nvml_initialized = True
                logger.info(f"NVML: {count} NVIDIA GPU(s), Driver {self._nvml_driver}")
                success = True
            except Exception as e:
                logger.warning(f"NVML Init fehlgeschlagen: {e}")
        
        # 2. WMI für AMD/Intel und CPU
        if WMI_AVAILABLE:
            try:
                self._wmi = wmi.WMI()
                logger.info("WMI initialisiert für AMD/Intel/CPU")
                success = True
            except Exception as e:
                logger.warning(f"WMI Init fehlgeschlagen: {e}")
        
        # 3. Fallback: Erkenne GPUs über nvidia-smi und dxdiag
        self._detect_all_gpus()
        
        return success
    
    def _detect_all_gpus(self):
        """Erkennt alle GPUs im System"""
        gpus_found = []
        
        # Via WMI Win32_VideoController
        if self._wmi:
            try:
                for gpu in self._wmi.Win32_VideoController():
                    name = gpu.Name or "Unknown GPU"
                    vram = int(gpu.AdapterRAM or 0) / (1024 * 1024)  # MB
                    
                    # Typ erkennen
                    hw_type = "Unknown"
                    if "NVIDIA" in name.upper():
                        hw_type = "NVIDIA"
                    elif "AMD" in name.upper() or "RADEON" in name.upper():
                        hw_type = "AMD"
                    elif "INTEL" in name.upper():
                        hw_type = "Intel"
                    
                    gpus_found.append({
                        'name': name,
                        'hw_type': hw_type,
                        'vram_mb': vram,
                        'driver': gpu.DriverVersion or "",
                    })
                    
                logger.info(f"WMI: {len(gpus_found)} GPU(s) erkannt")
            except Exception as e:
                logger.warning(f"WMI GPU-Erkennung fehlgeschlagen: {e}")
        
        # Via nvidia-smi als Fallback
        if not any(g['hw_type'] == 'NVIDIA' for g in gpus_found):
            try:
                result = subprocess.run(
                    ['nvidia-smi', '-L'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if 'GPU' in line:
                            match = re.search(r'GPU \d+: (.+?) \(', line)
                            if match:
                                gpus_found.append({
                                    'name': match.group(1),
                                    'hw_type': 'NVIDIA',
                                    'vram_mb': 0,
                                    'driver': '',
                                })
            except Exception:
                pass
        
        self._detected_gpus = gpus_found
        return gpus_found
    
    def _collect_nvidia_gpu(self, idx: int, handle) -> HardwareInfo:
        """Sammelt Daten für eine NVIDIA GPU"""
        hw = HardwareInfo(index=idx, hw_type="NVIDIA")
        
        try:
            name = nvmlDeviceGetName(handle)
            hw.name = name.decode('utf-8') if isinstance(name, bytes) else name
        except:
            hw.name = f"NVIDIA GPU {idx}"
        
        try:
            hw.temperature = nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU)
        except:
            pass
        
        try:
            hw.fan_speed = nvmlDeviceGetFanSpeed(handle)
        except:
            pass
        
        try:
            hw.power_watts = nvmlDeviceGetPowerUsage(handle) / 1000.0
        except:
            pass
        
        try:
            util = nvmlDeviceGetUtilizationRates(handle)
            hw.utilization = util.gpu
        except:
            pass
        
        try:
            mem = nvmlDeviceGetMemoryInfo(handle)
            hw.memory_used_mb = mem.used / (1024 * 1024)
            hw.memory_total_mb = mem.total / (1024 * 1024)
        except:
            pass
        
        try:
            hw.core_clock_mhz = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_GRAPHICS)
        except:
            pass
        
        try:
            hw.memory_clock_mhz = nvmlDeviceGetClockInfo(handle, NVML_CLOCK_MEM)
        except:
            pass
        
        hw.driver_version = self._nvml_driver
        
        return hw
    
    def _collect_amd_gpu_wmi(self, idx: int, name: str) -> HardwareInfo:
        """Sammelt AMD GPU Daten via WMI"""
        hw = HardwareInfo(index=idx, hw_type="AMD", name=name)
        
        # Basis-Daten von WMI
        if self._wmi:
            try:
                for gpu in self._wmi.Win32_VideoController():
                    if "AMD" in (gpu.Name or "").upper() or "RADEON" in (gpu.Name or "").upper():
                        hw.memory_total_mb = int(gpu.AdapterRAM or 0) / (1024 * 1024)
                        hw.driver_version = gpu.DriverVersion or ""
                        break
            except:
                pass
        
        # Versuche AMD ADL für mehr Details (optional)
        try:
            # AMD OverdriveN/AMD ADL könnte hier verwendet werden
            # Für jetzt: Basis-Werte
            pass
        except:
            pass
        
        return hw
    
    def _collect_cpu_info(self) -> HardwareInfo:
        """Sammelt CPU-Informationen"""
        idx = 100  # CPU bekommt hohen Index
        hw = HardwareInfo(index=idx, hw_type="CPU")
        
        # Via WMI
        if self._wmi:
            try:
                for cpu in self._wmi.Win32_Processor():
                    hw.name = cpu.Name or "Unknown CPU"
                    hw.cores = cpu.NumberOfCores or 0
                    hw.threads = cpu.NumberOfLogicalProcessors or 0
                    hw.frequency_mhz = cpu.MaxClockSpeed or 0
                    break
            except Exception as e:
                logger.debug(f"WMI CPU Error: {e}")
        
        # Via psutil
        if PSUTIL_AVAILABLE:
            try:
                hw.utilization = int(psutil.cpu_percent(interval=0.1))
                
                if not hw.cores:
                    hw.cores = psutil.cpu_count(logical=False) or 0
                if not hw.threads:
                    hw.threads = psutil.cpu_count(logical=True) or 0
                
                freq = psutil.cpu_freq()
                if freq:
                    hw.core_clock_mhz = int(freq.current)
                    if not hw.frequency_mhz:
                        hw.frequency_mhz = int(freq.max) if freq.max else int(freq.current)
                
                # CPU Temperatur (Windows: benötigt Admin oder spezielle Tools)
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name in ['coretemp', 'k10temp', 'zenpower', 'cpu_thermal']:
                            if name in temps and temps[name]:
                                hw.temperature = int(temps[name][0].current)
                                break
                except:
                    pass
                    
            except Exception as e:
                logger.debug(f"psutil CPU Error: {e}")
        
        # Name-Fallback
        if not hw.name or hw.name == "Unknown CPU":
            import platform
            hw.name = platform.processor() or "CPU"
        
        return hw
    
    def _collect_all_data(self) -> Dict[str, Any]:
        """Sammelt alle Hardware-Daten"""
        data = {
            'timestamp': time.time(),
            'devices': [],
            'gpus': [],
            'cpu': None,
            'totals': {
                'power_watts': 0.0,
                'hashrate': 0.0,
            }
        }
        
        device_idx = 0
        
        # 1. NVIDIA GPUs
        if self._nvml_initialized:
            for i, handle in enumerate(self._nvml_handles):
                try:
                    hw = self._collect_nvidia_gpu(device_idx, handle)
                    data['devices'].append(hw)
                    data['gpus'].append(hw)
                    data['totals']['power_watts'] += hw.power_watts
                    data['totals']['hashrate'] += hw.hashrate
                    device_idx += 1
                except Exception as e:
                    logger.error(f"NVIDIA GPU {i} Fehler: {e}")
        
        # 2. AMD GPUs (von WMI erkannt, die NICHT NVIDIA sind)
        for gpu_info in getattr(self, '_detected_gpus', []):
            if gpu_info['hw_type'] == 'AMD':
                try:
                    hw = self._collect_amd_gpu_wmi(device_idx, gpu_info['name'])
                    data['devices'].append(hw)
                    data['gpus'].append(hw)
                    data['totals']['power_watts'] += hw.power_watts
                    device_idx += 1
                except Exception as e:
                    logger.error(f"AMD GPU Fehler: {e}")
        
        # 3. Intel iGPUs
        for gpu_info in getattr(self, '_detected_gpus', []):
            if gpu_info['hw_type'] == 'Intel':
                try:
                    hw = HardwareInfo(
                        index=device_idx,
                        name=gpu_info['name'],
                        hw_type="Intel",
                        memory_total_mb=gpu_info.get('vram_mb', 0),
                    )
                    data['devices'].append(hw)
                    data['gpus'].append(hw)
                    device_idx += 1
                except Exception as e:
                    logger.error(f"Intel GPU Fehler: {e}")
        
        # 4. CPU
        try:
            cpu = self._collect_cpu_info()
            data['cpu'] = cpu
            data['devices'].append(cpu)
        except Exception as e:
            logger.error(f"CPU Fehler: {e}")
        
        return data
    
    def _monitor_loop(self):
        """Haupt-Monitoring-Schleife"""
        while not self._stopped:
            try:
                data = self._collect_all_data()
                
                with self._lock:
                    self._current_data = data
                    self._history.append(data)
                
                self._trigger_callbacks('update', data)
                
            except Exception as e:
                logger.error(f"Monitor Loop Fehler: {e}")
                self._trigger_callbacks('error', {'message': str(e)})
            
            time.sleep(self.poll_interval)
    
    def start(self):
        """Startet das Monitoring"""
        if not self._nvml_initialized and not self._wmi:
            if not self.initialize():
                logger.warning("Hardware-Monitoring konnte nicht vollständig initialisiert werden")
        
        self._stopped = False
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="SystemMonitor")
        self._thread.start()
        logger.info("System Monitoring gestartet")
        return True
    
    def stop(self):
        """Stoppt das Monitoring"""
        self._stopped = True
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        # NVML cleanup
        if self._nvml_initialized:
            try:
                nvmlShutdown()
            except:
                pass
        
        logger.info("System Monitoring gestoppt")
    
    def get_current(self) -> Dict[str, Any]:
        """Gibt aktuelle Daten zurück"""
        with self._lock:
            return self._current_data.copy() if self._current_data else {}
    
    def get_gpus(self) -> List[HardwareInfo]:
        """Gibt Liste aller GPUs zurück"""
        with self._lock:
            return self._current_data.get('gpus', [])
    
    def get_cpu(self) -> Optional[HardwareInfo]:
        """Gibt CPU-Info zurück"""
        with self._lock:
            return self._current_data.get('cpu')
    
    def get_all_devices(self) -> List[HardwareInfo]:
        """Gibt alle Geräte zurück (GPUs + CPU)"""
        with self._lock:
            return self._current_data.get('devices', [])
    
    @property
    def gpu_count(self) -> int:
        """Anzahl der GPUs"""
        with self._lock:
            return len(self._current_data.get('gpus', []))


# Convenience Funktion zum schnellen Testen
def detect_hardware():
    """Erkennt alle Hardware im System und gibt Summary aus"""
    monitor = SystemMonitor()
    monitor.initialize()
    
    print("\n=== HARDWARE ERKANNT ===\n")
    
    # NVIDIA
    if monitor._nvml_initialized:
        print(f"NVIDIA GPUs: {len(monitor._nvml_handles)}")
        print(f"  Driver: {monitor._nvml_driver}")
    
    # Alle erkannten GPUs
    for gpu in getattr(monitor, '_detected_gpus', []):
        print(f"\n  {gpu['hw_type']}: {gpu['name']}")
        if gpu['vram_mb'] > 0:
            print(f"    VRAM: {gpu['vram_mb']:.0f} MB")
    
    # CPU
    cpu = monitor._collect_cpu_info()
    print(f"\nCPU: {cpu.name}")
    print(f"  Cores: {cpu.cores}, Threads: {cpu.threads}")
    print(f"  Max Freq: {cpu.frequency_mhz} MHz")
    
    return monitor


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    detect_hardware()
