#!/usr/bin/env python3
"""
Hardware-Datenbank für GPU Mining GUI V11.0
============================================

Features:
- Automatische Erkennung aller GPUs und CPUs
- Lokale Speicherung der Hardware-Daten
- Automatische Synchronisation mit hashrate.no
- Erkennung neuer profitabler Coins
- Caching für schnellen Zugriff

Author: Claude
Version: 1.0.0
"""

import os
import sys
import json
import time
import logging
import subprocess
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================
# DATENSTRUKTUREN
# ============================================================

@dataclass
class GPUData:
    """GPU Hardware-Daten"""
    name: str                          # z.B. "NVIDIA GeForce RTX 3080"
    vendor: str = ""                   # NVIDIA, AMD, Intel
    model: str = ""                    # z.B. "RTX 3080"
    vram_mb: int = 0                   # VRAM in MB
    driver_version: str = ""
    pci_bus: str = ""
    
    # Erkannte Specs
    base_clock_mhz: int = 0
    boost_clock_mhz: int = 0
    memory_clock_mhz: int = 0
    tdp_watts: int = 0
    
    # hashrate.no Daten (werden automatisch gefüllt)
    supported_algorithms: List[str] = field(default_factory=list)
    benchmarks: Dict[str, Dict] = field(default_factory=dict)  # algo -> {hashrate, power, oc_settings}
    
    # Zeitstempel
    detected_at: str = ""
    last_sync: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GPUData':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CPUData:
    """CPU Hardware-Daten"""
    name: str                          # z.B. "AMD Ryzen 9 5900X"
    vendor: str = ""                   # AMD, Intel
    model: str = ""
    cores: int = 0
    threads: int = 0
    base_clock_mhz: int = 0
    boost_clock_mhz: int = 0
    l3_cache_mb: int = 0
    tdp_watts: int = 0
    
    # hashrate.no Daten
    supported_algorithms: List[str] = field(default_factory=list)
    benchmarks: Dict[str, Dict] = field(default_factory=dict)
    
    # Zeitstempel
    detected_at: str = ""
    last_sync: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CPUData':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CoinData:
    """Coin/Algorithmus Daten von hashrate.no"""
    coin: str                          # z.B. "RVN"
    algorithm: str                     # z.B. "kawpow"
    
    # Für diese GPU
    gpu_name: str = ""
    hashrate: float = 0.0              # In der jeweiligen Einheit
    hashrate_unit: str = "MH/s"
    power_watts: float = 0.0
    efficiency: float = 0.0            # Hash/Watt
    
    # OC Settings
    core_offset: int = 0
    memory_offset: int = 0
    power_limit: int = 100
    fan_speed: int = 0
    
    # Profit (wird separat berechnet)
    profit_usd_24h: float = 0.0
    
    # Meta
    source: str = "hashrate.no"
    verified: bool = False
    last_update: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class NewCoinAlert:
    """Alert für neue profitable Coins"""
    coin: str
    algorithm: str
    gpu_name: str
    estimated_profit_usd: float
    current_best_coin: str
    current_best_profit: float
    profit_increase_percent: float
    detected_at: str


# ============================================================
# HARDWARE DATENBANK
# ============================================================

