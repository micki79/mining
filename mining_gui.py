#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mining GUI - HiveOS-ähnliches Dashboard
Teil des GPU Mining Profit Switcher V12.7 Ultimate

Features:
- Live GPU Monitoring (Temp, Power, Fan, Clocks)
- Echtzeit Hashrate-Charts
- Flight Sheet Management
- Automatisches Overclocking via hashrate.no
- System Tray Integration
- 🤖 AI Agent mit Multi-LLM Support (GROQ, Gemini, DeepSeek, HuggingFace, OpenRouter)
- 💻 CPU Mining mit XMRig (Monero, Zephyr, Raptoreum, etc.)
- 🔧 Automatische Fehlererkennung und -behebung
- 📚 Lernfähige Wissensbasis für Problemlösungen
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# PySide6 Imports
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QGridLayout, QTabWidget, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QLineEdit, QComboBox, QSpinBox,
        QDoubleSpinBox, QCheckBox, QGroupBox, QSplitter,
        QTextEdit, QProgressBar, QSlider, QFrame, QMessageBox,
        QFileDialog, QStatusBar, QMenuBar, QMenu, QToolBar,
        QHeaderView, QAbstractItemView, QSizePolicy, QButtonGroup
    )
    from PySide6.QtCore import Qt, QTimer, QThread, Signal, QObject, QSize, QMetaObject, Slot
    from PySide6.QtGui import QAction, QIcon, QFont, QColor, QPalette, QPixmap
    PYSIDE_AVAILABLE = True
except ImportError:
    print("❌ PySide6 nicht installiert!")
    print("   Installiere mit: pip install PySide6")
    PYSIDE_AVAILABLE = False
    sys.exit(1)

# pyqtgraph für Charts
try:
    import pyqtgraph as pg
    pg.setConfigOptions(antialias=True)
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    print("⚠️ pyqtgraph nicht installiert - Charts deaktiviert")
    PYQTGRAPH_AVAILABLE = False

# Lokale Imports
from themes import COLORS, MAIN_STYLESHEET, apply_theme, get_temp_color
from gpu_monitor import GPUMonitor, GPUInfo
from miner_api import MinerManager, MinerType, MinerStats
from flight_sheets import FlightSheetManager, FlightSheet, COIN_ALGORITHMS
from overclock_manager import OverclockManager
from hashrateno_api import HashrateNoAPI
from tray_icon import MiningTrayIcon

# MSI Afterburner Integration (NEU!)
try:
    from msi_afterburner import MSIAfterburnerManager
    MSI_AB_AVAILABLE = True
except ImportError:
    MSI_AB_AVAILABLE = False

# Hardware-Datenbank (NEU!)
try:
    from hardware_db import HardwareDatabase, get_hardware_db
    HARDWARE_DB_AVAILABLE = True
except ImportError:
    HARDWARE_DB_AVAILABLE = False

# GPU Auto-Tuner (für OC-Optimierung)
try:
    from gpu_auto_tuner import get_auto_tuner, GPUAutoTuner
    AUTO_TUNER_AVAILABLE = True
except ImportError:
    AUTO_TUNER_AVAILABLE = False

# Wallet und Profit (neu)
try:
    from wallet_manager import WalletManager, get_wallet_manager
    from profit_calculator import ProfitCalculator, get_profit_calculator
    PROFIT_AVAILABLE = True
except ImportError:
    PROFIT_AVAILABLE = False

# AI Agent (NEU! V12.7)
try:
    from ai_agent import AIAgent, get_ai_agent
    from ai_agent_widget import AIAgentWidget
    AI_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AI Agent nicht verfügbar: {e}")
    AI_AGENT_AVAILABLE = False

# CPU Mining / XMRig (NEU! V12.7)
try:
    from cpu_mining import XMRigManager, get_xmrig_manager, CPUMiningWidget
    CPU_MINING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ CPU Mining nicht verfügbar: {e}")
    CPU_MINING_AVAILABLE = False

# Portfolio Manager (NEU! V12.8)
try:
    from portfolio_manager import get_portfolio_manager, PortfolioManager, PortfolioSettings
    from portfolio_widget import PortfolioWidget
    PORTFOLIO_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Portfolio Manager nicht verfügbar: {e}")
    PORTFOLIO_AVAILABLE = False

# Code Repair (NEU! V12.8)
try:
    from code_repair import get_repair_manager, CodeRepairManager
    CODE_REPAIR_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Code Repair nicht verfügbar: {e}")
    CODE_REPAIR_AVAILABLE = False

# Multi-GPU Mining (NEU! V12.8) - Jede GPU eigener Coin!
try:
    from multi_gpu_profit import get_multi_gpu_calculator, MultiGPUProfitCalculator, GPU_HASHRATES
    from multi_miner_manager import get_multi_miner_manager, get_multi_gpu_switcher, MultiMinerManager
    from multi_gpu_mining_widget import MultiGPUMiningWidget
    MULTI_GPU_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Multi-GPU Mining nicht verfügbar: {e}")
    MULTI_GPU_AVAILABLE = False

# System Memory Manager (NEU! V12.8)
try:
    from system_memory_manager import get_memory_manager, get_memory_ai, SystemMemoryManager
    from memory_manager_widget import MemoryManagerWidget
    MEMORY_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Memory Manager nicht verfügbar: {e}")
    MEMORY_MANAGER_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Hashrate-Einheiten pro Coin/Algorithmus
HASHRATE_UNITS = {
    # Cuckoo-basierte Algorithmen (graphs/second)
    'GRIN': 'g/s',
    'MWC': 'g/s',
    'AETERNITY': 'g/s',
    'cuckatoo32': 'g/s',
    'cuckatoo31': 'g/s',
    'cuckatoo29': 'g/s',
    'C32': 'g/s',
    'C31': 'g/s',
    'C29': 'g/s',
    
    # Equihash-basierte (solutions/second)
    'BEAM': 'Sol/s',
    'ZEC': 'Sol/s',
    'ZEN': 'Sol/s',
    'beamhash3': 'Sol/s',
    'beamhashiii': 'Sol/s',
    'BEAM-III': 'Sol/s',
    'equihash': 'Sol/s',
    
    # KHeavyHash (GH/s)
    'KAS': 'GH/s',
    'kheavyhash': 'GH/s',
    
    # Blake3-basierte (GH/s)
    'ALPH': 'GH/s',
    'IRON': 'GH/s',
    'blake3': 'GH/s',
    
    # RandomX (H/s oder KH/s)
    'XMR': 'H/s',
    'randomx': 'H/s',
    
    # Standard GPU Algos (MH/s)
    'RVN': 'MH/s',
    'ERG': 'MH/s',
    'ETC': 'MH/s',
    'ETH': 'MH/s',
    'FLUX': 'MH/s',
    'CLORE': 'MH/s',
    'kawpow': 'MH/s',
    'autolykos2': 'MH/s',
    'etchash': 'MH/s',
    'ethash': 'MH/s',
    'equihash125': 'Sol/s',
    'equihash144': 'Sol/s',
    'equihash192': 'Sol/s',
}

def get_hashrate_unit(coin_or_algo: str) -> str:
    """Gibt die richtige Hashrate-Einheit für einen Coin/Algorithmus zurück"""
    return HASHRATE_UNITS.get(coin_or_algo.upper(), HASHRATE_UNITS.get(coin_or_algo.lower(), 'MH/s'))


class WorkerSignals(QObject):
    """Signals für Worker-Threads"""
    update = Signal(dict)
    error = Signal(str)
    finished = Signal()


class MonitorWorker(QThread):
    """Background-Worker für GPU Monitoring"""
    
    update = Signal(dict)
    
    def __init__(self, gpu_monitor: GPUMonitor, interval: float = 1.0):
        super().__init__()
        self.gpu_monitor = gpu_monitor
        self.interval = interval
        self._running = True
    
    def run(self):
        while self._running:
            try:
                if self.gpu_monitor:
                    data = self.gpu_monitor.get_current()
                    if data:
                        self.update.emit(data)
            except Exception as e:
                logger.warning(f"MonitorWorker Fehler: {e}")
            
            # Interruptible sleep
            for _ in range(int(self.interval * 10)):
                if not self._running:
                    break
                time.sleep(0.1)
    
    def stop(self):
        self._running = False


class MinerStatsWorker(QThread):
    """Background-Worker für Miner-API Abfragen"""
    
    update = Signal(object)
    
    def __init__(self, miner_manager: MinerManager, interval: float = 2.0):
        super().__init__()
        self.miner_manager = miner_manager
        self.interval = interval
        self._running = True
    
    def run(self):
        # Kurz warten bis Miner gestartet ist
        time.sleep(3.0)
        
        while self._running:
            try:
                if self.miner_manager and self.miner_manager.is_mining():
                    stats = self.miner_manager.get_current_stats()
                    if stats:
                        self.update.emit(stats)
            except Exception as e:
                logger.warning(f"MinerStatsWorker Fehler: {e}")
            
            # Interruptible sleep
            for _ in range(int(self.interval * 10)):
                if not self._running:
                    break
                time.sleep(0.1)
    
    def stop(self):
        self._running = False


