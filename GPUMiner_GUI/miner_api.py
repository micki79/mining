#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Miner API Client - Kommunikation mit Mining-Software
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Unified API für T-Rex, NBMiner, GMiner, lolMiner
- Live Hashrate, Shares, Temperature Abruf
- Miner-Prozess Management
- Log-Streaming
"""

import json
import time
import logging
import subprocess
import threading
import re
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

try:
    import requests
except ImportError:
    requests = None
    print("⚠️ requests nicht installiert. Installiere mit: pip install requests")

logger = logging.getLogger(__name__)


class MinerType(Enum):
    """Unterstützte Miner"""
    TREX = "trex"
    NBMINER = "nbminer"
    GMINER = "gminer"
    LOLMINER = "lolminer"
    TEAMREDMINER = "teamredminer"
    PHOENIXMINER = "phoenixminer"
    RIGEL = "rigel"
    BZMINER = "bzminer"
    SRBMINER = "srbminer"
    ONEZEROMINER = "onezerominer"
    WILDRIG = "wildrig"
    XMRIG = "xmrig"  # CPU Miner für RandomX (Monero, Zephyr)
    UNKNOWN = "unknown"


@dataclass
class GPUMinerStats:
    """Mining-Statistiken pro GPU"""
    index: int
    hashrate: float = 0.0  # In Hash-Einheit des Algorithmus
    hashrate_unit: str = "MH/s"
    temperature: int = 0
    fan_speed: int = 0
    power: float = 0.0
    accepted: int = 0
    rejected: int = 0
    efficiency: float = 0.0


@dataclass
class MinerStats:
    """Gesamte Mining-Statistiken"""
    miner_type: str = ""
    version: str = ""
    uptime: int = 0
    algorithm: str = ""
    pool: str = ""
    total_hashrate: float = 0.0
    hashrate_unit: str = "MH/s"
    total_accepted: int = 0
    total_rejected: int = 0
    total_power: float = 0.0
    gpus: List[GPUMinerStats] = field(default_factory=list)
    raw_data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'miner_type': self.miner_type,
            'version': self.version,
            'uptime': self.uptime,
            'algorithm': self.algorithm,
            'pool': self.pool,
            'total_hashrate': self.total_hashrate,
            'hashrate_unit': self.hashrate_unit,
            'total_accepted': self.total_accepted,
            'total_rejected': self.total_rejected,
            'total_power': self.total_power,
            'gpus': [
                {
                    'index': g.index,
                    'hashrate': g.hashrate,
                    'temperature': g.temperature,
                    'fan_speed': g.fan_speed,
                    'power': g.power,
                    'accepted': g.accepted,
                    'rejected': g.rejected,
                }
                for g in self.gpus
            ]
        }


# Miner API Konfigurationen
MINER_API_CONFIG = {
    MinerType.TREX: {
        'default_port': 4067,
        'endpoint': '/summary',
        'protocol': 'http',
    },
    MinerType.NBMINER: {
        'default_port': 22333,
        'endpoint': '/api/v1/status',
        'protocol': 'http',
    },
    MinerType.GMINER: {
        'default_port': 10555,
        'endpoint': '/stat',
        'protocol': 'http',
    },
    MinerType.LOLMINER: {
        'default_port': 8080,
        'endpoint': '',  # lolMiner verwendet root "/" nicht "/summary"
        'protocol': 'http',
    },
    MinerType.TEAMREDMINER: {
        'default_port': 4028,
        'endpoint': None,  # Socket-basiert
        'protocol': 'socket',
    },
    MinerType.PHOENIXMINER: {
        'default_port': 3333,
        'endpoint': '/getstat',  # CDM Port
        'protocol': 'http',
    },
    MinerType.XMRIG: {
        'default_port': 8080,
        'endpoint': '/1/summary',  # XMRig HTTP API
        'protocol': 'http',
    },
}


class MinerAPIClient:
    """
    Client für Miner HTTP/Socket APIs.
    
    Verwendung:
        client = MinerAPIClient(MinerType.TREX, port=4067)
        stats = client.get_stats()
        print(f"Hashrate: {stats.total_hashrate} {stats.hashrate_unit}")
    """
    
    def __init__(self, miner_type: MinerType, host: str = '127.0.0.1', port: int = None):
        """
        Initialisiert den API Client.
        
        Args:
            miner_type: Typ des Miners
            host: API Host (default: localhost)
            port: API Port (default: miner-spezifisch)
        """
        self.miner_type = miner_type
        self.host = host
        
        config = MINER_API_CONFIG.get(miner_type, {})
        self.port = port or config.get('default_port', 4067)
        self.endpoint = config.get('endpoint', '/summary')
        self.protocol = config.get('protocol', 'http')
        
        self._last_stats: Optional[MinerStats] = None
        self._last_update = 0
    
    def get_url(self) -> str:
        """Gibt die vollständige API URL zurück"""
        return f"{self.protocol}://{self.host}:{self.port}{self.endpoint}"
    
    def is_available(self) -> bool:
        """Prüft ob der Miner erreichbar ist"""
        if not requests:
            return False
        
        try:
            response = requests.get(self.get_url(), timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def get_stats(self) -> Optional[MinerStats]:
        """
        Holt die aktuellen Mining-Statistiken.
        
        Returns:
            MinerStats Objekt oder None bei Fehler
        """
        if not requests:
            return None
        
        try:
            url = self.get_url()
            # INFO-Level für Debugging während Entwicklung
            logger.info(f"🔍 API Request: {url} (Miner: {self.miner_type.value})")
            response = requests.get(url, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"API Response Status: {response.status_code}")
                return None
            
            data = response.json()
            # Zeige API Response für Debug
            logger.info(f"📊 API Response Keys: {list(data.keys())}")
            
            stats = self._parse_response(data)
            
            if stats:
                logger.info(f"✅ Parsed: HR={stats.total_hashrate:.3f} {stats.hashrate_unit}, A={stats.total_accepted}, R={stats.total_rejected}, P={stats.total_power:.1f}W")
            else:
                logger.warning(f"❌ Parser returned None")
            
            self._last_stats = stats
            self._last_update = time.time()
            
            return stats
            
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ API Timeout: {self.miner_type.value}")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 Miner nicht erreichbar: {self.miner_type.value} auf {self.get_url()} - {e}")
        except json.JSONDecodeError as e:
            logger.error(f"📛 Ungültige JSON Response: {self.miner_type.value} - {e}")
        except Exception as e:
            logger.error(f"💥 API Fehler: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return None
    
    def _parse_response(self, data: Dict) -> MinerStats:
        """Parst die API Response basierend auf Miner-Typ"""
        
        if self.miner_type == MinerType.TREX:
            return self._parse_trex(data)
        elif self.miner_type == MinerType.NBMINER:
            return self._parse_nbminer(data)
        elif self.miner_type == MinerType.GMINER:
            return self._parse_gminer(data)
        elif self.miner_type == MinerType.LOLMINER:
            return self._parse_lolminer(data)
        elif self.miner_type == MinerType.PHOENIXMINER:
            return self._parse_phoenixminer(data)
        elif self.miner_type == MinerType.XMRIG:
            return self._parse_xmrig(data)
        else:
            return MinerStats(raw_data=data)
    
    def _parse_trex(self, data: Dict) -> MinerStats:
        """Parst T-Rex API Response"""
        stats = MinerStats(
            miner_type="T-Rex",
            version=data.get('version', ''),
            uptime=data.get('uptime', 0),
            algorithm=data.get('algorithm', ''),
            pool=data.get('active_pool', {}).get('url', ''),
            total_hashrate=data.get('hashrate', 0) / 1e6,  # H/s -> MH/s
            hashrate_unit="MH/s",
            total_accepted=data.get('accepted_count', 0),
            total_rejected=data.get('rejected_count', 0),
            raw_data=data,
        )
        
        # GPU Stats
        for gpu_data in data.get('gpus', []):
            gpu = GPUMinerStats(
                index=gpu_data.get('gpu_id', 0),
                hashrate=gpu_data.get('hashrate', 0) / 1e6,
                temperature=gpu_data.get('temperature', 0),
                fan_speed=gpu_data.get('fan_speed', 0),
                power=gpu_data.get('power', 0),
                accepted=gpu_data.get('accepted_count', 0),
                rejected=gpu_data.get('rejected_count', 0),
            )
            gpu.efficiency = gpu.hashrate / gpu.power if gpu.power > 0 else 0
            stats.gpus.append(gpu)
            stats.total_power += gpu.power
        
        return stats
    
    def _parse_nbminer(self, data: Dict) -> MinerStats:
        """Parst NBMiner API Response"""
        miner_info = data.get('miner', {})
        stratum = data.get('stratum', {})
        
        stats = MinerStats(
            miner_type="NBMiner",
            version=miner_info.get('version', ''),
            uptime=int(time.time() - miner_info.get('start_time', time.time())),
            algorithm=stratum.get('algorithm', ''),
            pool=stratum.get('url', ''),
            total_hashrate=miner_info.get('total_hashrate_raw', 0) / 1e6,
            hashrate_unit="MH/s",
            total_accepted=stratum.get('accepted_shares', 0),
            total_rejected=stratum.get('rejected_shares', 0),
            raw_data=data,
        )
        
        # GPU Stats
        for gpu_data in miner_info.get('devices', []):
            gpu = GPUMinerStats(
                index=gpu_data.get('id', 0),
                hashrate=gpu_data.get('hashrate_raw', 0) / 1e6,
                temperature=gpu_data.get('temperature', 0),
                fan_speed=gpu_data.get('fan', 0),
                power=gpu_data.get('power', 0),
                accepted=gpu_data.get('accepted_shares', 0),
                rejected=gpu_data.get('rejected_shares', 0),
            )
            gpu.efficiency = gpu.hashrate / gpu.power if gpu.power > 0 else 0
            stats.gpus.append(gpu)
            stats.total_power += gpu.power
        
        return stats
    
    def _parse_gminer(self, data: Dict) -> MinerStats:
        """Parst GMiner API Response"""
        stats = MinerStats(
            miner_type="GMiner",
            version=data.get('miner', ''),
            uptime=data.get('uptime', 0),
            algorithm=data.get('algorithm', ''),
            pool=data.get('server', ''),
            total_hashrate=data.get('total_hashrate', 0) / 1e6,
            hashrate_unit="MH/s",
            total_accepted=data.get('total_accepted_shares', 0),
            total_rejected=data.get('total_rejected_shares', 0),
            raw_data=data,
        )
        
        # GPU Stats
        for gpu_data in data.get('devices', []):
            gpu = GPUMinerStats(
                index=gpu_data.get('gpu_id', 0),
                hashrate=gpu_data.get('hashrate', 0) / 1e6,
                temperature=gpu_data.get('temperature', 0),
                fan_speed=gpu_data.get('fan', 0),
                power=gpu_data.get('power_usage', 0),
                accepted=gpu_data.get('accepted_shares', 0),
                rejected=gpu_data.get('rejected_shares', 0),
            )
            gpu.efficiency = gpu.hashrate / gpu.power if gpu.power > 0 else 0
            stats.gpus.append(gpu)
            stats.total_power += gpu.power
        
        return stats
    
    def _parse_lolminer(self, data: Dict) -> MinerStats:
        """Parst lolMiner API Response (v1.88+)
        
        lolMiner API kann verschiedene Formate haben:
        - Session.Performance_Summary oder Session.Total_Performance
        - GPUs[].Performance oder GPUs[].Hashrate
        - Verschiedene Temperatur-Feldnamen
        """
        session = data.get('Session', {})
        mining = data.get('Mining', {})
        
        # Debug: Zeige API Response Struktur
        logger.debug(f"lolMiner API Keys: {list(data.keys())}")
        logger.debug(f"Session Keys: {list(session.keys()) if session else 'None'}")
        
        # Hashrate aus verschiedenen möglichen Feldern
        total_hashrate = 0.0
        hashrate_fields = ['Performance_Summary', 'Total_Performance', 'Performance', 'Hashrate']
        for field in hashrate_fields:
            if field in session and session[field] > 0:
                total_hashrate = session[field]
                logger.debug(f"lolMiner Hashrate aus Session.{field}: {total_hashrate}")
                break
        
        # Wenn keine Session-Hashrate, summiere GPU Hashrates
        if total_hashrate == 0 and 'GPUs' in data:
            for gpu_data in data['GPUs']:
                gpu_hr = gpu_data.get('Performance', 0) or gpu_data.get('Hashrate', 0) or gpu_data.get('Speed', 0)
                total_hashrate += gpu_hr
            logger.debug(f"lolMiner Hashrate aus GPUs summiert: {total_hashrate}")
        
        # Algorithmus bestimmen für Hashrate-Einheit
        algorithm = mining.get('Algorithm', '') or session.get('Algorithm', '')
        
        # Hashrate-Einheit basierend auf Algorithmus
        hashrate_unit = "MH/s"
        algo_lower = algorithm.lower()
        if 'cuck' in algo_lower or 'c32' in algo_lower or 'c31' in algo_lower or 'c29' in algo_lower:
            hashrate_unit = "g/s"  # Cuckatoo = graphs/second
        elif 'equi' in algo_lower or 'beam' in algo_lower or 'zhash' in algo_lower:
            hashrate_unit = "Sol/s"  # Equihash = solutions/second
        elif 'kheavy' in algo_lower:
            hashrate_unit = "GH/s"  # KHeavyHash (KAS)
        elif 'blake3' in algo_lower:
            hashrate_unit = "GH/s"
        
        # Accepted/Rejected
        total_accepted = session.get('Accepted', 0) or session.get('Shares', {}).get('Accepted', 0) or 0
        total_rejected = session.get('Rejected', 0) or session.get('Shares', {}).get('Rejected', 0) or 0
        
        # Shares aus "Shares" Dict falls vorhanden
        if 'Shares' in session and isinstance(session['Shares'], dict):
            total_accepted = session['Shares'].get('Accepted', total_accepted)
            total_rejected = session['Shares'].get('Rejected', total_rejected)
        
        stats = MinerStats(
            miner_type="lolMiner",
            version=data.get('Software', ''),
            uptime=session.get('Uptime', 0),
            algorithm=algorithm,
            pool=session.get('ActivePool', '') or session.get('Pool', ''),
            total_hashrate=total_hashrate,
            hashrate_unit=hashrate_unit,
            total_accepted=total_accepted,
            total_rejected=total_rejected,
            raw_data=data,
        )
        
        # GPU Stats
        for gpu_data in data.get('GPUs', []):
            # Verschiedene mögliche Feldnamen für GPU-Daten
            gpu_hashrate = gpu_data.get('Performance', 0) or gpu_data.get('Hashrate', 0) or gpu_data.get('Speed', 0)
            gpu_temp = gpu_data.get('Temp (deg C)', 0) or gpu_data.get('Temperature', 0) or gpu_data.get('Temp', 0)
            gpu_fan = gpu_data.get('Fan Speed (%)', 0) or gpu_data.get('Fan', 0) or gpu_data.get('FanSpeed', 0)
            gpu_power = gpu_data.get('Power (W)', 0) or gpu_data.get('Power', 0) or gpu_data.get('PowerDraw', 0)
            
            gpu = GPUMinerStats(
                index=gpu_data.get('Index', 0),
                hashrate=gpu_hashrate,
                hashrate_unit=hashrate_unit,
                temperature=int(gpu_temp),
                fan_speed=int(gpu_fan),
                power=float(gpu_power),
                accepted=gpu_data.get('Session_Accepted', 0) or gpu_data.get('Accepted', 0),
                rejected=gpu_data.get('Session_Rejected', 0) or gpu_data.get('Rejected', 0),
            )
            gpu.efficiency = gpu.hashrate / gpu.power if gpu.power > 0 else 0
            stats.gpus.append(gpu)
            stats.total_power += gpu.power
        
        logger.debug(f"lolMiner Stats: HR={stats.total_hashrate:.2f} {stats.hashrate_unit}, A={stats.total_accepted}, R={stats.total_rejected}, Power={stats.total_power}W")
        
        return stats
    
    def _parse_phoenixminer(self, data: Dict) -> MinerStats:
        """Parst PhoenixMiner CDM API Response"""
        # PhoenixMiner hat ein anderes Format
        stats = MinerStats(
            miner_type="PhoenixMiner",
            raw_data=data,
        )
        
        # Einfaches Parsing - PhoenixMiner variiert stark
        if isinstance(data, dict):
            stats.total_hashrate = data.get('total_hashrate', 0) / 1e6
            stats.total_accepted = data.get('total_shares', 0)
        
        return stats
    
    def _parse_xmrig(self, data: Dict) -> MinerStats:
        """
        Parst XMRig HTTP API Response
        
        XMRig API Format (/1/summary):
        {
            "id": "...",
            "worker_id": "...",
            "version": "6.21.1",
            "kind": "cpu",
            "algo": "rx/0",
            "hashrate": {"total": [1234.5, 1200.0, 1150.0], "highest": 1300.0},
            "connection": {"pool": "pool:port", "accepted": 10, "rejected": 0},
            "cpu": {"brand": "AMD Ryzen 9 5900HX", "cores": 8, "threads": 16}
        }
        """
        hashrate_data = data.get('hashrate', {})
        connection = data.get('connection', {})
        cpu_info = data.get('cpu', {})
        
        # Hashrate in H/s (XMRig liefert H/s direkt)
        total_hashrates = hashrate_data.get('total', [0, 0, 0])
        current_hashrate = total_hashrates[0] if total_hashrates else 0
        
        stats = MinerStats(
            miner_type="XMRig",
            version=data.get('version', ''),
            uptime=data.get('uptime', 0),
            algorithm=data.get('algo', 'randomx'),
            pool=connection.get('pool', ''),
            total_hashrate=current_hashrate / 1000,  # H/s -> kH/s für Anzeige
            hashrate_unit="kH/s",  # RandomX wird in kH/s angezeigt
            total_accepted=connection.get('accepted', 0),
            total_rejected=connection.get('rejected', 0),
            raw_data=data,
        )
        
        # CPU als "GPU" 0 behandeln (für einheitliche Anzeige)
        cpu_gpu = GPUMinerStats(
            index=0,
            hashrate=current_hashrate / 1000,  # kH/s
            hashrate_unit="kH/s",
            temperature=0,  # XMRig liefert keine CPU Temp
            fan_speed=0,
            power=0,  # Keine Power-Info
            accepted=connection.get('accepted', 0),
            rejected=connection.get('rejected', 0),
        )
        stats.gpus.append(cpu_gpu)
        
        # CPU-Info in Stats speichern
        if cpu_info:
            stats.miner_type = f"XMRig (CPU: {cpu_info.get('brand', 'Unknown')})"
        
        return stats
    
    def get_hashrates(self) -> Dict[int, float]:
        """
        Holt nur die Hashrates pro GPU.
        
        Returns:
            Dict mit {gpu_index: hashrate}
        """
        stats = self.get_stats()
        if not stats:
            return {}
        
        return {gpu.index: gpu.hashrate for gpu in stats.gpus}


class MinerProcess:
    """
    Verwaltet einen Miner-Prozess.
    
    Verwendung:
        miner = MinerProcess(MinerType.TREX, "/path/to/t-rex.exe")
        miner.on_output = lambda line: print(line)
        miner.start(["-a", "kawpow", "-o", "pool:port", "-u", "wallet"])
        
        # Später
        miner.stop()
    """
    
    def __init__(self, miner_type: MinerType, executable_path: str):
        """
        Initialisiert den Miner-Prozess Manager.
        
        Args:
            miner_type: Typ des Miners
            executable_path: Pfad zur Miner-Executable
        """
        self.miner_type = miner_type
        self.executable_path = Path(executable_path)
        
        self._process: Optional[subprocess.Popen] = None
        self._output_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks
        self.on_output: Optional[Callable[[str], None]] = None
        self.on_hashrate: Optional[Callable[[Dict[int, float]], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_stopped: Optional[Callable[[], None]] = None
        
        # Regex für Hashrate-Extraktion aus Log
        self._hashrate_patterns = {
            MinerType.TREX: re.compile(r'GPU #(\d+):\s*([\d.]+)\s*([KMGT]?H/s)'),
            MinerType.NBMINER: re.compile(r'\[(\d+)\]\s*.*?\s*([\d.]+)\s*([KMGT]?H/s)'),
            MinerType.GMINER: re.compile(r'GPU(\d+)\s*([\d.]+)\s*([KMGT]?H/s)'),
        }
    
    def is_running(self) -> bool:
        """Prüft ob der Miner läuft"""
        return self._running and self._process is not None and self._process.poll() is None
    
    def start(self, args: List[str]) -> bool:
        """
        Startet den Miner mit den gegebenen Argumenten.
        
        Args:
            args: Kommandozeilen-Argumente
            
        Returns:
            True wenn erfolgreich gestartet
        """
        if self.is_running():
            logger.warning("Miner läuft bereits")
            return False
        
        if not self.executable_path.exists():
            logger.error(f"Miner nicht gefunden: {self.executable_path}")
            return False
        
        try:
            cmd = [str(self.executable_path)] + args
            logger.info(f"Starte Miner: {' '.join(cmd)}")
            
            # Miner-Fenster sichtbar starten (normal sichtbar, nicht minimiert)
            # So kann man Fehler sehen wenn etwas nicht funktioniert
            if hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
                # Windows: Neues Konsolenfenster erstellen - SICHTBAR!
                self._process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                    # KEINE stdout/stderr PIPE - sonst ist Fenster leer!
                )
            else:
                # Linux/Mac: Normal starten
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )
            
            self._running = True
            
            # Output-Thread nur auf Linux/Mac (Windows zeigt Fenster)
            if not hasattr(subprocess, 'CREATE_NEW_CONSOLE'):
                self._output_thread = threading.Thread(
                    target=self._read_output,
                    daemon=True,
                    name=f"MinerOutput-{self.miner_type.value}"
                )
                self._output_thread.start()
            
            logger.info(f"Miner gestartet: PID {self._process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Starten des Miners: {e}")
            if self.on_error:
                self.on_error(str(e))
            return False
    
    def stop(self, timeout: float = 10.0) -> bool:
        """
        Stoppt den Miner.
        
        Args:
            timeout: Timeout in Sekunden
            
        Returns:
            True wenn sauber beendet
        """
        if not self._process:
            return True
        
        self._running = False
        
        try:
            pid = self._process.pid
            
            # Auf Windows: taskkill mit Prozessbaum (/T) und Force (/F)
            if os.name == 'nt':
                try:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(pid)],
                        capture_output=True,
                        timeout=10
                    )
                    logger.info(f"Miner-Prozess {pid} mit taskkill beendet")
                except Exception as e:
                    logger.warning(f"taskkill fehlgeschlagen: {e}, versuche terminate()")
                    self._process.terminate()
            else:
                # Auf Linux: Sanft beenden
                self._process.terminate()
            
            try:
                self._process.wait(timeout=timeout)
                logger.info("Miner sauber beendet")
            except subprocess.TimeoutExpired:
                # Erzwingen
                self._process.kill()
                self._process.wait()
                logger.warning("Miner musste gekillt werden")
            
            self._process = None
            
            if self.on_stopped:
                self.on_stopped()
            
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Stoppen: {e}")
            return False
    
    def _read_output(self):
        """Liest die Miner-Ausgabe in einem Thread"""
        if not self._process or not self._process.stdout:
            return
        
        try:
            for line in self._process.stdout:
                if not self._running:
                    break
                
                try:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Output-Callback (thread-safe via Buffer in mining_gui.py)
                    if self.on_output:
                        try:
                            self.on_output(line)
                        except Exception:
                            pass  # GUI könnte geschlossen sein
                    
                    # Hashrate aus Log extrahieren
                    self._extract_hashrate(line)
                except Exception:
                    pass  # Einzelne Zeile überspringen bei Fehler
                
        except Exception as e:
            if self._running:
                logger.error(f"Output-Fehler: {e}")
        
        # Prozess beendet
        if self._running:
            self._running = False
            logger.warning("Miner unerwartet beendet")
            if self.on_stopped:
                try:
                    self.on_stopped()
                except Exception:
                    pass
    
    def _extract_hashrate(self, line: str):
        """Extrahiert Hashrate aus einer Log-Zeile"""
        pattern = self._hashrate_patterns.get(self.miner_type)
        if not pattern:
            return
        
        matches = pattern.findall(line)
        if matches and self.on_hashrate:
            hashrates = {}
            for match in matches:
                gpu_index = int(match[0])
                hashrate = float(match[1])
                unit = match[2]
                
                # Normalisieren auf MH/s
                if 'K' in unit:
                    hashrate /= 1000
                elif 'G' in unit:
                    hashrate *= 1000
                elif 'T' in unit:
                    hashrate *= 1000000
                
                hashrates[gpu_index] = hashrate
            
            self.on_hashrate(hashrates)


class MinerManager:
    """
    Verwaltet mehrere Miner und deren APIs.
    
    Verwendung:
        manager = MinerManager(miners_dir="/path/to/miners")
        
        # Miner starten
        manager.start_miner("trex", "kawpow", "pool:port", "wallet")
        
        # Stats holen
        stats = manager.get_current_stats()
        
        # Stoppen
        manager.stop_current()
    """
    
    def __init__(self, miners_dir: str = "miners"):
        """
        Initialisiert den Miner Manager.
        
        Args:
            miners_dir: Verzeichnis mit den Miner-Ordnern
        """
        self.miners_dir = Path(miners_dir)
        
        self._current_miner: Optional[MinerProcess] = None
        self._current_api: Optional[MinerAPIClient] = None
        self._current_type: Optional[MinerType] = None
        
        # Miner Executables
        self._miner_executables = {
            MinerType.TREX: "t-rex.exe",
            MinerType.NBMINER: "nbminer.exe",
            MinerType.GMINER: "miner.exe",
            MinerType.LOLMINER: "lolMiner.exe",
            MinerType.TEAMREDMINER: "teamredminer.exe",
            MinerType.PHOENIXMINER: "PhoenixMiner.exe",
        }
        
        # Callbacks
        self.on_stats_update: Optional[Callable[[MinerStats], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
    
    def get_available_miners(self) -> List[MinerType]:
        """Gibt eine Liste der verfügbaren Miner zurück"""
        available = []
        
        for miner_type, exe_name in self._miner_executables.items():
            miner_dir = self.miners_dir / miner_type.value
            exe_path = miner_dir / exe_name
            
            if exe_path.exists():
                available.append(miner_type)
        
        return available
    
    def get_miner_path(self, miner_type: MinerType) -> Optional[Path]:
        """Gibt den Pfad zur Miner-Executable zurück"""
        exe_name = self._miner_executables.get(miner_type)
        if not exe_name:
            return None
        
        miner_dir = self.miners_dir / miner_type.value
        exe_path = miner_dir / exe_name
        
        return exe_path if exe_path.exists() else None
    
    def build_miner_args(
        self,
        miner_type: MinerType,
        algorithm: str,
        pool_url: str,
        wallet: str,
        worker: str = "",
        password: str = "x",
        extra_args: List[str] = None
    ) -> List[str]:
        """Baut die Kommandozeilen-Argumente für einen Miner"""
        
        # WICHTIG: Memo von Wallet trennen (falls vorhanden)
        # Wallets von Börsen haben oft Format: "adresse memo" oder "adresse payment_id"
        if wallet and ' ' in wallet:
            wallet = wallet.split(' ')[0]
            logger.debug(f"Wallet-Memo entfernt, nutze nur Adresse: {wallet[:30]}...")
        
        args = []
        
        if miner_type == MinerType.TREX:
            args = [
                "-a", algorithm,
                "-o", pool_url,
                "-u", f"{wallet}.{worker}" if worker else wallet,
                "-p", password,
                "--api-bind-http", "127.0.0.1:4067",
            ]
        
        elif miner_type == MinerType.NBMINER:
            args = [
                "-a", algorithm,
                "-o", pool_url,
                "-u", f"{wallet}.{worker}" if worker else wallet,
                "--api", "127.0.0.1:22333",
            ]
        
        elif miner_type == MinerType.GMINER:
            # GMiner verwendet spezifische Algo-Namen
            gminer_algo_map = {
                'cuckatoo32': 'cuckoo32',
                'cuckatoo31': 'cuckoo31',
                'cuckatoo29': 'cuckoo29',
                'beamhash3': 'beamhash',
                'beamhashiii': 'beamhash',
                'beam': 'beamhash',
                'equihash125': 'equihash125_4',
                'equihash144': 'equihash144_5',
                'equihash192': 'equihash192_7',
                'autolykos2': 'autolykos2',
                'etchash': 'etchash',
                'ethash': 'ethash',
                'kheavyhash': 'kheavyhash',
                'kawpow': 'kawpow',
                'octopus': 'octopus',
                'blake3': 'alephium',
            }
            algo_name = gminer_algo_map.get(algorithm.lower(), algorithm.lower())
            
            args = [
                "--algo", algo_name,
                "--server", pool_url.replace("stratum+tcp://", "").replace("stratum+ssl://", ""),
                "--user", f"{wallet}.{worker}" if worker else wallet,
                "--pass", password,
                "--api", "10555",
            ]
        
        elif miner_type == MinerType.LOLMINER:
            # lolMiner verwendet andere Algo-Namen!
            lolminer_algo_map = {
                'cuckatoo32': 'C32',
                'cuckatoo31': 'C31',
                'cuckatoo29': 'C29AE',
                'beamhash3': 'BEAM-III',
                'beamhashiii': 'BEAM-III',
                'beam': 'BEAM-III',
                'equihash125': 'FLUX',
                'equihash144': 'EQUI144_5',
                'equihash192': 'EQUI192_7',
                'autolykos2': 'AUTOLYKOS2',
                'etchash': 'ETCHASH',
                'ethash': 'ETHASH',
                'kheavyhash': 'KASPA',
                'karlsenhash': 'KARLSEN',
                'pyrinhash': 'PYRIN',
                'nexapow': 'NEXA',
            }
            algo_name = lolminer_algo_map.get(algorithm.lower(), algorithm.upper())
            
            args = [
                "--algo", algo_name,
                "--pool", pool_url,
                "--user", f"{wallet}.{worker}" if worker else wallet,
                "--apiport", "8080",
            ]
        
        elif miner_type == MinerType.PHOENIXMINER:
            args = [
                "-pool", pool_url,
                "-wal", wallet,
                "-worker", worker or "rig",
                "-pass", password,
                "-cdmport", "3333",
            ]
        
        elif miner_type == MinerType.XMRIG:
            # XMRig für CPU Mining (RandomX - Monero, Zephyr)
            # Pool-URL Format: stratum+tcp://pool:port → pool:port
            clean_url = pool_url.replace("stratum+tcp://", "").replace("stratum+ssl://", "")
            args = [
                "-o", clean_url,
                "-u", f"{wallet}.{worker}" if worker else wallet,
                "-p", password,
                "--http-host", "127.0.0.1",
                "--http-port", "8080",
                "-t", "0",  # Auto-detect Threads
            ]
        
        if extra_args:
            args.extend(extra_args)
        
        return args
    
    def start_miner(
        self,
        miner_type: MinerType,
        algorithm: str,
        pool_url: str,
        wallet: str,
        worker: str = "",
        extra_args: List[str] = None
    ) -> bool:
        """
        Startet einen Miner.
        
        Args:
            miner_type: Miner-Typ
            algorithm: Algorithmus
            pool_url: Pool URL
            wallet: Wallet-Adresse
            worker: Worker-Name
            extra_args: Zusätzliche Argumente
            
        Returns:
            True wenn erfolgreich
        """
        # Vorherigen Miner stoppen
        self.stop_current()
        
        # Pfad prüfen
        exe_path = self.get_miner_path(miner_type)
        if not exe_path:
            logger.error(f"Miner nicht gefunden: {miner_type.value}")
            return False
        
        # Argumente bauen
        args = self.build_miner_args(
            miner_type, algorithm, pool_url, wallet, worker, extra_args=extra_args
        )
        
        # Miner starten
        self._current_miner = MinerProcess(miner_type, str(exe_path))
        self._current_miner.on_output = self._handle_log
        self._current_type = miner_type
        
        if self._current_miner.start(args):
            # API Client erstellen
            config = MINER_API_CONFIG.get(miner_type, {})
            self._current_api = MinerAPIClient(miner_type, port=config.get('default_port'))
            return True
        
        return False
    
    def stop_current(self) -> bool:
        """Stoppt den aktuellen Miner"""
        if self._current_miner:
            success = self._current_miner.stop()
            self._current_miner = None
            self._current_api = None
            self._current_type = None
            return success
        return True
    
    def get_current_stats(self) -> Optional[MinerStats]:
        """Holt die aktuellen Stats vom laufenden Miner"""
        if self._current_api:
            stats = self._current_api.get_stats()
            if stats and self.on_stats_update:
                self.on_stats_update(stats)
            return stats
        return None
    
    def is_mining(self) -> bool:
        """Prüft ob gerade geminert wird"""
        return self._current_miner is not None and self._current_miner.is_running()
    
    def get_current_miner_type(self) -> Optional[MinerType]:
        """Gibt den aktuellen Miner-Typ zurück"""
        return self._current_type
    
    def _handle_log(self, line: str):
        """Verarbeitet Log-Zeilen"""
        if self.on_log:
            self.on_log(line)
    
    def kill_all_miners(self):
        """Beendet alle bekannten Miner-Prozesse (Windows)"""
        if os.name != 'nt':
            return
        
        # Liste aller Miner-EXE-Namen
        miner_exes = [
            't-rex.exe', 'nbminer.exe', 'miner.exe', 'lolMiner.exe',
            'rigel.exe', 'bzminer.exe', 'teamredminer.exe', 'SRBMiner-MULTI.exe',
            'PhoenixMiner.exe', 'gminer.exe', 'xmrig.exe'  # CPU Miner
        ]
        
        killed_any = False
        
        # Erster Durchgang: Alle killen
        for exe in miner_exes:
            try:
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', exe],
                    capture_output=True,
                    timeout=5,
                    encoding='utf-8',
                    errors='ignore'
                )
                if result.returncode == 0:
                    logger.info(f"Beendet: {exe}")
                    killed_any = True
            except Exception:
                pass
        
        # Kurz warten wenn etwas gekillt wurde
        if killed_any:
            time.sleep(1.0)


# Standalone Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Miner API Client Test")
    print("=" * 60)
    
    # T-Rex API testen
    print("\n📊 Teste T-Rex API (Port 4067)...")
    client = MinerAPIClient(MinerType.TREX)
    
    if client.is_available():
        stats = client.get_stats()
        if stats:
            print(f"   Miner: {stats.miner_type} {stats.version}")
            print(f"   Algorithm: {stats.algorithm}")
            print(f"   Total Hashrate: {stats.total_hashrate:.2f} {stats.hashrate_unit}")
            print(f"   Accepted: {stats.total_accepted} | Rejected: {stats.total_rejected}")
            print(f"   Total Power: {stats.total_power:.0f}W")
            print(f"\n   GPUs:")
            for gpu in stats.gpus:
                print(f"      [{gpu.index}] {gpu.hashrate:.2f} MH/s | {gpu.temperature}°C | {gpu.power:.0f}W")
    else:
        print("   ❌ T-Rex nicht erreichbar (läuft er?)")
    
    # Manager Test
    print("\n📊 Miner Manager Test...")
    manager = MinerManager(miners_dir="C:/GPUMiner/miners")
    
    available = manager.get_available_miners()
    print(f"   Verfügbare Miner: {[m.value for m in available]}")
    
    print("\n✅ Test beendet")
