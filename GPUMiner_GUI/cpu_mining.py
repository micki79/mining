#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CPU Mining Modul für GPU Mining Profit Switcher
XMRig Integration mit automatischem Download und CPU-Monitoring

Features:
- XMRig automatisch downloaden/installieren
- RandomX Mining (Monero, etc.)
- CPU-Überwachung (Temp, Usage, Hashrate)
- Multi-Coin Support (XMR, ZEPH, RTM, etc.)
- Pool-Konfiguration

Author: GPU Mining Profit Switcher Team
Version: 1.0.0
"""

import os
import sys
import json
import time
import logging
import subprocess
import threading
import zipfile
import tarfile
import platform
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# HTTP Requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# psutil für CPU Monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# KONFIGURATION
# ============================================================================

class CPUAlgorithm(Enum):
    """Unterstützte CPU-Mining Algorithmen"""
    RANDOMX = "rx/0"  # Monero
    RANDOMX_WOW = "rx/wow"  # Wownero
    RANDOMX_ARQ = "rx/arq"  # ArQmA
    RANDOMX_GRAFT = "rx/graft"  # Graft
    RANDOMX_SFX = "rx/sfx"  # Safex
    RANDOMX_KEVA = "rx/keva"  # Kevacoin
    GHOSTRIDER = "gr"  # Raptoreum
    ARGON2 = "argon2/chukwav2"  # Turtlecoin
    ASTROBWT = "astrobwt"  # Dero


@dataclass
class CPUInfo:
    """CPU-Informationen"""
    name: str = "Unknown"
    cores: int = 0
    threads: int = 0
    frequency: float = 0.0
    temperature: float = 0.0
    usage: float = 0.0
    architecture: str = ""


@dataclass
class CPUMiningConfig:
    """Konfiguration für CPU Mining"""
    coin: str = "XMR"
    algorithm: str = "rx/0"
    pool_url: str = "pool.supportxmr.com:3333"
    wallet: str = ""
    worker_name: str = "Rig_D"
    password: str = "x"
    threads: int = 0  # 0 = Auto
    priority: int = 2  # 1-5 (1=idle, 5=realtime)
    huge_pages: bool = True
    enabled: bool = False


@dataclass
class CPUMiningStats:
    """CPU Mining Statistiken"""
    hashrate: float = 0.0
    hashrate_unit: str = "H/s"
    accepted: int = 0
    rejected: int = 0
    difficulty: float = 0.0
    pool: str = ""
    uptime: int = 0
    algorithm: str = ""
    threads_active: int = 0


# CPU Mining Coins und ihre Einstellungen
CPU_COINS = {
    "XMR": {
        "name": "Monero",
        "algorithm": "rx/0",
        "pools": [
            {"url": "pool.supportxmr.com:3333", "name": "SupportXMR"},
            {"url": "xmr.2miners.com:2222", "name": "2Miners"},
            {"url": "xmr-eu1.nanopool.org:14433", "name": "Nanopool"},
            {"url": "pool.hashvault.pro:3333", "name": "HashVault"},
        ],
        "hashrate_unit": "H/s"
    },
    "ZEPH": {
        "name": "Zephyr",
        "algorithm": "rx/0",
        "pools": [
            {"url": "zephyr.herominers.com:1123", "name": "HeroMiners"},
            {"url": "zeph.2miners.com:2222", "name": "2Miners"},
        ],
        "hashrate_unit": "H/s"
    },
    "RTM": {
        "name": "Raptoreum",
        "algorithm": "gr",
        "pools": [
            {"url": "stratum+tcp://rtm.suprnova.cc:6273", "name": "Suprnova"},
            {"url": "stratum+tcp://pool.raptoreum.com:3333", "name": "Official"},
        ],
        "hashrate_unit": "H/s"
    },
    "WOW": {
        "name": "Wownero",
        "algorithm": "rx/wow",
        "pools": [
            {"url": "pool.wownero.com:3333", "name": "Official"},
        ],
        "hashrate_unit": "H/s"
    },
    "DERO": {
        "name": "Dero",
        "algorithm": "astrobwt",
        "pools": [
            {"url": "dero.herominers.com:1111", "name": "HeroMiners"},
        ],
        "hashrate_unit": "H/s"
    }
}


# ============================================================================
# CPU MONITOR
# ============================================================================

class CPUMonitor:
    """Überwacht die CPU"""
    
    def __init__(self):
        self.info = CPUInfo()
        self._update_static_info()
    
    def _update_static_info(self):
        """Aktualisiert statische CPU-Infos"""
        if not PSUTIL_AVAILABLE:
            return
        
        try:
            self.info.name = platform.processor() or "Unknown CPU"
            self.info.cores = psutil.cpu_count(logical=False) or 1
            self.info.threads = psutil.cpu_count(logical=True) or 1
            self.info.architecture = platform.machine()
            
            # Frequenz
            freq = psutil.cpu_freq()
            if freq:
                self.info.frequency = freq.current
        except Exception as e:
            logger.warning(f"CPU Info Fehler: {e}")
    
    def get_info(self) -> CPUInfo:
        """Gibt aktuelle CPU-Infos zurück"""
        if PSUTIL_AVAILABLE:
            try:
                # Usage
                self.info.usage = psutil.cpu_percent(interval=0.1)
                
                # Temperatur (wenn verfügbar)
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for entry in entries:
                                if "cpu" in name.lower() or "core" in entry.label.lower():
                                    self.info.temperature = entry.current
                                    break
                except:
                    pass
                
            except Exception as e:
                logger.warning(f"CPU Monitor Fehler: {e}")
        
        return self.info
    
    def get_recommended_threads(self) -> int:
        """Gibt empfohlene Thread-Anzahl für Mining zurück"""
        # Lasse 1-2 Threads für System übrig
        threads = self.info.threads
        if threads <= 4:
            return max(1, threads - 1)
        elif threads <= 8:
            return threads - 2
        else:
            return threads - 4


# ============================================================================
# XMRIG MANAGER
# ============================================================================

class XMRigManager:
    """Verwaltet XMRig Installation und Mining"""
    
    XMRIG_VERSION = "6.21.1"
    XMRIG_DOWNLOAD_URLS = {
        "windows": f"https://github.com/xmrig/xmrig/releases/download/v{XMRIG_VERSION}/xmrig-{XMRIG_VERSION}-msvc-win64.zip",
        "linux": f"https://github.com/xmrig/xmrig/releases/download/v{XMRIG_VERSION}/xmrig-{XMRIG_VERSION}-linux-x64.tar.gz"
    }
    
    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.miners_dir = self.base_dir / "miners" / "xmrig"
        self.config_file = self.base_dir / "xmrig_config.json"
        
        # Status
        self.process: Optional[subprocess.Popen] = None
        self.is_mining = False
        self.stats = CPUMiningStats()
        self.config = CPUMiningConfig()
        
        # CPU Monitor
        self.cpu_monitor = CPUMonitor()
        
        # Stats Thread
        self.stats_thread: Optional[threading.Thread] = None
        self.stats_running = False
        
        # API Port
        self.api_port = 8081
        
        # Callbacks
        self.on_stats_update = None
        self.on_log_line = None
        
        # Load Config
        self._load_config()
    
    def _load_config(self):
        """Lädt die Konfiguration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        if hasattr(self.config, key):
                            setattr(self.config, key, value)
            except Exception as e:
                logger.warning(f"Config laden fehlgeschlagen: {e}")
    
    def save_config(self):
        """Speichert die Konfiguration"""
        with open(self.config_file, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)
    
    # ========================================================================
    # INSTALLATION
    # ========================================================================
    
    def is_installed(self) -> bool:
        """Prüft ob XMRig installiert ist"""
        xmrig_exe = self._get_xmrig_path()
        return xmrig_exe.exists()
    
    def _get_xmrig_path(self) -> Path:
        """Gibt den Pfad zur XMRig Executable zurück"""
        if sys.platform == "win32":
            return self.miners_dir / "xmrig.exe"
        else:
            return self.miners_dir / "xmrig"
    
    def download_xmrig(self, progress_callback=None) -> bool:
        """Lädt XMRig herunter und installiert es"""
        if not REQUESTS_AVAILABLE:
            logger.error("requests nicht installiert!")
            return False
        
        # Betriebssystem erkennen
        if sys.platform == "win32":
            url = self.XMRIG_DOWNLOAD_URLS["windows"]
            is_zip = True
        else:
            url = self.XMRIG_DOWNLOAD_URLS["linux"]
            is_zip = False
        
        logger.info(f"Downloade XMRig von {url}")
        
        try:
            # Verzeichnis erstellen
            self.miners_dir.mkdir(parents=True, exist_ok=True)
            
            # Download
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            archive_path = self.miners_dir / ("xmrig.zip" if is_zip else "xmrig.tar.gz")
            
            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress = int(downloaded / total_size * 100)
                        progress_callback(progress)
            
            logger.info("Download abgeschlossen, entpacke...")
            
            # Entpacken
            if is_zip:
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.miners_dir)
            else:
                with tarfile.open(archive_path, 'r:gz') as tar_ref:
                    tar_ref.extractall(self.miners_dir)
            
            # Finde und verschiebe xmrig
            for item in self.miners_dir.rglob("xmrig*"):
                if item.is_file() and ("xmrig.exe" in item.name or item.name == "xmrig"):
                    target = self._get_xmrig_path()
                    if item != target:
                        shutil.copy2(item, target)
                    # Linux: Ausführbar machen
                    if sys.platform != "win32":
                        os.chmod(target, 0o755)
                    break
            
            # Aufräumen
            archive_path.unlink()
            
            logger.info("XMRig erfolgreich installiert!")
            return True
            
        except Exception as e:
            logger.error(f"XMRig Installation fehlgeschlagen: {e}")
            return False
    
    # ========================================================================
    # MINING
    # ========================================================================
    
    def start_mining(self) -> bool:
        """Startet das CPU Mining"""
        if self.is_mining:
            logger.warning("Mining läuft bereits!")
            return False
        
        if not self.is_installed():
            logger.error("XMRig nicht installiert!")
            return False
        
        if not self.config.wallet:
            logger.error("Keine Wallet-Adresse konfiguriert!")
            return False
        
        # XMRig Config erstellen
        xmrig_config = self._create_xmrig_config()
        config_path = self.miners_dir / "config.json"
        
        with open(config_path, 'w') as f:
            json.dump(xmrig_config, f, indent=2)
        
        # XMRig starten
        xmrig_exe = self._get_xmrig_path()
        cmd = [str(xmrig_exe), "-c", str(config_path)]
        
        try:
            # Starte XMRig
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(self.miners_dir),
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            
            self.is_mining = True
            
            # Starte Log Reader Thread
            self._start_log_reader()
            
            # Starte Stats Thread
            self._start_stats_polling()
            
            logger.info(f"XMRig gestartet (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            logger.error(f"XMRig Start fehlgeschlagen: {e}")
            return False
    
    def stop_mining(self):
        """Stoppt das CPU Mining"""
        self.stats_running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                try:
                    self.process.kill()
                except:
                    pass
            self.process = None
        
        self.is_mining = False
        self.stats = CPUMiningStats()
        logger.info("XMRig gestoppt")
    
    def _create_xmrig_config(self) -> Dict:
        """Erstellt die XMRig Konfiguration"""
        threads = self.config.threads
        if threads <= 0:
            threads = self.cpu_monitor.get_recommended_threads()
        
        return {
            "autosave": True,
            "cpu": {
                "enabled": True,
                "huge-pages": self.config.huge_pages,
                "hw-aes": True,
                "priority": self.config.priority,
                "memory-pool": False,
                "yield": True,
                "max-threads-hint": 100,
                "asm": True,
                "argon2-impl": None,
                "cn/0": False,
                "cn-lite/0": False
            },
            "opencl": {"enabled": False},
            "cuda": {"enabled": False},
            "donate-level": 1,
            "donate-over-proxy": 1,
            "log-file": str(self.miners_dir / "xmrig.log"),
            "pools": [
                {
                    "url": self.config.pool_url,
                    "user": self.config.wallet,
                    "pass": f"{self.config.worker_name}",
                    "rig-id": self.config.worker_name,
                    "keepalive": True,
                    "tls": False,
                    "algo": self.config.algorithm
                }
            ],
            "print-time": 30,
            "health-print-time": 60,
            "retries": 5,
            "retry-pause": 5,
            "syslog": False,
            "user-agent": None,
            "verbose": 0,
            "watch": True,
            "http": {
                "enabled": True,
                "host": "127.0.0.1",
                "port": self.api_port,
                "access-token": None,
                "restricted": True
            }
        }
    
    def _start_log_reader(self):
        """Startet den Log Reader Thread"""
        def read_logs():
            while self.is_mining and self.process:
                try:
                    line = self.process.stdout.readline()
                    if line:
                        line = line.decode('utf-8', errors='ignore').strip()
                        if self.on_log_line:
                            self.on_log_line(line)
                        self._parse_log_line(line)
                except:
                    break
        
        thread = threading.Thread(target=read_logs, daemon=True)
        thread.start()
    
    def _parse_log_line(self, line: str):
        """Parst eine Log-Zeile für Stats"""
        try:
            # Hashrate aus Log
            if "speed" in line.lower() and "h/s" in line.lower():
                # Format: "speed 10s/60s/15m 1234.5 1234.5 1234.5 H/s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if "h/s" in part.lower():
                        if i > 0:
                            try:
                                self.stats.hashrate = float(parts[i-1])
                            except:
                                pass
                        break
            
            # Accepted/Rejected
            if "accepted" in line.lower():
                try:
                    # Format: "accepted (123/0)"
                    import re
                    match = re.search(r'\((\d+)/(\d+)\)', line)
                    if match:
                        self.stats.accepted = int(match.group(1))
                        self.stats.rejected = int(match.group(2))
                except:
                    pass
                    
        except Exception as e:
            pass
    
    def _start_stats_polling(self):
        """Startet das Stats Polling vom HTTP API"""
        self.stats_running = True
        
        def poll_stats():
            while self.stats_running and self.is_mining:
                try:
                    # XMRig HTTP API
                    response = requests.get(
                        f"http://127.0.0.1:{self.api_port}/2/summary",
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Hashrate
                        hashrate_data = data.get("hashrate", {})
                        total = hashrate_data.get("total", [0, 0, 0])
                        self.stats.hashrate = total[0] if total else 0
                        
                        # Shares
                        results = data.get("results", {})
                        self.stats.accepted = results.get("shares_good", 0)
                        self.stats.rejected = results.get("shares_total", 0) - self.stats.accepted
                        self.stats.difficulty = results.get("diff_current", 0)
                        
                        # Connection
                        conn = data.get("connection", {})
                        self.stats.pool = conn.get("pool", "")
                        self.stats.uptime = conn.get("uptime", 0)
                        self.stats.algorithm = conn.get("algo", "")
                        
                        # CPU
                        cpu = data.get("cpu", {})
                        self.stats.threads_active = cpu.get("threads", 0)
                        
                        # Callback
                        if self.on_stats_update:
                            self.on_stats_update(self.stats)
                            
                except Exception as e:
                    pass
                
                time.sleep(2)
        
        self.stats_thread = threading.Thread(target=poll_stats, daemon=True)
        self.stats_thread.start()
    
    def get_stats(self) -> CPUMiningStats:
        """Gibt aktuelle Mining-Stats zurück"""
        return self.stats
    
    def get_cpu_info(self) -> CPUInfo:
        """Gibt CPU-Informationen zurück"""
        return self.cpu_monitor.get_info()
    
    # ========================================================================
    # KONFIGURATION
    # ========================================================================
    
    def set_coin(self, coin: str):
        """Setzt den zu minenden Coin"""
        if coin in CPU_COINS:
            coin_info = CPU_COINS[coin]
            self.config.coin = coin
            self.config.algorithm = coin_info["algorithm"]
            if coin_info["pools"]:
                self.config.pool_url = coin_info["pools"][0]["url"]
            self.save_config()
    
    def set_wallet(self, wallet: str):
        """Setzt die Wallet-Adresse"""
        self.config.wallet = wallet
        self.save_config()
    
    def set_pool(self, pool_url: str):
        """Setzt den Pool"""
        self.config.pool_url = pool_url
        self.save_config()
    
    def set_threads(self, threads: int):
        """Setzt die Thread-Anzahl"""
        self.config.threads = threads
        self.save_config()
    
    def get_available_coins(self) -> Dict:
        """Gibt verfügbare Coins zurück"""
        return CPU_COINS


# ============================================================================
# CPU MINING WIDGET
# ============================================================================

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QGroupBox, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QLineEdit, QComboBox,
        QProgressBar, QSpinBox, QCheckBox, QTextEdit,
        QHeaderView, QMessageBox, QSizePolicy
    )
    from PySide6.QtCore import Qt, QTimer, Signal
    from PySide6.QtGui import QFont, QColor
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

if PYSIDE_AVAILABLE:
    # Themes Import
    try:
        from themes import COLORS
    except ImportError:
        COLORS = {
            "primary": "#1a1a2e",
            "secondary": "#16213e",
            "accent": "#0f3460",
            "highlight": "#e94560",
            "text": "#ffffff",
            "text_secondary": "#a0a0a0",
            "success": "#00ff88",
            "warning": "#ffaa00",
            "error": "#ff4444"
        }
    
    class CPUMiningWidget(QWidget):
        """Widget für CPU Mining Tab"""
        
        stats_updated = Signal(object)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            # XMRig Manager
            self.xmrig = XMRigManager()
            self.xmrig.on_stats_update = self._on_stats_update
            self.xmrig.on_log_line = self._on_log_line
            
            # UI Setup
            self._setup_ui()
            
            # Update Timer
            self.update_timer = QTimer()
            self.update_timer.timeout.connect(self._update_display)
            self.update_timer.start(1000)
            
            # Initial Update
            self._update_display()
        
        def _setup_ui(self):
            """Erstellt die UI"""
            layout = QVBoxLayout(self)
            layout.setSpacing(10)
            
            # Header mit Status
            header = self._create_header()
            layout.addWidget(header)
            
            # Haupt-Content
            content_layout = QHBoxLayout()
            
            # Links: Stats und CPU Info
            left_panel = QVBoxLayout()
            left_panel.addWidget(self._create_stats_panel())
            left_panel.addWidget(self._create_cpu_info_panel())
            content_layout.addLayout(left_panel)
            
            # Rechts: Konfiguration und Logs
            right_panel = QVBoxLayout()
            right_panel.addWidget(self._create_config_panel())
            right_panel.addWidget(self._create_log_panel())
            content_layout.addLayout(right_panel)
            
            layout.addLayout(content_layout)
        
        def _create_header(self) -> QWidget:
            """Erstellt den Header"""
            header = QGroupBox("💻 CPU Mining (XMRig)")
            layout = QHBoxLayout(header)
            
            # Status
            self.status_label = QLabel("⏸️ Gestoppt")
            self.status_label.setStyleSheet(f"color: {COLORS.get('warning', '#ffaa00')}; font-weight: bold; font-size: 14px;")
            layout.addWidget(self.status_label)
            
            # Hashrate
            self.hashrate_label = QLabel("0 H/s")
            self.hashrate_label.setStyleSheet(f"color: {COLORS.get('success', '#00ff88')}; font-weight: bold; font-size: 14px;")
            layout.addWidget(self.hashrate_label)
            
            # Shares
            self.shares_label = QLabel("A: 0 | R: 0")
            layout.addWidget(self.shares_label)
            
            layout.addStretch()
            
            # Install Button (wenn nicht installiert)
            self.install_btn = QPushButton("📥 XMRig installieren")
            self.install_btn.clicked.connect(self._install_xmrig)
            self.install_btn.setVisible(not self.xmrig.is_installed())
            layout.addWidget(self.install_btn)
            
            # Start/Stop Button
            self.toggle_btn = QPushButton("▶️ Starten")
            self.toggle_btn.clicked.connect(self._toggle_mining)
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('success', '#00ff88')};
                    color: black;
                    font-weight: bold;
                    padding: 10px 20px;
                    border-radius: 5px;
                }}
            """)
            self.toggle_btn.setEnabled(self.xmrig.is_installed())
            layout.addWidget(self.toggle_btn)
            
            return header
        
        def _create_stats_panel(self) -> QWidget:
            """Erstellt das Stats Panel"""
            panel = QGroupBox("📊 Mining Stats")
            layout = QGridLayout(panel)
            
            # Stats Labels
            stats = [
                ("Hashrate:", "hashrate_stat", "0 H/s"),
                ("Akzeptiert:", "accepted_stat", "0"),
                ("Abgelehnt:", "rejected_stat", "0"),
                ("Difficulty:", "diff_stat", "0"),
                ("Pool:", "pool_stat", "-"),
                ("Uptime:", "uptime_stat", "0s"),
                ("Threads:", "threads_stat", "0"),
                ("Algorithmus:", "algo_stat", "-"),
            ]
            
            self.stat_labels = {}
            for i, (label, key, default) in enumerate(stats):
                row = i // 2
                col = (i % 2) * 2
                
                layout.addWidget(QLabel(label), row, col)
                value_label = QLabel(default)
                value_label.setStyleSheet(f"color: {COLORS.get('text', '#ffffff')}; font-weight: bold;")
                self.stat_labels[key] = value_label
                layout.addWidget(value_label, row, col + 1)
            
            return panel
        
        def _create_cpu_info_panel(self) -> QWidget:
            """Erstellt das CPU Info Panel"""
            panel = QGroupBox("🖥️ CPU Information")
            layout = QGridLayout(panel)
            
            cpu_info = self.xmrig.get_cpu_info()
            
            # CPU Info Labels
            infos = [
                ("Name:", cpu_info.name),
                ("Kerne:", str(cpu_info.cores)),
                ("Threads:", str(cpu_info.threads)),
                ("Architektur:", cpu_info.architecture),
            ]
            
            for i, (label, value) in enumerate(infos):
                layout.addWidget(QLabel(label), i, 0)
                layout.addWidget(QLabel(value), i, 1)
            
            # Live-Werte
            layout.addWidget(QLabel("Auslastung:"), len(infos), 0)
            self.cpu_usage_label = QLabel("0%")
            layout.addWidget(self.cpu_usage_label, len(infos), 1)
            
            self.cpu_usage_bar = QProgressBar()
            self.cpu_usage_bar.setMaximum(100)
            layout.addWidget(self.cpu_usage_bar, len(infos) + 1, 0, 1, 2)
            
            return panel
        
        def _create_config_panel(self) -> QWidget:
            """Erstellt das Config Panel"""
            panel = QGroupBox("⚙️ Konfiguration")
            layout = QGridLayout(panel)
            
            # Coin Auswahl
            layout.addWidget(QLabel("Coin:"), 0, 0)
            self.coin_combo = QComboBox()
            self.coin_combo.addItems(list(CPU_COINS.keys()))
            self.coin_combo.setCurrentText(self.xmrig.config.coin)
            self.coin_combo.currentTextChanged.connect(self._on_coin_changed)
            layout.addWidget(self.coin_combo, 0, 1)
            
            # Pool
            layout.addWidget(QLabel("Pool:"), 1, 0)
            self.pool_combo = QComboBox()
            self._update_pools()
            layout.addWidget(self.pool_combo, 1, 1)
            
            # Wallet
            layout.addWidget(QLabel("Wallet:"), 2, 0)
            self.wallet_input = QLineEdit()
            self.wallet_input.setText(self.xmrig.config.wallet)
            self.wallet_input.setPlaceholderText("Deine XMR Wallet-Adresse...")
            layout.addWidget(self.wallet_input, 2, 1)
            
            # Worker Name
            layout.addWidget(QLabel("Worker:"), 3, 0)
            self.worker_input = QLineEdit()
            self.worker_input.setText(self.xmrig.config.worker_name)
            layout.addWidget(self.worker_input, 3, 1)
            
            # Threads
            layout.addWidget(QLabel("Threads:"), 4, 0)
            thread_layout = QHBoxLayout()
            self.threads_spin = QSpinBox()
            self.threads_spin.setRange(0, self.xmrig.get_cpu_info().threads)
            self.threads_spin.setValue(self.xmrig.config.threads)
            self.threads_spin.setSpecialValueText("Auto")
            thread_layout.addWidget(self.threads_spin)
            thread_layout.addWidget(QLabel("(0 = Auto)"))
            layout.addLayout(thread_layout, 4, 1)
            
            # Huge Pages
            layout.addWidget(QLabel("Huge Pages:"), 5, 0)
            self.huge_pages_check = QCheckBox("Aktiviert (bessere Performance)")
            self.huge_pages_check.setChecked(self.xmrig.config.huge_pages)
            layout.addWidget(self.huge_pages_check, 5, 1)
            
            # Save Button
            save_btn = QPushButton("💾 Speichern")
            save_btn.clicked.connect(self._save_config)
            layout.addWidget(save_btn, 6, 0, 1, 2)
            
            return panel
        
        def _create_log_panel(self) -> QWidget:
            """Erstellt das Log Panel"""
            panel = QGroupBox("📝 Logs")
            layout = QVBoxLayout(panel)
            
            self.log_text = QTextEdit()
            self.log_text.setReadOnly(True)
            self.log_text.setMaximumHeight(200)
            self.log_text.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {COLORS.get('primary', '#1a1a2e')};
                    color: {COLORS.get('text', '#ffffff')};
                    font-family: monospace;
                    font-size: 11px;
                }}
            """)
            layout.addWidget(self.log_text)
            
            # Clear Button
            clear_btn = QPushButton("🗑️ Logs löschen")
            clear_btn.clicked.connect(lambda: self.log_text.clear())
            layout.addWidget(clear_btn)
            
            return panel
        
        # ====================================================================
        # EVENT HANDLERS
        # ====================================================================
        
        def _toggle_mining(self):
            """Startet/Stoppt Mining"""
            if self.xmrig.is_mining:
                self.xmrig.stop_mining()
                self.toggle_btn.setText("▶️ Starten")
                self.toggle_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {COLORS.get('success', '#00ff88')};
                        color: black;
                        font-weight: bold;
                        padding: 10px 20px;
                        border-radius: 5px;
                    }}
                """)
                self.status_label.setText("⏸️ Gestoppt")
                self.status_label.setStyleSheet(f"color: {COLORS.get('warning', '#ffaa00')};")
            else:
                # Speichere Config vor Start
                self._save_config()
                
                if not self.xmrig.config.wallet:
                    QMessageBox.warning(self, "Fehler", "Bitte gib eine Wallet-Adresse ein!")
                    return
                
                if self.xmrig.start_mining():
                    self.toggle_btn.setText("⏹️ Stoppen")
                    self.toggle_btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {COLORS.get('error', '#ff4444')};
                            color: white;
                            font-weight: bold;
                            padding: 10px 20px;
                            border-radius: 5px;
                        }}
                    """)
                    self.status_label.setText("⛏️ Mining...")
                    self.status_label.setStyleSheet(f"color: {COLORS.get('success', '#00ff88')};")
                else:
                    QMessageBox.critical(self, "Fehler", "Mining konnte nicht gestartet werden!")
        
        def _install_xmrig(self):
            """Installiert XMRig"""
            self.install_btn.setEnabled(False)
            self.install_btn.setText("📥 Wird installiert...")
            
            def on_progress(progress):
                self.install_btn.setText(f"📥 {progress}%")
            
            # In Thread ausführen
            def install():
                success = self.xmrig.download_xmrig(on_progress)
                return success
            
            import threading
            def run_install():
                success = install()
                # UI Update im Main Thread
                from PySide6.QtCore import QMetaObject, Qt
                QMetaObject.invokeMethod(
                    self, "_on_install_complete",
                    Qt.QueuedConnection,
                    success
                )
            
            thread = threading.Thread(target=run_install, daemon=True)
            thread.start()
        
        def _on_install_complete(self, success: bool):
            """Wird aufgerufen wenn Installation abgeschlossen"""
            if success:
                self.install_btn.setVisible(False)
                self.toggle_btn.setEnabled(True)
                QMessageBox.information(self, "Erfolg", "XMRig wurde erfolgreich installiert!")
            else:
                self.install_btn.setEnabled(True)
                self.install_btn.setText("📥 XMRig installieren")
                QMessageBox.critical(self, "Fehler", "XMRig Installation fehlgeschlagen!")
        
        def _on_coin_changed(self, coin: str):
            """Wird aufgerufen wenn Coin geändert wird"""
            self.xmrig.set_coin(coin)
            self._update_pools()
        
        def _update_pools(self):
            """Aktualisiert die Pool-Liste"""
            self.pool_combo.clear()
            coin = self.coin_combo.currentText()
            if coin in CPU_COINS:
                for pool in CPU_COINS[coin]["pools"]:
                    self.pool_combo.addItem(f"{pool['name']} ({pool['url']})", pool['url'])
        
        def _save_config(self):
            """Speichert die Konfiguration"""
            self.xmrig.config.wallet = self.wallet_input.text().strip()
            self.xmrig.config.worker_name = self.worker_input.text().strip()
            self.xmrig.config.threads = self.threads_spin.value()
            self.xmrig.config.huge_pages = self.huge_pages_check.isChecked()
            
            # Pool aus Combo
            pool_url = self.pool_combo.currentData()
            if pool_url:
                self.xmrig.config.pool_url = pool_url
            
            self.xmrig.save_config()
        
        def _on_stats_update(self, stats: CPUMiningStats):
            """Wird aufgerufen wenn Stats aktualisiert werden"""
            self.stats_updated.emit(stats)
        
        def _on_log_line(self, line: str):
            """Wird aufgerufen wenn neue Log-Zeile kommt"""
            # Limitiere Log-Größe
            if self.log_text.document().blockCount() > 500:
                cursor = self.log_text.textCursor()
                cursor.movePosition(cursor.Start)
                cursor.movePosition(cursor.Down, cursor.KeepAnchor, 100)
                cursor.removeSelectedText()
            
            self.log_text.append(line)
        
        def _update_display(self):
            """Aktualisiert die Anzeige"""
            # Stats
            stats = self.xmrig.get_stats()
            self.hashrate_label.setText(f"{stats.hashrate:.2f} H/s")
            self.shares_label.setText(f"A: {stats.accepted} | R: {stats.rejected}")
            
            self.stat_labels["hashrate_stat"].setText(f"{stats.hashrate:.2f} H/s")
            self.stat_labels["accepted_stat"].setText(str(stats.accepted))
            self.stat_labels["rejected_stat"].setText(str(stats.rejected))
            self.stat_labels["diff_stat"].setText(f"{stats.difficulty:.0f}")
            self.stat_labels["pool_stat"].setText(stats.pool[:30] if stats.pool else "-")
            self.stat_labels["uptime_stat"].setText(f"{stats.uptime}s")
            self.stat_labels["threads_stat"].setText(str(stats.threads_active))
            self.stat_labels["algo_stat"].setText(stats.algorithm or "-")
            
            # CPU Info
            cpu = self.xmrig.get_cpu_info()
            self.cpu_usage_label.setText(f"{cpu.usage:.1f}%")
            self.cpu_usage_bar.setValue(int(cpu.usage))


# ============================================================================
# SINGLETON
# ============================================================================

_xmrig_instance: Optional[XMRigManager] = None

def get_xmrig_manager() -> XMRigManager:
    """Gibt die Singleton-Instanz zurück"""
    global _xmrig_instance
    if _xmrig_instance is None:
        _xmrig_instance = XMRigManager()
    return _xmrig_instance


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("💻 CPU Mining Test")
    print("=" * 50)
    
    manager = get_xmrig_manager()
    
    # CPU Info
    cpu = manager.get_cpu_info()
    print(f"\n🖥️ CPU: {cpu.name}")
    print(f"   Kerne: {cpu.cores}")
    print(f"   Threads: {cpu.threads}")
    print(f"   Empfohlene Mining-Threads: {manager.cpu_monitor.get_recommended_threads()}")
    
    # XMRig Status
    print(f"\n📥 XMRig installiert: {manager.is_installed()}")
    
    # Verfügbare Coins
    print(f"\n💰 Verfügbare Coins:")
    for coin, info in CPU_COINS.items():
        print(f"   {coin}: {info['name']} ({info['algorithm']})")
    
    print("\n✅ Test abgeschlossen!")