class GPUTableWidget(QTableWidget):
    """GPU Status Tabelle mit Auswahl-Checkboxen"""
    
    COLUMNS = ['✓', 'GPU', 'Typ', 'Hashrate', 'Temp', 'Fan', 'Power', 'Core', 'Memory', 'Efficiency']
    
    gpu_selection_changed = Signal(list)  # Liste der ausgewählten GPU-Indizes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gpu_checkboxes = {}  # {row: checkbox}
        self.setup_table()
    
    def setup_table(self):
        self.setColumnCount(len(self.COLUMNS))
        self.setHorizontalHeaderLabels(self.COLUMNS)
        
        # Header-Styling
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 30)  # Checkbox-Spalte schmal
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # GPU Name
        header.setSectionResizeMode(2, QHeaderView.Fixed)    # Typ
        self.setColumnWidth(2, 60)
        for i in range(3, len(self.COLUMNS)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
    
    def update_gpus(self, gpus: List[GPUInfo], miner_stats: Optional[MinerStats] = None, current_coin: str = None):
        """Aktualisiert die GPU-Tabelle"""
        # Hashrate-Einheit bestimmen
        hashrate_unit = get_hashrate_unit(current_coin) if current_coin else 'MH/s'
        
        self.setRowCount(len(gpus))
        
        for row, gpu in enumerate(gpus):
            # Checkbox für GPU-Auswahl (nur einmal erstellen)
            if row not in self.gpu_checkboxes:
                checkbox = QCheckBox()
                checkbox.setChecked(True)  # Standardmäßig alle GPUs aktiviert
                checkbox.stateChanged.connect(self._on_checkbox_changed)
                self.gpu_checkboxes[row] = checkbox
                
                # Checkbox in Widget zentrieren
                widget = QWidget()
                layout = QHBoxLayout(widget)
                layout.addWidget(checkbox)
                layout.setAlignment(Qt.AlignCenter)
                layout.setContentsMargins(0, 0, 0, 0)
                self.setCellWidget(row, 0, widget)
            
            # GPU Name
            name_item = QTableWidgetItem(gpu.name)
            self.setItem(row, 1, name_item)
            
            # GPU Typ mit Farbe
            gpu_type = getattr(gpu, 'gpu_type', 'NVIDIA')
            type_item = QTableWidgetItem(gpu_type)
            type_colors = {
                'NVIDIA': '#76B900',  # NVIDIA Grün
                'AMD': '#ED1C24',     # AMD Rot
                'Intel': '#0071C5',   # Intel Blau
            }
            type_item.setForeground(QColor(type_colors.get(gpu_type, COLORS['text_primary'])))
            self.setItem(row, 2, type_item)
            
            # Hashrate (von Miner API wenn verfügbar)
            hashrate = gpu.hashrate
            if miner_stats and row < len(miner_stats.gpus):
                hashrate = miner_stats.gpus[row].hashrate
            
            hashrate_item = QTableWidgetItem(f"{hashrate:.2f} {hashrate_unit}")
            hashrate_item.setForeground(QColor(COLORS['hashrate']))
            hashrate_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.setItem(row, 3, hashrate_item)
            
            # Temperatur mit Farbcodierung
            temp_item = QTableWidgetItem(f"{gpu.temperature}°C" if gpu.temperature > 0 else "--")
            temp_color = get_temp_color(gpu.temperature) if gpu.temperature > 0 else COLORS['text_secondary']
            temp_item.setForeground(QColor(temp_color))
            self.setItem(row, 4, temp_item)
            
            # Fan
            fan_item = QTableWidgetItem(f"{gpu.fan_speed}%" if gpu.fan_speed > 0 else "--")
            self.setItem(row, 5, fan_item)
            
            # Power
            power_item = QTableWidgetItem(f"{gpu.power_watts:.0f}W" if gpu.power_watts > 0 else "--")
            power_item.setForeground(QColor(COLORS['power']))
            self.setItem(row, 6, power_item)
            
            # Core Clock
            core_item = QTableWidgetItem(f"{gpu.core_clock_mhz} MHz" if gpu.core_clock_mhz > 0 else "--")
            self.setItem(row, 7, core_item)
            
            # Memory Clock
            mem_item = QTableWidgetItem(f"{gpu.memory_clock_mhz} MHz" if gpu.memory_clock_mhz > 0 else "--")
            self.setItem(row, 8, mem_item)
            
            # Efficiency
            efficiency = hashrate / gpu.power_watts if gpu.power_watts > 0 and hashrate > 0 else 0
            eff_item = QTableWidgetItem(f"{efficiency:.3f}" if efficiency > 0 else "--")
            eff_item.setForeground(QColor(COLORS['efficiency']))
            self.setItem(row, 9, eff_item)
    
    def _on_checkbox_changed(self):
        """Wird aufgerufen wenn eine GPU-Checkbox geändert wird"""
        selected = self.get_selected_gpus()
        self.gpu_selection_changed.emit(selected)
    
    def get_selected_gpus(self) -> List[int]:
        """Gibt Liste der ausgewählten GPU-Indizes zurück"""
        selected = []
        for row, checkbox in self.gpu_checkboxes.items():
            if checkbox.isChecked():
                selected.append(row)
        return selected
    
    def select_all_gpus(self):
        """Wählt alle GPUs aus"""
        for checkbox in self.gpu_checkboxes.values():
            checkbox.setChecked(True)
    
    def deselect_all_gpus(self):
        """Wählt alle GPUs ab"""
        for checkbox in self.gpu_checkboxes.values():
            checkbox.setChecked(False)


class HashrateChartWidget(QWidget):
    """Echtzeit Hashrate-Chart"""
    
    def __init__(self, parent=None, history_size: int = 300):
        super().__init__(parent)
        self.history_size = history_size
        self.data = []
        self.timestamps = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if PYQTGRAPH_AVAILABLE:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground(COLORS['background'])
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('left', 'Hashrate', 'MH/s')
            self.plot_widget.setLabel('bottom', 'Zeit', 's')
            
            self.curve = self.plot_widget.plot(
                [], [], 
                pen=pg.mkPen(color=COLORS['hashrate'], width=2),
                fillLevel=0,
                brush=pg.mkBrush(color=COLORS['hashrate'] + '40')
            )
            
            layout.addWidget(self.plot_widget)
        else:
            label = QLabel("Charts nicht verfügbar\n(pyqtgraph fehlt)")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    
    def update_data(self, hashrate: float):
        """Fügt einen neuen Datenpunkt hinzu"""
        self.data.append(hashrate)
        self.timestamps.append(time.time())
        
        # Historie begrenzen
        if len(self.data) > self.history_size:
            self.data.pop(0)
            self.timestamps.pop(0)
        
        if PYQTGRAPH_AVAILABLE and self.data:
            # X-Achse: Sekunden seit Start
            x = [t - self.timestamps[0] for t in self.timestamps]
            self.curve.setData(x, self.data)


class TemperatureChartWidget(QWidget):
    """Multi-GPU Temperatur-Chart"""
    
    def __init__(self, parent=None, gpu_count: int = 1, history_size: int = 300):
        super().__init__(parent)
        self.history_size = history_size
        self.gpu_count = gpu_count
        self.data: Dict[int, List[float]] = {i: [] for i in range(gpu_count)}
        self.timestamps = []
        self.curves = {}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        if PYQTGRAPH_AVAILABLE:
            self.plot_widget = pg.PlotWidget()
            self.plot_widget.setBackground(COLORS['background'])
            self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
            self.plot_widget.setLabel('left', 'Temperatur', '°C')
            self.plot_widget.setLabel('bottom', 'Zeit', 's')
            self.plot_widget.addLegend()
            
            # Verschiedene Farben für GPUs
            colors = ['#ff4444', '#00ff88', '#00bfff', '#ffff00', '#ff00ff', '#00ffff']
            
            for i in range(gpu_count):
                color = colors[i % len(colors)]
                self.curves[i] = self.plot_widget.plot(
                    [], [],
                    pen=pg.mkPen(color=color, width=2),
                    name=f'GPU {i}'
                )
            
            layout.addWidget(self.plot_widget)
        else:
            label = QLabel("Charts nicht verfügbar")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
    
    def set_gpu_count(self, count: int):
        """Setzt die Anzahl der GPUs"""
        if count != self.gpu_count and PYQTGRAPH_AVAILABLE:
            self.gpu_count = count
            # Neue Kurven hinzufügen falls nötig
            colors = ['#ff4444', '#00ff88', '#00bfff', '#ffff00', '#ff00ff', '#00ffff']
            for i in range(count):
                if i not in self.curves:
                    color = colors[i % len(colors)]
                    self.curves[i] = self.plot_widget.plot([], [], pen=pg.mkPen(color=color, width=2))
                if i not in self.data:
                    self.data[i] = []
    
    def update_data(self, temperatures: Dict[int, int]):
        """Aktualisiert Temperaturen für alle GPUs"""
        self.timestamps.append(time.time())
        
        for gpu_idx, temp in temperatures.items():
            if gpu_idx not in self.data:
                self.data[gpu_idx] = []
            self.data[gpu_idx].append(temp)
            
            if len(self.data[gpu_idx]) > self.history_size:
                self.data[gpu_idx].pop(0)
        
        if len(self.timestamps) > self.history_size:
            self.timestamps.pop(0)
        
        if PYQTGRAPH_AVAILABLE and self.timestamps:
            x = [t - self.timestamps[0] for t in self.timestamps]
            for gpu_idx, curve in self.curves.items():
                if gpu_idx in self.data and self.data[gpu_idx]:
                    curve.setData(x[:len(self.data[gpu_idx])], self.data[gpu_idx])


class DashboardTab(QWidget):
    """Dashboard Tab - Hauptübersicht"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top Stats Bar
        stats_layout = QHBoxLayout()
        
        # Gesamt-Hashrate
        hashrate_group = QGroupBox("Gesamt Hashrate")
        hashrate_layout = QVBoxLayout(hashrate_group)
        self.hashrate_label = QLabel("0.00 MH/s")
        self.hashrate_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {COLORS['hashrate']};")
        self.hashrate_label.setAlignment(Qt.AlignCenter)
        hashrate_layout.addWidget(self.hashrate_label)
        stats_layout.addWidget(hashrate_group)
        
        # Aktiver Coin
        coin_group = QGroupBox("Aktiver Coin")
        coin_layout = QVBoxLayout(coin_group)
        self.coin_label = QLabel("--")
        self.coin_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['info']};")
        self.coin_label.setAlignment(Qt.AlignCenter)
        coin_layout.addWidget(self.coin_label)
        stats_layout.addWidget(coin_group)
        
        # Power
        power_group = QGroupBox("Power")
        power_layout = QVBoxLayout(power_group)
        self.power_label = QLabel("0 W")
        self.power_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['power']};")
        self.power_label.setAlignment(Qt.AlignCenter)
        power_layout.addWidget(self.power_label)
        stats_layout.addWidget(power_group)
        
        # Uptime
        uptime_group = QGroupBox("Uptime")
        uptime_layout = QVBoxLayout(uptime_group)
        self.uptime_label = QLabel("00:00:00")
        self.uptime_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.uptime_label.setAlignment(Qt.AlignCenter)
        uptime_layout.addWidget(self.uptime_label)
        stats_layout.addWidget(uptime_group)
        
        # Shares
        shares_group = QGroupBox("Shares")
        shares_layout = QVBoxLayout(shares_group)
        self.shares_label = QLabel("A: 0 | R: 0")
        self.shares_label.setStyleSheet("font-size: 20px;")
        self.shares_label.setAlignment(Qt.AlignCenter)
        shares_layout.addWidget(self.shares_label)
        stats_layout.addWidget(shares_group)
        
        # Profit USD/Tag (NEU!)
        profit_group = QGroupBox("Profit/Tag")
        profit_layout = QVBoxLayout(profit_group)
        self.profit_label = QLabel("$0.00")
        self.profit_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['accepted']};")
        self.profit_label.setAlignment(Qt.AlignCenter)
        profit_layout.addWidget(self.profit_label)
        stats_layout.addWidget(profit_group)
        
        layout.addLayout(stats_layout)
        
        # Splitter für Tabelle und Charts
        splitter = QSplitter(Qt.Horizontal)
        
        # GPU Tabelle
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        table_label = QLabel("GPU Status")
        table_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        table_layout.addWidget(table_label)
        
        self.gpu_table = GPUTableWidget()
        table_layout.addWidget(self.gpu_table)
        
        splitter.addWidget(table_widget)
        
        # Charts
        charts_widget = QWidget()
        charts_layout = QVBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        
        # Hashrate Chart
        hashrate_chart_label = QLabel("Hashrate Verlauf")
        hashrate_chart_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        charts_layout.addWidget(hashrate_chart_label)
        
        self.hashrate_chart = HashrateChartWidget()
        self.hashrate_chart.setMinimumHeight(150)
        charts_layout.addWidget(self.hashrate_chart)
        
        # Temperature Chart
        temp_chart_label = QLabel("Temperatur Verlauf")
        temp_chart_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        charts_layout.addWidget(temp_chart_label)
        
        self.temp_chart = TemperatureChartWidget(gpu_count=4)
        self.temp_chart.setMinimumHeight(150)
        charts_layout.addWidget(self.temp_chart)
        
        splitter.addWidget(charts_widget)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        
        # OC-Profile Controls (NEU!)
        oc_layout = QHBoxLayout()
        
        oc_label = QLabel("⚡ OC-Profile:")
        oc_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        oc_layout.addWidget(oc_label)
        
        self.oc_low_btn = QPushButton("LOW")
        self.oc_low_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        self.oc_low_btn.setCheckable(True)
        oc_layout.addWidget(self.oc_low_btn)
        
        self.oc_med_btn = QPushButton("MED")
        self.oc_med_btn.setStyleSheet(f"padding: 8px 16px; font-size: 12px; background-color: {COLORS['button_primary']};")
        self.oc_med_btn.setCheckable(True)
        self.oc_med_btn.setChecked(True)
        oc_layout.addWidget(self.oc_med_btn)
        
        self.oc_high_btn = QPushButton("HIGH")
        self.oc_high_btn.setStyleSheet("padding: 8px 16px; font-size: 12px;")
        self.oc_high_btn.setCheckable(True)
        oc_layout.addWidget(self.oc_high_btn)
        
        # Button Group für exclusive selection
        self.oc_button_group = QButtonGroup(self)
        self.oc_button_group.addButton(self.oc_low_btn, 0)
        self.oc_button_group.addButton(self.oc_med_btn, 1)
        self.oc_button_group.addButton(self.oc_high_btn, 2)
        self.oc_button_group.setExclusive(True)
        
        oc_layout.addStretch()
        
        # Auto-OC Toggle
        self.auto_oc_checkbox = QCheckBox("Auto-OC")
        self.auto_oc_checkbox.setStyleSheet("font-size: 12px;")
        self.auto_oc_checkbox.setToolTip("Automatische Overclock-Anpassung basierend auf Temperatur")
        oc_layout.addWidget(self.auto_oc_checkbox)
        
        layout.addLayout(oc_layout)
        
        # Bottom Control Buttons
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Mining Starten")
        self.start_btn.setStyleSheet(f"background-color: {COLORS['button_success']}; font-size: 14px; padding: 12px;")
        controls_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Mining Stoppen")
        self.stop_btn.setStyleSheet(f"background-color: {COLORS['button_danger']}; font-size: 14px; padding: 12px;")
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        self.switch_btn = QPushButton("🔄 Coin Wechseln")
        self.switch_btn.setStyleSheet("font-size: 14px; padding: 12px;")
        controls_layout.addWidget(self.switch_btn)
        
        layout.addLayout(controls_layout)
    
    def update_stats(self, hashrate: float, power: float, coin: str, uptime: int, accepted: int, rejected: int, profit_usd: float = 0.0):
        """Aktualisiert die Stats-Anzeigen"""
        # Dynamische Hashrate-Einheit basierend auf Coin
        unit = get_hashrate_unit(coin) if coin else 'MH/s'
        self.hashrate_label.setText(f"{hashrate:.2f} {unit}")
        self.power_label.setText(f"{power:.0f} W")
        self.coin_label.setText(coin or "--")
        
        # Uptime formatieren
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        seconds = uptime % 60
        self.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        
        # Shares mit Farben
        self.shares_label.setText(f"<span style='color:{COLORS['accepted']}'>A: {accepted}</span> | "
                                   f"<span style='color:{COLORS['rejected']}'>R: {rejected}</span>")
        
        # Profit USD/Tag
        if profit_usd > 0:
            self.profit_label.setText(f"${profit_usd:.2f}")
            self.profit_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['accepted']};")
        else:
            self.profit_label.setText("$0.00")
            self.profit_label.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {COLORS['text_secondary']};")


class FlightSheetsTab(QWidget):
    """Flight Sheets Tab - Mining-Konfigurationen"""
    
    flight_sheet_applied = Signal(str)  # sheet_id
    
    def __init__(self, flight_manager: FlightSheetManager, parent=None):
        super().__init__(parent)
        self.flight_manager = flight_manager
        self.setup_ui()
        self.load_sheets()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Linke Seite: Liste
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_label = QLabel("Flight Sheets")
        left_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(left_label)
        
        self.sheets_table = QTableWidget()
        self.sheets_table.setColumnCount(4)
        self.sheets_table.setHorizontalHeaderLabels(['Name', 'Coin', 'Pool', 'Miner'])
        self.sheets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sheets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sheets_table.itemSelectionChanged.connect(self.on_selection_changed)
        left_layout.addWidget(self.sheets_table)
        
        btn_layout = QHBoxLayout()
        self.new_btn = QPushButton("➕ Neu")
        self.new_btn.clicked.connect(self.new_sheet)
        btn_layout.addWidget(self.new_btn)
        
        self.delete_btn = QPushButton("🗑️ Löschen")
        self.delete_btn.clicked.connect(self.delete_sheet)
        btn_layout.addWidget(self.delete_btn)
        
        self.apply_btn = QPushButton("▶️ Anwenden")
        self.apply_btn.setStyleSheet(f"background-color: {COLORS['button_success']};")
        self.apply_btn.clicked.connect(self.apply_sheet)
        btn_layout.addWidget(self.apply_btn)
        
        left_layout.addLayout(btn_layout)
        layout.addWidget(left_widget, 1)
        
        # Rechte Seite: Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        right_label = QLabel("Flight Sheet bearbeiten")
        right_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(right_label)
        
        form_layout = QGridLayout()
        
        # Name
        form_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        form_layout.addWidget(self.name_edit, 0, 1)
        
        # Coin
        form_layout.addWidget(QLabel("Coin:"), 1, 0)
        self.coin_combo = QComboBox()
        self.coin_combo.addItems(['RVN', 'ERG', 'ETC', 'FLUX', 'KAS', 'CLORE', 'ALPH', 'NEXA', 'DNX', 'CFX', 'FIRO', 'RXD', 'XNA', 'BTG', 'BEAM', 'KLS', 'XMR', 'ZEPH'])
        self.coin_combo.currentTextChanged.connect(self.on_coin_changed)
        form_layout.addWidget(self.coin_combo, 1, 1)
        
        # Pool
        form_layout.addWidget(QLabel("Pool:"), 2, 0)
        self.pool_combo = QComboBox()
        form_layout.addWidget(self.pool_combo, 2, 1)
        
        # Wallet
        form_layout.addWidget(QLabel("Wallet:"), 3, 0)
        wallet_layout = QHBoxLayout()
        self.wallet_edit = QLineEdit()
        self.wallet_edit.setPlaceholderText("Wallet-Adresse eingeben...")
        wallet_layout.addWidget(self.wallet_edit)
        
        # Wallet speichern/laden Buttons
        self.wallet_save_btn = QPushButton("💾")
        self.wallet_save_btn.setToolTip("Wallet für diesen Coin speichern")
        self.wallet_save_btn.setMaximumWidth(40)
        self.wallet_save_btn.clicked.connect(self.save_wallet)
        wallet_layout.addWidget(self.wallet_save_btn)
        
        self.wallet_load_btn = QPushButton("📂")
        self.wallet_load_btn.setToolTip("Gespeicherte Wallet laden")
        self.wallet_load_btn.setMaximumWidth(40)
        self.wallet_load_btn.clicked.connect(self.load_wallet)
        wallet_layout.addWidget(self.wallet_load_btn)
        
        # CoinEx Sync Button
        self.coinex_sync_btn = QPushButton("🔄 CoinEx")
        self.coinex_sync_btn.setToolTip("Wallet von CoinEx laden")
        self.coinex_sync_btn.setMaximumWidth(80)
        self.coinex_sync_btn.clicked.connect(self.sync_coinex_wallet)
        wallet_layout.addWidget(self.coinex_sync_btn)
        
        # Gate.io Sync Button
        self.gateio_sync_btn = QPushButton("🔄 Gate.io")
        self.gateio_sync_btn.setToolTip("Wallet von Gate.io laden")
        self.gateio_sync_btn.setMaximumWidth(80)
        self.gateio_sync_btn.clicked.connect(self.sync_gateio_wallet)
        wallet_layout.addWidget(self.gateio_sync_btn)
        
        form_layout.addLayout(wallet_layout, 3, 1)
        
        # Worker Name
        form_layout.addWidget(QLabel("Worker:"), 4, 0)
        self.worker_edit = QLineEdit()
        self.worker_edit.setText("Rig_D")
        form_layout.addWidget(self.worker_edit, 4, 1)
        
        # Miner
        form_layout.addWidget(QLabel("Miner:"), 5, 0)
        self.miner_combo = QComboBox()
        self.miner_combo.addItems(['trex', 'nbminer', 'gminer', 'lolminer', 'rigel', 'bzminer', 'teamredminer', 'srbminer', 'xmrig'])
        form_layout.addWidget(self.miner_combo, 5, 1)
        
        # Extra Args
        form_layout.addWidget(QLabel("Extra Args:"), 6, 0)
        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("Zusätzliche Miner-Argumente...")
        form_layout.addWidget(self.extra_args_edit, 6, 1)
        
        # Auto OC
        self.auto_oc_check = QCheckBox("Auto-Overclocking (hashrate.no)")
        self.auto_oc_check.setChecked(True)
        form_layout.addWidget(self.auto_oc_check, 7, 0, 1, 2)
        
        right_layout.addLayout(form_layout)
        
        # Save Button
        self.save_btn = QPushButton("💾 Speichern")
        self.save_btn.clicked.connect(self.save_sheet)
        right_layout.addWidget(self.save_btn)
        
        right_layout.addStretch()
        layout.addWidget(right_widget, 1)
        
        # Initial Pool-Liste laden
        self.on_coin_changed(self.coin_combo.currentText())
    
    def load_sheets(self):
        """Lädt alle Flight Sheets in die Tabelle"""
        sheets = self.flight_manager.list_all()
        self.sheets_table.setRowCount(len(sheets))
        
        for row, sheet in enumerate(sheets):
            self.sheets_table.setItem(row, 0, QTableWidgetItem(sheet.name))
            self.sheets_table.setItem(row, 1, QTableWidgetItem(sheet.coin))
            self.sheets_table.setItem(row, 2, QTableWidgetItem(sheet.pool_name or sheet.pool_url[:30]))
            self.sheets_table.setItem(row, 3, QTableWidgetItem(sheet.miner))
            
            # ID speichern
            self.sheets_table.item(row, 0).setData(Qt.UserRole, sheet.id)
    
    def on_selection_changed(self):
        """Lädt ausgewähltes Flight Sheet in Editor"""
        rows = self.sheets_table.selectionModel().selectedRows()
        if not rows:
            return
        
        row = rows[0].row()
        sheet_id = self.sheets_table.item(row, 0).data(Qt.UserRole)
        sheet = self.flight_manager.get(sheet_id)
        
        if sheet:
            self.name_edit.setText(sheet.name)
            self.coin_combo.setCurrentText(sheet.coin)
            self.wallet_edit.setText(sheet.wallet)
            self.worker_edit.setText(sheet.worker_name)
            self.miner_combo.setCurrentText(sheet.miner)
            self.extra_args_edit.setText(sheet.extra_args)
            
            # Pool in Combo finden
            for i in range(self.pool_combo.count()):
                if sheet.pool_url in self.pool_combo.itemData(i):
                    self.pool_combo.setCurrentIndex(i)
                    break
    
    def on_coin_changed(self, coin: str):
        """Aktualisiert Pool-Liste für Coin"""
        self.pool_combo.clear()
        pools = FlightSheetManager.get_pools_for_coin(coin)
        for pool in pools:
            self.pool_combo.addItem(pool['name'], pool['url'])
        
        # Auto-Load Wallet wenn verfügbar
        self.load_wallet()
    
    def save_wallet(self):
        """Speichert Wallet für aktuellen Coin"""
        if not PROFIT_AVAILABLE:
            return
        
        coin = self.coin_combo.currentText()
        wallet = self.wallet_edit.text().strip()
        
        if not wallet:
            QMessageBox.warning(self, "Fehler", "Bitte Wallet-Adresse eingeben!")
            return
        
        wm = get_wallet_manager()
        if wm.set_wallet(coin, wallet):
            QMessageBox.information(self, "Gespeichert", f"Wallet für {coin} gespeichert!")
        else:
            QMessageBox.warning(self, "Fehler", "Wallet konnte nicht gespeichert werden!")
    
    def load_wallet(self):
        """Lädt gespeicherte Wallet für aktuellen Coin"""
        if not PROFIT_AVAILABLE:
            return
        
        coin = self.coin_combo.currentText()
        wm = get_wallet_manager()
        wallet = wm.get_wallet(coin)
        
        if wallet and not wallet.startswith("DEINE_"):
            self.wallet_edit.setText(wallet)
    
    def sync_coinex_wallet(self):
        """Lädt Wallet von CoinEx für aktuellen Coin"""
        if not PROFIT_AVAILABLE:
            QMessageBox.warning(self, "Fehler", "Wallet-Manager nicht verfügbar")
            return
        
        coin = self.coin_combo.currentText()
        self.coinex_sync_btn.setText("⏳...")
        self.coinex_sync_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            from coinex_api import CoinExAPI
            
            api = CoinExAPI()
            
            if not api.is_configured():
                QMessageBox.warning(self, "CoinEx", "CoinEx API nicht konfiguriert!\n\nPrüfe coinex_config.json")
                return
            
            # Wallet für diesen Coin abrufen
            result = api.get_deposit_address(coin)
            
            if result and result.get('is_valid'):
                address = result['address']
                self.wallet_edit.setText(address)
                
                # Auch in Wallet Manager speichern
                wm = get_wallet_manager()
                wm.set_wallet(coin, address)
                
                QMessageBox.information(
                    self, "CoinEx", 
                    f"✅ {coin} Wallet geladen!\n\n{address[:30]}..."
                )
            else:
                QMessageBox.warning(
                    self, "CoinEx", 
                    f"❌ Keine {coin} Deposit-Adresse gefunden.\n\n"
                    f"Bitte erstelle eine Adresse auf CoinEx."
                )
        
        except ImportError:
            QMessageBox.warning(self, "Fehler", "CoinEx API Modul nicht gefunden!")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"CoinEx Fehler: {e}")
        finally:
            self.coinex_sync_btn.setText("🔄 CoinEx")
            self.coinex_sync_btn.setEnabled(True)
    
    def sync_gateio_wallet(self):
        """Lädt Wallet von Gate.io für aktuellen Coin"""
        if not PROFIT_AVAILABLE:
            QMessageBox.warning(self, "Fehler", "Wallet-Manager nicht verfügbar")
            return
        
        coin = self.coin_combo.currentText()
        self.gateio_sync_btn.setText("⏳...")
        self.gateio_sync_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            from gateio_api import GateIOAPI
            
            api = GateIOAPI()
            
            if not api.is_configured():
                QMessageBox.warning(self, "Gate.io", "Gate.io API nicht konfiguriert!\n\nPrüfe gateio_config.json")
                return
            
            # Wallet für diesen Coin abrufen
            wallet = api.get_deposit_address(coin)
            
            if wallet and wallet.address:
                address = wallet.address
                self.wallet_edit.setText(address)
                
                # Auch in Wallet Manager speichern
                wm = get_wallet_manager()
                wm.set_wallet(coin, address)
                
                QMessageBox.information(
                    self, "Gate.io", 
                    f"✅ {coin} Wallet geladen!\n\n{address[:30]}..."
                )
            else:
                QMessageBox.warning(
                    self, "Gate.io", 
                    f"❌ Keine {coin} Deposit-Adresse gefunden.\n\n"
                    f"Bitte erstelle eine Adresse auf Gate.io."
                )
        
        except ImportError:
            QMessageBox.warning(self, "Fehler", "Gate.io API Modul nicht gefunden!")
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Gate.io Fehler: {e}")
        finally:
            self.gateio_sync_btn.setText("🔄 Gate.io")
            self.gateio_sync_btn.setEnabled(True)
    
    def new_sheet(self):
        """Erstellt neues Flight Sheet"""
        self.name_edit.setText("")
        self.wallet_edit.setText("")
        self.extra_args_edit.setText("")
        self.sheets_table.clearSelection()
    
    def save_sheet(self):
        """Speichert Flight Sheet"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Fehler", "Bitte Namen eingeben!")
            return
        
        wallet = self.wallet_edit.text().strip()
        if not wallet:
            QMessageBox.warning(self, "Fehler", "Bitte Wallet-Adresse eingeben!")
            return
        
        coin = self.coin_combo.currentText()
        pool_url = self.pool_combo.currentData()
        pool_name = self.pool_combo.currentText()
        
        sheet = FlightSheet(
            id="",  # Wird automatisch generiert
            name=name,
            coin=coin,
            algorithm=COIN_ALGORITHMS.get(coin, ""),
            wallet=wallet,
            pool_url=pool_url,
            pool_name=pool_name,
            miner=self.miner_combo.currentText(),
            worker_name=self.worker_edit.text(),
            extra_args=self.extra_args_edit.text(),
        )
        
        self.flight_manager.add(sheet)
        self.load_sheets()
        QMessageBox.information(self, "Gespeichert", f"Flight Sheet '{name}' gespeichert!")
    
    def delete_sheet(self):
        """Löscht Flight Sheet"""
        rows = self.sheets_table.selectionModel().selectedRows()
        if not rows:
            return
        
        row = rows[0].row()
        sheet_id = self.sheets_table.item(row, 0).data(Qt.UserRole)
        name = self.sheets_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Löschen bestätigen",
            f"Flight Sheet '{name}' wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.flight_manager.delete(sheet_id)
            self.load_sheets()
    
    def apply_sheet(self):
        """Wendet Flight Sheet an (startet Mining)"""
        rows = self.sheets_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Fehler", "Bitte Flight Sheet auswählen!")
            return
        
        row = rows[0].row()
        sheet_id = self.sheets_table.item(row, 0).data(Qt.UserRole)
        self.flight_sheet_applied.emit(sheet_id)