class HardwareDatabase:
    """
    Lokale Datenbank für Hardware und hashrate.no Daten
    
    Speichert:
    - Alle erkannten GPUs und CPUs
    - Benchmarks und OC-Settings von hashrate.no
    - Neue Coins die profitabler sein könnten
    """
    
    def __init__(self, db_path: str = "hardware_db.json"):
        self.db_path = Path(db_path)
        self.gpus: Dict[str, GPUData] = {}           # gpu_id -> GPUData
        self.cpus: Dict[str, CPUData] = {}           # cpu_id -> CPUData
        self.coin_data: Dict[str, CoinData] = {}     # "gpu_coin" -> CoinData
        self.new_coins: List[NewCoinAlert] = []      # Neue profitable Coins
        
        # Sync-Einstellungen
        self.sync_interval_hours = 6                  # Alle 6 Stunden syncen
        self.last_full_sync: Optional[datetime] = None
        
        # hashrate.no API Referenz
        self.hashrate_api = None
        
        # Laden
        self._load_database()
    
    def _generate_gpu_id(self, gpu: GPUData) -> str:
        """Generiert eindeutige ID für eine GPU"""
        return hashlib.md5(f"{gpu.name}_{gpu.pci_bus}".encode()).hexdigest()[:12]
    
    def _generate_cpu_id(self, cpu: CPUData) -> str:
        """Generiert eindeutige ID für eine CPU"""
        return hashlib.md5(f"{cpu.name}_{cpu.cores}_{cpu.threads}".encode()).hexdigest()[:12]
    
    # ============================================================
    # HARDWARE ERKENNUNG
    # ============================================================
    
    def detect_all_hardware(self) -> Tuple[List[GPUData], List[CPUData]]:
        """Erkennt alle GPUs und CPUs im System"""
        gpus = self._detect_gpus()
        cpus = self._detect_cpus()
        
        # In Datenbank speichern
        for gpu in gpus:
            gpu_id = self._generate_gpu_id(gpu)
            if gpu_id not in self.gpus:
                gpu.detected_at = datetime.now().isoformat()
                logger.info(f"Neue GPU erkannt: {gpu.name}")
            self.gpus[gpu_id] = gpu
        
        for cpu in cpus:
            cpu_id = self._generate_cpu_id(cpu)
            if cpu_id not in self.cpus:
                cpu.detected_at = datetime.now().isoformat()
                logger.info(f"Neue CPU erkannt: {cpu.name}")
            self.cpus[cpu_id] = cpu
        
        self._save_database()
        return gpus, cpus
    
    def _detect_gpus(self) -> List[GPUData]:
        """Erkennt alle GPUs"""
        gpus = []
        
        # 1. NVIDIA GPUs via nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,driver_version,pci.bus_id,clocks.max.graphics,clocks.max.memory,power.default_limit",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = [p.strip() for p in line.split(',')]
                        if len(parts) >= 7:
                            gpu = GPUData(
                                name=parts[0],
                                vendor="NVIDIA",
                                model=parts[0].replace("NVIDIA ", "").replace("GeForce ", ""),
                                vram_mb=int(float(parts[1])) if parts[1] else 0,
                                driver_version=parts[2],
                                pci_bus=parts[3],
                                boost_clock_mhz=int(float(parts[4])) if parts[4] else 0,
                                memory_clock_mhz=int(float(parts[5])) if parts[5] else 0,
                                tdp_watts=int(float(parts[6])) if parts[6] else 0,
                            )
                            gpus.append(gpu)
                            logger.info(f"NVIDIA GPU: {gpu.name}, {gpu.vram_mb}MB VRAM, {gpu.tdp_watts}W TDP")
        except Exception as e:
            logger.debug(f"nvidia-smi nicht verfügbar: {e}")
        
        # 2. AMD GPUs via WMI (Windows)
        if sys.platform == 'win32':
            try:
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", 
                     "Name,AdapterRAM,DriverVersion,PNPDeviceID", "/format:csv"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n')[2:]:  # Skip headers
                        if line.strip() and ('AMD' in line or 'Radeon' in line):
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 4:
                                vram = int(parts[1]) // (1024*1024) if parts[1].isdigit() else 0
                                gpu = GPUData(
                                    name=parts[2],
                                    vendor="AMD",
                                    model=parts[2].replace("AMD ", "").replace("Radeon ", ""),
                                    vram_mb=vram,
                                    driver_version=parts[3] if len(parts) > 3 else "",
                                    pci_bus=parts[4] if len(parts) > 4 else "",
                                )
                                gpus.append(gpu)
                                logger.info(f"AMD GPU: {gpu.name}, {gpu.vram_mb}MB VRAM")
            except Exception as e:
                logger.debug(f"WMI AMD Erkennung fehlgeschlagen: {e}")
        
        # 3. Intel GPUs (iGPU)
        if sys.platform == 'win32':
            try:
                result = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "Name", "/format:csv"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if 'Intel' in line and 'UHD' in line or 'Iris' in line:
                            name = line.split(',')[-1].strip()
                            if name and name not in [g.name for g in gpus]:
                                gpu = GPUData(
                                    name=name,
                                    vendor="Intel",
                                    model=name.replace("Intel(R) ", ""),
                                )
                                gpus.append(gpu)
                                logger.info(f"Intel GPU: {gpu.name}")
            except:
                pass
        
        return gpus
    
    def _detect_cpus(self) -> List[CPUData]:
        """Erkennt alle CPUs"""
        cpus = []
        
        if sys.platform == 'win32':
            try:
                # CPU Name
                result = subprocess.run(
                    ["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed", 
                     "/format:csv"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                
                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n')[2:]:
                        if line.strip():
                            parts = [p.strip() for p in line.split(',')]
                            if len(parts) >= 4:
                                vendor = "AMD" if "AMD" in parts[2] else "Intel" if "Intel" in parts[2] else ""
                                cpu = CPUData(
                                    name=parts[2],
                                    vendor=vendor,
                                    model=parts[2],
                                    boost_clock_mhz=int(parts[1]) if parts[1].isdigit() else 0,
                                    cores=int(parts[3]) if parts[3].isdigit() else 0,
                                    threads=int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0,
                                )
                                cpus.append(cpu)
                                logger.info(f"CPU: {cpu.name}, {cpu.cores} Cores, {cpu.threads} Threads")
            except Exception as e:
                logger.debug(f"CPU Erkennung fehlgeschlagen: {e}")
        
        return cpus
    
    # ============================================================
    # HASHRATE.NO SYNCHRONISATION
    # ============================================================
    
    def set_hashrate_api(self, api):
        """Setzt die hashrate.no API Referenz"""
        self.hashrate_api = api
        logger.info("HardwareDB: hashrate.no API verbunden")
    
    def sync_with_hashrate_no(self, force: bool = False) -> Dict[str, Any]:
        """
        Synchronisiert alle Hardware-Daten mit hashrate.no
        
        Returns:
            Dict mit Sync-Ergebnissen
        """
        results = {
            'gpus_synced': 0,
            'coins_found': 0,
            'new_profitable_coins': [],
            'errors': []
        }
        
        if not self.hashrate_api:
            results['errors'].append("hashrate.no API nicht verfügbar")
            return results
        
        # Prüfen ob Sync nötig
        if not force and self.last_full_sync:
            hours_since_sync = (datetime.now() - self.last_full_sync).total_seconds() / 3600
            if hours_since_sync < self.sync_interval_hours:
                logger.info(f"Sync nicht nötig (letzter Sync vor {hours_since_sync:.1f}h)")
                return results
        
        logger.info("Starte hashrate.no Synchronisation...")
        
        # Für jede GPU
        for gpu_id, gpu in self.gpus.items():
            try:
                # Alle Algorithmen/Coins für diese GPU holen
                benchmarks = self._fetch_gpu_benchmarks(gpu)
                
                if benchmarks:
                    gpu.benchmarks = benchmarks
                    gpu.supported_algorithms = list(benchmarks.keys())
                    gpu.last_sync = datetime.now().isoformat()
                    results['gpus_synced'] += 1
                    results['coins_found'] += len(benchmarks)
                    
                    logger.info(f"GPU {gpu.name}: {len(benchmarks)} Algorithmen synchronisiert")
                    
            except Exception as e:
                results['errors'].append(f"{gpu.name}: {e}")
                logger.warning(f"Sync-Fehler für {gpu.name}: {e}")
        
        # Neue profitable Coins erkennen
        new_coins = self._detect_new_profitable_coins()
        results['new_profitable_coins'] = new_coins
        self.new_coins.extend(new_coins)
        
        self.last_full_sync = datetime.now()
        self._save_database()
        
        logger.info(f"Sync abgeschlossen: {results['gpus_synced']} GPUs, {results['coins_found']} Coins")
        return results
    
    def _fetch_gpu_benchmarks(self, gpu: GPUData) -> Dict[str, Dict]:
        """Holt alle Benchmarks für eine GPU von hashrate.no"""
        benchmarks = {}
        
        if not self.hashrate_api:
            return benchmarks
        
        # Bekannte Algorithmen durchgehen
        algorithms = [
            ('kawpow', 'RVN'),
            ('autolykos2', 'ERG'),
            ('etchash', 'ETC'),
            ('kheavyhash', 'KAS'),
            ('blake3', 'ALPH'),
            ('equihash', 'ZEC'),
            ('beamhash3', 'BEAM'),
            ('octopus', 'CFX'),
            ('nexapow', 'NEXA'),
            ('sha512256d', 'RXD'),
            ('dynexsolve', 'DNX'),
            ('randomx', 'XMR'),
            ('ghostrider', 'RTM'),
            ('firopow', 'FIRO'),
            ('ethash', 'ETC'),
            ('zelhash', 'FLUX'),
            ('cuckatoo32', 'GRIN'),
        ]
        
        for algo, default_coin in algorithms:
            try:
                oc_settings = self.hashrate_api.get_oc_settings(gpu.name, algo)
                
                if oc_settings and oc_settings.hashrate > 0:
                    benchmarks[algo] = {
                        'coin': oc_settings.coin or default_coin,
                        'hashrate': oc_settings.hashrate,
                        'hashrate_unit': self._get_hashrate_unit(algo),
                        'power_watts': oc_settings.power_consumption,
                        'efficiency': oc_settings.efficiency,
                        'core_offset': oc_settings.core_clock_offset,
                        'memory_offset': oc_settings.memory_clock_offset,
                        'power_limit': oc_settings.power_limit_percent,
                        'fan_speed': oc_settings.fan_speed,
                        'source': oc_settings.source,
                        'verified': oc_settings.verified,
                    }
                    
            except Exception as e:
                logger.debug(f"Benchmark für {gpu.name}/{algo} nicht verfügbar: {e}")
        
        return benchmarks
    
    def _get_hashrate_unit(self, algorithm: str) -> str:
        """Gibt die Hashrate-Einheit für einen Algorithmus zurück"""
        units = {
            'kawpow': 'MH/s',
            'autolykos2': 'MH/s',
            'etchash': 'MH/s',
            'ethash': 'MH/s',
            'kheavyhash': 'GH/s',
            'blake3': 'GH/s',
            'equihash': 'Sol/s',
            'beamhash3': 'Sol/s',
            'octopus': 'MH/s',
            'randomx': 'H/s',
            'ghostrider': 'H/s',
        }
        return units.get(algorithm, 'H/s')
    
    # ============================================================
    # NEUE COINS ERKENNUNG
    # ============================================================
    
    def _detect_new_profitable_coins(self) -> List[NewCoinAlert]:
        """Erkennt neue Coins die profitabler sein könnten"""
        alerts = []
        
        # Für jede GPU die besten Coins vergleichen
        for gpu_id, gpu in self.gpus.items():
            if not gpu.benchmarks:
                continue
            
            # Aktuell besten Coin finden (aus vorherigem Sync)
            best_coin = None
            best_profit = 0.0
            
            # Alle Coins mit Profit-Daten
            for algo, data in gpu.benchmarks.items():
                # Profit würde hier von WhatToMine kommen
                # Für jetzt: Effizienz als Proxy
                efficiency = data.get('efficiency', 0)
                
                if efficiency > best_profit:
                    best_profit = efficiency
                    best_coin = data.get('coin', algo)
            
            # Neue Coins die besser sind als bisher bekannte
            # (In Zukunft: Vergleich mit gespeichertem "current_mining" Coin)
            
        return alerts
    
    def get_new_coins_for_gpu(self, gpu_name: str) -> List[CoinData]:
        """Gibt neue/unbekannte Coins für eine GPU zurück"""
        new_coins = []
        
        for gpu_id, gpu in self.gpus.items():
            if gpu_name.lower() in gpu.name.lower():
                for algo, data in gpu.benchmarks.items():
                    coin_key = f"{gpu_id}_{data.get('coin', algo)}"
                    
                    if coin_key not in self.coin_data:
                        # Neuer Coin!
                        coin = CoinData(
                            coin=data.get('coin', ''),
                            algorithm=algo,
                            gpu_name=gpu.name,
                            hashrate=data.get('hashrate', 0),
                            hashrate_unit=data.get('hashrate_unit', 'H/s'),
                            power_watts=data.get('power_watts', 0),
                            efficiency=data.get('efficiency', 0),
                            core_offset=data.get('core_offset', 0),
                            memory_offset=data.get('memory_offset', 0),
                            power_limit=data.get('power_limit', 100),
                            source=data.get('source', 'hashrate.no'),
                            verified=data.get('verified', False),
                            last_update=datetime.now().isoformat(),
                        )
                        new_coins.append(coin)
                        self.coin_data[coin_key] = coin
        
        return new_coins
    
    # ============================================================
    # DATEN ABFRAGEN
    # ============================================================
    
    def get_gpu_by_name(self, name: str) -> Optional[GPUData]:
        """Findet eine GPU nach Namen"""
        for gpu in self.gpus.values():
            if name.lower() in gpu.name.lower():
                return gpu
        return None
    
    def get_all_gpus(self) -> List[GPUData]:
        """Gibt alle GPUs zurück"""
        return list(self.gpus.values())
    
    def get_all_cpus(self) -> List[CPUData]:
        """Gibt alle CPUs zurück"""
        return list(self.cpus.values())
    
    def get_oc_settings(self, gpu_name: str, coin_or_algo: str) -> Optional[Dict]:
        """Gibt OC-Settings für eine GPU/Coin Kombination zurück"""
        gpu = self.get_gpu_by_name(gpu_name)
        if not gpu or not gpu.benchmarks:
            return None
        
        # Nach Algorithmus oder Coin suchen
        coin_upper = coin_or_algo.upper()
        algo_lower = coin_or_algo.lower()
        
        # Erst nach Coin suchen
        for algo, data in gpu.benchmarks.items():
            if data.get('coin', '').upper() == coin_upper:
                return data
        
        # Dann nach Algorithmus
        if algo_lower in gpu.benchmarks:
            return gpu.benchmarks[algo_lower]
        
        return None
    
    def get_best_coins_for_gpu(self, gpu_name: str, top_n: int = 10) -> List[Dict]:
        """Gibt die besten Coins für eine GPU zurück (nach Effizienz)"""
        gpu = self.get_gpu_by_name(gpu_name)
        if not gpu or not gpu.benchmarks:
            return []
        
        coins = []
        for algo, data in gpu.benchmarks.items():
            coins.append({
                'coin': data.get('coin', algo),
                'algorithm': algo,
                'hashrate': data.get('hashrate', 0),
                'hashrate_unit': data.get('hashrate_unit', 'H/s'),
                'power_watts': data.get('power_watts', 0),
                'efficiency': data.get('efficiency', 0),
                'oc_settings': {
                    'core_offset': data.get('core_offset', 0),
                    'memory_offset': data.get('memory_offset', 0),
                    'power_limit': data.get('power_limit', 100),
                }
            })
        
        # Nach Effizienz sortieren
        coins.sort(key=lambda x: x['efficiency'], reverse=True)
        return coins[:top_n]
    
    # ============================================================
    # PERSISTENZ
    # ============================================================
    
    def _save_database(self):
        """Speichert die Datenbank"""
        try:
            data = {
                'version': '1.0',
                'last_full_sync': self.last_full_sync.isoformat() if self.last_full_sync else None,
                'gpus': {gpu_id: gpu.to_dict() for gpu_id, gpu in self.gpus.items()},
                'cpus': {cpu_id: cpu.to_dict() for cpu_id, cpu in self.cpus.items()},
                'coin_data': {k: v.to_dict() for k, v in self.coin_data.items()},
                'new_coins': [asdict(c) for c in self.new_coins[-100:]],  # Letzte 100
            }
            
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Hardware-DB gespeichert: {len(self.gpus)} GPUs, {len(self.cpus)} CPUs")
            
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Hardware-DB: {e}")
    
    def _load_database(self):
        """Lädt die Datenbank"""
        if not self.db_path.exists():
            logger.info("Keine Hardware-DB gefunden, erstelle neue...")
            return
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # GPUs laden
            for gpu_id, gpu_data in data.get('gpus', {}).items():
                self.gpus[gpu_id] = GPUData.from_dict(gpu_data)
            
            # CPUs laden
            for cpu_id, cpu_data in data.get('cpus', {}).items():
                self.cpus[cpu_id] = CPUData.from_dict(cpu_data)
            
            # Coin-Daten laden
            for key, coin_data in data.get('coin_data', {}).items():
                self.coin_data[key] = CoinData(**coin_data)
            
            # Last sync
            if data.get('last_full_sync'):
                self.last_full_sync = datetime.fromisoformat(data['last_full_sync'])
            
            logger.info(f"Hardware-DB geladen: {len(self.gpus)} GPUs, {len(self.cpus)} CPUs")
            
        except Exception as e:
            logger.error(f"Fehler beim Laden der Hardware-DB: {e}")
    
    # ============================================================
    # STATISTIKEN
    # ============================================================
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zur Datenbank zurück"""
        total_benchmarks = sum(len(gpu.benchmarks) for gpu in self.gpus.values())
        
        return {
            'gpus_count': len(self.gpus),
            'cpus_count': len(self.cpus),
            'total_benchmarks': total_benchmarks,
            'coins_tracked': len(self.coin_data),
            'new_coins_alerts': len(self.new_coins),
            'last_sync': self.last_full_sync.isoformat() if self.last_full_sync else "Nie",
            'db_size_kb': self.db_path.stat().st_size // 1024 if self.db_path.exists() else 0,
        }
    
    def print_summary(self):
        """Druckt eine Zusammenfassung"""
        stats = self.get_stats()
        
        print("\n" + "=" * 60)
        print("  HARDWARE DATENBANK ZUSAMMENFASSUNG")
        print("=" * 60)
        print(f"  GPUs erkannt:      {stats['gpus_count']}")
        print(f"  CPUs erkannt:      {stats['cpus_count']}")
        print(f"  Benchmarks:        {stats['total_benchmarks']}")
        print(f"  Coins getrackt:    {stats['coins_tracked']}")
        print(f"  Letzter Sync:      {stats['last_sync']}")
        print(f"  DB Größe:          {stats['db_size_kb']} KB")
        print("=" * 60)
        
        # GPUs auflisten
        print("\n  ERKANNTE GPUs:")
        for gpu in self.gpus.values():
            algos = len(gpu.benchmarks)
            print(f"  • {gpu.name}")
            print(f"    VRAM: {gpu.vram_mb}MB | TDP: {gpu.tdp_watts}W | Algos: {algos}")
        
        # CPUs auflisten
        if self.cpus:
            print("\n  ERKANNTE CPUs:")
            for cpu in self.cpus.values():
                print(f"  • {cpu.name}")
                print(f"    Cores: {cpu.cores} | Threads: {cpu.threads}")
        
        print()


# ============================================================
# SINGLETON ACCESSOR
# ============================================================

_hardware_db_instance: Optional[HardwareDatabase] = None

def get_hardware_db(db_path: str = "hardware_db.json") -> HardwareDatabase:
    """Gibt die Singleton-Instanz der Hardware-Datenbank zurück"""
    global _hardware_db_instance
    if _hardware_db_instance is None:
        _hardware_db_instance = HardwareDatabase(db_path)
    return _hardware_db_instance


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("\n=== Hardware Datenbank Test ===\n")
    
    db = HardwareDatabase()
    
    # Hardware erkennen
    print("Erkenne Hardware...")
    gpus, cpus = db.detect_all_hardware()
    
    print(f"\nGefunden: {len(gpus)} GPUs, {len(cpus)} CPUs")
    
    # Zusammenfassung
    db.print_summary()
    
    # Beste Coins für erste GPU
    if gpus:
        print(f"\nBeste Coins für {gpus[0].name}:")
        best = db.get_best_coins_for_gpu(gpus[0].name, top_n=5)
        for i, coin in enumerate(best, 1):
            print(f"  {i}. {coin['coin']} ({coin['algorithm']})")
            print(f"     Hashrate: {coin['hashrate']} {coin['hashrate_unit']}")
            print(f"     Effizienz: {coin['efficiency']:.2f}")
