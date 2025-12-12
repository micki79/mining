#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Miner Manager - Startet mehrere Miner gleichzeitig für verschiedene GPUs
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Jede GPU kann einen eigenen Miner-Prozess haben
- Jede GPU mined den für SIE profitabelsten Coin
- Automatisches OC pro GPU und Coin
- Prozess-Überwachung und Auto-Restart
- Unterstützt 1-9 GPUs gleichzeitig

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import signal
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class MinerType(Enum):
    """Unterstützte Miner"""
    TREX = "t-rex"
    LOLMINER = "lolminer"
    GMINER = "gminer"
    NBMINER = "nbminer"
    TEAMREDMINER = "teamredminer"
    RIGEL = "rigel"
    SRBMINER = "srbminer"
    BZMINER = "bzminer"


@dataclass
class GPUMinerConfig:
    """Konfiguration für einen einzelnen GPU-Miner"""
    gpu_index: int
    gpu_name: str
    gpu_model: str
    
    # Mining Config
    coin: str
    algorithm: str
    pool_url: str
    pool_name: str
    wallet: str
    worker: str
    miner_type: MinerType
    
    # OC Settings
    oc_core: int = 0
    oc_memory: int = 0
    oc_power_limit: int = 100
    
    # Expected Performance
    expected_hashrate: float = 0.0
    expected_profit_usd: float = 0.0
    
    def to_dict(self) -> Dict:
        result = asdict(self)
        result['miner_type'] = self.miner_type.value
        return result


@dataclass
class GPUMinerStatus:
    """Status eines laufenden GPU-Miners"""
    gpu_index: int
    config: GPUMinerConfig
    
    # Process Info
    process: Optional[subprocess.Popen] = None
    pid: int = 0
    is_running: bool = False
    start_time: Optional[datetime] = None
    
    # Performance
    current_hashrate: float = 0.0
    hashrate_unit: str = "MH/s"
    accepted_shares: int = 0
    rejected_shares: int = 0
    
    # Profit
    current_profit_usd: float = 0.0
    total_earned_usd: float = 0.0
    
    # Health
    last_share_time: Optional[datetime] = None
    error_count: int = 0
    restart_count: int = 0