class OverclockTab(QWidget):
    """Overclocking Tab"""
    
    def __init__(self, oc_manager: OverclockManager, hashrate_api: HashrateNoAPI, parent=None):
        super().__init__(parent)
        self.oc_manager = oc_manager
        self.hashrate_api = hashrate_api
        self.msi_ab_manager = None  # Wird von MainWindow gesetzt
        self.setup_ui()
    
    def set_msi_ab_manager(self, manager):
        """Setzt MSI Afterburner Manager"""
        self.msi_ab_manager = manager
        self.update_msi_ab_status()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # ============================================================
        # MSI AFTERBURNER SEKTION (NEU!)
        # ============================================================
        msi_group = QGroupBox("🎮 MSI Afterburner (Empfohlen für Laptops)")
        msi_layout = QGridLayout(msi_group)
        
        # Status
        msi_layout.addWidget(QLabel("Status:"), 0, 0)
        self.msi_status_label = QLabel("Prüfe...")
        self.msi_status_label.setStyleSheet("font-weight: bold;")
        msi_layout.addWidget(self.msi_status_label, 0, 1)
        
        # Version
        msi_layout.addWidget(QLabel("Version:"), 0, 2)
        self.msi_version_label = QLabel("--")
        msi_layout.addWidget(self.msi_version_label, 0, 3)
        
        # Buttons
        self.msi_install_btn = QPushButton("📥 Installieren")
        self.msi_install_btn.clicked.connect(self.install_msi_afterburner)
        msi_layout.addWidget(self.msi_install_btn, 1, 0)
        
        self.msi_start_btn = QPushButton("▶️ Starten")
        self.msi_start_btn.clicked.connect(self.start_msi_afterburner)
        msi_layout.addWidget(self.msi_start_btn, 1, 1)
        
        self.msi_update_btn = QPushButton("🔄 Update prüfen")
        self.msi_update_btn.clicked.connect(self.check_msi_update)
        msi_layout.addWidget(self.msi_update_btn, 1, 2)
        
        # Info
        msi_info = QLabel("💡 MSI Afterburner ermöglicht OC auch ohne Admin-Rechte und auf Laptops!")
        msi_info.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        msi_layout.addWidget(msi_info, 2, 0, 1, 4)
        
        layout.addWidget(msi_group)
        
        # ============================================================
        # ORIGINAL OC SEKTION
        # ============================================================
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("GPU Overclocking")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header_label)
        
        self.auto_oc_btn = QPushButton("🔧 Auto-OC (hashrate.no)")
        self.auto_oc_btn.clicked.connect(self.apply_auto_oc)
        header_layout.addWidget(self.auto_oc_btn)
        
        self.reset_btn = QPushButton("↩️ Reset All")
        self.reset_btn.clicked.connect(self.reset_all)
        header_layout.addWidget(self.reset_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Coin-Auswahl für Auto-OC
        coin_layout = QHBoxLayout()
        coin_layout.addWidget(QLabel("Coin für Auto-OC:"))
        self.coin_combo = QComboBox()
        self.coin_combo.addItems(['RVN', 'ERG', 'FLUX', 'ETC', 'KAS', 'ALPH', 'ZEC', 'BEAM'])
        coin_layout.addWidget(self.coin_combo)
        
        # Use MSI AB Checkbox
        self.use_msi_ab_check = QCheckBox("MSI Afterburner nutzen")
        self.use_msi_ab_check.setChecked(True)
        coin_layout.addWidget(self.use_msi_ab_check)
        
        coin_layout.addStretch()
        layout.addLayout(coin_layout)
        
        # GPU Slider-Bereich
        self.gpu_widgets = []
        self.sliders_layout = QVBoxLayout()
        layout.addLayout(self.sliders_layout)
        
        layout.addStretch()
        
        # Apply Button
        self.apply_btn = QPushButton("✅ Einstellungen anwenden")
        self.apply_btn.setStyleSheet(f"background-color: {COLORS['button_success']}; padding: 12px;")
        self.apply_btn.clicked.connect(self.apply_manual_oc)
        layout.addWidget(self.apply_btn)
    
    def update_msi_ab_status(self):
        """Aktualisiert MSI Afterburner Status-Anzeige"""
        if not self.msi_ab_manager:
            self.msi_status_label.setText("❌ Modul nicht geladen")
            self.msi_status_label.setStyleSheet("color: #ff4444; font-weight: bold;")
            return
        
        if self.msi_ab_manager.is_installed:
            if self.msi_ab_manager.check_running():
                self.msi_status_label.setText("✅ Läuft")
                self.msi_status_label.setStyleSheet(f"color: {COLORS['accepted']}; font-weight: bold;")
            else:
                self.msi_status_label.setText("⚡ Installiert")
                self.msi_status_label.setStyleSheet(f"color: {COLORS['info']}; font-weight: bold;")
            
            self.msi_version_label.setText(self.msi_ab_manager.version or "Unknown")
            self.msi_install_btn.setEnabled(False)
            self.msi_install_btn.setText("✅ Installiert")
            self.msi_start_btn.setEnabled(True)
            self.use_msi_ab_check.setEnabled(True)
        else:
            self.msi_status_label.setText("❌ Nicht installiert")
            self.msi_status_label.setStyleSheet("color: #ffa500; font-weight: bold;")
            self.msi_version_label.setText("--")
            self.msi_install_btn.setEnabled(True)
            self.msi_start_btn.setEnabled(False)
            self.use_msi_ab_check.setEnabled(False)
            self.use_msi_ab_check.setChecked(False)
    
    def install_msi_afterburner(self):
        """Installiert MSI Afterburner"""
        if not self.msi_ab_manager:
            QMessageBox.warning(self, "Fehler", "MSI Afterburner Modul nicht verfügbar")
            return
        
        reply = QMessageBox.question(
            self, "MSI Afterburner installieren",
            "MSI Afterburner wird heruntergeladen und installiert.\n\n"
            "Dies ermöglicht Overclocking auch auf Laptops und ohne Admin-Rechte.\n\n"
            "Fortfahren?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.msi_install_btn.setText("⏳ Installiere...")
        self.msi_install_btn.setEnabled(False)
        QApplication.processEvents()
        
        def progress_callback(percent, message):
            self.msi_install_btn.setText(f"⏳ {message}")
            QApplication.processEvents()
        
        success, message = self.msi_ab_manager.download_and_install(progress_callback)
        
        if success:
            QMessageBox.information(self, "Erfolg", message)
        else:
            QMessageBox.warning(self, "Installation", message)
        
        self.update_msi_ab_status()
    
    def start_msi_afterburner(self):
        """Startet MSI Afterburner"""
        if not self.msi_ab_manager:
            return
        
        if self.msi_ab_manager.check_running():
            QMessageBox.information(self, "Info", "MSI Afterburner läuft bereits!")
            return
        
        if self.msi_ab_manager.start_afterburner(minimized=True):
            QMessageBox.information(self, "Gestartet", "MSI Afterburner wurde gestartet!")
        else:
            QMessageBox.warning(self, "Fehler", "MSI Afterburner konnte nicht gestartet werden")
        
        self.update_msi_ab_status()
    
    def check_msi_update(self):
        """Prüft auf MSI Afterburner Updates"""
        if not self.msi_ab_manager:
            return
        
        update_available, current, latest = self.msi_ab_manager.check_for_updates()
        
        if update_available:
            reply = QMessageBox.question(
                self, "Update verfügbar",
                f"Aktuelle Version: {current}\n"
                f"Neueste Version: {latest}\n\n"
                "Website öffnen zum Download?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open("https://www.msi.com/Landing/afterburner/graphics-cards")
        else:
            QMessageBox.information(
                self, "Kein Update",
                f"MSI Afterburner ist aktuell (v{current})"
            )
    
    def setup_gpu_sliders(self, gpu_count: int):
        """Erstellt Slider für alle GPUs"""
        # Alte Widgets entfernen
        for widget in self.gpu_widgets:
            widget.deleteLater()
        self.gpu_widgets.clear()
        
        for i in range(gpu_count):
            group = QGroupBox(f"GPU {i}")
            group_layout = QGridLayout(group)
            
            info = self.oc_manager.get_gpu_info(i) if self.oc_manager else None
            name = info.name if info else f"GPU {i}"
            
            group.setTitle(f"GPU {i}: {name}")
            
            # Core Offset
            group_layout.addWidget(QLabel("Core Offset:"), 0, 0)
            core_slider = QSlider(Qt.Horizontal)
            core_slider.setRange(-500, 500)
            core_slider.setValue(0)
            core_label = QLabel("0 MHz")
            core_slider.valueChanged.connect(lambda v, l=core_label: l.setText(f"{v:+d} MHz"))
            group_layout.addWidget(core_slider, 0, 1)
            group_layout.addWidget(core_label, 0, 2)
            
            # Memory Offset
            group_layout.addWidget(QLabel("Memory Offset:"), 1, 0)
            mem_slider = QSlider(Qt.Horizontal)
            mem_slider.setRange(0, 2000)
            mem_slider.setValue(0)
            mem_label = QLabel("0 MHz")
            mem_slider.valueChanged.connect(lambda v, l=mem_label: l.setText(f"+{v} MHz"))
            group_layout.addWidget(mem_slider, 1, 1)
            group_layout.addWidget(mem_label, 1, 2)
            
            # Power Limit
            group_layout.addWidget(QLabel("Power Limit:"), 2, 0)
            power_slider = QSlider(Qt.Horizontal)
            power_slider.setRange(50, 100)
            power_slider.setValue(100)
            power_label = QLabel("100%")
            power_slider.valueChanged.connect(lambda v, l=power_label: l.setText(f"{v}%"))
            group_layout.addWidget(power_slider, 2, 1)
            group_layout.addWidget(power_label, 2, 2)
            
            self.sliders_layout.addWidget(group)
            self.gpu_widgets.append(group)
            
            # Slider speichern für späteren Zugriff
            group.core_slider = core_slider
            group.mem_slider = mem_slider
            group.power_slider = power_slider
    
    def apply_auto_oc(self):
        """Wendet Auto-OC von hashrate.no an"""
        coin = self.coin_combo.currentText()
        
        # MSI Afterburner bevorzugt
        if self.use_msi_ab_check.isChecked() and self.msi_ab_manager and self.msi_ab_manager.is_installed:
            success, msg = self.msi_ab_manager.apply_mining_profile(coin)
            if success:
                QMessageBox.information(self, "Auto-OC (MSI AB)", f"✅ {msg}")
                return
            else:
                logger.warning(f"MSI AB fehlgeschlagen: {msg}, versuche NVML...")
        
        # Fallback: NVML
        if self.oc_manager:
            success = self.oc_manager.apply_auto_oc_all(coin)
            if success:
                QMessageBox.information(self, "Auto-OC", f"Overclocking für {coin} angewendet!")
            else:
                QMessageBox.warning(self, "Auto-OC", "Fehler beim Anwenden des Overclockings\n\n"
                    "Tipp: Installiere MSI Afterburner für OC auf Laptops!")
    
    def apply_manual_oc(self):
        """Wendet manuelle OC-Einstellungen an"""
        if not self.gpu_widgets:
            QMessageBox.warning(self, "Fehler", "Keine GPUs gefunden!")
            return
        
        # Werte aus Slidern holen
        for i, group in enumerate(self.gpu_widgets):
            core = group.core_slider.value()
            mem = group.mem_slider.value()
            power = group.power_slider.value()
            
            # MSI Afterburner bevorzugt
            if self.use_msi_ab_check.isChecked() and self.msi_ab_manager and self.msi_ab_manager.is_installed:
                success, msg = self.msi_ab_manager.apply_oc_direct(
                    gpu_index=i,
                    core_offset=core,
                    memory_offset=mem,
                    power_limit=power
                )
                if success:
                    logger.info(f"GPU {i}: MSI AB OC - {msg}")
                    continue
            
            # Fallback: NVML
            if self.oc_manager:
                self.oc_manager.set_power_limit_percent(i, power)
                self.oc_manager.set_clock_offset(i, core, mem)
        
        QMessageBox.information(self, "OC", "Overclocking-Einstellungen angewendet!")
    
    def reset_all(self):
        """Setzt alle GPUs auf Default"""
        # MSI Afterburner Reset
        if self.use_msi_ab_check.isChecked() and self.msi_ab_manager and self.msi_ab_manager.is_installed:
            success, msg = self.msi_ab_manager.reset_oc()
            if success:
                logger.info(f"MSI AB Reset: {msg}")
        
        # NVML Reset
        if self.oc_manager:
            self.oc_manager.reset_all_gpus()
        
        # Slider zurücksetzen
        for group in self.gpu_widgets:
            group.core_slider.setValue(0)
            group.mem_slider.setValue(0)
            group.power_slider.setValue(100)
        
        QMessageBox.information(self, "Reset", "Alle GPUs auf Default zurückgesetzt!")


class LogsTab(QWidget):
    """Logs Tab - Miner-Output"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Controls
        controls = QHBoxLayout()
        
        self.auto_scroll_check = QCheckBox("Auto-Scroll")
        self.auto_scroll_check.setChecked(True)
        controls.addWidget(self.auto_scroll_check)
        
        self.clear_btn = QPushButton("🗑️ Leeren")
        self.clear_btn.clicked.connect(self.clear_logs)
        controls.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("💾 Exportieren")
        self.export_btn.clicked.connect(self.export_logs)
        controls.addWidget(self.export_btn)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Log-Anzeige
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet(f"""
            background-color: {COLORS['background_dark']};
            font-family: 'Consolas', monospace;
            font-size: 11px;
        """)
        layout.addWidget(self.log_view)
    
    def append_log(self, text: str):
        """Fügt Log-Zeile hinzu"""
        # Farbcodierung
        if 'error' in text.lower() or 'fail' in text.lower():
            text = f"<span style='color:{COLORS['error']}'>{text}</span>"
        elif 'warn' in text.lower():
            text = f"<span style='color:{COLORS['warning']}'>{text}</span>"
        elif 'accepted' in text.lower():
            text = f"<span style='color:{COLORS['accepted']}'>{text}</span>"
        
        self.log_view.append(text)
        
        if self.auto_scroll_check.isChecked():
            self.log_view.verticalScrollBar().setValue(
                self.log_view.verticalScrollBar().maximum()
            )
    
    def clear_logs(self):
        self.log_view.clear()
    
    def export_logs(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Logs exportieren", "mining_log.txt", "Text Files (*.txt)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.log_view.toPlainText())


class HardwareTab(QWidget):
    """
    Hardware Tab - Zeigt alle erkannten GPUs/CPUs und hashrate.no Daten
    
    Features:
    - Automatische Hardware-Erkennung
    - Synchronisation mit hashrate.no
    - Beste Coins pro GPU anzeigen
    - OC-Settings aus der Datenbank
    """
    
    sync_completed = Signal(dict)
    
    def __init__(self, hardware_db=None, parent=None):
        super().__init__(parent)
        self.hardware_db = hardware_db
        self.setup_ui()
    
    def set_hardware_db(self, db):
        """Setzt die Hardware-Datenbank"""
        self.hardware_db = db
        self.refresh_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        header_label = QLabel("🖥️ Hardware-Datenbank")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(header_label)
        
        # Buttons
        self.detect_btn = QPushButton("🔍 Hardware erkennen")
        self.detect_btn.clicked.connect(self.detect_hardware)
        header_layout.addWidget(self.detect_btn)
        
        self.sync_btn = QPushButton("🔄 Mit hashrate.no synchronisieren")
        self.sync_btn.clicked.connect(self.sync_with_hashrate_no)
        header_layout.addWidget(self.sync_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # === STATISTIKEN ===
        stats_group = QGroupBox("📊 Statistiken")
        stats_layout = QGridLayout(stats_group)
        
        stats_layout.addWidget(QLabel("GPUs:"), 0, 0)
        self.gpus_count_label = QLabel("0")
        self.gpus_count_label.setStyleSheet(f"font-weight: bold; color: {COLORS['hashrate']};")
        stats_layout.addWidget(self.gpus_count_label, 0, 1)
        
        stats_layout.addWidget(QLabel("CPUs:"), 0, 2)
        self.cpus_count_label = QLabel("0")
        self.cpus_count_label.setStyleSheet(f"font-weight: bold; color: {COLORS['info']};")
        stats_layout.addWidget(self.cpus_count_label, 0, 3)
        
        stats_layout.addWidget(QLabel("Benchmarks:"), 0, 4)
        self.benchmarks_label = QLabel("0")
        self.benchmarks_label.setStyleSheet(f"font-weight: bold; color: {COLORS['efficiency']};")
        stats_layout.addWidget(self.benchmarks_label, 0, 5)
        
        stats_layout.addWidget(QLabel("Letzter Sync:"), 0, 6)
        self.last_sync_label = QLabel("Nie")
        self.last_sync_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        stats_layout.addWidget(self.last_sync_label, 0, 7)
        
        layout.addWidget(stats_group)
        
        # === GPU TABELLE ===
        gpu_group = QGroupBox("🎮 Erkannte GPUs")
        gpu_layout = QVBoxLayout(gpu_group)
        
        self.gpu_table = QTableWidget()
        self.gpu_table.setColumnCount(7)
        self.gpu_table.setHorizontalHeaderLabels([
            "GPU", "Vendor", "VRAM", "TDP", "Algorithmen", "Letzter Sync", "Aktionen"
        ])
        self.gpu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gpu_table.setAlternatingRowColors(True)
        self.gpu_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        gpu_layout.addWidget(self.gpu_table)
        
        layout.addWidget(gpu_group)
        
        # === CPU TABELLE ===
        cpu_group = QGroupBox("💻 Erkannte CPUs")
        cpu_layout = QVBoxLayout(cpu_group)
        
        self.cpu_table = QTableWidget()
        self.cpu_table.setColumnCount(5)
        self.cpu_table.setHorizontalHeaderLabels([
            "CPU", "Vendor", "Cores/Threads", "Boost Clock", "Algorithmen"
        ])
        self.cpu_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cpu_table.setAlternatingRowColors(True)
        cpu_layout.addWidget(self.cpu_table)
        
        layout.addWidget(cpu_group)
        
        # === BESTE COINS SEKTION ===
        coins_group = QGroupBox("💰 Beste Coins für ausgewählte GPU")
        coins_layout = QVBoxLayout(coins_group)
        
        # GPU Auswahl
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("GPU auswählen:"))
        self.gpu_select_combo = QComboBox()
        self.gpu_select_combo.currentTextChanged.connect(self.on_gpu_selected)
        select_layout.addWidget(self.gpu_select_combo)
        select_layout.addStretch()
        coins_layout.addLayout(select_layout)
        
        # Coins Tabelle
        self.coins_table = QTableWidget()
        self.coins_table.setColumnCount(7)
        self.coins_table.setHorizontalHeaderLabels([
            "Coin", "Algorithmus", "Hashrate", "Power", "Effizienz", "OC-Settings", "Status"
        ])
        self.coins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.coins_table.setAlternatingRowColors(True)
        coins_layout.addWidget(self.coins_table)
        
        layout.addWidget(coins_group)
        
        # Initial laden
        QTimer.singleShot(500, self.refresh_data)
    
    def refresh_data(self):
        """Aktualisiert alle Daten"""
        if not self.hardware_db:
            return
        
        # Statistiken
        stats = self.hardware_db.get_stats()
        self.gpus_count_label.setText(str(stats['gpus_count']))
        self.cpus_count_label.setText(str(stats['cpus_count']))
        self.benchmarks_label.setText(str(stats['total_benchmarks']))
        self.last_sync_label.setText(stats['last_sync'])
        
        # GPU Tabelle - filtere mining-fähige GPUs (>= 2GB VRAM)
        all_gpus = self.hardware_db.get_all_gpus()
        mining_gpus = [gpu for gpu in all_gpus if gpu.vram_mb >= 2048]  # Min 2GB für Mining
        igpus = [gpu for gpu in all_gpus if gpu.vram_mb < 2048]  # iGPUs ausfiltern
        
        if igpus:
            igpu_names = ", ".join(g.name for g in igpus)
            logger.info(f"iGPUs gefunden (nicht mining-fähig): {igpu_names}")
        
        self.gpu_table.setRowCount(len(mining_gpus))
        self.gpu_select_combo.clear()
        
        for row, gpu in enumerate(mining_gpus):
            self.gpu_table.setItem(row, 0, QTableWidgetItem(gpu.name))
            self.gpu_table.setItem(row, 1, QTableWidgetItem(gpu.vendor))
            self.gpu_table.setItem(row, 2, QTableWidgetItem(f"{gpu.vram_mb} MB"))
            self.gpu_table.setItem(row, 3, QTableWidgetItem(f"{gpu.tdp_watts} W"))
            self.gpu_table.setItem(row, 4, QTableWidgetItem(str(len(gpu.supported_algorithms))))
            self.gpu_table.setItem(row, 5, QTableWidgetItem(gpu.last_sync or "Nie"))
            
            # Details Button
            details_btn = QPushButton("📋 Details")
            details_btn.clicked.connect(lambda checked, g=gpu: self.show_gpu_details(g))
            self.gpu_table.setCellWidget(row, 6, details_btn)
            
            # Für Combo
            self.gpu_select_combo.addItem(gpu.name)
        
        # GPU Count aktualisieren (nur mining-fähige)
        self.gpus_count_label.setText(str(len(mining_gpus)))
        
        # CPU Tabelle
        cpus = self.hardware_db.get_all_cpus()
        self.cpu_table.setRowCount(len(cpus))
        
        for row, cpu in enumerate(cpus):
            self.cpu_table.setItem(row, 0, QTableWidgetItem(cpu.name))
            self.cpu_table.setItem(row, 1, QTableWidgetItem(cpu.vendor))
            self.cpu_table.setItem(row, 2, QTableWidgetItem(f"{cpu.cores}/{cpu.threads}"))
            self.cpu_table.setItem(row, 3, QTableWidgetItem(f"{cpu.boost_clock_mhz} MHz"))
            # CPU Mining: RandomX für Monero/Zephyr
            cpu_algos = cpu.supported_algorithms if cpu.supported_algorithms else ["randomx"]
            self.cpu_table.setItem(row, 4, QTableWidgetItem(", ".join(cpu_algos) if cpu_algos else "randomx"))
        
        # Erste GPU auswählen
        if mining_gpus:
            self.on_gpu_selected(mining_gpus[0].name)
    
    def detect_hardware(self):
        """Erkennt Hardware neu"""
        if not self.hardware_db:
            QMessageBox.warning(self, "Fehler", "Hardware-DB nicht verfügbar")
            return
        
        self.detect_btn.setText("⏳ Erkenne...")
        self.detect_btn.setEnabled(False)
        QApplication.processEvents()
        
        gpus, cpus = self.hardware_db.detect_all_hardware()
        
        self.detect_btn.setText("🔍 Hardware erkennen")
        self.detect_btn.setEnabled(True)
        
        self.refresh_data()
        
        QMessageBox.information(
            self, "Hardware erkannt",
            f"Gefunden:\n• {len(gpus)} GPUs\n• {len(cpus)} CPUs"
        )
    
    def sync_with_hashrate_no(self):
        """Synchronisiert mit hashrate.no"""
        if not self.hardware_db:
            QMessageBox.warning(self, "Fehler", "Hardware-DB nicht verfügbar")
            return
        
        self.sync_btn.setText("⏳ Synchronisiere...")
        self.sync_btn.setEnabled(False)
        QApplication.processEvents()
        
        results = self.hardware_db.sync_with_hashrate_no(force=True)
        
        self.sync_btn.setText("🔄 Mit hashrate.no synchronisieren")
        self.sync_btn.setEnabled(True)
        
        self.refresh_data()
        
        # Ergebnis anzeigen
        msg = f"Synchronisation abgeschlossen!\n\n"
        msg += f"• GPUs synchronisiert: {results['gpus_synced']}\n"
        msg += f"• Coins/Algorithmen: {results['coins_found']}\n"
        
        if results['new_profitable_coins']:
            msg += f"\n🆕 Neue profitable Coins gefunden: {len(results['new_profitable_coins'])}"
        
        if results['errors']:
            msg += f"\n\n⚠️ Fehler: {len(results['errors'])}"
        
        QMessageBox.information(self, "Sync Ergebnis", msg)
        
        self.sync_completed.emit(results)
    
    def on_gpu_selected(self, gpu_name: str):
        """Zeigt beste Coins für ausgewählte GPU"""
        if not self.hardware_db or not gpu_name:
            return
        
        # Beste Coins holen
        best_coins = self.hardware_db.get_best_coins_for_gpu(gpu_name, top_n=15)
        
        self.coins_table.setRowCount(len(best_coins))
        
        for row, coin in enumerate(best_coins):
            self.coins_table.setItem(row, 0, QTableWidgetItem(coin['coin']))
            self.coins_table.setItem(row, 1, QTableWidgetItem(coin['algorithm']))
            self.coins_table.setItem(row, 2, QTableWidgetItem(
                f"{coin['hashrate']:.2f} {coin['hashrate_unit']}"
            ))
            self.coins_table.setItem(row, 3, QTableWidgetItem(f"{coin['power_watts']:.0f} W"))
            
            # Effizienz mit Farbe
            eff_item = QTableWidgetItem(f"{coin['efficiency']:.4f}")
            if coin['efficiency'] > 0.1:
                eff_item.setForeground(QColor(COLORS['accepted']))
            self.coins_table.setItem(row, 4, eff_item)
            
            # OC Settings
            oc = coin['oc_settings']
            oc_text = f"Core: {oc['core_offset']:+d}, Mem: {oc['memory_offset']:+d}, PL: {oc['power_limit']}%"
            self.coins_table.setItem(row, 5, QTableWidgetItem(oc_text))
            
            # Status
            status_item = QTableWidgetItem("✅ Verifiziert" if coin.get('verified') else "📊 Daten")
            self.coins_table.setItem(row, 6, status_item)
    
    def show_gpu_details(self, gpu):
        """Zeigt GPU-Details"""
        msg = f"GPU: {gpu.name}\n"
        msg += f"=" * 50 + "\n\n"
        msg += f"Vendor: {gpu.vendor}\n"
        msg += f"Model: {gpu.model}\n"
        msg += f"VRAM: {gpu.vram_mb} MB\n"
        msg += f"TDP: {gpu.tdp_watts} W\n"
        msg += f"Boost Clock: {gpu.boost_clock_mhz} MHz\n"
        msg += f"Memory Clock: {gpu.memory_clock_mhz} MHz\n"
        msg += f"Driver: {gpu.driver_version}\n"
        msg += f"PCI Bus: {gpu.pci_bus}\n\n"
        msg += f"Unterstützte Algorithmen: {len(gpu.supported_algorithms)}\n"
        
        if gpu.supported_algorithms:
            msg += f"  {', '.join(gpu.supported_algorithms[:10])}"
            if len(gpu.supported_algorithms) > 10:
                msg += f" ... (+{len(gpu.supported_algorithms) - 10})"
        
        msg += f"\n\nLetzter Sync: {gpu.last_sync or 'Nie'}"
        msg += f"\nErkannt: {gpu.detected_at or 'Unbekannt'}"
        
        QMessageBox.information(self, f"GPU Details: {gpu.name}", msg)


class SettingsTab(QWidget):
    """Settings Tab"""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Worker Settings
        worker_group = QGroupBox("Worker Einstellungen")
        worker_layout = QGridLayout(worker_group)
        
        worker_layout.addWidget(QLabel("Worker Name:"), 0, 0)
        self.worker_name_edit = QLineEdit("Rig_D")
        worker_layout.addWidget(self.worker_name_edit, 0, 1)
        
        worker_layout.addWidget(QLabel("GPU Power (W):"), 1, 0)
        self.gpu_power_spin = QSpinBox()
        self.gpu_power_spin.setRange(50, 500)
        self.gpu_power_spin.setValue(200)
        worker_layout.addWidget(self.gpu_power_spin, 1, 1)
        
        worker_layout.addWidget(QLabel("Stromkosten (€/kWh):"), 2, 0)
        self.electricity_spin = QDoubleSpinBox()
        self.electricity_spin.setRange(0, 1)
        self.electricity_spin.setDecimals(3)
        self.electricity_spin.setValue(0.30)
        worker_layout.addWidget(self.electricity_spin, 2, 1)
        
        layout.addWidget(worker_group)
        
        # Profit Switching
        switch_group = QGroupBox("Profit Switching")
        switch_layout = QGridLayout(switch_group)
        
        switch_layout.addWidget(QLabel("Wechsel-Intervall (Min):"), 0, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(15)
        switch_layout.addWidget(self.interval_spin, 0, 1)
        
        switch_layout.addWidget(QLabel("Min. Profit-Differenz (%):"), 1, 0)
        self.profit_diff_spin = QSpinBox()
        self.profit_diff_spin.setRange(0, 50)
        self.profit_diff_spin.setValue(5)
        switch_layout.addWidget(self.profit_diff_spin, 1, 1)
        
        self.auto_switch_check = QCheckBox("Automatisches Coin-Switching")
        self.auto_switch_check.setChecked(False)
        switch_layout.addWidget(self.auto_switch_check, 2, 0, 1, 2)
        
        layout.addWidget(switch_group)
        
        # hashrate.no API
        api_group = QGroupBox("hashrate.no API")
        api_layout = QGridLayout(api_group)
        
        api_layout.addWidget(QLabel("API Key:"), 0, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("Optional - für Live-Daten von hashrate.no")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_layout.addWidget(self.api_key_edit, 0, 1)
        
        api_info = QLabel("Kostenloser Key: Registriere dich auf hashrate.no")
        api_info.setStyleSheet(f"color: {COLORS['text_muted']};")
        api_layout.addWidget(api_info, 1, 0, 1, 2)
        
        layout.addWidget(api_group)
        
        # Alerts
        alert_group = QGroupBox("Benachrichtigungen")
        alert_layout = QGridLayout(alert_group)
        
        alert_layout.addWidget(QLabel("Temp-Warnung (°C):"), 0, 0)
        self.temp_warn_spin = QSpinBox()
        self.temp_warn_spin.setRange(50, 100)
        self.temp_warn_spin.setValue(80)
        alert_layout.addWidget(self.temp_warn_spin, 0, 1)
        
        self.notifications_check = QCheckBox("Desktop-Benachrichtigungen")
        self.notifications_check.setChecked(True)
        alert_layout.addWidget(self.notifications_check, 1, 0, 1, 2)
        
        self.minimize_to_tray_check = QCheckBox("In System Tray minimieren")
        self.minimize_to_tray_check.setChecked(True)
        alert_layout.addWidget(self.minimize_to_tray_check, 2, 0, 1, 2)
        
        layout.addWidget(alert_group)
        
        layout.addStretch()
        
        # Save Button
        self.save_btn = QPushButton("💾 Einstellungen speichern")
        self.save_btn.setStyleSheet(f"background-color: {COLORS['button_success']}; padding: 12px;")
        self.save_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_btn)
    
    def save_settings(self):
        settings = {
            'worker_name': self.worker_name_edit.text(),
            'gpu_power': self.gpu_power_spin.value(),
            'electricity_cost': self.electricity_spin.value(),
            'switch_interval': self.interval_spin.value(),
            'min_profit_diff': self.profit_diff_spin.value(),
            'auto_switch': self.auto_switch_check.isChecked(),
            'api_key': self.api_key_edit.text(),
            'temp_warning': self.temp_warn_spin.value(),
            'notifications': self.notifications_check.isChecked(),
            'minimize_to_tray': self.minimize_to_tray_check.isChecked(),
        }
        self.settings_changed.emit(settings)
        QMessageBox.information(self, "Gespeichert", "Einstellungen wurden gespeichert!")


class WalletsTab(QWidget):
    """Wallets & Börsen Tab - Konfiguration von Exchange APIs und Wallet-Adressen"""
    
    wallet_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.exchange_manager = None
        self.setup_ui()
        self.load_exchange_manager()
    
    def load_exchange_manager(self):
        """Lädt den Exchange Manager"""
        try:
            from exchange_api import ExchangeManager, get_supported_exchanges, get_mining_coins, EXCHANGE_CLASSES
            self.exchange_manager = ExchangeManager()
            self.supported_exchanges = get_supported_exchanges()
            self.mining_coins = get_mining_coins()
            self.exchange_classes = EXCHANGE_CLASSES
            self.refresh_exchanges_list()
            self.refresh_wallets_list()
        except ImportError as e:
            logger.error(f"Exchange API nicht verfügbar: {e}")
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # === OBEN: Börsen-Status Karten ===
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        
        # CoinEx Karte
        self.coinex_card = QFrame()
        self.coinex_card.setFrameStyle(QFrame.Box)
        self.coinex_card.setStyleSheet(f"background-color: {COLORS['card_bg']}; border-radius: 8px; padding: 10px;")
        coinex_layout = QVBoxLayout(self.coinex_card)
        self.coinex_status = QLabel("🔵 CoinEx")
        self.coinex_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #2196F3;")
        self.coinex_wallets = QLabel("📦 0 Wallets")
        coinex_layout.addWidget(self.coinex_status)
        coinex_layout.addWidget(self.coinex_wallets)
        status_layout.addWidget(self.coinex_card)
        
        # Gate.io Karte
        self.gateio_card = QFrame()
        self.gateio_card.setFrameStyle(QFrame.Box)
        self.gateio_card.setStyleSheet(f"background-color: {COLORS['card_bg']}; border-radius: 8px; padding: 10px;")
        gateio_layout = QVBoxLayout(self.gateio_card)
        self.gateio_status = QLabel("🟢 Gate.io")
        self.gateio_status.setStyleSheet("font-size: 14px; font-weight: bold; color: #4CAF50;")
        self.gateio_wallets = QLabel("📦 0 Wallets")
        gateio_layout.addWidget(self.gateio_status)
        gateio_layout.addWidget(self.gateio_wallets)
        status_layout.addWidget(self.gateio_card)
        
        # Börse hinzufügen Button
        add_card = QFrame()
        add_card.setFrameStyle(QFrame.Box)
        add_card.setStyleSheet(f"background-color: {COLORS['card_bg']}; border-radius: 8px; padding: 10px;")
        add_layout = QVBoxLayout(add_card)
        self.show_add_form_btn = QPushButton("➕ Börse hinzufügen")
        self.show_add_form_btn.setStyleSheet(f"background-color: {COLORS['button_success']}; padding: 8px;")
        self.show_add_form_btn.clicked.connect(self.toggle_add_form)
        add_layout.addWidget(self.show_add_form_btn)
        self.fetch_all_btn = QPushButton("🔄 Alle Wallets laden")
        self.fetch_all_btn.clicked.connect(self.fetch_all_wallets)
        add_layout.addWidget(self.fetch_all_btn)
        status_layout.addWidget(add_card)
        
        main_layout.addWidget(status_widget)
        
        # === Börse hinzufügen Formular (versteckt) ===
        self.add_form_widget = QWidget()
        self.add_form_widget.setVisible(False)
        add_form_layout = QHBoxLayout(self.add_form_widget)
        add_form_layout.setContentsMargins(0, 0, 0, 0)
        
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["CoinEx", "Gate.io", "Binance", "Kraken", "KuCoin"])
        add_form_layout.addWidget(QLabel("Börse:"))
        add_form_layout.addWidget(self.exchange_combo)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("API Key")
        add_form_layout.addWidget(self.api_key_edit)
        
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setPlaceholderText("API Secret")
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        add_form_layout.addWidget(self.api_secret_edit)
        
        self.passphrase_edit = QLineEdit()
        self.passphrase_edit.setPlaceholderText("Passphrase (optional)")
        self.passphrase_edit.setEchoMode(QLineEdit.Password)
        add_form_layout.addWidget(self.passphrase_edit)
        
        self.add_exchange_btn = QPushButton("✅ Hinzufügen")
        self.add_exchange_btn.clicked.connect(self.add_exchange)
        add_form_layout.addWidget(self.add_exchange_btn)
        
        main_layout.addWidget(self.add_form_widget)
        
        # === MITTE: Splitter mit Coin-Zuordnung & Wallets ===
        splitter = QSplitter(Qt.Horizontal)
        
        # --- LINKS: Coin-Börsen-Zuordnung ---
        coin_widget = QWidget()
        coin_layout = QVBoxLayout(coin_widget)
        coin_layout.setContentsMargins(0, 0, 5, 0)
        
        coin_header = QLabel("📊 Coin → Börse (Klick zum Ändern)")
        coin_header.setStyleSheet("font-size: 13px; font-weight: bold;")
        coin_layout.addWidget(coin_header)
        
        self.coin_exchange_table = QTableWidget()
        self.coin_exchange_table.setColumnCount(4)
        self.coin_exchange_table.setHorizontalHeaderLabels(['Coin', 'CoinEx', 'Gate.io', 'Favorit'])
        self.coin_exchange_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.coin_exchange_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.coin_exchange_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.coin_exchange_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.coin_exchange_table.verticalHeader().setVisible(False)
        self.coin_exchange_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.coin_exchange_table.cellClicked.connect(self.on_coin_exchange_click)
        coin_layout.addWidget(self.coin_exchange_table)
        
        splitter.addWidget(coin_widget)
        
        # --- RECHTS: Wallet-Adressen ---
        wallet_widget = QWidget()
        wallet_layout = QVBoxLayout(wallet_widget)
        wallet_layout.setContentsMargins(5, 0, 0, 0)
        
        wallet_header = QLabel("💰 Wallet-Adressen")
        wallet_header.setStyleSheet("font-size: 13px; font-weight: bold;")
        wallet_layout.addWidget(wallet_header)
        
        self.wallets_table = QTableWidget()
        self.wallets_table.setColumnCount(3)
        self.wallets_table.setHorizontalHeaderLabels(['Coin', 'Adresse', 'Quelle'])
        self.wallets_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.wallets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.wallets_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.wallets_table.verticalHeader().setVisible(False)
        self.wallets_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        wallet_layout.addWidget(self.wallets_table)
        
        # Manuelle Wallet (kompakt)
        manual_layout = QHBoxLayout()
        self.wallet_coin_combo = QComboBox()
        self.wallet_coin_combo.setEditable(True)
        self.wallet_coin_combo.addItems(["RVN", "ERG", "GRIN", "BEAM", "KAS", "FLUX"])
        self.wallet_coin_combo.setMinimumWidth(70)
        manual_layout.addWidget(self.wallet_coin_combo)
        
        self.wallet_address_edit = QLineEdit()
        self.wallet_address_edit.setPlaceholderText("Wallet-Adresse eingeben...")
        manual_layout.addWidget(self.wallet_address_edit, 1)
        
        self.wallet_memo_edit = QLineEdit()
        self.wallet_memo_edit.setPlaceholderText("Memo")
        self.wallet_memo_edit.setMaximumWidth(80)
        manual_layout.addWidget(self.wallet_memo_edit)
        
        self.save_wallet_btn = QPushButton("💾")
        self.save_wallet_btn.setMaximumWidth(40)
        self.save_wallet_btn.clicked.connect(self.save_manual_wallet)
        manual_layout.addWidget(self.save_wallet_btn)
        
        wallet_layout.addLayout(manual_layout)
        splitter.addWidget(wallet_widget)
        
        # Splitter-Proportionen
        splitter.setSizes([400, 600])
        main_layout.addWidget(splitter, 1)
        
        # Dummy für altes Interface
        self.add_manual_btn = QPushButton()
        self.exchanges_table = QTableWidget()
        
        # Favoriten-Daten initialisieren
        self.coin_favorites = {}
        self.load_coin_favorites()
    
    def toggle_add_form(self):
        """Zeigt/versteckt das Börse-hinzufügen Formular"""
        self.add_form_widget.setVisible(not self.add_form_widget.isVisible())
    
    def refresh_exchanges_list(self):
        """Aktualisiert die Börsen-Liste - zeigt nur aktive Börsen"""
        if not self.exchange_manager:
            return
        
        # Wallet-Quellen aus wallets.json laden
        wallet_sources = {}
        try:
            import json
            from pathlib import Path
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallet_sources = data.get("wallet_sources", {})
        except Exception as e:
            logger.debug(f"Fehler beim Laden von wallets.json: {e}")
        
        # Zähle Wallets pro Börse
        exchange_wallet_counts = {'coinex': 0, 'gateio': 0}
        for coin, source in wallet_sources.items():
            source_key = source.lower().replace(".", "").replace(" ", "")
            if "coinex" in source_key:
                exchange_wallet_counts['coinex'] += 1
            elif "gate" in source_key:
                exchange_wallet_counts['gateio'] += 1
        
        # Karten aktualisieren
        coinex_count = exchange_wallet_counts.get('coinex', 0)
        gateio_count = exchange_wallet_counts.get('gateio', 0)
        
        # CoinEx Karte
        try:
            from coinex_api import CoinExAPI
            coinex = CoinExAPI()
            if coinex.is_configured():
                self.coinex_status.setText("🔵 CoinEx ✅")
                self.coinex_wallets.setText(f"📦 {coinex_count} Wallets")
            else:
                self.coinex_status.setText("🔵 CoinEx ⚠️")
                self.coinex_wallets.setText("Nicht konfiguriert")
        except:
            self.coinex_status.setText("🔵 CoinEx ❌")
            self.coinex_wallets.setText("Fehler")
        
        # Gate.io Karte
        try:
            from gateio_api import GateIOAPI
            gateio = GateIOAPI()
            if gateio.is_configured():
                self.gateio_status.setText("🟢 Gate.io ✅")
                self.gateio_wallets.setText(f"📦 {gateio_count} Wallets")
            else:
                self.gateio_status.setText("🟢 Gate.io ⚠️")
                self.gateio_wallets.setText("Nicht konfiguriert")
        except:
            self.gateio_status.setText("🟢 Gate.io ❌")
            self.gateio_wallets.setText("Fehler")
        
        # Coin-Exchange-Tabelle auch aktualisieren
        self.refresh_coin_exchange_table()
    
    def refresh_wallets_list(self):
        """Aktualisiert die Wallets-Liste direkt aus wallets.json"""
        import json
        from pathlib import Path
        
        # Wallet-Daten aus wallets.json laden
        wallets_data = {}
        wallet_sources = {}
        try:
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallets_data = data.get("wallets", {})
                    wallet_sources = data.get("wallet_sources", {})
        except Exception as e:
            logger.error(f"Fehler beim Laden von wallets.json: {e}")
        
        # Sortierte Liste erstellen
        wallet_list = sorted(wallets_data.items(), key=lambda x: x[0])
        self.wallets_table.setRowCount(len(wallet_list))
        
        for row, (coin, address) in enumerate(wallet_list):
            # Coin
            coin_item = QTableWidgetItem(coin)
            coin_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.wallets_table.setItem(row, 0, coin_item)
            
            # Adresse (gekürzt)
            if len(address) > 40:
                addr_display = address[:20] + "..." + address[-15:]
            else:
                addr_display = address
            addr_item = QTableWidgetItem(addr_display)
            addr_item.setToolTip(address)  # Volle Adresse als Tooltip
            self.wallets_table.setItem(row, 1, addr_item)
            
            # Quelle aus wallet_sources
            source = wallet_sources.get(coin, 'Manual')
            source_item = QTableWidgetItem(source)
            # Farbe je nach Quelle
            if source == "Gate.io":
                source_item.setForeground(QColor("#4CAF50"))  # Grün
            elif source == "CoinEx":
                source_item.setForeground(QColor("#2196F3"))  # Blau
            self.wallets_table.setItem(row, 2, source_item)
    
    def load_coin_favorites(self):
        """Lädt gespeicherte Favoriten aus wallets.json"""
        try:
            import json
            from pathlib import Path
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.coin_favorites = data.get("coin_favorites", {})
        except:
            self.coin_favorites = {}
    
    def save_coin_favorites(self):
        """Speichert Favoriten in wallets.json"""
        try:
            import json
            from pathlib import Path
            wallets_file = Path("wallets.json")
            
            data = {}
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            data["coin_favorites"] = self.coin_favorites
            
            with open(wallets_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Fehler beim Speichern der Favoriten: {e}")
    
    def refresh_coin_exchange_table(self):
        """Füllt die Coin-Börsen-Zuordnungs-Tabelle"""
        import json
        from pathlib import Path
        
        # Wallet-Daten laden
        wallet_sources = {}
        wallets_data = {}
        try:
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallet_sources = data.get("wallet_sources", {})
                    wallets_data = data.get("wallets", {})
        except:
            pass
        
        # Coins nach Börsen gruppieren
        coinex_coins = set()
        gateio_coins = set()
        
        for coin, source in wallet_sources.items():
            source_lower = source.lower().replace(".", "").replace(" ", "")
            if source_lower == "coinex":
                coinex_coins.add(coin)
            elif source_lower == "gateio":
                gateio_coins.add(coin)
        
        # Alle Coins sammeln
        all_coins = sorted(set(wallets_data.keys()))
        
        # Gebühren-Info (typische Withdrawal Fees - Gate.io oft günstiger für größere Coins)
        # Diese werden für die automatische Favorit-Auswahl genutzt
        EXCHANGE_FEES = {
            # Gate.io bevorzugt (bessere Liquidität, oft niedrigere Gebühren)
            'gateio_preferred': ['ETH', 'BTC', 'LTC', 'BCH', 'DOGE', 'DASH', 'ZEC', 
                                 'XMR', 'KAS', 'FLUX', 'ERG', 'RVN', 'ETC', 'ALPH',
                                 'GRIN', 'BEAM', 'FIRO', 'CFX', 'KDA', 'DNX', 'XNA',
                                 'IRON', 'CLORE', 'DGB', 'ARRR', 'QTC', 'CKB'],
            # CoinEx bevorzugt (einzige Option oder bessere Konditionen)
            'coinex_preferred': ['ALEO', 'NEXA', 'RTM', 'ZEPH', 'EPIC', 'DERO', 
                                 'NEOX', 'MONA', 'VTC', 'HNS', 'KMD', 'QUAI']
        }
        
        self.coin_exchange_table.setRowCount(len(all_coins))
        
        for row, coin in enumerate(all_coins):
            # Coin-Name
            coin_item = QTableWidgetItem(coin)
            coin_item.setFont(QFont('Arial', 10, QFont.Bold))
            self.coin_exchange_table.setItem(row, 0, coin_item)
            
            # CoinEx verfügbar?
            has_coinex = coin in coinex_coins or wallet_sources.get(coin) == "CoinEx"
            coinex_item = QTableWidgetItem("✅" if has_coinex else "❌")
            coinex_item.setTextAlignment(Qt.AlignCenter)
            if has_coinex:
                coinex_item.setForeground(QColor("#2196F3"))
            else:
                coinex_item.setForeground(QColor("#666666"))
            self.coin_exchange_table.setItem(row, 1, coinex_item)
            
            # Gate.io verfügbar?
            has_gateio = coin in gateio_coins or wallet_sources.get(coin) == "Gate.io"
            gateio_item = QTableWidgetItem("✅" if has_gateio else "❌")
            gateio_item.setTextAlignment(Qt.AlignCenter)
            if has_gateio:
                gateio_item.setForeground(QColor("#4CAF50"))
            else:
                gateio_item.setForeground(QColor("#666666"))
            self.coin_exchange_table.setItem(row, 2, gateio_item)
            
            # Favorit bestimmen
            if coin in self.coin_favorites:
                # Manuell gesetzt
                favorite = self.coin_favorites[coin]
                reason = "Benutzer-Wahl"
            elif has_gateio and not has_coinex:
                favorite = "Gate.io"
                reason = "Nur dort verfügbar"
            elif has_coinex and not has_gateio:
                favorite = "CoinEx"
                reason = "Nur dort verfügbar"
            elif coin in EXCHANGE_FEES['gateio_preferred']:
                favorite = "Gate.io"
                reason = "Bessere Liquidität"
            elif coin in EXCHANGE_FEES['coinex_preferred']:
                favorite = "CoinEx"
                reason = "Niedrigere Gebühren"
            elif has_gateio:
                favorite = "Gate.io"
                reason = "Standard (bessere Liquidität)"
            elif has_coinex:
                favorite = "CoinEx"
                reason = "Standard"
            else:
                favorite = "-"
                reason = "Keine Börse"
            
            # Favorit anzeigen (mit Grund als Tooltip)
            fav_text = f"⭐ {favorite}" if favorite != "-" else "-"
            fav_item = QTableWidgetItem(fav_text)
            fav_item.setToolTip(reason)  # Grund als Tooltip
            fav_item.setTextAlignment(Qt.AlignCenter)
            if favorite == "Gate.io":
                fav_item.setForeground(QColor("#4CAF50"))
            elif favorite == "CoinEx":
                fav_item.setForeground(QColor("#2196F3"))
            self.coin_exchange_table.setItem(row, 3, fav_item)
    
    def on_coin_exchange_click(self, row: int, column: int):
        """Klick auf CoinEx oder Gate.io Spalte wechselt den Favorit"""
        if column not in [1, 2]:  # Nur CoinEx (1) oder Gate.io (2) Spalten
            return
        
        coin_item = self.coin_exchange_table.item(row, 0)
        if not coin_item:
            return
        coin = coin_item.text()
        
        coinex_item = self.coin_exchange_table.item(row, 1)
        gateio_item = self.coin_exchange_table.item(row, 2)
        
        has_coinex = coinex_item and "✅" in coinex_item.text()
        has_gateio = gateio_item and "✅" in gateio_item.text()
        
        # Neuen Favorit setzen
        if column == 1 and has_coinex:
            self.coin_favorites[coin] = "CoinEx"
            logger.info(f"Favorit für {coin} auf CoinEx gesetzt")
        elif column == 2 and has_gateio:
            self.coin_favorites[coin] = "Gate.io"
            logger.info(f"Favorit für {coin} auf Gate.io gesetzt")
        else:
            return  # Keine Änderung wenn Börse nicht verfügbar
        
        # Speichern und Tabelle aktualisieren
        self.save_coin_favorites()
        self.refresh_coin_exchange_table()
    
    def get_preferred_exchange(self, coin: str) -> str:
        """Gibt die bevorzugte Börse für einen Coin zurück"""
        if coin in self.coin_favorites:
            return self.coin_favorites[coin]
        
        # Standard-Logik
        import json
        from pathlib import Path
        
        try:
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    source = data.get("wallet_sources", {}).get(coin)
                    if source:
                        return source
        except:
            pass
        
        return "Gate.io"  # Standard-Fallback
    
    def add_exchange(self):
        """Fügt eine Börse hinzu"""
        if not self.exchange_manager:
            QMessageBox.warning(self, "Fehler", "Exchange Manager nicht verfügbar!")
            return
        
        exchange_name = self.exchange_combo.currentText().lower().replace(".", "")
        api_key = self.api_key_edit.text().strip()
        api_secret = self.api_secret_edit.text().strip()
        passphrase = self.passphrase_edit.text().strip()
        
        if not api_key or not api_secret:
            QMessageBox.warning(self, "Fehler", "API Key und Secret sind erforderlich!")
            return
        
        # Verbindung testen und hinzufügen
        self.add_exchange_btn.setText("⏳ Teste Verbindung...")
        self.add_exchange_btn.setEnabled(False)
        QApplication.processEvents()
        
        success, message = self.exchange_manager.add_exchange(
            exchange_name, api_key, api_secret, passphrase
        )
        
        self.add_exchange_btn.setText("➕ Börse hinzufügen & testen")
        self.add_exchange_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Erfolg", message)
            self.api_key_edit.clear()
            self.api_secret_edit.clear()
            self.passphrase_edit.clear()
            self.refresh_exchanges_list()
        else:
            QMessageBox.warning(self, "Fehler", message)
    
    def remove_exchange(self, exchange_id: str):
        """Entfernt eine Börse"""
        reply = QMessageBox.question(
            self, "Bestätigen",
            f"Börse {exchange_id.upper()} wirklich entfernen?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.exchange_manager.remove_exchange(exchange_id)
            self.refresh_exchanges_list()
    
    def fetch_all_wallets(self):
        """Holt alle Wallets von allen Börsen (CoinEx zuerst!)"""
        if not self.exchange_manager:
            return
        
        self.fetch_all_btn.setText("⏳ Lade Wallets...")
        self.fetch_all_btn.setEnabled(False)
        QApplication.processEvents()
        
        total_count = 0
        
        # 1. CoinEx ZUERST (vorinstalliert!)
        try:
            from coinex_api import CoinExAPI
            coinex = CoinExAPI()
            
            if coinex.is_configured():
                logger.info("Lade Wallets von CoinEx...")
                coinex_wallets = coinex.get_all_mining_wallets()
                
                for coin, data in coinex_wallets.items():
                    address = data.get('address', '')
                    if address:
                        # WICHTIG: Nur coin als Key, nicht coinex_coin!
                        from exchange_manager import WalletInfo
                        wallet = WalletInfo(
                            coin=coin.upper(),
                            address=address,
                            chain=data.get('chain', coin),
                            memo=data.get('memo', ''),
                            source='CoinEx',
                            last_sync=time.strftime('%Y-%m-%d %H:%M:%S')
                        )
                        # Speichere mit coin als Key
                        self.exchange_manager.wallets[coin.upper()] = wallet
                        total_count += 1
                
                logger.info(f"CoinEx: {total_count} Wallets geladen")
                
                # WICHTIG: Wallets sofort speichern!
                self.exchange_manager._save_wallets()
                
        except ImportError:
            logger.debug("CoinEx API nicht verfügbar")
        except Exception as e:
            logger.error(f"CoinEx Wallet-Laden Fehler: {e}")
        
        # 2. Dann andere Börsen
        try:
            other_count = self.exchange_manager.fetch_all_wallets()
            total_count += other_count
        except Exception as e:
            logger.error(f"Andere Börsen Fehler: {e}")
        
        self.fetch_all_btn.setText("🔄 Alle Wallets laden")
        self.fetch_all_btn.setEnabled(True)
        
        # Tabelle aktualisieren
        self.refresh_wallets_list()
        
        if total_count > 0:
            QMessageBox.information(self, "Fertig", f"✅ {total_count} Wallets geladen und gespeichert!")
        else:
            QMessageBox.warning(
                self, "Keine Wallets", 
                "Keine Wallets gefunden.\n\n"
                "Mögliche Ursachen:\n"
                "• CoinEx API Key ungültig/abgelaufen\n"
                "• Keine Deposit-Adressen auf CoinEx erstellt\n"
                "• Andere Börsen nicht konfiguriert\n\n"
                "Tipp: Erstelle Deposit-Adressen auf CoinEx für die Coins die du minen willst!"
            )
        
        self.wallet_updated.emit()
    
    def add_manual_wallet(self):
        """Öffnet Dialog für manuelle Wallet"""
        # Scrolle zum manuellen Bereich
        pass
    
    def save_manual_wallet(self):
        """Speichert manuell eingegebene Wallet"""
        if not self.exchange_manager:
            return
        
        coin = self.wallet_coin_combo.currentText().strip().upper()
        address = self.wallet_address_edit.text().strip()
        memo = self.wallet_memo_edit.text().strip()
        
        if not coin or not address:
            QMessageBox.warning(self, "Fehler", "Coin und Adresse sind erforderlich!")
            return
        
        self.exchange_manager.add_manual_wallet(coin, address, coin, memo)
        
        self.wallet_address_edit.clear()
        self.wallet_memo_edit.clear()
        
        self.refresh_wallets_list()
        QMessageBox.information(self, "Gespeichert", f"Wallet für {coin} gespeichert!")
        self.wallet_updated.emit()


class AutoProfitTab(QWidget):
    """
    Auto-Profit Tab - Automatischer Coin-Wechsel für maximalen Gewinn!
    
    Features:
    - Live Top 10 profitabelste Coins (REINER GEWINN ohne Strom!)
    - Automatische Pool-Auswahl
    - Auto-Switch wenn besserer Coin gefunden
    - Ständiges Testen im Hintergrund
    """
    
    switch_requested = Signal(dict)  # Signal zum Mining-Wechsel
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.profit_calc = None
        self.auto_switch_enabled = False
        self.current_coin = ""
        self.min_profit_diff = 5.0  # Mindestens 5% mehr für Wechsel
        
        # Timer für Updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_profits)
        
        self.setup_ui()
        self.load_profit_calculator()
    
    def set_current_coin(self, coin: str):
        """Setzt den aktuellen Coin (wird vom Dashboard aufgerufen)"""
        self.current_coin = coin
        self.current_coin_label.setText(coin if coin else "--")
        
        # Aktuellen Profit finden
        if coin and self.profit_calc:
            try:
                top_coins = self.profit_calc.get_most_profitable()[:20]
                for coin_data in top_coins:
                    if coin_data['coin'] == coin:
                        self.current_profit_label.setText(f"${coin_data['usd_profit_24h']:.2f}")
                        break
            except:
                pass
        
        logger.info(f"AutoProfit: Aktueller Coin = {coin}")
    
    def load_profit_calculator(self):
        """Lädt den Profit Calculator mit GPU-Erkennung"""
        try:
            from profit_calculator import get_profit_calculator
            
            # GPU-Name aus Parent (MiningDashboard) holen
            gpu_name = None
            try:
                # Versuche GPU-Name aus dem Parent zu bekommen
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'gpu_monitor') and parent.gpu_monitor:
                        gpus = parent.gpu_monitor.get_gpu_stats()
                        if gpus:
                            gpu_name = gpus[0].name
                            break
                    parent = parent.parent() if hasattr(parent, 'parent') else None
            except:
                pass
            
            # Fallback: NVML direkt nutzen
            if not gpu_name:
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(gpu_name, bytes):
                        gpu_name = gpu_name.decode('utf-8')
                    pynvml.nvmlShutdown()
                except:
                    gpu_name = "RTX 3070"  # Default
            
            self.profit_calc = get_profit_calculator(gpu_name)
            logger.info(f"AutoProfit: Calculator geladen für GPU: {gpu_name}")
            self.refresh_profits()
        except ImportError as e:
            logger.error(f"Profit Calculator nicht verfügbar: {e}")
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # === HEADER ===
        header_layout = QHBoxLayout()
        
        title = QLabel("💰 AUTO-PROFIT SWITCHER")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #FFD700;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Auto-Switch Toggle
        self.auto_switch_check = QCheckBox("🔄 Auto-Switch aktiv")
        self.auto_switch_check.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.auto_switch_check.toggled.connect(self.toggle_auto_switch)
        header_layout.addWidget(self.auto_switch_check)
        
        layout.addLayout(header_layout)
        
        # === INFO BOX ===
        info_box = QFrame()
        info_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['background_alt']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        info_layout = QHBoxLayout(info_box)
        
        # Aktueller Coin
        current_frame = QFrame()
        current_layout = QVBoxLayout(current_frame)
        current_layout.addWidget(QLabel("Aktueller Coin:"))
        self.current_coin_label = QLabel("--")
        self.current_coin_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #76B900;")
        current_layout.addWidget(self.current_coin_label)
        info_layout.addWidget(current_frame)
        
        # Aktueller Gewinn
        profit_frame = QFrame()
        profit_layout = QVBoxLayout(profit_frame)
        profit_layout.addWidget(QLabel("Reiner Gewinn/Tag:"))
        self.current_profit_label = QLabel("$0.00")
        self.current_profit_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #00FF00;")
        profit_layout.addWidget(self.current_profit_label)
        info_layout.addWidget(profit_frame)
        
        # Bester verfügbarer Coin
        best_frame = QFrame()
        best_layout = QVBoxLayout(best_frame)
        best_layout.addWidget(QLabel("Bester Coin:"))
        self.best_coin_label = QLabel("--")
        self.best_coin_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFD700;")
        best_layout.addWidget(self.best_coin_label)
        info_layout.addWidget(best_frame)
        
        # Bester Gewinn
        best_profit_frame = QFrame()
        best_profit_layout = QVBoxLayout(best_profit_frame)
        best_profit_layout.addWidget(QLabel("Bester Gewinn/Tag:"))
        self.best_profit_label = QLabel("$0.00")
        self.best_profit_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFD700;")
        best_profit_layout.addWidget(self.best_profit_label)
        info_layout.addWidget(best_profit_frame)
        
        layout.addWidget(info_box)
        
        # === TOP COINS TABELLE ===
        table_header = QLabel("📊 TOP 15 PROFITABELSTE COINS (Reiner Gewinn ohne Stromkosten)")
        table_header.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(table_header)
        
        self.coins_table = QTableWidget()
        self.coins_table.setColumnCount(7)
        self.coins_table.setHorizontalHeaderLabels([
            'Rang', 'Coin', 'Algorithmus', '$/Tag', 'Pool', 'Miner', 'Aktion'
        ])
        self.coins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.coins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.coins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.coins_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.coins_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.coins_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.coins_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.coins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.coins_table.setAlternatingRowColors(True)
        layout.addWidget(self.coins_table)
        
        # === BUTTONS ===
        btn_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("🔄 Jetzt aktualisieren")
        self.refresh_btn.clicked.connect(self.refresh_profits)
        btn_layout.addWidget(self.refresh_btn)
        
        self.switch_best_btn = QPushButton("⚡ Zu bestem Coin wechseln")
        self.switch_best_btn.setStyleSheet(f"background-color: {COLORS['button_success']}; padding: 10px;")
        self.switch_best_btn.clicked.connect(self.switch_to_best)
        btn_layout.addWidget(self.switch_best_btn)
        
        layout.addLayout(btn_layout)
        
        # === EINSTELLUNGEN ===
        settings_group = QGroupBox("Auto-Switch Einstellungen")
        settings_layout = QGridLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Min. Profit-Differenz (%):"), 0, 0)
        self.min_diff_spin = QSpinBox()
        self.min_diff_spin.setRange(1, 50)
        self.min_diff_spin.setValue(5)
        self.min_diff_spin.valueChanged.connect(lambda v: setattr(self, 'min_profit_diff', v))
        settings_layout.addWidget(self.min_diff_spin, 0, 1)
        
        settings_layout.addWidget(QLabel("Update-Intervall (Sek):"), 0, 2)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(30, 600)
        self.interval_spin.setValue(180)
        self.interval_spin.valueChanged.connect(self.update_interval)
        settings_layout.addWidget(self.interval_spin, 0, 3)
        
        # Last Update
        self.last_update_label = QLabel("Letztes Update: --")
        self.last_update_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        settings_layout.addWidget(self.last_update_label, 1, 0, 1, 4)
        
        layout.addWidget(settings_group)
    
    def toggle_auto_switch(self, enabled: bool):
        """Auto-Switch ein/ausschalten"""
        self.auto_switch_enabled = enabled
        if enabled:
            # Aktuellen Coin vom Parent holen falls nicht gesetzt
            if not self.current_coin:
                try:
                    parent = self.parent()
                    while parent:
                        if hasattr(parent, '_current_coin') and parent._current_coin:
                            self.set_current_coin(parent._current_coin)
                            break
                        parent = parent.parent() if hasattr(parent, 'parent') else None
                except:
                    pass
            
            self.update_timer.start(self.interval_spin.value() * 1000)
            logger.info(f"Auto-Switch aktiviert (Aktueller Coin: {self.current_coin or 'keiner'})")
            
            # Sofort erste Prüfung
            self.refresh_profits()
        else:
            self.update_timer.stop()
            logger.info("Auto-Switch deaktiviert")
    
    def update_interval(self, seconds: int):
        """Update-Intervall ändern"""
        if self.update_timer.isActive():
            self.update_timer.setInterval(seconds * 1000)
    
    def refresh_profits(self):
        """Aktualisiert alle Profit-Daten"""
        if not self.profit_calc:
            return
        
        self.refresh_btn.setText("⏳ Lade...")
        self.refresh_btn.setEnabled(False)
        QApplication.processEvents()
        
        try:
            # Top Coins holen
            top_coins = self.profit_calc.get_most_profitable()[:15]
            
            # Verfügbare Wallets holen
            available_wallets = self.get_available_wallets()
            
            # Tabelle füllen
            self.coins_table.setRowCount(len(top_coins))
            
            # Pool-Fetcher für automatische Pools
            try:
                from auto_pool_fetcher import get_pool_fetcher, KNOWN_POOLS
                pool_fetcher = get_pool_fetcher()
            except ImportError:
                pool_fetcher = None
                KNOWN_POOLS = {}
            
            from auto_profit_switcher import BEST_POOLS, ALGO_MINER_MAP
            
            best_mineable = None  # Bester Coin MIT Wallet
            
            for row, coin_data in enumerate(top_coins):
                coin = coin_data['coin']
                algo = coin_data['algorithm']
                profit = coin_data['usd_profit_24h']
                has_wallet = coin in available_wallets
                
                # Bester mineabler Coin merken
                if has_wallet and best_mineable is None:
                    best_mineable = coin_data
                
                # Rang
                rang_item = QTableWidgetItem(f"#{row + 1}")
                rang_item.setTextAlignment(Qt.AlignCenter)
                if row == 0:
                    rang_item.setForeground(QColor("#FFD700"))  # Gold
                elif row == 1:
                    rang_item.setForeground(QColor("#C0C0C0"))  # Silber
                elif row == 2:
                    rang_item.setForeground(QColor("#CD7F32"))  # Bronze
                self.coins_table.setItem(row, 0, rang_item)
                
                # Coin (mit Wallet-Indikator)
                coin_text = f"✅ {coin}" if has_wallet else f"❌ {coin}"
                coin_item = QTableWidgetItem(coin_text)
                coin_item.setFont(QFont('Arial', 10, QFont.Bold))
                if not has_wallet:
                    coin_item.setForeground(QColor("#888888"))  # Grau wenn keine Wallet
                self.coins_table.setItem(row, 1, coin_item)
                
                # Algorithmus
                algo_item = QTableWidgetItem(algo)
                if not has_wallet:
                    algo_item.setForeground(QColor("#888888"))
                self.coins_table.setItem(row, 2, algo_item)
                
                # Profit
                profit_item = QTableWidgetItem(f"${profit:.2f}")
                profit_item.setForeground(QColor("#00FF00") if has_wallet else QColor("#666666"))
                profit_item.setFont(QFont('Arial', 10, QFont.Bold))
                self.coins_table.setItem(row, 3, profit_item)
                
                # Bester Pool (Auto-Fetch!)
                pool_name = "N/A"
                # 1. Versuche von auto_pool_fetcher
                if pool_fetcher:
                    best_pool = pool_fetcher.get_best_pool(coin)
                    if best_pool:
                        pool_name = best_pool['name']
                # 2. Fallback auf BEST_POOLS
                if pool_name == "N/A":
                    pools = BEST_POOLS.get(coin, [])
                    if pools:
                        pool_name = pools[0].name if hasattr(pools[0], 'name') else str(pools[0])
                # 3. Fallback auf KNOWN_POOLS
                if pool_name == "N/A" and coin in KNOWN_POOLS:
                    pool_name = KNOWN_POOLS[coin][0]['name']
                
                pool_item = QTableWidgetItem(pool_name)
                if not has_wallet:
                    pool_item.setForeground(QColor("#888888"))
                self.coins_table.setItem(row, 4, pool_item)
                
                # Bester Miner
                miners = ALGO_MINER_MAP.get(algo, [])
                miner_name = miners[0] if miners else "N/A"
                miner_item = QTableWidgetItem(miner_name)
                if not has_wallet:
                    miner_item.setForeground(QColor("#888888"))
                self.coins_table.setItem(row, 5, miner_item)
                
                # Mine-Button (nur aktiv wenn Wallet vorhanden)
                if has_wallet:
                    mine_btn = QPushButton("⛏️ Mine")
                    mine_btn.clicked.connect(lambda checked, c=coin: self.start_mining_coin(c))
                else:
                    mine_btn = QPushButton("🔒 Wallet")
                    mine_btn.setToolTip(f"Keine Wallet für {coin} konfiguriert!\nBitte im Wallets Tab hinzufügen.")
                    mine_btn.setStyleSheet("color: #888888;")
                    mine_btn.clicked.connect(lambda checked, c=coin: self._show_wallet_hint(c))
                self.coins_table.setCellWidget(row, 6, mine_btn)
            
            # Besten MINEBAREN Coin anzeigen (nicht den absolut besten)
            if best_mineable:
                self.best_coin_label.setText(f"✅ {best_mineable['coin']}")
                self.best_profit_label.setText(f"${best_mineable['usd_profit_24h']:.2f}")
            elif top_coins:
                self.best_coin_label.setText(f"❌ {top_coins[0]['coin']}")
                self.best_profit_label.setText(f"(keine Wallet)")
            
            # Auto-Switch prüfen (nur wenn aktiviert)
            if self.auto_switch_enabled:
                self.check_auto_switch(top_coins)
            
            # Update Zeit
            from datetime import datetime
            self.last_update_label.setText(f"Letztes Update: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            logger.error(f"Profit-Update Fehler: {e}")
        
        self.refresh_btn.setText("🔄 Jetzt aktualisieren")
        self.refresh_btn.setEnabled(True)
    
    def _show_wallet_hint(self, coin: str):
        """Zeigt Hinweis dass Wallet fehlt"""
        QMessageBox.information(
            self, 
            f"Wallet für {coin} fehlt",
            f"Um {coin} zu minen, musst du eine Wallet-Adresse konfigurieren.\n\n"
            f"So geht's:\n"
            f"1. Gehe zum 'Börsen' Tab\n"
            f"2. Klicke auf 'Wallet hinzufügen'\n"
            f"3. Wähle {coin} und gib deine Adresse ein\n\n"
            f"Tipp: Du kannst auch CoinEx-Adressen automatisch importieren!"
        )
    
    def get_available_wallets(self) -> Dict[str, str]:
        """
        Holt alle verfügbaren Wallets.
        
        EINFACHE LOGIK: Nur aus wallets.json laden!
        CoinEx speichert dort automatisch beim Start.
        """
        wallets = {}
        
        # Aus wallets.json laden (EINZIGE QUELLE!)
        try:
            import json
            import os
            
            # Datei finden
            wallet_file = Path(__file__).parent / 'wallets.json'
            if not wallet_file.exists():
                wallet_file = Path('wallets.json')
            
            if wallet_file.exists():
                with open(wallet_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Wallets extrahieren
                raw_wallets = data.get('wallets', {})
                
                for coin, value in raw_wallets.items():
                    # Einfaches Format: "RVN": "adresse"
                    if isinstance(value, str) and len(value) > 10:
                        wallets[coin.upper()] = value
                    # Dict Format: "RVN": {"address": "...", ...}
                    elif isinstance(value, dict):
                        addr = value.get('address', '')
                        if addr and len(addr) > 10:
                            wallets[coin.upper()] = addr
                
                logger.debug(f"wallets.json: {len(wallets)} Wallets geladen")
                
        except Exception as e:
            logger.error(f"wallets.json Fehler: {e}")
        
        # Ungültige filtern
        valid_wallets = {
            coin: addr for coin, addr in wallets.items()
            if addr and len(addr) > 10 
            and not addr.startswith("DEINE_")
            and not addr.endswith("...")  # Platzhalter
        }
        
        if valid_wallets:
            logger.info(f"Verfügbare Wallets: {len(valid_wallets)} ({', '.join(sorted(valid_wallets.keys())[:10])}...)")
        else:
            logger.warning("Keine gültigen Wallets gefunden! Führe SYNC_COINEX.bat aus.")
        
        return valid_wallets
    
    def check_auto_switch(self, top_coins: list):
        """Prüft ob automatisch gewechselt werden soll - NUR Coins mit Wallet!"""
        if not top_coins:
            return
        
        # Verfügbare Wallets holen
        available_wallets = self.get_available_wallets()
        
        # Nur Coins mit Wallet filtern
        mineable_coins = [c for c in top_coins if c['coin'] in available_wallets]
        
        if not mineable_coins:
            logger.warning("Auto-Switch: Keine Coins mit konfigurierter Wallet gefunden!")
            return
        
        # Blacklist vom MainWindow holen und fehlgeschlagene Coins überspringen
        failed_coins = set()
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, '_failed_coins'):
                    failed_coins = parent._failed_coins
                    break
                parent = parent.parent() if hasattr(parent, 'parent') else None
        except:
            pass
        
        # Fehlgeschlagene Coins aus Liste entfernen
        if failed_coins:
            mineable_coins = [c for c in mineable_coins if c['coin'] not in failed_coins]
            if not mineable_coins:
                logger.warning(f"Auto-Switch: Alle Coins auf Blacklist! ({', '.join(failed_coins)})")
                return
            logger.debug(f"Auto-Switch: {len(failed_coins)} Coins auf Blacklist übersprungen")
        
        best = mineable_coins[0]
        
        # Wenn kein aktueller Coin, versuche vom Parent zu holen
        if not self.current_coin:
            try:
                parent = self.parent()
                while parent:
                    if hasattr(parent, '_current_coin') and parent._current_coin:
                        self.current_coin = parent._current_coin
                        self.current_coin_label.setText(parent._current_coin)
                        break
                    parent = parent.parent() if hasattr(parent, 'parent') else None
            except:
                pass
        
        # Immer noch kein Coin? -> Zum besten wechseln!
        if not self.current_coin:
            logger.info(f"Auto-Switch: Kein aktiver Coin, starte {best['coin']}")
            self.start_mining_coin(best['coin'])
            return
        
        # Wenn bereits bester Coin -> nichts tun
        if self.current_coin == best['coin']:
            return
        
        # Aktuellen Coin in Liste finden
        current_profit = 0
        for coin_data in mineable_coins:
            if coin_data['coin'] == self.current_coin:
                current_profit = coin_data['usd_profit_24h']
                break
        
        if current_profit <= 0:
            # Aktueller Coin nicht in minebare Liste -> wechseln!
            logger.info(f"Auto-Switch: {self.current_coin} nicht minebar/profitabel, wechsle zu {best['coin']}")
            self.start_mining_coin(best['coin'])
            return
        
        # Profit-Differenz berechnen
        diff_percent = ((best['usd_profit_24h'] - current_profit) / current_profit) * 100
        
        if diff_percent >= self.min_profit_diff:
            logger.info(f"Auto-Switch: {self.current_coin} -> {best['coin']} (+{diff_percent:.1f}%)")
            self.start_mining_coin(best['coin'])
    
    def start_mining_coin(self, coin: str):
        """Startet Mining für einen Coin"""
        try:
            from auto_profit_switcher import BEST_POOLS, ALGO_MINER_MAP
            
            # Besten Pool und Miner finden
            pools = BEST_POOLS.get(coin, [])
            if not pools:
                QMessageBox.warning(self, "Fehler", f"Kein Pool für {coin} gefunden!")
                return
            
            pool = pools[0]
            
            # Algorithmus vom profit_calc holen
            top_coins = self.profit_calc.get_most_profitable()
            algo = ""
            profit = 0
            for c in top_coins:
                if c['coin'] == coin:
                    algo = c['algorithm']
                    profit = c['usd_profit_24h']
                    break
            
            miners = ALGO_MINER_MAP.get(algo, [])
            miner = miners[0] if miners else "T-Rex"
            
            config = {
                'coin': coin,
                'algorithm': algo,
                'pool_name': pool.name,
                'pool_url': pool.stratum_url,
                'miner': miner,
                'profit_usd': profit,
            }
            
            self.current_coin = coin
            self.current_coin_label.setText(coin)
            self.current_profit_label.setText(f"${profit:.2f}")
            
            # Signal senden
            self.switch_requested.emit(config)
            
            logger.info(f"Mining gestartet: {coin} auf {pool.name} mit {miner}")
            
        except Exception as e:
            logger.error(f"Mining-Start Fehler: {e}")
            QMessageBox.warning(self, "Fehler", str(e))
    
    def switch_to_best(self):
        """Wechselt zum aktuell besten Coin"""
        if not self.profit_calc:
            return
        
        top_coins = self.profit_calc.get_most_profitable()
        if top_coins:
            self.start_mining_coin(top_coins[0]['coin'])
    
    def get_top_coins(self) -> list:
        """Gibt die Liste der profitabelsten Coins zurück (für Fallback bei Fehlern)"""
        if not self.profit_calc:
            return []
        
        top_coins = self.profit_calc.get_most_profitable()[:10]
        result = []
        
        for coin_data in top_coins:
            coin = coin_data.get('coin', '')
            if not coin:
                continue
            
            # Pool und Miner Daten aus coin_config holen
            from coin_config import COIN_CONFIGS
            config = COIN_CONFIGS.get(coin, {})
            
            pools = config.get('pools', [])
            pool_url = pools[0]['url'] if pools else f"stratum+tcp://{coin.lower()}.2miners.com:3030"
            pool_name = pools[0]['name'] if pools else "2miners"
            
            miners = config.get('miners', ['trex'])
            miner = miners[0] if miners else 'trex'
            
            result.append({
                'coin': coin,
                'algorithm': config.get('algorithm', coin_data.get('algorithm', '')),
                'pool_url': pool_url,
                'pool_name': pool_name,
                'miner': miner,
                'profit_usd': coin_data.get('profit_usd', 0),
            })
        
        return result
    
    def set_current_coin(self, coin: str, profit: float = 0):
        """Setzt den aktuellen Mining-Coin"""
        self.current_coin = coin
        self.current_coin_label.setText(coin if coin else "--")
        self.current_profit_label.setText(f"${profit:.2f}" if profit > 0 else "$0.00")


class MiningMainWindow(QMainWindow):
    """Hauptfenster der Mining-GUI"""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("GPU Mining Profit Switcher V11.0 Ultimate")
        self.setMinimumSize(1200, 800)
        
        # Manager initialisieren
        self.gpu_monitor = GPUMonitor(poll_interval=1.0)
        # Miner-Verzeichnis: Erst im aktuellen Ordner, dann im übergeordneten
        miners_path = Path("miners")
        if not miners_path.exists():
            miners_path = Path(__file__).parent / "miners"
        if not miners_path.exists():
            miners_path = Path(__file__).parent.parent / "miners"
        self.miner_manager = MinerManager(miners_dir=str(miners_path))
        self.flight_manager = FlightSheetManager("flight_sheets.json")
        self.oc_manager = OverclockManager(profiles_path="oc_profiles.json")
        self.hashrate_api = HashrateNoAPI()
        
        # MSI Afterburner Manager (NEU!)
        self.msi_ab_manager = None
        if MSI_AB_AVAILABLE:
            self.msi_ab_manager = MSIAfterburnerManager()
            # hashrate.no API verbinden für GPU-spezifische OC-Settings!
            self.msi_ab_manager.set_hashrate_api(self.hashrate_api)
            if self.msi_ab_manager.is_installed:
                logger.info(f"MSI Afterburner v{self.msi_ab_manager.version} verfügbar")
            else:
                logger.warning("MSI Afterburner nicht installiert - kann automatisch installiert werden")
        
        # Hardware-Datenbank (NEU!)
        self.hardware_db = None
        if HARDWARE_DB_AVAILABLE:
            self.hardware_db = get_hardware_db()
            self.hardware_db.set_hashrate_api(self.hashrate_api)
            # Hardware erkennen und speichern
            gpus, cpus = self.hardware_db.detect_all_hardware()
            logger.info(f"Hardware-DB: {len(gpus)} GPUs, {len(cpus)} CPUs erkannt")
            
            # MSI AB mit Hardware-DB verbinden
            if self.msi_ab_manager:
                self.msi_ab_manager.set_hardware_db(self.hardware_db)
        
        # Profit Calculator (neu)
        self.profit_calculator = None
        if PROFIT_AVAILABLE:
            self.profit_calculator = get_profit_calculator()
        
        # State
        self._mining = False
        self._start_time = 0
        self._current_coin = ""
        
        # UI Setup
        self.setup_ui()
        self.setup_tray()
        self.setup_workers()
        
        # Theme anwenden
        apply_theme(QApplication.instance())
        
        # GPU Monitor starten
        if self.gpu_monitor.initialize():
            # GPU Monitor Thread starten (sammelt Daten im Hintergrund)
            self.gpu_monitor.start()
            
            # Qt Worker starten (holt Daten und aktualisiert UI)
            self.monitor_worker.start()
            
            # OC Manager initialisieren
            self.oc_manager.initialize()
            self.oc_tab.setup_gpu_sliders(self.gpu_monitor.get_gpu_count())
            self.dashboard.temp_chart.set_gpu_count(self.gpu_monitor.get_gpu_count())
        
        # MSI Afterburner Auto-Check beim Start (verzögert)
        QTimer.singleShot(2000, self.check_msi_afterburner_auto)
        
        # Exchange Manager für automatisches Wallet-Loading (verzögert)
        QTimer.singleShot(3000, self.auto_sync_all_exchanges)
    
    def auto_sync_all_exchanges(self):
        """Synchronisiert Wallets automatisch von ALLEN Börsen beim Start"""
        try:
            total_new = 0
            total_updated = 0
            
            # ============================================
            # 1. COINEX
            # ============================================
            try:
                from coinex_api import CoinExAPI, CoinExWalletSync
                
                api = CoinExAPI()
                if api.is_configured():
                    logger.info("CoinEx API konfiguriert - lade Wallets direkt...")
                    
                    sync = CoinExWalletSync(api)
                    new_count, updated_count = sync.sync_from_coinex()
                    
                    total = len(sync.get_all_coinex_wallets())
                    logger.info(f"✅ CoinEx: {total} Wallets geladen ({new_count} neu, {updated_count} aktualisiert)")
                    
                    if total > 0:
                        self.logs_tab.append_log(f"✅ CoinEx: {total} Wallets synchronisiert")
                        total_new += new_count
                        total_updated += updated_count
                    
            except ImportError as e:
                logger.debug(f"CoinEx direkt nicht verfügbar: {e}")
            except Exception as e:
                logger.warning(f"CoinEx direkt Fehler: {e}")
            
            # ============================================
            # 2. GATE.IO
            # ============================================
            try:
                from gateio_api import GateIOAPI, GateIOWalletSync
                
                gateio_api = GateIOAPI()
                if gateio_api.is_configured():
                    logger.info("Gate.io API konfiguriert - lade Wallets...")
                    
                    gateio_sync = GateIOWalletSync(gateio_api)
                    result = gateio_sync.sync_all()
                    
                    total = result.get('total', 0)
                    new_count = result.get('new', 0)
                    updated_count = result.get('updated', 0)
                    
                    logger.info(f"✅ Gate.io: {total} Wallets geladen ({new_count} neu, {updated_count} aktualisiert)")
                    
                    if total > 0:
                        self.logs_tab.append_log(f"✅ Gate.io: {total} Wallets synchronisiert")
                        total_new += new_count
                        total_updated += updated_count
                    
            except ImportError as e:
                logger.debug(f"Gate.io nicht verfügbar: {e}")
            except Exception as e:
                logger.warning(f"Gate.io Fehler: {e}")
            
            # ============================================
            # WALLETS AKTUALISIEREN
            # ============================================
            if total_new > 0 or total_updated > 0:
                # WICHTIG: Wallets-Tab aktualisieren!
                try:
                    if hasattr(self, 'wallets_tab') and self.wallets_tab.exchange_manager:
                        # Wallets neu laden (verschiedene ExchangeManager Versionen)
                        if hasattr(self.wallets_tab.exchange_manager, '_load_wallets'):
                            self.wallets_tab.exchange_manager._load_wallets()
                        elif hasattr(self.wallets_tab.exchange_manager, 'load_wallets'):
                            self.wallets_tab.exchange_manager.load_wallets()
                        
                        # Tabellen aktualisieren
                        QTimer.singleShot(100, self.wallets_tab.refresh_wallets_list)
                        QTimer.singleShot(200, self.wallets_tab.refresh_exchanges_list)  # Börsen-Tabelle auch!
                        logger.info(f"Wallets-Tab aktualisiert")
                except Exception as e:
                    logger.debug(f"Wallets-Tab Update: {e}")
                
                # Auto-Profit Tab aktualisieren
                if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
                    QTimer.singleShot(500, self.auto_profit_tab.refresh_profits)
                
                self.status_bar.showMessage(f"Wallets geladen: {total_new} neu, {total_updated} aktualisiert - bereit!", 5000)
                return
            
            # FALLBACK: Exchange Manager
            from exchange_manager import get_exchange_manager, ExchangeStatus
            
            logger.info("=== Automatische Wallet-Synchronisierung (Exchange Manager) ===")
            
            # Exchange Manager holen (synchronisiert automatisch)
            self.exchange_manager = get_exchange_manager(auto_sync=True)
            
            # Status anzeigen
            total_wallets = len(self.exchange_manager.get_all_wallets())
            
            for name, info in self.exchange_manager.get_exchange_status().items():
                if info.status == ExchangeStatus.CONNECTED:
                    logger.info(f"✅ {info.name}: {info.wallet_count} Wallets geladen")
                    if info.wallet_count > 0:
                        self.logs_tab.append_log(f"✅ {info.name}: {info.wallet_count} Wallets synchronisiert")
                elif info.status == ExchangeStatus.NOT_CONFIGURED:
                    logger.debug(f"⚪ {info.name}: Nicht konfiguriert")
                else:
                    logger.warning(f"❌ {info.name}: {info.error_message}")
            
            if total_wallets > 0:
                logger.info(f"📊 Gesamt: {total_wallets} Wallets für Auto-Switch verfügbar")
                self.status_bar.showMessage(f"{total_wallets} Wallets geladen - bereit für Auto-Switch", 5000)
                
                # Auto-Profit Tab aktualisieren
                if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
                    self.auto_profit_tab.refresh_profits()
            else:
                logger.warning("⚠️ Keine Wallets gefunden - Auto-Switch nicht möglich!")
                self.logs_tab.append_log("⚠️ Keine Wallets konfiguriert - bitte CoinEx/Gate.io API einrichten!")
                
        except ImportError as e:
            logger.warning(f"Exchange Manager nicht verfügbar: {e}")
            # Fallback auf alte Methode
            self._fallback_coinex_sync()
        except Exception as e:
            logger.error(f"Exchange Sync Fehler: {e}")
    
    def _merge_gateio_wallets(self, gateio_wallets: dict):
        """Fügt Gate.io Wallets zu wallets.json hinzu"""
        try:
            import json
            from pathlib import Path
            
            wallets_file = Path("wallets.json")
            existing = {}
            
            if wallets_file.exists():
                with open(wallets_file, 'r') as f:
                    data = json.load(f)
                    existing = data.get('wallets', {})
            
            # Gate.io Wallets hinzufügen (überschreibt nicht existierende)
            for coin, address in gateio_wallets.items():
                if coin not in existing:
                    existing[coin] = address
                    logger.info(f"Gate.io Wallet hinzugefügt: {coin}")
            
            # Speichern
            with open(wallets_file, 'w') as f:
                json.dump({'wallets': existing}, f, indent=2)
            
            logger.info(f"wallets.json aktualisiert: {len(existing)} Wallets")
            
        except Exception as e:
            logger.error(f"Gate.io Wallets merge Fehler: {e}")
    
    def _fallback_coinex_sync(self):
        """Fallback: Alte CoinEx-Sync Methode"""
        try:
            from coinex_api import CoinExAPI
            
            api = CoinExAPI()
            
            if api.is_configured():
                logger.info("CoinEx API konfiguriert - synchronisiere Wallets...")
                
                if PROFIT_AVAILABLE:
                    wm = get_wallet_manager()
                    new_count, updated_count, error = wm.sync_from_coinex()
                    
                    if error:
                        logger.warning(f"CoinEx Sync Fehler: {error}")
                    elif new_count > 0 or updated_count > 0:
                        logger.info(f"✅ CoinEx: {new_count} neue, {updated_count} aktualisierte Wallets")
                        self.logs_tab.append_log(f"✅ CoinEx: {new_count} neue Wallets synchronisiert")
        except Exception as e:
            logger.error(f"Fallback CoinEx Sync Fehler: {e}")
    
    def setup_ui(self):
        """Erstellt das UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab Widget
        self.tabs = QTabWidget()
        
        # Dashboard Tab
        self.dashboard = DashboardTab()
        self.dashboard.start_btn.clicked.connect(self.start_mining)
        self.dashboard.stop_btn.clicked.connect(self.stop_mining)
        
        # Dashboard OC-Profile Buttons verbinden
        self.dashboard.oc_button_group.buttonClicked.connect(self._on_dashboard_oc_changed)
        self.dashboard.auto_oc_checkbox.stateChanged.connect(self._on_dashboard_auto_oc_changed)
        
        self.tabs.addTab(self.dashboard, "📊 Dashboard")
        
        # Auto-Profit Tab (NEU!)
        self.auto_profit_tab = AutoProfitTab()
        self.auto_profit_tab.switch_requested.connect(self.on_auto_switch)
        self.tabs.addTab(self.auto_profit_tab, "💰 Auto-Profit")
        
        # Flight Sheets Tab
        self.flight_tab = FlightSheetsTab(self.flight_manager)
        self.flight_tab.flight_sheet_applied.connect(self.apply_flight_sheet)
        self.tabs.addTab(self.flight_tab, "📋 Flight Sheets")
        
        # Overclock Tab
        self.oc_tab = OverclockTab(self.oc_manager, self.hashrate_api)
        if self.msi_ab_manager:
            self.oc_tab.set_msi_ab_manager(self.msi_ab_manager)
        self.tabs.addTab(self.oc_tab, "⚡ Overclock")
        
        # Logs Tab
        self.logs_tab = LogsTab()
        self.tabs.addTab(self.logs_tab, "📝 Logs")
        
        # Wallets & Exchanges Tab
        self.wallets_tab = WalletsTab()
        self.wallets_tab.wallet_updated.connect(self.on_wallets_updated)
        self.tabs.addTab(self.wallets_tab, "🏦 Börsen")
        
        # Hardware Tab (NEU!)
        self.hardware_tab = HardwareTab()
        if self.hardware_db:
            self.hardware_tab.set_hardware_db(self.hardware_db)
        self.tabs.addTab(self.hardware_tab, "🖥️ Hardware")
        
        # Settings Tab
        self.settings_tab = SettingsTab()
        self.settings_tab.settings_changed.connect(self.on_settings_changed)
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        # AI Agent Tab (NEU! V12.7)
        if AI_AGENT_AVAILABLE:
            self.ai_agent_tab = AIAgentWidget()
            # Registriere Callbacks für GPU und Miner
            if hasattr(self, 'gpu_monitor'):
                self.ai_agent_tab.register_gpu_callbacks(self.gpu_monitor)
            if hasattr(self, 'miner_manager'):
                self.ai_agent_tab.register_miner_callbacks(self.miner_manager)
            if hasattr(self, 'oc_manager'):
                self.ai_agent_tab.register_oc_callbacks(self.oc_manager)
            self.tabs.addTab(self.ai_agent_tab, "🤖 AI Agent")
        else:
            self.ai_agent_tab = None
        
        # CPU Mining Tab (NEU! V12.7)
        if CPU_MINING_AVAILABLE:
            self.cpu_mining_tab = CPUMiningWidget()
            self.tabs.addTab(self.cpu_mining_tab, "💻 CPU Mining")
        else:
            self.cpu_mining_tab = None
        
        # Portfolio Tab (NEU! V12.8)
        if PORTFOLIO_AVAILABLE:
            self.portfolio_tab = PortfolioWidget()
            self.portfolio_tab.alert_triggered.connect(self.on_portfolio_alert)
            self.tabs.addTab(self.portfolio_tab, "💰 Portfolio")
        else:
            self.portfolio_tab = None
        
        # Multi-GPU Mining Tab (NEU! V12.8) - Jede GPU eigener Coin!
        if MULTI_GPU_AVAILABLE:
            self.multi_gpu_tab = MultiGPUMiningWidget()
            self.multi_gpu_tab.mining_started.connect(self.on_multi_gpu_started)
            self.multi_gpu_tab.mining_stopped.connect(self.on_multi_gpu_stopped)
            self.multi_gpu_tab.gpu_switched.connect(self.on_gpu_coin_switch)
            self.tabs.addTab(self.multi_gpu_tab, "🎮 Multi-GPU")
            # Manager nach GPU-Monitor initialisieren
            QTimer.singleShot(2000, self.setup_multi_gpu_managers)
        else:
            self.multi_gpu_tab = None
        
        # Memory Manager Tab (NEU! V12.8)
        if MEMORY_MANAGER_AVAILABLE:
            self.memory_tab = MemoryManagerWidget()
            self.memory_tab.optimization_started.connect(self.on_memory_optimization_started)
            self.memory_tab.optimization_completed.connect(self.on_memory_optimization_completed)
            self.memory_tab.restart_scheduled.connect(self.on_restart_scheduled)
            self.tabs.addTab(self.memory_tab, "💾 Speicher")
            # Memory Manager nach GPU-Erkennung initialisieren
            QTimer.singleShot(3000, self.setup_memory_manager)
        else:
            self.memory_tab = None
        
        layout.addWidget(self.tabs)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Bereit")
        
        # Update Timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(1000)
    
    def setup_tray(self):
        """Erstellt System Tray Icon"""
        self.tray_icon = MiningTrayIcon(self)
        self.tray_icon.show_requested.connect(self.show_from_tray)
        self.tray_icon.start_requested.connect(self.start_mining)
        self.tray_icon.stop_requested.connect(self.stop_mining)
        self.tray_icon.quit_requested.connect(self.quit_app)
        self.tray_icon.show()
    
    def setup_workers(self):
        """Erstellt Background-Worker"""
        self.monitor_worker = MonitorWorker(self.gpu_monitor)
        self.monitor_worker.update.connect(self.on_gpu_update, Qt.QueuedConnection)
        
        self.miner_stats_worker = MinerStatsWorker(self.miner_manager)
        self.miner_stats_worker.update.connect(self.on_miner_stats, Qt.QueuedConnection)
        
        # Log-Buffer für Thread-sichere Log-Ausgabe
        self._log_buffer = []
        self._log_timer = QTimer()
        self._log_timer.timeout.connect(self._flush_logs)
        self._log_timer.start(100)  # Alle 100ms Logs flushen
        
        # Miner Log Callback - wird in separatem Thread aufgerufen!
        self.miner_manager.on_log = self._buffer_log
        
        # Code Repair Integration (NEU! V12.8)
        if CODE_REPAIR_AVAILABLE:
            self.setup_code_repair_integration()
    
    def _buffer_log(self, line: str):
        """Puffert Log-Zeilen (thread-safe)"""
        try:
            self._log_buffer.append(line)
        except Exception:
            pass
    
    def _flush_logs(self):
        """Flusht Log-Buffer ins UI (Main Thread)"""
        if not self._log_buffer:
            return
        
        # Buffer leeren und Logs anzeigen
        logs = self._log_buffer[:]
        self._log_buffer.clear()
        
        for line in logs:
            self.logs_tab.append_log(line)
    
    def on_gpu_update(self, data: dict):
        """Handler für GPU-Monitor Updates"""
        try:
            gpus = data.get('gpus', [])
            
            # Debug-Log (kann später entfernt werden)
            if gpus:
                logger.debug(f"GPU Update: {len(gpus)} GPUs erkannt")
            
            # Tabelle aktualisieren
            miner_stats = None
            if self._mining:
                try:
                    miner_stats = self.miner_manager.get_current_stats()
                except Exception:
                    pass
            self.dashboard.gpu_table.update_gpus(gpus, miner_stats, self._current_coin)
            
            # Charts aktualisieren
            total_hashrate = sum(gpu.hashrate for gpu in gpus)
            if miner_stats:
                total_hashrate = miner_stats.total_hashrate
            
            self.dashboard.hashrate_chart.update_data(total_hashrate)
            
            temps = {gpu.index: gpu.temperature for gpu in gpus}
            self.dashboard.temp_chart.update_data(temps)
            
            # Tray aktualisieren
            avg_temp = sum(gpu.temperature for gpu in gpus) / len(gpus) if gpus else 0
            total_power = sum(gpu.power_watts for gpu in gpus)
            self.tray_icon.update_stats(total_hashrate, int(avg_temp), total_power)
            
            # High Temp Check
            for gpu in gpus:
                if gpu.temperature >= 85:
                    self.tray_icon.notify_high_temp(gpu.index, gpu.temperature)
        except Exception as e:
            logger.error(f"Fehler in on_gpu_update: {e}")
    
    def on_miner_stats(self, stats: MinerStats):
        """Handler für Miner-Stats Updates"""
        try:
            if not stats:
                return
            
            uptime = int(time.time() - self._start_time) if self._mining else 0
            
            # Profit berechnen
            profit_usd = 0.0
            if self.profit_calculator and self._current_coin and stats.total_hashrate > 0:
                try:
                    power_watts = stats.total_power if stats.total_power > 0 else 140  # Fallback
                    power_cost = self.settings_tab.electricity_spin.value()
                    
                    result = self.profit_calculator.calculate_profit(
                        coin=self._current_coin,
                        hashrate=stats.total_hashrate,
                        power_watts=power_watts,
                        power_cost=power_cost
                    )
                    
                    if result:
                        profit_usd = result.get('usd_profit_24h', 0.0)
                        # Debug: Zeige Profit im Log
                        if uptime % 10 == 0:  # Alle 10 Sekunden
                            logger.debug(f"Profit result: ${profit_usd:.4f}/Tag (raw: {result})")
                    else:
                        logger.warning(f"Kein Profit-Ergebnis für {self._current_coin}")
                        
                except Exception as e:
                    logger.warning(f"Profit-Berechnung fehlgeschlagen: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
            
            # WICHTIG: Immer update_stats aufrufen, auch wenn profit_usd = 0
            self.dashboard.update_stats(
                hashrate=stats.total_hashrate,
                power=stats.total_power,
                coin=self._current_coin,
                uptime=uptime,
                accepted=stats.total_accepted,
                rejected=stats.total_rejected,
                profit_usd=profit_usd
            )
            
            # Debug-Log für GUI-Update
            if uptime % 30 == 0 and uptime > 0:
                unit = get_hashrate_unit(self._current_coin) if self._current_coin else 'MH/s'
                logger.info(f"GUI Update: {stats.total_hashrate:.2f} {unit}, ${profit_usd:.2f}/Tag, A:{stats.total_accepted} R:{stats.total_rejected}")
                
        except Exception as e:
            logger.error(f"Fehler in on_miner_stats: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    def on_miner_log(self, line: str):
        """Handler für Miner-Logs"""
        self.logs_tab.append_log(line)
    
    def update_ui(self):
        """Periodisches UI-Update - nutzt GPU-Monitor + Miner Daten für Dashboard"""
        if self._mining:
            uptime = int(time.time() - self._start_time)
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            seconds = uptime % 60
            self.dashboard.uptime_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Miner-Stats und GPU-Daten für Dashboard
            try:
                total_hashrate = 0.0
                total_power = 0.0
                total_accepted = 0
                total_rejected = 0
                
                # 1. Versuche Miner-API Stats
                if self.miner_manager:
                    stats = self.miner_manager.get_current_stats()
                    if stats and stats.total_hashrate > 0:
                        total_hashrate = stats.total_hashrate
                        total_power = stats.total_power
                        total_accepted = stats.total_accepted
                        total_rejected = stats.total_rejected
                
                # 2. Fallback: GPU-Monitor Power (falls Miner keine Power liefert)
                if total_power == 0:
                    metrics = self.gpu_monitor.get_latest_metrics()
                    if metrics and metrics.get('gpus'):
                        for gpu in metrics['gpus']:
                            if hasattr(gpu, 'power_watts'):
                                total_power += gpu.power_watts or 0
                
                # Dashboard aktualisieren
                if total_hashrate > 0:
                    unit = get_hashrate_unit(self._current_coin) if self._current_coin else 'MH/s'
                    self.dashboard.hashrate_label.setText(f"{total_hashrate:.2f} {unit}")
                
                if total_power > 0:
                    self.dashboard.power_label.setText(f"{total_power:.0f} W")
                
                self.dashboard.coin_label.setText(self._current_coin or "--")
                
                # Shares aktualisieren
                self.dashboard.shares_label.setText(
                    f"<span style='color:{COLORS['accepted']}'>A: {total_accepted}</span> | "
                    f"<span style='color:{COLORS['rejected']}'>R: {total_rejected}</span>"
                )
                
                # Profit berechnen
                if self.profit_calculator and self._current_coin and total_hashrate > 0:
                    try:
                        result = self.profit_calculator.calculate_profit(
                            coin=self._current_coin,
                            hashrate=total_hashrate
                        )
                        if result:
                            profit_usd = result.get('usd_profit_24h', 0.0)
                            self.dashboard.profit_label.setText(f"${profit_usd:.2f}")
                            self.dashboard.profit_label.setStyleSheet(
                                f"font-size: 28px; font-weight: bold; color: {COLORS['accepted']};"
                            )
                    except Exception as e:
                        logger.debug(f"Profit-Calc Fehler: {e}")
                    
            except Exception as e:
                logger.debug(f"UI-Update Fehler: {e}")
    
    def start_mining(self):
        """Startet Mining mit aktivem Flight Sheet"""
        # Speicher-Prüfung vor Mining-Start (NEU! V12.8)
        if not self.check_memory_before_mining():
            self.logs_tab.append_log("⏸️ Mining pausiert - Speicher-Optimierung erforderlich")
            return
        
        active = self.flight_manager.get_active()
        if not active:
            # Erstes Flight Sheet nehmen oder Dialog zeigen
            sheets = self.flight_manager.list_all()
            if sheets:
                active = sheets[0]
                self.flight_manager.set_active(active.id)
            else:
                QMessageBox.warning(self, "Kein Flight Sheet", 
                    "Bitte erstelle zuerst ein Flight Sheet!")
                self.tabs.setCurrentWidget(self.flight_tab)
                return
        
        self.apply_flight_sheet(active.id)
    
    def apply_flight_sheet(self, sheet_id: str):
        """Wendet ein Flight Sheet an"""
        sheet = self.flight_manager.get(sheet_id)
        if not sheet:
            return
        
        # Overclocking anwenden (MSI Afterburner bevorzugt!)
        if self.flight_tab.auto_oc_check.isChecked():
            oc_applied = False
            
            # 1. MSI Afterburner automatisch starten und OC anwenden
            if self.msi_ab_manager and self.msi_ab_manager.is_installed:
                try:
                    # Auto-Start wenn nicht läuft
                    if not self.msi_ab_manager.check_running():
                        logger.info("MSI Afterburner wird automatisch gestartet...")
                        self.msi_ab_manager.start_afterburner(minimized=True)
                        time.sleep(2)  # Warten bis gestartet
                    
                    # OC automatisch anwenden
                    success, msg = self.msi_ab_manager.apply_mining_profile(sheet.coin)
                    if success:
                        self.logs_tab.append_log(f"✅ MSI Afterburner: {msg}")
                        oc_applied = True
                    else:
                        logger.warning(f"MSI AB OC fehlgeschlagen: {msg}")
                except Exception as e:
                    logger.warning(f"MSI AB Fehler: {e}")
            
            # 2. Fallback: NVML (benötigt Admin-Rechte)
            if not oc_applied and self.oc_manager:
                try:
                    self.oc_manager.apply_auto_oc_all(sheet.coin)
                    self.logs_tab.append_log(f"NVML OC für {sheet.coin} angewendet")
                except Exception as e:
                    logger.warning(f"NVML OC fehlgeschlagen: {e}")
        
        # Miner-Typ bestimmen
        miner_type_map = {
            "trex": MinerType.TREX,
            "nbminer": MinerType.NBMINER,
            "gminer": MinerType.GMINER,
            "lolminer": MinerType.LOLMINER,
            "rigel": MinerType.RIGEL,
            "bzminer": MinerType.BZMINER,
            "teamredminer": MinerType.TEAMREDMINER,
            "srbminer": MinerType.SRBMINER,
            "xmrig": MinerType.XMRIG,  # CPU Miner für XMR
        }
        
        miner_type = miner_type_map.get(sheet.miner.lower(), MinerType.TREX)
        
        # CPU Mining: Kein OC nötig
        is_cpu_mining = sheet.miner.lower() == "xmrig" or getattr(sheet, 'mining_type', None) == 'cpu'
        if is_cpu_mining:
            self.logs_tab.append_log("💻 CPU Mining - kein GPU OC erforderlich")
        
        # Miner starten
        extra_args = sheet.extra_args.split() if sheet.extra_args else None
        
        success = self.miner_manager.start_miner(
            miner_type=miner_type,
            algorithm=sheet.algorithm,
            pool_url=sheet.pool_url,
            wallet=sheet.wallet,
            worker=sheet.worker_name,
            extra_args=extra_args
        )
        
        if success:
            self._mining = True
            self._start_time = time.time()
            self._current_coin = sheet.coin
            
            # Auto-Profit Tab synchronisieren
            if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
                self.auto_profit_tab.set_current_coin(sheet.coin)
            
            self.dashboard.start_btn.setEnabled(False)
            self.dashboard.stop_btn.setEnabled(True)
            self.tray_icon.set_mining_state(True)
            self.tray_icon.notify_miner_started(sheet.coin, sheet.pool_name or sheet.pool_url)
            
            # Stats Worker starten
            self.miner_stats_worker.start()
            
            # AI Agent automatisch starten für Überwachung
            if AI_AGENT_AVAILABLE and hasattr(self, 'ai_agent_tab') and self.ai_agent_tab:
                self.ai_agent_tab.auto_start_monitoring(interval=5.0)
            
            # Portfolio Monitoring automatisch starten (NEU! V12.8)
            if PORTFOLIO_AVAILABLE and hasattr(self, 'portfolio_tab') and self.portfolio_tab:
                self.portfolio_tab.start_monitoring()
            
            self.status_bar.showMessage(f"Mining {sheet.coin} auf {sheet.pool_name}...")
            self.logs_tab.append_log(f"=== Mining gestartet: {sheet.coin} ===")
        else:
            QMessageBox.warning(self, "Fehler", "Mining konnte nicht gestartet werden!")
    
    def stop_mining(self):
        """Stoppt Mining"""
        # Miner stoppen
        self.miner_manager.stop_current()
        
        # Sicherheitshalber alle Miner-Prozesse killen
        self.miner_manager.kill_all_miners()
        
        # OC zurücksetzen (GPU auf Standard)
        try:
            # MSI Afterburner Reset
            if self.msi_ab_manager and self.msi_ab_manager.is_installed:
                success, msg = self.msi_ab_manager.reset_oc()
                if success:
                    self.logs_tab.append_log("MSI Afterburner OC zurückgesetzt")
            
            # NVML Reset
            self.oc_manager.reset_all_gpus()
            self.logs_tab.append_log("GPU Overclocking zurückgesetzt")
        except Exception as e:
            logger.warning(f"OC Reset fehlgeschlagen: {e}")
        
        # Stats Worker stoppen (wenn er läuft)
        try:
            if self.miner_stats_worker.isRunning():
                self.miner_stats_worker._running = False
                self.miner_stats_worker.wait(1000)  # 1 Sekunde warten
        except Exception:
            pass
        
        # AI Agent Monitoring stoppen
        if AI_AGENT_AVAILABLE and hasattr(self, 'ai_agent_tab') and self.ai_agent_tab:
            self.ai_agent_tab.auto_stop_monitoring()
        
        # Portfolio Monitoring stoppen (NEU! V12.8)
        if PORTFOLIO_AVAILABLE and hasattr(self, 'portfolio_tab') and self.portfolio_tab:
            self.portfolio_tab.stop_monitoring()
        
        self._mining = False
        self._current_coin = ""
        
        # Auto-Profit Tab synchronisieren
        if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
            self.auto_profit_tab.set_current_coin("")
        
        self.dashboard.start_btn.setEnabled(True)
        self.dashboard.stop_btn.setEnabled(False)
        self.tray_icon.set_mining_state(False)
        self.tray_icon.notify_miner_stopped()
        
        self.status_bar.showMessage("Mining gestoppt")
        self.logs_tab.append_log("=== Mining gestoppt ===")
    
    def check_msi_afterburner_auto(self):
        """
        Automatischer MSI Afterburner Check beim Start
        - Prüft ob installiert
        - Fragt nach Installation wenn nicht
        - Prüft auf Updates
        """
        if not self.msi_ab_manager:
            return
        
        # 1. Nicht installiert? Fragen ob installieren
        if not self.msi_ab_manager.is_installed:
            reply = QMessageBox.question(
                self, "MSI Afterburner nicht gefunden",
                "MSI Afterburner ist nicht installiert.\n\n"
                "MSI Afterburner ermöglicht Overclocking auch auf Laptops\n"
                "und ohne Administrator-Rechte.\n\n"
                "Jetzt automatisch installieren?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._install_msi_afterburner_auto()
            return
        
        # 2. Update verfügbar? Fragen ob aktualisieren
        update_available, current, latest = self.msi_ab_manager.check_for_updates()
        
        if update_available:
            reply = QMessageBox.question(
                self, "MSI Afterburner Update",
                f"Ein Update für MSI Afterburner ist verfügbar!\n\n"
                f"Installiert: v{current}\n"
                f"Verfügbar: v{latest}\n\n"
                "Jetzt aktualisieren?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                import webbrowser
                webbrowser.open("https://www.msi.com/Landing/afterburner/graphics-cards")
                QMessageBox.information(
                    self, "Download",
                    "Die Download-Seite wurde geöffnet.\n\n"
                    "Bitte lade die neue Version herunter und installiere sie.\n"
                    "Das Programm wird dann beim nächsten Start erkannt."
                )
        else:
            # Alles OK - kurze Info im Log
            logger.info(f"MSI Afterburner v{current} ist aktuell")
            self.logs_tab.append_log(f"✅ MSI Afterburner v{current} bereit")
    
    def _install_msi_afterburner_auto(self):
        """Installiert MSI Afterburner automatisch"""
        # Progress Dialog
        progress = QMessageBox(self)
        progress.setWindowTitle("MSI Afterburner Installation")
        progress.setText("⏳ Lade MSI Afterburner herunter...\n\nBitte warten...")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        QApplication.processEvents()
        
        def update_progress(percent, message):
            progress.setText(f"⏳ {message}\n\n{percent}% abgeschlossen...")
            QApplication.processEvents()
        
        success, message = self.msi_ab_manager.download_and_install(update_progress)
        progress.close()
        
        if success:
            QMessageBox.information(
                self, "Installation erfolgreich",
                f"✅ {message}\n\n"
                "MSI Afterburner wird jetzt automatisch für\n"
                "Overclocking beim Mining verwendet."
            )
            # OC Tab aktualisieren
            if hasattr(self, 'oc_tab'):
                self.oc_tab.update_msi_ab_status()
        else:
            QMessageBox.warning(
                self, "Installation",
                f"⚠️ {message}\n\n"
                "Du kannst MSI Afterburner auch manuell installieren:\n"
                "https://www.msi.com/Landing/afterburner"
            )
    
    def on_settings_changed(self, settings: dict):
        """Handler für Settings-Änderungen"""
        # API Key für hashrate.no
        if settings.get('api_key'):
            self.hashrate_api = HashrateNoAPI(api_key=settings['api_key'])
        
        # Temp Warning Threshold
        if self.gpu_monitor:
            self.gpu_monitor.temp_warning = settings.get('temp_warning', 80)
    
    def on_portfolio_alert(self, level: str, message: str):
        """Handler für Portfolio-Alerts (NEU! V12.8)"""
        # Log anzeigen
        self.logs_tab.append_log(f"💰 [{level.upper()}] {message}")
        
        # Bei kritischen Alerts: Status Bar aktualisieren
        if level == "critical":
            self.status_bar.showMessage(f"⚠️ PORTFOLIO: {message}", 10000)
        
        # Tray Notification wenn minimiert
        if hasattr(self, 'tray_icon') and self.tray_icon and not self.isVisible():
            self.tray_icon.showMessage(
                f"Portfolio Alert ({level})",
                message,
                self.tray_icon.Information,
                5000
            )
    
    def setup_multi_gpu_managers(self):
        """Initialisiert Multi-GPU Manager (NEU! V12.8)"""
        if not MULTI_GPU_AVAILABLE or not hasattr(self, 'multi_gpu_tab') or not self.multi_gpu_tab:
            return
        
        try:
            # Manager holen
            miner_manager = get_multi_miner_manager()
            switcher = get_multi_gpu_switcher()
            calculator = get_multi_gpu_calculator()
            
            # OC Manager setzen
            miner_manager.oc_manager = self.oc_manager
            miner_manager.msi_ab_manager = self.msi_ab_manager
            
            # Manager an Widget übergeben
            self.multi_gpu_tab.set_managers(miner_manager, switcher, calculator)
            
            # GPUs erkennen und an Widget übergeben
            gpus = self._detect_all_gpus()
            if gpus:
                self.multi_gpu_tab.setup_gpus(gpus)
                logger.info(f"🎮 Multi-GPU Setup: {len(gpus)} GPUs erkannt")
            
        except Exception as e:
            logger.error(f"Multi-GPU Setup Fehler: {e}")
    
    def _detect_all_gpus(self) -> list:
        """Erkennt alle GPUs und gibt Liste zurück (NEU! V12.8)"""
        gpus = []
        
        try:
            if self.gpu_monitor and hasattr(self.gpu_monitor, '_gpu_count'):
                for i in range(self.gpu_monitor._gpu_count):
                    gpu_info = self.gpu_monitor._collect_gpu_data(i)
                    if gpu_info:
                        gpus.append((i, gpu_info.name))
        except Exception as e:
            logger.warning(f"GPU-Erkennung Fehler: {e}")
        
        # Fallback: NVML direkt
        if not gpus:
            try:
                import pynvml
                pynvml.nvmlInit()
                count = pynvml.nvmlDeviceGetCount()
                for i in range(count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    if isinstance(name, bytes):
                        name = name.decode('utf-8')
                    gpus.append((i, name))
            except:
                pass
        
        return gpus
    
    def on_multi_gpu_started(self):
        """Handler: Multi-GPU Mining gestartet (NEU! V12.8)"""
        self.logs_tab.append_log("🎮 Multi-GPU Mining gestartet")
        self.status_bar.showMessage("🎮 Multi-GPU Mining aktiv")
        
        # Tray Icon aktualisieren
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.set_mining_state(True)
    
    def on_multi_gpu_stopped(self):
        """Handler: Multi-GPU Mining gestoppt (NEU! V12.8)"""
        self.logs_tab.append_log("🎮 Multi-GPU Mining gestoppt")
        self.status_bar.showMessage("🎮 Multi-GPU Mining gestoppt")
        
        # Tray Icon aktualisieren
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.set_mining_state(False)
    
    def on_gpu_coin_switch(self, gpu_index: int, old_coin: str, new_coin: str):
        """Handler: GPU hat Coin gewechselt (NEU! V12.8)"""
        self.logs_tab.append_log(f"🔄 GPU {gpu_index}: {old_coin} → {new_coin}")
        
        # Tray Notification
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                "Coin-Wechsel",
                f"GPU {gpu_index}: {old_coin} → {new_coin}",
                self.tray_icon.Information,
                3000
            )
    
    def setup_memory_manager(self):
        """Initialisiert Memory Manager (NEU! V12.8)"""
        if not MEMORY_MANAGER_AVAILABLE or not hasattr(self, 'memory_tab') or not self.memory_tab:
            return
        
        try:
            memory_manager = get_memory_manager()
            memory_ai = get_memory_ai()
            
            # Manager an Widget übergeben
            self.memory_tab.set_managers(memory_manager, memory_ai)
            
            # Mining-Config setzen (GPUs und Coins)
            gpus = self._detect_all_gpus()
            coins = self._get_configured_coins()
            self.memory_tab.set_mining_config(len(gpus), coins)
            
            logger.info(f"💾 Memory Manager Setup: {len(gpus)} GPUs, {len(coins)} Coins")
            
            # Automatische Prüfung bei Start
            memory_ai.evaluate_situation(len(gpus), coins)
            
        except Exception as e:
            logger.error(f"Memory Manager Setup Fehler: {e}")
    
    def _get_configured_coins(self) -> list:
        """Holt alle konfigurierten Coins (NEU! V12.8)"""
        coins = []
        
        try:
            # Aus Wallets-Config lesen
            import json
            from pathlib import Path
            
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallets = data.get("wallets", {})
                    coins = list(wallets.keys())
        except:
            pass
        
        # Fallback: Standard-Coins
        if not coins:
            coins = ["RVN", "ERG", "ETC", "FLUX", "KAS"]
        
        return coins
    
    def on_memory_optimization_started(self):
        """Handler: Memory-Optimierung gestartet (NEU! V12.8)"""
        self.logs_tab.append_log("💾 Speicher-Optimierung gestartet...")
        self.status_bar.showMessage("💾 Optimiere virtuellen Speicher...")
        
        # Mining pausieren
        if self._mining:
            self.logs_tab.append_log("⏸️ Mining pausiert für Speicher-Optimierung")
            self.stop_mining()
    
    def on_memory_optimization_completed(self, success: bool, message: str):
        """Handler: Memory-Optimierung abgeschlossen (NEU! V12.8)"""
        if success:
            self.logs_tab.append_log(f"✅ Speicher-Optimierung: {message}")
        else:
            self.logs_tab.append_log(f"❌ Speicher-Optimierung fehlgeschlagen: {message}")
        
        self.status_bar.showMessage(f"💾 {message[:50]}...")
    
    def on_restart_scheduled(self, seconds: int):
        """Handler: PC-Neustart geplant (NEU! V12.8)"""
        self.logs_tab.append_log(f"🔄 PC-Neustart in {seconds} Sekunden geplant")
        
        # Tray Notification
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                "⚠️ Neustart geplant",
                f"PC wird in {seconds} Sekunden neu gestartet für Speicher-Optimierung",
                self.tray_icon.Warning,
                10000
            )
        
        # Mining sicher beenden
        self.stop_mining()
        
        # Einstellungen speichern
        if hasattr(self.settings_tab, 'save_all_settings'):
            self.settings_tab.save_all_settings()
    
    def check_memory_before_mining(self) -> bool:
        """Prüft Speicher vor Mining-Start (NEU! V12.8)"""
        if not MEMORY_MANAGER_AVAILABLE or not hasattr(self, 'memory_tab') or not self.memory_tab:
            return True
        
        return self.memory_tab.check_before_mining()
    
    def setup_code_repair_integration(self):
        """Initialisiert Code Repair Integration (NEU! V12.8)"""
        if not CODE_REPAIR_AVAILABLE:
            return
        
        try:
            repair_manager = get_repair_manager()
            
            # Callbacks setzen
            def on_code_error(error):
                self.logs_tab.append_log(f"🐛 Code-Fehler erkannt: {error.error_type} in {error.file_path}:{error.line_number}")
            
            def on_fix_applied(action):
                if action.status == "success":
                    self.logs_tab.append_log(f"✅ Code-Fix angewendet: {action.fix.explanation if action.fix else 'N/A'}")
                else:
                    self.logs_tab.append_log(f"❌ Code-Fix fehlgeschlagen: {action.error_message}")
            
            def on_restart_required():
                self.logs_tab.append_log("🔄 Programm-Neustart durch Code Repair angefordert...")
                # Sanfter Shutdown
                QTimer.singleShot(3000, self.restart_application)
            
            repair_manager.on_error_detected = on_code_error
            repair_manager.on_fix_applied = on_fix_applied
            repair_manager.on_restart_required = on_restart_required
            
            logger.info("🔧 Code Repair Integration aktiviert")
            
        except Exception as e:
            logger.error(f"Code Repair Integration Fehler: {e}")
    
    def restart_application(self):
        """Startet die Anwendung neu (NUR Programm, nicht PC!) (NEU! V12.8)"""
        import subprocess
        import sys
        
        self.logs_tab.append_log("🔄 Starte Programm neu...")
        
        # Mining stoppen
        if self._mining:
            self.stop_mining()
        
        # Einstellungen speichern
        try:
            if hasattr(self, 'portfolio_tab') and self.portfolio_tab:
                self.portfolio_tab.stop_monitoring()
        except:
            pass
        
        # Neuen Prozess starten
        python = sys.executable
        script = sys.argv[0]
        
        if sys.platform == "win32":
            subprocess.Popen(f'start "" "{python}" "{script}"', shell=True)
        else:
            subprocess.Popen([python, script], start_new_session=True)
        
        # Aktuellen Prozess beenden
        QTimer.singleShot(500, lambda: os._exit(0))
    
    def on_wallets_updated(self):
        """Handler wenn Wallets aktualisiert wurden"""
        logger.info("Wallets wurden aktualisiert")
        # Flight Sheets Tab könnte aktualisiert werden um neue Wallets anzuzeigen
        self.flight_tab.load_sheets()
    
    def on_auto_switch(self, config: dict):
        """Handler für Auto-Profit Switch - wechselt automatisch zum profitabelsten Coin"""
        logger.info(f"Auto-Switch: Wechsle zu {config.get('coin')} (${config.get('profit_usd', 0):.2f}/Tag)")
        
        coin = config.get('coin', '')
        pool_url = config.get('pool_url', '')
        miner = config.get('miner', 'T-Rex')
        algo = config.get('algorithm', '')
        
        # Mining stoppen falls aktiv
        if self._mining:
            self.stop_mining()
            time.sleep(1)
        
        # Wallet für diesen Coin suchen
        wallet = ""
        
        # 1. Versuch: Exchange Manager
        try:
            if hasattr(self, 'wallets_tab') and self.wallets_tab.exchange_manager:
                wallet_obj = self.wallets_tab.exchange_manager.get_wallet_address(coin)
                if wallet_obj:
                    wallet = wallet_obj.address
        except:
            pass
        
        # 2. Versuch: Direkt aus wallets.json (wichtig für Gate.io Wallets!)
        if not wallet:
            try:
                import json
                from pathlib import Path
                wallets_file = Path("wallets.json")
                if wallets_file.exists():
                    with open(wallets_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        wallets_data = data.get("wallets", {})
                        if coin.upper() in wallets_data:
                            wallet = wallets_data[coin.upper()]
                            # Memo von Wallet trennen (falls vorhanden)
                            if ' ' in wallet:
                                wallet = wallet.split(' ')[0]
                            logger.info(f"Wallet für {coin} aus wallets.json geladen: {wallet[:20]}...")
            except Exception as e:
                logger.debug(f"wallets.json Fallback: {e}")
        
        # 3. Versuch: Wallets aus COIN_CONFIGS
        if not wallet:
            from coin_config import COIN_CONFIGS
            if coin in COIN_CONFIGS:
                wallet = COIN_CONFIGS[coin].get('wallet', '')
        
        if not wallet:
            logger.warning(f"Keine Wallet für {coin} gefunden - bitte manuell konfigurieren!")
            QMessageBox.warning(
                self, "Wallet fehlt", 
                f"Keine Wallet-Adresse für {coin} gefunden!\n\n"
                f"Bitte im 'Wallets' Tab oder in coin_config.py konfigurieren."
            )
            return
        
        # Mining starten
        self._current_coin = coin
        self.dashboard.coin_label.setText(coin)
        
        # Auto-Profit Tab synchronisieren
        if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
            self.auto_profit_tab.set_current_coin(coin)
        
        # Miner-Befehl zusammenbauen
        worker = "Rig_D"
        
        logger.info(f"Auto-Switch Mining: {coin} auf {pool_url} mit {miner}")
        
        # Miner-String zu MinerType konvertieren
        from miner_api import MinerType
        miner_type_map = {
            'trex': MinerType.TREX,
            't-rex': MinerType.TREX,
            'lolminer': MinerType.LOLMINER,
            'nbminer': MinerType.NBMINER,
            'gminer': MinerType.GMINER,
            'teamredminer': MinerType.TEAMREDMINER,
            'phoenixminer': MinerType.PHOENIXMINER,
            'rigel': MinerType.RIGEL,
            'srbminer': MinerType.SRBMINER,
            'xmrig': MinerType.XMRIG,
        }
        miner_type = miner_type_map.get(miner.lower().replace('-', '').replace(' ', ''), MinerType.TREX)
        
        # Miner starten
        try:
            # MSI Afterburner OC automatisch anwenden
            if self.msi_ab_manager and self.msi_ab_manager.is_installed:
                if not self.msi_ab_manager.check_running():
                    logger.info("MSI Afterburner wird automatisch gestartet...")
                    self.msi_ab_manager.start_afterburner(minimized=True)
                    time.sleep(2)
                
                success_oc, msg_oc = self.msi_ab_manager.apply_mining_profile(coin)
                if success_oc:
                    self.logs_tab.append_log(f"✅ Auto-OC: {msg_oc}")
            
            success = self.miner_manager.start_miner(
                miner_type=miner_type,
                algorithm=algo,
                pool_url=pool_url,
                wallet=wallet,
                worker=worker,
            )
            
            if success:
                self._mining = True
                self._start_time = time.time()
                self._current_coin = coin  # WICHTIG: Aktuellen Coin setzen!
                self.dashboard.start_btn.setEnabled(False)
                self.dashboard.stop_btn.setEnabled(True)
                self.status_bar.showMessage(f"Mining {coin} auf {config.get('pool_name', 'Pool')}")
                
                # WICHTIG: Stats Worker starten für API-Abfrage!
                try:
                    if not self.miner_stats_worker.isRunning():
                        self.miner_stats_worker._running = True
                        self.miner_stats_worker.start()
                        logger.info("MinerStatsWorker gestartet für API-Abfrage")
                except Exception as e:
                    logger.warning(f"MinerStatsWorker Start fehlgeschlagen: {e}")
                
                # Auto-Profit Tab aktualisieren
                if hasattr(self, 'auto_profit_tab'):
                    self.auto_profit_tab.set_current_coin(coin, config.get('profit_usd', 0))
                
                # Tray Icon aktualisieren
                self.tray_icon.set_mining_state(True)
                self.tray_icon.notify_miner_started(coin, config.get('pool_name', 'Pool'))
                
                # Nach 5 Sekunden prüfen ob Miner noch läuft (OHNE GUI zu blockieren!)
                QTimer.singleShot(5000, lambda c=coin, m=miner: self._check_miner_running(c, m))
            else:
                logger.error(f"Miner {miner} konnte nicht gestartet werden")
                self._try_next_coin(coin, f"Miner {miner} nicht gefunden oder Fehler")
                
        except Exception as e:
            logger.error(f"Auto-Switch Mining Fehler: {e}")
            self._try_next_coin(coin, str(e))
    
    def _check_miner_running(self, coin: str, miner: str):
        """Prüft ob der Miner noch läuft (wird verzögert aufgerufen)"""
        if not self.miner_manager.is_mining():
            logger.error(f"Miner {miner} ist nach Start abgestürzt!")
            self._try_next_coin(coin, f"Miner {miner} abgestürzt")
    
    def _try_next_coin(self, failed_coin: str, reason: str):
        """Versucht den nächsten profitablen Coin wenn der aktuelle fehlschlägt"""
        logger.warning(f"Coin {failed_coin} fehlgeschlagen: {reason}")
        logger.info("Versuche nächsten profitablen Coin...")
        
        # Blacklist für fehlgeschlagene Coins (verhindert Endlosschleife)
        if not hasattr(self, '_failed_coins'):
            self._failed_coins = set()
        self._failed_coins.add(failed_coin)
        
        # Nächsten Coin aus Auto-Profit Tab holen
        if hasattr(self, 'auto_profit_tab') and self.auto_profit_tab:
            top_coins = self.auto_profit_tab.get_top_coins()
            
            for coin_config in top_coins:
                next_coin = coin_config.get('coin', '')
                # Überspringe fehlgeschlagene Coins!
                if next_coin and next_coin not in self._failed_coins:
                    # Prüfen ob Wallet vorhanden
                    wallet = self._get_wallet_for_coin(next_coin)
                    if wallet:
                        logger.info(f"Wechsle zu nächstem Coin: {next_coin}")
                        self.logs_tab.append_log(f"⚠️ {failed_coin} fehlgeschlagen: {reason}")
                        self.logs_tab.append_log(f"➡️ Wechsle zu {next_coin}")
                        
                        # Neuen Coin starten (verzögert)
                        QTimer.singleShot(2000, lambda c=coin_config: self.on_auto_switch(c))
                        return
                    else:
                        logger.debug(f"Überspringe {next_coin} - keine Wallet")
        
        # Kein alternativer Coin gefunden
        logger.error("Kein alternativer Coin verfügbar!")
        self.logs_tab.append_log(f"❌ {failed_coin} fehlgeschlagen und kein Backup-Coin verfügbar")
        self.logs_tab.append_log(f"⏳ Blacklist: {', '.join(self._failed_coins)}")
        self.status_bar.showMessage("Mining gestoppt - kein Coin verfügbar")
        
        # Blacklist nach 5 Minuten zurücksetzen
        QTimer.singleShot(300000, self._clear_failed_coins)
    
    def _clear_failed_coins(self):
        """Setzt die Blacklist zurück"""
        if hasattr(self, '_failed_coins'):
            logger.info(f"Blacklist zurückgesetzt (war: {self._failed_coins})")
            self._failed_coins.clear()
    
    def _get_wallet_for_coin(self, coin: str) -> str:
        """Holt Wallet für einen Coin aus allen Quellen"""
        wallet = ""
        
        # 1. Exchange Manager
        try:
            if hasattr(self, 'wallets_tab') and self.wallets_tab.exchange_manager:
                wallet_obj = self.wallets_tab.exchange_manager.get_wallet_address(coin)
                if wallet_obj:
                    wallet = wallet_obj.address
        except:
            pass
        
        # 2. wallets.json
        if not wallet:
            try:
                import json
                from pathlib import Path
                wallets_file = Path("wallets.json")
                if wallets_file.exists():
                    with open(wallets_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        wallets_data = data.get("wallets", {})
                        if coin.upper() in wallets_data:
                            wallet = wallets_data[coin.upper()]
            except:
                pass
        
        # 3. COIN_CONFIGS
        if not wallet:
            try:
                from coin_config import COIN_CONFIGS
                if coin in COIN_CONFIGS:
                    wallet = COIN_CONFIGS[coin].get('wallet', '')
            except:
                pass
        
        # Memo von Wallet trennen (falls vorhanden)
        if wallet and ' ' in wallet:
            wallet = wallet.split(' ')[0]
        
        return wallet
    
    def _on_dashboard_oc_changed(self, button):
        """Handler für Dashboard OC-Profile Buttons"""
        button_id = self.dashboard.oc_button_group.id(button)
        profile_map = {0: "low", 1: "medium", 2: "high"}
        profile = profile_map.get(button_id, "medium")
        
        logger.info(f"Dashboard OC: Wechsle zu Profile '{profile}'")
        
        try:
            # OC-Manager verwenden
            if hasattr(self, 'oc_manager') and self.oc_manager:
                for gpu_idx in range(self.oc_manager.gpu_count):
                    self.oc_manager.apply_profile(gpu_idx, profile)
                
                self.status_bar.showMessage(f"OC-Profile '{profile.upper()}' angewendet", 3000)
            
            # Multi-GPU Tab synchronisieren falls vorhanden
            if hasattr(self, 'multi_gpu_tab') and self.multi_gpu_tab:
                # Profile in Cards aktualisieren
                pass  # Cards haben eigene OC-Buttons
            
        except Exception as e:
            logger.error(f"OC-Profile Fehler: {e}")
            self.status_bar.showMessage(f"OC-Fehler: {e}", 5000)
    
    def _on_dashboard_auto_oc_changed(self, state):
        """Handler für Dashboard Auto-OC Checkbox"""
        enabled = state == Qt.CheckState.Checked.value
        logger.info(f"Dashboard Auto-OC: {'aktiviert' if enabled else 'deaktiviert'}")
        
        try:
            if hasattr(self, 'oc_manager') and self.oc_manager:
                # Auto-OC Einstellung speichern
                self.oc_manager.auto_oc_enabled = enabled
                
                if enabled:
                    self.status_bar.showMessage("Auto-OC aktiviert - passt OC automatisch an Temperatur an", 3000)
                else:
                    self.status_bar.showMessage("Auto-OC deaktiviert", 3000)
                    
        except Exception as e:
            logger.error(f"Auto-OC Fehler: {e}")
    
    def show_from_tray(self):
        """Zeigt Fenster aus Tray"""
        self.showNormal()
        self.activateWindow()
    
    def quit_app(self):
        """Beendet Anwendung sauber"""
        # Mining stoppen
        self.stop_mining()
        
        # Multi-GPU Mining stoppen (NEU! V12.8)
        if MULTI_GPU_AVAILABLE and hasattr(self, 'multi_gpu_tab') and self.multi_gpu_tab:
            try:
                self.multi_gpu_tab.cleanup()
            except:
                pass
        
        # Portfolio stoppen (NEU! V12.8)
        if PORTFOLIO_AVAILABLE and hasattr(self, 'portfolio_tab') and self.portfolio_tab:
            try:
                self.portfolio_tab.stop_monitoring()
            except:
                pass
        
        # Log-Timer stoppen
        if hasattr(self, '_log_timer'):
            self._log_timer.stop()
        
        # Alle Miner-Prozesse killen (Sicherheit)
        self.miner_manager.kill_all_miners()
        
        # Workers stoppen
        self.monitor_worker.stop()
        self.miner_stats_worker._running = False
        
        # GPU Monitor stoppen
        self.gpu_monitor.stop()
        
        # OC zurücksetzen
        self.oc_manager.reset_all_gpus()
        self.oc_manager.shutdown()
        
        QApplication.quit()
    
    def closeEvent(self, event):
        """Minimiert ins Tray statt zu schließen"""
        if self.settings_tab.minimize_to_tray_check.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.show_notification(
                "Minimiert",
                "Mining läuft im Hintergrund weiter"
            )
        else:
            self.quit_app()
            event.accept()


def main():
    """Haupteinstiegspunkt"""
    app = QApplication(sys.argv)
    app.setApplicationName("GPU Mining Profit Switcher")
    app.setOrganizationName("MiningTools")
    
    # Fenster erstellen und anzeigen
    window = MiningMainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
