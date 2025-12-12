#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Benchmark Manager - Echter Multi-Coin Benchmark mit Miner-Starts

Features:
- Startet echte Miner für jeden Coin
- Misst echte Hashrate über Miner-API
- Holt erwartete Werte von hashrate.no
- Berechnet Profit pro Coin
- Speichert Ergebnisse in JSON
"""

import json
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
import statistics

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CoinBenchmarkResult:
    """Ergebnis eines Coin-Benchmarks"""
    coin: str
    algorithm: str
    miner: str
    pool: str
    
    # Gemessene Werte
    avg_hashrate: float = 0.0
    min_hashrate: float = 0.0
    max_hashrate: float = 0.0
    hashrate_unit: str = "MH/s"
    
    # GPU Stats
    avg_temp: int = 0
    max_temp: int = 0
    avg_power: int = 0
    avg_fan: int = 0
    
    # Erwartete Werte (von hashrate.no)
    expected_hashrate: float = 0.0
    hashrate_diff_percent: float = 0.0  # Gemessen vs Erwartet
    
    # Profit
    profit_usd_day: float = 0.0
    profit_btc_day: float = 0.0
    electricity_cost: float = 0.0
    net_profit_day: float = 0.0
    
    # Effizienz
    efficiency: float = 0.0  # H/W
    
    # Meta
    duration_seconds: int = 60
    samples: int = 0
    stability: float = 0.0  # 0-100%
    timestamp: str = ""
    status: str = "pending"  # pending, running, success, failed, skipped
    error: str = ""


@dataclass
class BenchmarkSession:
    """Eine komplette Benchmark-Session"""
    session_id: str
    gpu_name: str
    gpu_index: int
    start_time: str
    end_time: str = ""
    
    results: List[CoinBenchmarkResult] = field(default_factory=list)
    
    # Gesamt-Stats
    total_coins_tested: int = 0
    successful_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    
    # Bester Coin
    best_coin: str = ""
    best_profit: float = 0.0
    best_hashrate: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "gpu_name": self.gpu_name,
            "gpu_index": self.gpu_index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "results": [asdict(r) for r in self.results],
            "total_coins_tested": self.total_coins_tested,
            "successful_tests": self.successful_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "best_coin": self.best_coin,
            "best_profit": self.best_profit,
            "best_hashrate": self.best_hashrate
        }


# =============================================================================
# COIN CONFIGURATIONS
# =============================================================================

# Coin -> (Algorithmus, Miner, Pool-URL, Port, Hashrate-Unit)
BENCHMARK_COINS = {
    "RVN": {
        "algorithm": "kawpow",
        "miner": "trex",
        "pool": "stratum+tcp://rvn.2miners.com",
        "port": 6060,
        "unit": "MH/s",
        "algo_param": "kawpow"
    },
    "ERG": {
        "algorithm": "autolykos2",
        "miner": "trex",
        "pool": "stratum+tcp://erg.2miners.com",
        "port": 8888,
        "unit": "MH/s",
        "algo_param": "autolykos2"
    },
    "ETC": {
        "algorithm": "etchash",
        "miner": "trex",
        "pool": "stratum+tcp://etc.2miners.com",
        "port": 1010,
        "unit": "MH/s",
        "algo_param": "etchash"
    },
    "FLUX": {
        "algorithm": "equihash125",
        "miner": "lolminer",
        "pool": "stratum+tcp://flux.2miners.com",
        "port": 9090,
        "unit": "Sol/s",
        "algo_param": "FLUX"
    },
    "BEAM": {
        "algorithm": "beamhash3",
        "miner": "lolminer",
        "pool": "stratum+tcp://beam.2miners.com",
        "port": 5252,
        "unit": "Sol/s",
        "algo_param": "BEAM-III"
    },
    "FIRO": {
        "algorithm": "firopow",
        "miner": "trex",
        "pool": "stratum+tcp://firo.2miners.com",
        "port": 8181,
        "unit": "MH/s",
        "algo_param": "firopow"
    },
    "CLORE": {
        "algorithm": "kawpow",
        "miner": "trex",
        "pool": "stratum+tcp://clore.woolypooly.com",
        "port": 3124,
        "unit": "MH/s",
        "algo_param": "kawpow"
    },
    "XNA": {
        "algorithm": "kawpow",
        "miner": "trex",
        "pool": "stratum+tcp://xna.woolypooly.com",
        "port": 3130,
        "unit": "MH/s",
        "algo_param": "kawpow"
    },
    "NEOX": {
        "algorithm": "kawpow",
        "miner": "trex",
        "pool": "stratum+tcp://neox.woolypooly.com",
        "port": 3128,
        "unit": "MH/s",
        "algo_param": "kawpow"
    },
    "KAS": {
        "algorithm": "kheavyhash",
        "miner": "lolminer",
        "pool": "stratum+tcp://kas.2miners.com",
        "port": 1818,
        "unit": "MH/s",
        "algo_param": "KASPA"
    },
    "ALPH": {
        "algorithm": "blake3",
        "miner": "trex",
        "pool": "stratum+tcp://alph.2miners.com",
        "port": 2020,
        "unit": "GH/s",
        "algo_param": "blake3"
    },
    "CFX": {
        "algorithm": "octopus",
        "miner": "trex",
        "pool": "stratum+tcp://cfx.2miners.com",
        "port": 6565,
        "unit": "MH/s",
        "algo_param": "octopus"
    },
    "NEXA": {
        "algorithm": "nexapow",
        "miner": "lolminer",
        "pool": "stratum+tcp://nexa.acc-pool.pw",
        "port": 16000,
        "unit": "MH/s",
        "algo_param": "NEXA"
    },
    "GRIN": {
        "algorithm": "cuckatoo32",
        "miner": "lolminer",
        "pool": "stratum+tcp://grin.2miners.com",
        "port": 3030,
        "unit": "G/s",
        "algo_param": "C32"
    },
    "ZEPH": {
        "algorithm": "randomx",
        "miner": "xmrig",
        "pool": "stratum+tcp://pool.zephyrprotocol.com",
        "port": 3333,
        "unit": "H/s",
        "algo_param": "rx/0"
    }
}


# =============================================================================
# MINER CONFIGURATIONS
# =============================================================================

MINER_CONFIGS = {
    "trex": {
        "exe": "miners/trex/t-rex.exe",
        "api_port": 4067,
        "cmd_template": "{exe} -a {algo} -o {pool}:{port} -u {wallet}.{worker} -p x --api-bind-http 127.0.0.1:{api_port}",
        "hashrate_key": "hashrate"
    },
    "lolminer": {
        "exe": "miners/lolminer/lolMiner.exe",
        "api_port": 8080,
        "cmd_template": "{exe} --algo {algo} --pool {pool}:{port} --user {wallet}.{worker} --apiport {api_port}",
        "hashrate_key": "Total_Performance"
    },
    "nbminer": {
        "exe": "miners/nbminer/nbminer.exe",
        "api_port": 22333,
        "cmd_template": "{exe} -a {algo} -o {pool}:{port} -u {wallet}.{worker} --api 127.0.0.1:{api_port}",
        "hashrate_key": "hashrate_raw"
    },
    "gminer": {
        "exe": "miners/gminer/miner.exe",
        "api_port": 10555,
        "cmd_template": "{exe} -a {algo} -s {pool} -n {port} -u {wallet}.{worker} --api {api_port}",
        "hashrate_key": "speed"
    },
    "xmrig": {
        "exe": "miners/xmrig/xmrig.exe",
        "api_port": 8888,
        "cmd_template": "{exe} -a {algo} -o {pool}:{port} -u {wallet} -p {worker} --http-port={api_port}",
        "hashrate_key": "hashrate.total[0]"
    }
}


# =============================================================================
# BENCHMARK MANAGER
# =============================================================================

class BenchmarkManager:
    """
    Manager für echte Multi-Coin Benchmarks
    """
    
    RESULTS_FILE = "benchmark_results.json"
    STABILIZE_TIME = 30  # Sekunden warten bevor Messung
    SAMPLE_INTERVAL = 5  # Sekunden zwischen Samples
    
    def __init__(self, wallets: Dict[str, str] = None, worker_name: str = "Rig_D"):
        """
        Args:
            wallets: Dict mit {coin: wallet_address}
            worker_name: Worker-Name für Pool
        """
        self.wallets = wallets or {}
        self.worker = worker_name
        
        self._running = False
        self._current_process: Optional[subprocess.Popen] = None
        self._current_session: Optional[BenchmarkSession] = None
        
        # Callbacks
        self._on_progress: Optional[Callable] = None
        self._on_coin_complete: Optional[Callable] = None
        self._on_session_complete: Optional[Callable] = None
        
        # hashrate.no API
        self._hashrate_api = None
        self._init_hashrate_api()
        
        # Profit Calculator
        self._profit_calc = None
        self._init_profit_calc()
    
    def _init_hashrate_api(self):
        """Initialisiert hashrate.no API"""
        try:
            from hashrateno_api import HashrateNoAPI
            self._hashrate_api = HashrateNoAPI()
            logger.info("hashrate.no API verbunden für Benchmark")
        except ImportError:
            logger.warning("hashrate.no API nicht verfügbar")
    
    def _init_profit_calc(self):
        """Initialisiert Profit Calculator"""
        try:
            from profit_calculator import ProfitCalculator
            self._profit_calc = ProfitCalculator()
            logger.info("Profit Calculator verbunden")
        except ImportError:
            logger.warning("Profit Calculator nicht verfügbar")
    
    def get_expected_hashrate(self, gpu_name: str, algorithm: str) -> float:
        """Holt erwartete Hashrate von hashrate.no"""
        if self._hashrate_api:
            try:
                return self._hashrate_api.get_expected_hashrate(gpu_name, algorithm)
            except Exception as e:
                logger.debug(f"hashrate.no Fehler: {e}")
        
        return 0.0
    
    def get_oc_settings_for_coin(self, gpu_name: str, coin: str) -> dict:
        """Holt OC-Settings für GPU + Coin von hashrate.no"""
        if self._hashrate_api:
            try:
                oc = self._hashrate_api.get_oc_settings(gpu_name, coin)
                return {
                    "core_offset": oc.core_clock_offset,
                    "mem_offset": oc.memory_clock_offset,
                    "power_limit": oc.power_limit_percent,
                    "fan_speed": oc.fan_speed,
                    "expected_hashrate": oc.hashrate,
                    "expected_power": oc.power_consumption,
                    "source": oc.source
                }
            except Exception as e:
                logger.debug(f"OC Settings Fehler: {e}")
        
        return {}
    
    def set_callbacks(self, 
                      on_progress: Callable = None,
                      on_coin_complete: Callable = None,
                      on_session_complete: Callable = None):
        """Setzt Callback-Funktionen"""
        self._on_progress = on_progress
        self._on_coin_complete = on_coin_complete
        self._on_session_complete = on_session_complete
    
    def get_available_coins(self) -> List[str]:
        """Gibt Liste der benchmarkbaren Coins zurück"""
        available = []
        
        for coin, config in BENCHMARK_COINS.items():
            miner = config.get("miner", "")
            miner_config = MINER_CONFIGS.get(miner, {})
            exe = miner_config.get("exe", "")
            
            # Prüfe ob Miner installiert
            if os.path.exists(exe):
                # Prüfe ob Wallet vorhanden
                if coin in self.wallets or coin.upper() in self.wallets:
                    available.append(coin)
                else:
                    logger.debug(f"{coin}: Keine Wallet konfiguriert")
            else:
                logger.debug(f"{coin}: Miner {miner} nicht installiert ({exe})")
        
        return available
    
    def get_coin_profit(self, coin: str, hashrate: float, power_watts: int) -> Tuple[float, float]:
        """
        Berechnet Profit für einen Coin
        
        Returns:
            (profit_usd_day, net_profit_after_electricity)
        """
        if not self._profit_calc:
            return 0.0, 0.0
        
        try:
            result = self._profit_calc.calculate_profit(coin, hashrate, power_watts)
            if result:
                gross = result.get("profit_usd_day", 0.0)
                electricity = result.get("electricity_cost_day", 0.0)
                return gross, gross - electricity
        except Exception as e:
            logger.debug(f"Profit Berechnung Fehler: {e}")
        
        return 0.0, 0.0
    
    def start_benchmark_session(self, 
                                 gpu_name: str,
                                 gpu_index: int,
                                 coins: List[str],
                                 duration_per_coin: int = 60) -> BenchmarkSession:
        """
        Startet eine Benchmark-Session für mehrere Coins
        
        Args:
            gpu_name: Name der GPU
            gpu_index: GPU Index
            coins: Liste der zu testenden Coins
            duration_per_coin: Sekunden pro Coin (ohne Stabilisierung)
        
        Returns:
            BenchmarkSession mit allen Ergebnissen
        """
        self._running = True
        
        # Session erstellen
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_session = BenchmarkSession(
            session_id=session_id,
            gpu_name=gpu_name,
            gpu_index=gpu_index,
            start_time=datetime.now().isoformat(),
            total_coins_tested=len(coins)
        )
        
        logger.info(f"=== Benchmark Session {session_id} ===")
        logger.info(f"GPU: {gpu_name}")
        logger.info(f"Coins: {', '.join(coins)}")
        logger.info(f"Dauer pro Coin: {duration_per_coin}s + {self.STABILIZE_TIME}s Stabilisierung")
        
        # Jeden Coin benchmarken
        for i, coin in enumerate(coins):
            if not self._running:
                logger.info("Benchmark abgebrochen")
                break
            
            progress = (i / len(coins)) * 100
            if self._on_progress:
                self._on_progress(progress, f"Teste {coin} ({i+1}/{len(coins)})...")
            
            result = self._benchmark_single_coin(
                coin, gpu_name, gpu_index, duration_per_coin
            )
            
            self._current_session.results.append(result)
            
            if result.status == "success":
                self._current_session.successful_tests += 1
            elif result.status == "failed":
                self._current_session.failed_tests += 1
            else:
                self._current_session.skipped_tests += 1
            
            if self._on_coin_complete:
                self._on_coin_complete(result)
            
            # Kurze Pause zwischen Coins
            if self._running and i < len(coins) - 1:
                time.sleep(3)
        
        # Besten Coin finden
        successful_results = [r for r in self._current_session.results if r.status == "success"]
        if successful_results:
            best = max(successful_results, key=lambda r: r.net_profit_day)
            self._current_session.best_coin = best.coin
            self._current_session.best_profit = best.net_profit_day
            self._current_session.best_hashrate = best.avg_hashrate
        
        self._current_session.end_time = datetime.now().isoformat()
        
        # Speichern
        self._save_results()
        
        if self._on_session_complete:
            self._on_session_complete(self._current_session)
        
        if self._on_progress:
            self._on_progress(100, "Benchmark abgeschlossen!")
        
        logger.info(f"=== Benchmark Session abgeschlossen ===")
        logger.info(f"Erfolgreich: {self._current_session.successful_tests}")
        logger.info(f"Fehlgeschlagen: {self._current_session.failed_tests}")
        if self._current_session.best_coin:
            logger.info(f"Bester Coin: {self._current_session.best_coin} (${self._current_session.best_profit:.2f}/Tag)")
        
        self._running = False
        return self._current_session
    
    def _benchmark_single_coin(self, coin: str, gpu_name: str, gpu_index: int, 
                                duration: int) -> CoinBenchmarkResult:
        """Benchmarkt einen einzelnen Coin"""
        config = BENCHMARK_COINS.get(coin)
        if not config:
            return CoinBenchmarkResult(
                coin=coin, algorithm="", miner="", pool="",
                status="skipped", error="Coin nicht konfiguriert"
            )
        
        miner_id = config.get("miner", "")
        miner_config = MINER_CONFIGS.get(miner_id, {})
        
        if not miner_config:
            return CoinBenchmarkResult(
                coin=coin, algorithm=config["algorithm"], miner=miner_id, pool="",
                status="skipped", error=f"Miner {miner_id} nicht konfiguriert"
            )
        
        exe = miner_config.get("exe", "")
        if not os.path.exists(exe):
            return CoinBenchmarkResult(
                coin=coin, algorithm=config["algorithm"], miner=miner_id, pool="",
                status="skipped", error=f"Miner nicht installiert: {exe}"
            )
        
        # Wallet suchen
        wallet = self.wallets.get(coin) or self.wallets.get(coin.upper(), "")
        if not wallet:
            return CoinBenchmarkResult(
                coin=coin, algorithm=config["algorithm"], miner=miner_id, pool="",
                status="skipped", error="Keine Wallet konfiguriert"
            )
        
        result = CoinBenchmarkResult(
            coin=coin,
            algorithm=config["algorithm"],
            miner=miner_id,
            pool=f"{config['pool']}:{config['port']}",
            hashrate_unit=config["unit"],
            duration_seconds=duration,
            timestamp=datetime.now().isoformat(),
            status="running"
        )
        
        # Erwartete Hashrate von hashrate.no
        result.expected_hashrate = self.get_expected_hashrate(gpu_name, config["algorithm"])
        
        logger.info(f"--- Benchmark {coin} ---")
        logger.info(f"Miner: {miner_id}, Algo: {config['algorithm']}")
        logger.info(f"Pool: {config['pool']}:{config['port']}")
        logger.info(f"Erwartete Hashrate: {result.expected_hashrate} {result.hashrate_unit}")
        
        try:
            # Miner starten
            cmd = self._build_miner_command(miner_id, config, wallet)
            logger.info(f"Starte: {cmd}")
            
            self._current_process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Stabilisierung
            logger.info(f"Warte {self.STABILIZE_TIME}s auf Stabilisierung...")
            for i in range(self.STABILIZE_TIME):
                if not self._running:
                    break
                time.sleep(1)
                if self._on_progress:
                    sub_progress = (i / self.STABILIZE_TIME) * 30
                    self._on_progress(sub_progress, f"{coin}: Stabilisierung... {i+1}/{self.STABILIZE_TIME}s")
            
            # Samples sammeln
            samples_hashrate = []
            samples_temp = []
            samples_power = []
            samples_fan = []
            
            api_port = miner_config.get("api_port", 4067)
            sample_count = duration // self.SAMPLE_INTERVAL
            
            logger.info(f"Sammle {sample_count} Samples über {duration}s...")
            
            for i in range(sample_count):
                if not self._running:
                    break
                
                # Hashrate von Miner-API holen
                hashrate = self._get_miner_hashrate(miner_id, api_port)
                gpu_stats = self._get_gpu_stats(gpu_index)
                
                if hashrate > 0:
                    samples_hashrate.append(hashrate)
                    samples_temp.append(gpu_stats.get("temp", 0))
                    samples_power.append(gpu_stats.get("power", 0))
                    samples_fan.append(gpu_stats.get("fan", 0))
                
                time.sleep(self.SAMPLE_INTERVAL)
                
                if self._on_progress:
                    sub_progress = 30 + ((i / sample_count) * 60)
                    self._on_progress(sub_progress, f"{coin}: Messe... {hashrate:.1f} {result.hashrate_unit}")
            
            # Miner stoppen
            self._stop_miner()
            
            # Ergebnis berechnen
            if samples_hashrate:
                result.avg_hashrate = statistics.mean(samples_hashrate)
                result.min_hashrate = min(samples_hashrate)
                result.max_hashrate = max(samples_hashrate)
                result.samples = len(samples_hashrate)
                
                if samples_temp:
                    result.avg_temp = int(statistics.mean(samples_temp))
                    result.max_temp = max(samples_temp)
                if samples_power:
                    result.avg_power = int(statistics.mean(samples_power))
                if samples_fan:
                    result.avg_fan = int(statistics.mean(samples_fan))
                
                # Stabilität
                if len(samples_hashrate) > 1:
                    std = statistics.stdev(samples_hashrate)
                    result.stability = max(0, 100 - (std / result.avg_hashrate * 100))
                else:
                    result.stability = 100
                
                # Effizienz
                if result.avg_power > 0:
                    result.efficiency = result.avg_hashrate / result.avg_power
                
                # Differenz zu erwartet
                if result.expected_hashrate > 0:
                    result.hashrate_diff_percent = (
                        (result.avg_hashrate - result.expected_hashrate) / result.expected_hashrate * 100
                    )
                
                # Profit berechnen
                gross, net = self.get_coin_profit(coin, result.avg_hashrate, result.avg_power)
                result.profit_usd_day = gross
                result.net_profit_day = net
                result.electricity_cost = gross - net
                
                result.status = "success"
                logger.info(f"✓ {coin}: {result.avg_hashrate:.2f} {result.hashrate_unit}, ${result.net_profit_day:.2f}/Tag")
            else:
                result.status = "failed"
                result.error = "Keine Hashrate-Samples gesammelt"
                logger.error(f"✗ {coin}: Keine Samples")
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            logger.error(f"✗ {coin}: {e}")
            self._stop_miner()
        
        return result
    
    def _build_miner_command(self, miner_id: str, coin_config: dict, wallet: str) -> str:
        """Baut den Miner-Befehl"""
        miner = MINER_CONFIGS.get(miner_id, {})
        
        template = miner.get("cmd_template", "")
        exe = miner.get("exe", "")
        api_port = miner.get("api_port", 4067)
        
        pool = coin_config.get("pool", "")
        port = coin_config.get("port", 3333)
        algo = coin_config.get("algo_param", "")
        
        cmd = template.format(
            exe=exe,
            algo=algo,
            pool=pool,
            port=port,
            wallet=wallet,
            worker=self.worker,
            api_port=api_port
        )
        
        return cmd
    
    def _get_miner_hashrate(self, miner_id: str, port: int) -> float:
        """Holt Hashrate von Miner-API"""
        import requests
        
        try:
            if miner_id == "trex":
                r = requests.get(f"http://127.0.0.1:{port}/summary", timeout=5)
                data = r.json()
                return data.get("hashrate", 0) / 1_000_000  # H/s -> MH/s
            
            elif miner_id == "lolminer":
                r = requests.get(f"http://127.0.0.1:{port}/", timeout=5)
                data = r.json()
                return data.get("Session", {}).get("Performance_Summary", 0)
            
            elif miner_id == "nbminer":
                r = requests.get(f"http://127.0.0.1:{port}/api/v1/status", timeout=5)
                data = r.json()
                devices = data.get("miner", {}).get("devices", [])
                if devices:
                    return devices[0].get("hashrate_raw", 0) / 1_000_000
            
            elif miner_id == "gminer":
                r = requests.get(f"http://127.0.0.1:{port}/stat", timeout=5)
                data = r.json()
                devices = data.get("devices", [])
                if devices:
                    return devices[0].get("speed", 0) / 1_000_000
            
            elif miner_id == "xmrig":
                r = requests.get(f"http://127.0.0.1:{port}/1/summary", timeout=5)
                data = r.json()
                hashrate = data.get("hashrate", {}).get("total", [0])[0]
                return hashrate
        
        except Exception as e:
            logger.debug(f"Miner API Fehler: {e}")
        
        return 0.0
    
    def _get_gpu_stats(self, gpu_index: int) -> dict:
        """Holt GPU Stats via NVML"""
        try:
            from pynvml import nvmlInit, nvmlDeviceGetHandleByIndex
            from pynvml import nvmlDeviceGetTemperature, nvmlDeviceGetPowerUsage
            from pynvml import nvmlDeviceGetUtilizationRates, NVML_TEMPERATURE_GPU
            
            nvmlInit()
            handle = nvmlDeviceGetHandleByIndex(gpu_index)
            
            return {
                "temp": nvmlDeviceGetTemperature(handle, NVML_TEMPERATURE_GPU),
                "power": nvmlDeviceGetPowerUsage(handle) // 1000,  # mW -> W
                "fan": 0  # Braucht extra API
            }
        except Exception as e:
            logger.debug(f"NVML Fehler: {e}")
        
        return {"temp": 0, "power": 0, "fan": 0}
    
    def _stop_miner(self):
        """Stoppt den aktuellen Miner-Prozess"""
        if self._current_process:
            try:
                if os.name == 'nt':
                    subprocess.run(
                        f"taskkill /F /T /PID {self._current_process.pid}",
                        shell=True, capture_output=True
                    )
                else:
                    self._current_process.terminate()
                
                self._current_process.wait(timeout=5)
            except:
                pass
            finally:
                self._current_process = None
    
    def stop(self):
        """Stoppt den Benchmark"""
        self._running = False
        self._stop_miner()
    
    def _save_results(self):
        """Speichert Ergebnisse in JSON"""
        if not self._current_session:
            return
        
        try:
            # Existierende Ergebnisse laden
            results_file = Path(self.RESULTS_FILE)
            all_sessions = []
            
            if results_file.exists():
                with open(results_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_sessions = data.get("sessions", [])
            
            # Neue Session hinzufügen
            all_sessions.append(self._current_session.to_dict())
            
            # Nur letzte 10 Sessions behalten
            all_sessions = all_sessions[-10:]
            
            # Speichern
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "sessions": all_sessions,
                    "last_update": datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Benchmark-Ergebnisse gespeichert: {results_file}")
        
        except Exception as e:
            logger.error(f"Ergebnisse speichern Fehler: {e}")
    
    def load_last_results(self) -> Optional[BenchmarkSession]:
        """Lädt die letzte Benchmark-Session"""
        try:
            results_file = Path(self.RESULTS_FILE)
            if not results_file.exists():
                return None
            
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions = data.get("sessions", [])
                
                if sessions:
                    last = sessions[-1]
                    session = BenchmarkSession(
                        session_id=last["session_id"],
                        gpu_name=last["gpu_name"],
                        gpu_index=last["gpu_index"],
                        start_time=last["start_time"],
                        end_time=last.get("end_time", ""),
                        total_coins_tested=last.get("total_coins_tested", 0),
                        successful_tests=last.get("successful_tests", 0),
                        failed_tests=last.get("failed_tests", 0),
                        skipped_tests=last.get("skipped_tests", 0),
                        best_coin=last.get("best_coin", ""),
                        best_profit=last.get("best_profit", 0),
                        best_hashrate=last.get("best_hashrate", 0)
                    )
                    
                    for r in last.get("results", []):
                        session.results.append(CoinBenchmarkResult(**r))
                    
                    return session
        
        except Exception as e:
            logger.error(f"Ergebnisse laden Fehler: {e}")
        
        return None


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=== Benchmark Manager Test ===\n")
    
    # Test-Wallets
    test_wallets = {
        "RVN": "RUVuL3CG2c9qTX3bCr32AfCZ5DJEfdJUTR",
        "ERG": "9gXA8UYPGvh4FMy5K1JQRqhp7rSUzZ3Y4kz4BfQhRnwJEuvYmqX"
    }
    
    manager = BenchmarkManager(wallets=test_wallets)
    
    available = manager.get_available_coins()
    print(f"Verfügbare Coins: {available}")
    
    # Letzte Ergebnisse
    last = manager.load_last_results()
    if last:
        print(f"\nLetzte Session: {last.session_id}")
        print(f"Bester Coin: {last.best_coin} (${last.best_profit:.2f}/Tag)")