class MultiMinerManager:
    """
    Verwaltet mehrere Miner-Prozesse für individuelles GPU-Mining
    
    Jede GPU kann einen eigenen Coin minen mit eigenem:
    - Miner-Prozess (T-Rex, lolMiner, etc.)
    - Pool
    - OC-Settings
    """
    
    # Miner-Pfade
    MINER_PATHS = {
        MinerType.TREX: "miners/t-rex/t-rex.exe",
        MinerType.LOLMINER: "miners/lolminer/lolMiner.exe",
        MinerType.GMINER: "miners/gminer/miner.exe",
        MinerType.NBMINER: "miners/nbminer/nbminer.exe",
        MinerType.TEAMREDMINER: "miners/teamredminer/teamredminer.exe",
        MinerType.RIGEL: "miners/rigel/rigel.exe",
        MinerType.SRBMINER: "miners/srbminer/SRBMiner-MULTI.exe",
        MinerType.BZMINER: "miners/bzminer/bzminer.exe",
    }
    
    # API Ports pro GPU (für Stats-Abfrage)
    BASE_API_PORT = 4067
    
    # Algorithmus zu Miner-Argument Mapping
    ALGO_ARGS = {
        # T-Rex
        ("kawpow", MinerType.TREX): "-a kawpow",
        ("autolykos2", MinerType.TREX): "-a autolykos2",
        ("etchash", MinerType.TREX): "-a etchash",
        ("octopus", MinerType.TREX): "-a octopus",
        ("firopow", MinerType.TREX): "-a firopow",
        
        # lolMiner
        ("equihash125", MinerType.LOLMINER): "--algo EQUI125_4",
        ("equihash144", MinerType.LOLMINER): "--algo EQUI144_5",
        ("beamhashiii", MinerType.LOLMINER): "--algo BEAM-III",
        ("cuckatoo32", MinerType.LOLMINER): "--algo C32",
        ("kheavyhash", MinerType.LOLMINER): "--algo KASPA",
        ("blake3", MinerType.LOLMINER): "--algo ALEPH",
        ("nexapow", MinerType.LOLMINER): "--algo NEXA",
        ("autolykos2", MinerType.LOLMINER): "--algo AUTOLYKOS2",
        ("etchash", MinerType.LOLMINER): "--algo ETCHASH",
        
        # GMiner
        ("equihash125", MinerType.GMINER): "-a 125_4",
        ("equihash144", MinerType.GMINER): "-a 144_5",
        ("beamhashiii", MinerType.GMINER): "-a beamhash",
        ("cuckatoo32", MinerType.GMINER): "-a cuckatoo32",
        ("kheavyhash", MinerType.GMINER): "-a kheavyhash",
        ("autolykos2", MinerType.GMINER): "-a autolykos2",
        ("etchash", MinerType.GMINER): "-a etchash",
        ("octopus", MinerType.GMINER): "-a octopus",
        
        # Rigel
        ("kheavyhash", MinerType.RIGEL): "-a kheavyhash",
        ("autolykos2", MinerType.RIGEL): "-a autolykos2",
        ("etchash", MinerType.RIGEL): "-a etchash",
        ("nexapow", MinerType.RIGEL): "-a nexapow",
    }
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self._gpu_miners: Dict[int, GPUMinerStatus] = {}
        self._lock = threading.Lock()
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks
        self.on_miner_started: Optional[Callable[[int, GPUMinerConfig], None]] = None
        self.on_miner_stopped: Optional[Callable[[int, str], None]] = None
        self.on_miner_error: Optional[Callable[[int, str], None]] = None
        self.on_stats_update: Optional[Callable[[int, GPUMinerStatus], None]] = None
        self.on_log: Optional[Callable[[int, str], None]] = None
        
        # OC Manager (wird extern gesetzt)
        self.oc_manager = None
        self.msi_ab_manager = None
    
    def get_miner_path(self, miner_type: MinerType) -> Optional[Path]:
        """Gibt den Pfad zum Miner zurück"""
        rel_path = self.MINER_PATHS.get(miner_type)
        if not rel_path:
            return None
        
        path = self.base_path / rel_path
        
        # Linux-Pfad
        if sys.platform != "win32":
            path = Path(str(path).replace(".exe", ""))
        
        return path if path.exists() else None
    
    def get_api_port(self, gpu_index: int) -> int:
        """Gibt den API-Port für eine GPU zurück"""
        return self.BASE_API_PORT + gpu_index
    
    def build_miner_command(self, config: GPUMinerConfig) -> Optional[List[str]]:
        """
        Baut den Miner-Befehl für eine GPU-Konfiguration
        
        Args:
            config: GPU-Miner-Konfiguration
            
        Returns:
            Command-Liste oder None bei Fehler
        """
        miner_path = self.get_miner_path(config.miner_type)
        if not miner_path:
            logger.error(f"Miner nicht gefunden: {config.miner_type.value}")
            return None
        
        # Algorithmus-Argument
        algo_key = (config.algorithm, config.miner_type)
        algo_arg = self.ALGO_ARGS.get(algo_key)
        if not algo_arg:
            # Fallback: direkt verwenden
            algo_arg = f"-a {config.algorithm}"
        
        api_port = self.get_api_port(config.gpu_index)
        
        # Basis-Command je nach Miner
        if config.miner_type == MinerType.TREX:
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "-o", config.pool_url,
                "-u", config.wallet,
                "-p", f"x",
                "-w", config.worker,
                "-d", str(config.gpu_index),  # Nur DIESE GPU!
                "--api-bind-http", f"127.0.0.1:{api_port}",
                "--no-watchdog",
            ]
            
        elif config.miner_type == MinerType.LOLMINER:
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "--pool", config.pool_url.replace("stratum+tcp://", ""),
                "--user", config.wallet,
                "--worker", config.worker,
                "--devices", str(config.gpu_index),  # Nur DIESE GPU!
                "--apiport", str(api_port),
            ]
            
        elif config.miner_type == MinerType.GMINER:
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "-s", config.pool_url.replace("stratum+tcp://", "").replace("stratum+ssl://", ""),
                "-u", config.wallet,
                "-w", config.worker,
                "-d", str(config.gpu_index),  # Nur DIESE GPU!
                "--api", str(api_port),
            ]
            
        elif config.miner_type == MinerType.RIGEL:
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "-o", config.pool_url,
                "-u", config.wallet,
                "-w", config.worker,
                "--gpu", str(config.gpu_index),  # Nur DIESE GPU!
                "--api-bind", f"127.0.0.1:{api_port}",
            ]
            
        elif config.miner_type == MinerType.NBMINER:
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "-o", config.pool_url,
                "-u", f"{config.wallet}.{config.worker}",
                "-d", str(config.gpu_index),  # Nur DIESE GPU!
                "--api", f"127.0.0.1:{api_port}",
            ]
            
        else:
            # Generischer Fallback
            cmd = [
                str(miner_path),
                *algo_arg.split(),
                "-o", config.pool_url,
                "-u", config.wallet,
                "-w", config.worker,
                "-d", str(config.gpu_index),
            ]
        
        return cmd
    
    def apply_oc_for_gpu(self, config: GPUMinerConfig) -> bool:
        """
        Wendet OC-Settings für eine GPU an
        
        Args:
            config: GPU-Konfiguration mit OC-Settings
            
        Returns:
            True wenn erfolgreich
        """
        success = True
        
        # MSI Afterburner bevorzugt
        if self.msi_ab_manager and self.msi_ab_manager.is_installed:
            try:
                result, msg = self.msi_ab_manager.apply_oc_direct(
                    gpu_index=config.gpu_index,
                    core_offset=config.oc_core,
                    memory_offset=config.oc_memory,
                    power_limit=config.oc_power_limit
                )
                if result:
                    logger.info(f"GPU {config.gpu_index}: MSI AB OC angewendet - {msg}")
                    return True
            except Exception as e:
                logger.warning(f"GPU {config.gpu_index}: MSI AB OC fehlgeschlagen: {e}")
        
        # Fallback: NVML
        if self.oc_manager:
            try:
                self.oc_manager.set_power_limit_percent(config.gpu_index, config.oc_power_limit)
                self.oc_manager.set_clock_offset(config.gpu_index, config.oc_core, config.oc_memory)
                logger.info(f"GPU {config.gpu_index}: NVML OC angewendet - Core {config.oc_core:+d}, Mem {config.oc_memory:+d}, PL {config.oc_power_limit}%")
                return True
            except Exception as e:
                logger.error(f"GPU {config.gpu_index}: NVML OC fehlgeschlagen: {e}")
                return False
        
        logger.warning(f"GPU {config.gpu_index}: Kein OC-Manager verfügbar")
        return False
    
    def start_gpu_miner(self, config: GPUMinerConfig) -> bool:
        """
        Startet einen Miner für eine einzelne GPU
        
        Args:
            config: GPU-Miner-Konfiguration
            
        Returns:
            True wenn erfolgreich gestartet
        """
        gpu_idx = config.gpu_index
        
        with self._lock:
            # Prüfen ob GPU bereits mined
            if gpu_idx in self._gpu_miners and self._gpu_miners[gpu_idx].is_running:
                logger.warning(f"GPU {gpu_idx} mined bereits - stoppe zuerst")
                self.stop_gpu_miner(gpu_idx)
                time.sleep(1)
        
        # OC anwenden
        self.apply_oc_for_gpu(config)
        
        # Miner-Befehl bauen
        cmd = self.build_miner_command(config)
        if not cmd:
            logger.error(f"GPU {gpu_idx}: Konnte Miner-Befehl nicht erstellen")
            if self.on_miner_error:
                self.on_miner_error(gpu_idx, "Miner-Befehl konnte nicht erstellt werden")
            return False
        
        logger.info(f"GPU {gpu_idx}: Starte {config.miner_type.value} für {config.coin}")
        logger.debug(f"GPU {gpu_idx}: Command = {' '.join(cmd)}")
        
        try:
            # Prozess starten
            if sys.platform == "win32":
                # Windows: CREATE_NEW_CONSOLE für separates Fenster
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    cwd=str(self.base_path)
                )
            else:
                # Linux/Mac
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    cwd=str(self.base_path)
                )
            
            # Status speichern
            status = GPUMinerStatus(
                gpu_index=gpu_idx,
                config=config,
                process=process,
                pid=process.pid,
                is_running=True,
                start_time=datetime.now()
            )
            
            with self._lock:
                self._gpu_miners[gpu_idx] = status
            
            # Log-Reader Thread starten
            self._start_log_reader(gpu_idx, process)
            
            # Callback
            if self.on_miner_started:
                self.on_miner_started(gpu_idx, config)
            
            logger.info(f"GPU {gpu_idx}: Miner gestartet (PID {process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"GPU {gpu_idx}: Miner-Start fehlgeschlagen: {e}")
            if self.on_miner_error:
                self.on_miner_error(gpu_idx, str(e))
            return False
    
    def _start_log_reader(self, gpu_idx: int, process: subprocess.Popen):
        """Startet Thread zum Lesen der Miner-Logs"""
        def read_logs():
            try:
                for line in iter(process.stdout.readline, b''):
                    if not line:
                        break
                    
                    try:
                        text = line.decode('utf-8', errors='ignore').strip()
                        if text and self.on_log:
                            self.on_log(gpu_idx, text)
                        
                        # Stats aus Log parsen (optional)
                        self._parse_log_line(gpu_idx, text)
                    except:
                        pass
            except:
                pass
        
        thread = threading.Thread(target=read_logs, daemon=True)
        thread.start()
    
    def _parse_log_line(self, gpu_idx: int, line: str):
        """Parst relevante Informationen aus Miner-Log"""
        # Einfaches Parsing - kann erweitert werden
        line_lower = line.lower()
        
        with self._lock:
            if gpu_idx not in self._gpu_miners:
                return
            status = self._gpu_miners[gpu_idx]
        
        # Share akzeptiert
        if "accepted" in line_lower or "share accepted" in line_lower:
            status.accepted_shares += 1
            status.last_share_time = datetime.now()
        
        # Share rejected
        if "rejected" in line_lower or "share rejected" in line_lower:
            status.rejected_shares += 1
    
    def stop_gpu_miner(self, gpu_index: int, reason: str = "User request") -> bool:
        """
        Stoppt den Miner für eine GPU
        
        Args:
            gpu_index: GPU Index
            reason: Grund für Stop
            
        Returns:
            True wenn erfolgreich
        """
        with self._lock:
            if gpu_index not in self._gpu_miners:
                return False
            
            status = self._gpu_miners[gpu_index]
        
        if not status.is_running or not status.process:
            return True
        
        logger.info(f"GPU {gpu_index}: Stoppe Miner ({reason})")
        
        try:
            # Sanfter Stop
            if sys.platform == "win32":
                status.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                status.process.terminate()
            
            # Warten
            try:
                status.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Erzwungener Stop
                status.process.kill()
                status.process.wait(timeout=3)
            
            status.is_running = False
            status.process = None
            
            # Callback
            if self.on_miner_stopped:
                self.on_miner_stopped(gpu_index, reason)
            
            logger.info(f"GPU {gpu_index}: Miner gestoppt")
            return True
            
        except Exception as e:
            logger.error(f"GPU {gpu_index}: Fehler beim Stoppen: {e}")
            return False
    
    def stop_all_miners(self, reason: str = "Shutdown"):
        """Stoppt alle laufenden Miner"""
        with self._lock:
            gpu_indices = list(self._gpu_miners.keys())
        
        for gpu_idx in gpu_indices:
            self.stop_gpu_miner(gpu_idx, reason)
    
    def restart_gpu_miner(self, gpu_index: int) -> bool:
        """Startet einen GPU-Miner neu"""
        with self._lock:
            if gpu_index not in self._gpu_miners:
                return False
            status = self._gpu_miners[gpu_index]
            config = status.config
            status.restart_count += 1
        
        self.stop_gpu_miner(gpu_index, "Restart")
        time.sleep(2)
        return self.start_gpu_miner(config)
    
    def get_gpu_status(self, gpu_index: int) -> Optional[GPUMinerStatus]:
        """Gibt Status einer GPU zurück"""
        with self._lock:
            return self._gpu_miners.get(gpu_index)
    
    def get_all_status(self) -> Dict[int, GPUMinerStatus]:
        """Gibt Status aller GPUs zurück"""
        with self._lock:
            return dict(self._gpu_miners)
    
    def is_gpu_mining(self, gpu_index: int) -> bool:
        """Prüft ob GPU mined"""
        with self._lock:
            if gpu_index not in self._gpu_miners:
                return False
            return self._gpu_miners[gpu_index].is_running
    
    def get_mining_gpu_count(self) -> int:
        """Gibt Anzahl der minenden GPUs zurück"""
        with self._lock:
            return sum(1 for s in self._gpu_miners.values() if s.is_running)
    
    def start_monitoring(self, interval: float = 5.0):
        """Startet Monitoring-Thread für alle Miner"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,), daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stoppt Monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
    
    def _monitor_loop(self, interval: float):
        """Monitoring-Loop: Prüft Miner-Status und holt Stats"""
        while self._running:
            try:
                self._check_miners()
                self._fetch_all_stats()
            except Exception as e:
                logger.error(f"Monitor-Fehler: {e}")
            
            time.sleep(interval)
    
    def _check_miners(self):
        """Prüft ob alle Miner noch laufen"""
        with self._lock:
            for gpu_idx, status in self._gpu_miners.items():
                if status.is_running and status.process:
                    # Prüfen ob Prozess noch läuft
                    poll = status.process.poll()
                    if poll is not None:
                        # Prozess beendet!
                        logger.warning(f"GPU {gpu_idx}: Miner unerwartet beendet (Code {poll})")
                        status.is_running = False
                        status.error_count += 1
                        
                        if self.on_miner_error:
                            self.on_miner_error(gpu_idx, f"Miner beendet (Code {poll})")
    
    def _fetch_all_stats(self):
        """Holt Stats von allen laufenden Minern"""
        try:
            import requests
        except ImportError:
            return
        
        with self._lock:
            miners = [(idx, status) for idx, status in self._gpu_miners.items() if status.is_running]
        
        for gpu_idx, status in miners:
            try:
                api_port = self.get_api_port(gpu_idx)
                url = f"http://127.0.0.1:{api_port}"
                
                # Miner-spezifische API
                if status.config.miner_type == MinerType.TREX:
                    url = f"{url}/summary"
                elif status.config.miner_type == MinerType.LOLMINER:
                    pass  # Root endpoint
                
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    self._parse_stats(gpu_idx, status, data)
                    
                    if self.on_stats_update:
                        self.on_stats_update(gpu_idx, status)
                        
            except Exception as e:
                logger.debug(f"GPU {gpu_idx}: Stats-Abruf fehlgeschlagen: {e}")
    
    def _parse_stats(self, gpu_idx: int, status: GPUMinerStatus, data: dict):
        """Parst Miner-API Response"""
        miner_type = status.config.miner_type
        
        if miner_type == MinerType.TREX:
            # T-Rex Format
            status.current_hashrate = data.get("hashrate", 0) / 1_000_000  # H/s -> MH/s
            status.accepted_shares = data.get("accepted_count", 0)
            status.rejected_shares = data.get("rejected_count", 0)
            
        elif miner_type == MinerType.LOLMINER:
            # lolMiner Format
            gpus = data.get("GPUs", [])
            for gpu in gpus:
                if gpu.get("Index", -1) == gpu_idx:
                    status.current_hashrate = gpu.get("Performance", 0)
                    break
            
            session = data.get("Session", {})
            status.accepted_shares = session.get("Accepted", 0)
            status.rejected_shares = session.get("Submitted", 0) - session.get("Accepted", 0)
        
        # Hashrate-Einheit bestimmen
        algo = status.config.algorithm
        if algo in ["cuckatoo32"]:
            status.hashrate_unit = "G/s"
        elif algo in ["kheavyhash", "blake3"]:
            status.hashrate_unit = "GH/s"
        elif algo in ["equihash125", "equihash144", "beamhashiii"]:
            status.hashrate_unit = "Sol/s"
        elif algo in ["dynexsolve"]:
            status.hashrate_unit = "H/s"
        else:
            status.hashrate_unit = "MH/s"


# ============================================================================
# MULTI-GPU AUTO-SWITCHER
# ============================================================================

class MultiGPUAutoSwitcher:
    """
    Kombiniert Multi-GPU Profit Calculator mit Multi-Miner Manager
    
    Automatisch:
    1. Erkennt alle GPUs
    2. Berechnet besten Coin pro GPU
    3. Startet Miner pro GPU mit OC
    4. Überwacht und switched bei Profit-Änderung
    """
    
    def __init__(self, miner_manager: MultiMinerManager):
        self.miner_manager = miner_manager
        self._profit_calculator = None
        self._gpu_infos: List[Tuple[int, str]] = []  # (index, name)
        self._wallets: Dict[str, str] = {}
        self._worker_name = "Rig_D"
        self._running = False
        self._switch_thread: Optional[threading.Thread] = None
        self._min_switch_interval = 300  # 5 Minuten Minimum zwischen Switches
        self._profit_threshold = 0.05  # 5% Profit-Unterschied für Switch
        self._last_switch_time: Dict[int, float] = {}
        
        # Callbacks
        self.on_switch: Optional[Callable[[int, str, str], None]] = None
        self.on_profit_update: Optional[Callable[[List[Any]], None]] = None
    
    def set_gpu_infos(self, gpus: List[Tuple[int, str]]):
        """Setzt GPU-Informationen"""
        self._gpu_infos = gpus
    
    def set_wallets(self, wallets: Dict[str, str]):
        """Setzt Wallet-Adressen pro Coin"""
        self._wallets = wallets
    
    def set_worker_name(self, name: str):
        """Setzt Worker-Namen"""
        self._worker_name = name
    
    def get_profit_calculator(self):
        """Lazy-Load des Profit Calculators"""
        if self._profit_calculator is None:
            from multi_gpu_profit import get_multi_gpu_calculator
            self._profit_calculator = get_multi_gpu_calculator()
        return self._profit_calculator
    
    def calculate_optimal_configs(self) -> List[GPUMinerConfig]:
        """
        Berechnet optimale Mining-Konfiguration für alle GPUs
        
        Returns:
            Liste von GPU-Miner-Konfigurationen
        """
        if not self._gpu_infos:
            logger.warning("Keine GPUs konfiguriert")
            return []
        
        calc = self.get_profit_calculator()
        result = calc.calculate_all_gpus(self._gpu_infos)
        
        configs = []
        for gpu_info in result.gpus:
            # Wallet für diesen Coin
            wallet = self._wallets.get(gpu_info.best_coin, "")
            if not wallet:
                logger.warning(f"GPU {gpu_info.gpu_index}: Keine Wallet für {gpu_info.best_coin}")
                continue
            
            # Pool Info
            pool_info = calc.POOLS.get(gpu_info.best_coin, {})
            
            # Miner-Typ bestimmen
            miner_str = pool_info.get("miner", "T-Rex").lower()
            miner_type_map = {
                "t-rex": MinerType.TREX,
                "trex": MinerType.TREX,
                "lolminer": MinerType.LOLMINER,
                "gminer": MinerType.GMINER,
                "nbminer": MinerType.NBMINER,
                "rigel": MinerType.RIGEL,
            }
            miner_type = miner_type_map.get(miner_str, MinerType.TREX)
            
            config = GPUMinerConfig(
                gpu_index=gpu_info.gpu_index,
                gpu_name=gpu_info.gpu_name,
                gpu_model=gpu_info.gpu_model,
                coin=gpu_info.best_coin,
                algorithm=gpu_info.best_algorithm,
                pool_url=pool_info.get("url", ""),
                pool_name=pool_info.get("name", ""),
                wallet=wallet,
                worker=self._worker_name,
                miner_type=miner_type,
                expected_hashrate=gpu_info.best_hashrate,
                expected_profit_usd=gpu_info.best_profit_usd,
            )
            
            # OC-Settings holen (wenn verfügbar)
            self._apply_oc_settings(config)
            
            configs.append(config)
        
        return configs
    
    def _apply_oc_settings(self, config: GPUMinerConfig):
        """Lädt OC-Settings für eine Konfiguration"""
        try:
            # Versuche hashrate.no oder lokale Profile
            if hasattr(self.miner_manager, 'msi_ab_manager') and self.miner_manager.msi_ab_manager:
                profile = self.miner_manager.msi_ab_manager.get_mining_profile(
                    config.coin, 
                    config.gpu_name
                )
                if profile:
                    config.oc_core = profile.core_clock_offset
                    config.oc_memory = profile.memory_clock_offset
                    config.oc_power_limit = profile.power_limit
        except Exception as e:
            logger.debug(f"OC-Settings laden fehlgeschlagen: {e}")
    
    def start_all_optimal(self) -> bool:
        """
        Startet Mining auf allen GPUs mit optimalem Coin
        
        Returns:
            True wenn mindestens eine GPU gestartet
        """
        configs = self.calculate_optimal_configs()
        
        if not configs:
            logger.error("Keine Mining-Konfigurationen erstellt")
            return False
        
        success_count = 0
        for config in configs:
            if self.miner_manager.start_gpu_miner(config):
                success_count += 1
                logger.info(f"GPU {config.gpu_index}: Mining {config.coin} gestartet")
        
        logger.info(f"✅ {success_count}/{len(configs)} GPUs gestartet")
        return success_count > 0
    
    def stop_all(self):
        """Stoppt alle Miner"""
        self.miner_manager.stop_all_miners("User Stop")
    
    def start_auto_switching(self, check_interval: float = 180.0):
        """
        Startet automatisches Switching bei Profit-Änderungen
        
        Args:
            check_interval: Sekunden zwischen Profit-Checks
        """
        if self._running:
            return
        
        self._running = True
        self._switch_thread = threading.Thread(
            target=self._auto_switch_loop, 
            args=(check_interval,),
            daemon=True
        )
        self._switch_thread.start()
        logger.info("🔄 Auto-Switching gestartet")
    
    def stop_auto_switching(self):
        """Stoppt Auto-Switching"""
        self._running = False
        if self._switch_thread:
            self._switch_thread.join(timeout=2)
        logger.info("⏹️ Auto-Switching gestoppt")
    
    def _auto_switch_loop(self, interval: float):
        """Loop für automatisches Coin-Switching"""
        while self._running:
            try:
                self._check_for_switches()
            except Exception as e:
                logger.error(f"Auto-Switch Fehler: {e}")
            
            time.sleep(interval)
    
    def _check_for_switches(self):
        """Prüft ob Coin-Switches sinnvoll sind"""
        calc = self.get_profit_calculator()
        calc.fetch_coin_prices()  # Preise aktualisieren
        
        current_status = self.miner_manager.get_all_status()
        
        for gpu_idx, (idx, gpu_name) in enumerate(self._gpu_infos):
            if idx not in current_status:
                continue
            
            status = current_status[idx]
            if not status.is_running:
                continue
            
            current_coin = status.config.coin
            
            # Neuen besten Coin berechnen
            gpu_info = calc.calculate_best_coin_for_gpu(idx, gpu_name)
            new_best_coin = gpu_info.best_coin
            
            if new_best_coin == current_coin:
                continue
            
            # Profit-Unterschied prüfen
            current_profit = calc.calculate_profit_for_gpu(
                calc.match_gpu_model(gpu_name), 
                current_coin
            )
            new_profit = gpu_info.best_profit_usd
            
            if current_profit <= 0:
                profit_diff = 1.0  # 100% Unterschied wenn aktuell 0
            else:
                profit_diff = (new_profit - current_profit) / current_profit
            
            if profit_diff < self._profit_threshold:
                continue  # Zu wenig Unterschied
            
            # Minimum-Intervall prüfen
            last_switch = self._last_switch_time.get(idx, 0)
            if time.time() - last_switch < self._min_switch_interval:
                continue  # Zu früh für Switch
            
            # SWITCH!
            logger.info(f"GPU {idx}: Switch von {current_coin} zu {new_best_coin} (+{profit_diff*100:.1f}% Profit)")
            
            # Wallet prüfen
            wallet = self._wallets.get(new_best_coin, "")
            if not wallet:
                logger.warning(f"GPU {idx}: Keine Wallet für {new_best_coin} - Switch abgebrochen")
                continue
            
            # Neue Config erstellen
            pool_info = calc.POOLS.get(new_best_coin, {})
            miner_str = pool_info.get("miner", "T-Rex").lower()
            miner_type_map = {
                "t-rex": MinerType.TREX,
                "lolminer": MinerType.LOLMINER,
                "gminer": MinerType.GMINER,
            }
            
            new_config = GPUMinerConfig(
                gpu_index=idx,
                gpu_name=gpu_name,
                gpu_model=calc.match_gpu_model(gpu_name),
                coin=new_best_coin,
                algorithm=gpu_info.best_algorithm,
                pool_url=pool_info.get("url", ""),
                pool_name=pool_info.get("name", ""),
                wallet=wallet,
                worker=self._worker_name,
                miner_type=miner_type_map.get(miner_str, MinerType.TREX),
                expected_hashrate=gpu_info.best_hashrate,
                expected_profit_usd=new_profit,
            )
            
            self._apply_oc_settings(new_config)
            
            # Miner neu starten
            self.miner_manager.stop_gpu_miner(idx, f"Switch zu {new_best_coin}")
            time.sleep(2)
            self.miner_manager.start_gpu_miner(new_config)
            
            self._last_switch_time[idx] = time.time()
            
            if self.on_switch:
                self.on_switch(idx, current_coin, new_best_coin)


# ============================================================================
# SINGLETON
# ============================================================================

_manager: Optional[MultiMinerManager] = None
_switcher: Optional[MultiGPUAutoSwitcher] = None

def get_multi_miner_manager() -> MultiMinerManager:
    """Gibt Singleton-Instanz zurück"""
    global _manager
    if _manager is None:
        _manager = MultiMinerManager()
    return _manager

def get_multi_gpu_switcher() -> MultiGPUAutoSwitcher:
    """Gibt Singleton-Instanz zurück"""
    global _switcher
    if _switcher is None:
        _switcher = MultiGPUAutoSwitcher(get_multi_miner_manager())
    return _switcher


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 70)
    print("🎮 Multi-Miner Manager Test")
    print("=" * 70)
    
    manager = get_multi_miner_manager()
    switcher = get_multi_gpu_switcher()
    
    # Test GPUs konfigurieren
    test_gpus = [
        (0, "NVIDIA GeForce RTX 3080 Laptop GPU"),
        (1, "NVIDIA GeForce RTX 3070"),
    ]
    
    # Test Wallets
    test_wallets = {
        "RVN": "RVN_WALLET_ADDRESS",
        "ERG": "ERG_WALLET_ADDRESS",
        "GRIN": "GRIN_WALLET_ADDRESS",
        "KAS": "KAS_WALLET_ADDRESS",
    }
    
    switcher.set_gpu_infos(test_gpus)
    switcher.set_wallets(test_wallets)
    
    print("\n📊 Optimale Konfigurationen:")
    configs = switcher.calculate_optimal_configs()
    for config in configs:
        print(f"  GPU {config.gpu_index} ({config.gpu_model}):")
        print(f"    Coin: {config.coin}")
        print(f"    Algo: {config.algorithm}")
        print(f"    Pool: {config.pool_name}")
        print(f"    Miner: {config.miner_type.value}")
        print(f"    Profit: ${config.expected_profit_usd:.2f}/Tag")
    
    print("\n" + "=" * 70)
    print("✅ Test abgeschlossen!")
    print("=" * 70)
