#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Optimizer Widget - Live GUI für automatische GPU-Optimierung
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Live Temperatur/Hashrate/Power Anzeige
- Automatische OC-Anpassung visualisiert
- Performance-Mode Auswahl pro GPU
- Effizienz-Ranking
- Benchmark-Funktion
- Multi-GPU Support
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QGroupBox, QFrame, QScrollArea, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSlider, QSpinBox, QCheckBox, QTabWidget
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette

try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except ImportError:
    HAS_PYQTGRAPH = False

from gpu_auto_optimizer import (
    GPUAutoOptimizer, get_gpu_optimizer,
    ThermalState, PerformanceMode, GPUState
)
from gpu_profit_manager import (
    GPUProfitManager, get_gpu_profit_manager,
    OCProfile, OCSettings
)

logger = logging.getLogger(__name__)


# ============================================================================
# FARBEN
# ============================================================================

COLORS = {
    "cold": "#3498db",      # Blau
    "cool": "#2ecc71",      # Grün
    "optimal": "#27ae60",   # Dunkelgrün
    "warm": "#f39c12",      # Orange
    "hot": "#e74c3c",       # Rot
    "critical": "#c0392b",  # Dunkelrot
    
    "low": "#3498db",       # Blau
    "medium": "#f39c12",    # Orange
    "high": "#e74c3c",      # Rot
    
    "efficiency": "#9b59b6",   # Lila
    "balanced": "#3498db",     # Blau
    "performance": "#e74c3c",  # Rot
}


def get_temp_color(temp: int) -> str:
    """Gibt Farbe basierend auf Temperatur zurück"""
    if temp >= 85:
        return COLORS["critical"]
    elif temp >= 80:
        return COLORS["hot"]
    elif temp >= 70:
        return COLORS["warm"]
    elif temp >= 60:
        return COLORS["optimal"]
    elif temp >= 50:
        return COLORS["cool"]
    else:
        return COLORS["cold"]


# ============================================================================
# GPU CARD WIDGET (Einzelne GPU)
# ============================================================================

class GPUCardWidget(QFrame):
    """Widget für eine einzelne GPU mit allen Infos"""
    
    profile_changed = Signal(int, str)  # gpu_index, new_profile
    mode_changed = Signal(int, str)     # gpu_index, new_mode
    benchmark_requested = Signal(int)   # gpu_index
    
    def __init__(self, gpu_index: int, gpu_name: str, parent=None):
        super().__init__(parent)
        self.gpu_index = gpu_index
        self.gpu_name = gpu_name
        
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            GPUCardWidget {
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        self._setup_ui()
        
        # Temperatur-Historie für Chart
        self.temp_history: List[int] = []
        self.hashrate_history: List[float] = []
        self.max_history = 60
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        # GPU Name & Index
        self.lbl_name = QLabel(f"GPU {self.gpu_index}: {self.gpu_name}")
        self.lbl_name.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_name.setStyleSheet("color: #fff;")
        header.addWidget(self.lbl_name)
        
        header.addStretch()
        
        # Status-Indikator
        self.lbl_status = QLabel("●")
        self.lbl_status.setFont(QFont("Segoe UI", 16))
        self.lbl_status.setStyleSheet(f"color: {COLORS['optimal']};")
        header.addWidget(self.lbl_status)
        
        layout.addLayout(header)
        
        # === HAUPT-METRIKEN ===
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(10)
        
        # Temperatur
        self.lbl_temp_title = QLabel("🌡️ Temperatur")
        self.lbl_temp_title.setStyleSheet("color: #aaa;")
        self.lbl_temp = QLabel("--°C")
        self.lbl_temp.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.lbl_temp.setStyleSheet("color: #2ecc71;")
        self.lbl_temp_trend = QLabel("→ stabil")
        self.lbl_temp_trend.setStyleSheet("color: #888;")
        
        metrics_grid.addWidget(self.lbl_temp_title, 0, 0)
        metrics_grid.addWidget(self.lbl_temp, 1, 0)
        metrics_grid.addWidget(self.lbl_temp_trend, 2, 0)
        
        # Hashrate
        self.lbl_hash_title = QLabel("⚡ Hashrate")
        self.lbl_hash_title.setStyleSheet("color: #aaa;")
        self.lbl_hashrate = QLabel("-- MH/s")
        self.lbl_hashrate.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.lbl_hashrate.setStyleSheet("color: #3498db;")
        self.lbl_stability = QLabel("Stabilität: --%")
        self.lbl_stability.setStyleSheet("color: #888;")
        
        metrics_grid.addWidget(self.lbl_hash_title, 0, 1)
        metrics_grid.addWidget(self.lbl_hashrate, 1, 1)
        metrics_grid.addWidget(self.lbl_stability, 2, 1)
        
        # Power & Effizienz
        self.lbl_power_title = QLabel("🔌 Power")
        self.lbl_power_title.setStyleSheet("color: #aaa;")
        self.lbl_power = QLabel("-- W")
        self.lbl_power.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.lbl_power.setStyleSheet("color: #f39c12;")
        self.lbl_efficiency = QLabel("Effizienz: -- H/W")
        self.lbl_efficiency.setStyleSheet("color: #888;")
        
        metrics_grid.addWidget(self.lbl_power_title, 0, 2)
        metrics_grid.addWidget(self.lbl_power, 1, 2)
        metrics_grid.addWidget(self.lbl_efficiency, 2, 2)
        
        layout.addLayout(metrics_grid)
        
        # === TEMPERATUR-FORTSCHRITT ===
        temp_bar_layout = QHBoxLayout()
        temp_bar_layout.addWidget(QLabel("0°C"))
        
        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(0, 100)
        self.temp_bar.setValue(0)
        self.temp_bar.setTextVisible(False)
        self.temp_bar.setFixedHeight(12)
        self.temp_bar.setStyleSheet("""
            QProgressBar {
                background-color: #444;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background-color: #2ecc71;
                border-radius: 6px;
            }
        """)
        temp_bar_layout.addWidget(self.temp_bar)
        temp_bar_layout.addWidget(QLabel("100°C"))
        
        layout.addLayout(temp_bar_layout)
        
        # === PROFILE & MODE AUSWAHL ===
        controls = QHBoxLayout()
        
        # OC Profile
        profile_group = QVBoxLayout()
        profile_group.addWidget(QLabel("OC Profile:"))
        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["LOW", "MEDIUM", "HIGH"])
        self.combo_profile.setCurrentIndex(1)  # Medium default
        self.combo_profile.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                padding: 5px 10px;
                border: 1px solid #555;
                border-radius: 4px;
                min-width: 100px;
            }
        """)
        self.combo_profile.currentTextChanged.connect(self._on_profile_change)
        profile_group.addWidget(self.combo_profile)
        controls.addLayout(profile_group)
        
        # Performance Mode
        mode_group = QVBoxLayout()
        mode_group.addWidget(QLabel("Modus:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["⚡ EFFICIENCY", "⚖️ BALANCED", "🚀 PERFORMANCE"])
        self.combo_mode.setCurrentIndex(1)  # Balanced default
        self.combo_mode.setStyleSheet("""
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                padding: 5px 10px;
                border: 1px solid #555;
                border-radius: 4px;
                min-width: 140px;
            }
        """)
        self.combo_mode.currentTextChanged.connect(self._on_mode_change)
        mode_group.addWidget(self.combo_mode)
        controls.addLayout(mode_group)
        
        # Auto-Optimize Toggle
        self.chk_auto = QCheckBox("Auto-Optimize")
        self.chk_auto.setChecked(True)
        self.chk_auto.setStyleSheet("color: #aaa;")
        controls.addWidget(self.chk_auto)
        
        controls.addStretch()
        
        # Benchmark Button
        self.btn_benchmark = QPushButton("🔬 Benchmark")
        self.btn_benchmark.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        self.btn_benchmark.clicked.connect(lambda: self.benchmark_requested.emit(self.gpu_index))
        controls.addWidget(self.btn_benchmark)
        
        layout.addLayout(controls)
        
        # === OC SETTINGS ANZEIGE ===
        self.oc_frame = QFrame()
        self.oc_frame.setStyleSheet("background-color: #252525; border-radius: 4px; padding: 5px;")
        oc_layout = QGridLayout(self.oc_frame)
        oc_layout.setSpacing(5)
        
        oc_layout.addWidget(QLabel("Core:"), 0, 0)
        self.lbl_oc_core = QLabel("+0 MHz")
        self.lbl_oc_core.setStyleSheet("color: #3498db; font-weight: bold;")
        oc_layout.addWidget(self.lbl_oc_core, 0, 1)
        
        oc_layout.addWidget(QLabel("Mem:"), 0, 2)
        self.lbl_oc_mem = QLabel("+0 MHz")
        self.lbl_oc_mem.setStyleSheet("color: #e74c3c; font-weight: bold;")
        oc_layout.addWidget(self.lbl_oc_mem, 0, 3)
        
        oc_layout.addWidget(QLabel("PL:"), 0, 4)
        self.lbl_oc_pl = QLabel("100%")
        self.lbl_oc_pl.setStyleSheet("color: #f39c12; font-weight: bold;")
        oc_layout.addWidget(self.lbl_oc_pl, 0, 5)
        
        oc_layout.addWidget(QLabel("Fan:"), 0, 6)
        self.lbl_oc_fan = QLabel("Auto")
        self.lbl_oc_fan.setStyleSheet("color: #2ecc71; font-weight: bold;")
        oc_layout.addWidget(self.lbl_oc_fan, 0, 7)
        
        layout.addWidget(self.oc_frame)
        
        # === AKTUELLER COIN ===
        coin_layout = QHBoxLayout()
        self.lbl_coin = QLabel("Coin: -")
        self.lbl_coin.setStyleSheet("color: #aaa;")
        coin_layout.addWidget(self.lbl_coin)
        
        self.lbl_revenue = QLabel("Revenue: $--.--/Tag")
        self.lbl_revenue.setStyleSheet("color: #2ecc71; font-weight: bold;")
        coin_layout.addWidget(self.lbl_revenue)
        
        coin_layout.addStretch()
        
        self.lbl_last_action = QLabel("")
        self.lbl_last_action.setStyleSheet("color: #888; font-style: italic;")
        coin_layout.addWidget(self.lbl_last_action)
        
        layout.addLayout(coin_layout)
    
    def _on_profile_change(self, text: str):
        profile = text.lower()
        self.profile_changed.emit(self.gpu_index, profile)
    
    def _on_mode_change(self, text: str):
        if "EFFICIENCY" in text:
            mode = "efficiency"
        elif "PERFORMANCE" in text:
            mode = "performance"
        else:
            mode = "balanced"
        self.mode_changed.emit(self.gpu_index, mode)
    
    def update_state(self, state: GPUState, stability: float = 100.0, trend: str = "stable"):
        """Aktualisiert alle Anzeigen"""
        # Temperatur
        temp = state.temperature
        self.lbl_temp.setText(f"{temp}°C")
        temp_color = get_temp_color(temp)
        self.lbl_temp.setStyleSheet(f"color: {temp_color};")
        
        # Temperatur-Bar
        self.temp_bar.setValue(min(100, temp))
        self.temp_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #444;
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {temp_color};
                border-radius: 6px;
            }}
        """)
        
        # Trend
        trend_icons = {"rising": "↑ steigend", "falling": "↓ fallend", "stable": "→ stabil"}
        trend_colors = {"rising": "#e74c3c", "falling": "#3498db", "stable": "#888"}
        self.lbl_temp_trend.setText(trend_icons.get(trend, "→"))
        self.lbl_temp_trend.setStyleSheet(f"color: {trend_colors.get(trend, '#888')};")
        
        # Hashrate
        self.lbl_hashrate.setText(f"{state.hashrate:.2f} {state.hashrate_unit}")
        
        # Stabilität
        stab_color = "#2ecc71" if stability > 95 else "#f39c12" if stability > 85 else "#e74c3c"
        self.lbl_stability.setText(f"Stabilität: {stability:.1f}%")
        self.lbl_stability.setStyleSheet(f"color: {stab_color};")
        
        # Power
        self.lbl_power.setText(f"{state.power_draw} W")
        
        # Effizienz
        if state.efficiency > 0:
            self.lbl_efficiency.setText(f"Effizienz: {state.efficiency:.3f} H/W")
        
        # Status-Indikator
        status_colors = {
            ThermalState.COLD: COLORS["cold"],
            ThermalState.COOL: COLORS["cool"],
            ThermalState.OPTIMAL: COLORS["optimal"],
            ThermalState.WARM: COLORS["warm"],
            ThermalState.HOT: COLORS["hot"],
            ThermalState.CRITICAL: COLORS["critical"],
        }
        self.lbl_status.setStyleSheet(f"color: {status_colors.get(state.thermal_state, '#888')};")
        
        # Profil-Combo aktualisieren (ohne Signal)
        self.combo_profile.blockSignals(True)
        self.combo_profile.setCurrentText(state.current_profile.upper())
        self.combo_profile.blockSignals(False)
        
        # Coin
        if state.current_coin:
            self.lbl_coin.setText(f"Coin: {state.current_coin}")
        
        # Historie aktualisieren
        self.temp_history.append(temp)
        self.hashrate_history.append(state.hashrate)
        if len(self.temp_history) > self.max_history:
            self.temp_history = self.temp_history[-self.max_history:]
            self.hashrate_history = self.hashrate_history[-self.max_history:]
    
    def update_oc_settings(self, settings: OCSettings):
        """Aktualisiert OC-Settings Anzeige"""
        self.lbl_oc_core.setText(f"{settings.core_clock:+d} MHz")
        self.lbl_oc_mem.setText(f"{settings.mem_clock:+d} MHz")
        self.lbl_oc_pl.setText(f"{settings.power_limit}%")
        self.lbl_oc_fan.setText(f"{settings.fan_speed}%")
    
    def show_action(self, action: str):
        """Zeigt letzte Aktion an"""
        self.lbl_last_action.setText(f"⚡ {action}")
        # Nach 5 Sekunden ausblenden
        QTimer.singleShot(5000, lambda: self.lbl_last_action.setText(""))
    
    def set_revenue(self, revenue: float):
        """Setzt Revenue-Anzeige"""
        self.lbl_revenue.setText(f"Revenue: ${revenue:.2f}/Tag")


# ============================================================================
# EFFIZIENZ-RANKING WIDGET
# ============================================================================

class EfficiencyRankingWidget(QWidget):
    """Widget für GPU-Effizienz-Ranking"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Titel
        title = QLabel("📊 GPU Effizienz-Ranking")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        layout.addWidget(title)
        
        # Tabelle
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Rank", "GPU", "Coin", "Hashrate", "Power", "Effizienz", "Temp"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: white;
                gridline-color: #444;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 5px;
                border: 1px solid #444;
            }
        """)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)
    
    def update_ranking(self, ranking: List[Dict]):
        """Aktualisiert das Ranking"""
        self.table.setRowCount(len(ranking))
        
        for row, data in enumerate(ranking):
            # Rank
            rank_item = QTableWidgetItem(f"#{row + 1}")
            rank_item.setTextAlignment(Qt.AlignCenter)
            if row == 0:
                rank_item.setBackground(QColor("#27ae60"))
            self.table.setItem(row, 0, rank_item)
            
            # GPU
            self.table.setItem(row, 1, QTableWidgetItem(data.get("name", "")))
            
            # Coin
            self.table.setItem(row, 2, QTableWidgetItem(data.get("coin", "-")))
            
            # Hashrate
            hr = data.get("hashrate", 0)
            unit = data.get("hashrate_unit", "MH/s")
            self.table.setItem(row, 3, QTableWidgetItem(f"{hr:.2f} {unit}"))
            
            # Power
            self.table.setItem(row, 4, QTableWidgetItem(f"{data.get('power', 0)}W"))
            
            # Effizienz
            eff = data.get("efficiency", 0)
            eff_item = QTableWidgetItem(f"{eff:.4f}")
            eff_item.setForeground(QColor("#9b59b6"))
            self.table.setItem(row, 5, eff_item)
            
            # Temp
            temp = data.get("temperature", 0)
            temp_item = QTableWidgetItem(f"{temp}°C")
            temp_item.setForeground(QColor(get_temp_color(temp)))
            self.table.setItem(row, 6, temp_item)


# ============================================================================
# HAUPT-OPTIMIZER WIDGET
# ============================================================================

class GPUOptimizerWidget(QWidget):
    """Haupt-Widget für GPU Auto-Optimizer"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.optimizer = get_gpu_optimizer()
        self.profit_manager = get_gpu_profit_manager()
        
        # GPU Cards
        self.gpu_cards: Dict[int, GPUCardWidget] = {}
        
        self._setup_ui()
        self._connect_signals()
        
        # Update Timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_all)
        self.update_timer.start(2000)  # Alle 2 Sekunden
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        title = QLabel("🎮 GPU Auto-Optimizer")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #fff;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Global Auto-Optimize
        self.chk_global_auto = QCheckBox("Global Auto-Optimize")
        self.chk_global_auto.setChecked(True)
        self.chk_global_auto.setStyleSheet("color: #aaa; font-size: 12px;")
        header.addWidget(self.chk_global_auto)
        
        # Refresh Button
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._refresh_gpus)
        btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                padding: 8px 15px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        header.addWidget(btn_refresh)
        
        layout.addLayout(header)
        
        # === TABS ===
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #1e1e1e;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaa;
                padding: 10px 20px;
                border: 1px solid #444;
            }
            QTabBar::tab:selected {
                background-color: #3d3d3d;
                color: white;
            }
        """)
        
        # Tab 1: GPU Cards
        self.gpu_container = QWidget()
        self.gpu_layout = QVBoxLayout(self.gpu_container)
        self.gpu_layout.setSpacing(15)
        
        # Scroll Area für GPU Cards
        scroll = QScrollArea()
        scroll.setWidget(self.gpu_container)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        self.tabs.addTab(scroll, "🖥️ GPUs")
        
        # Tab 2: Effizienz-Ranking
        self.efficiency_widget = EfficiencyRankingWidget()
        self.tabs.addTab(self.efficiency_widget, "📊 Effizienz")
        
        # Tab 3: Benchmark
        self.benchmark_widget = self._create_benchmark_tab()
        self.tabs.addTab(self.benchmark_widget, "🔬 Benchmark")
        
        # Tab 4: Einstellungen
        self.settings_widget = self._create_settings_tab()
        self.tabs.addTab(self.settings_widget, "⚙️ Settings")
        
        layout.addWidget(self.tabs)
        
        # === STATUS BAR ===
        status_bar = QHBoxLayout()
        
        self.lbl_status = QLabel("Bereit")
        self.lbl_status.setStyleSheet("color: #888;")
        status_bar.addWidget(self.lbl_status)
        
        status_bar.addStretch()
        
        self.lbl_total_hashrate = QLabel("Total: -- MH/s")
        self.lbl_total_hashrate.setStyleSheet("color: #3498db; font-weight: bold;")
        status_bar.addWidget(self.lbl_total_hashrate)
        
        self.lbl_total_power = QLabel("Power: -- W")
        self.lbl_total_power.setStyleSheet("color: #f39c12; font-weight: bold;")
        status_bar.addWidget(self.lbl_total_power)
        
        self.lbl_avg_efficiency = QLabel("Eff: -- H/W")
        self.lbl_avg_efficiency.setStyleSheet("color: #9b59b6; font-weight: bold;")
        status_bar.addWidget(self.lbl_avg_efficiency)
        
        layout.addLayout(status_bar)
        
        # Initial GPUs laden
        self._refresh_gpus()
    
    def _create_benchmark_tab(self) -> QWidget:
        """Erstellt Benchmark-Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info
        info = QLabel(
            "Der Auto-Benchmark testet alle OC-Profile (Low/Medium/High) für jeden Coin\n"
            "und findet automatisch die effizientesten Einstellungen."
        )
        info.setStyleSheet("color: #aaa; padding: 10px;")
        layout.addWidget(info)
        
        # GPU Auswahl
        gpu_select = QHBoxLayout()
        gpu_select.addWidget(QLabel("GPU:"))
        self.combo_bench_gpu = QComboBox()
        self.combo_bench_gpu.setMinimumWidth(200)
        gpu_select.addWidget(self.combo_bench_gpu)
        
        gpu_select.addWidget(QLabel("Coin:"))
        self.combo_bench_coin = QComboBox()
        self.combo_bench_coin.addItems(["RVN", "ERG", "ETC", "KAS", "FLUX", "ALPH", "BEAM", "FIRO"])
        self.combo_bench_coin.setMinimumWidth(100)
        gpu_select.addWidget(self.combo_bench_coin)
        
        gpu_select.addStretch()
        
        self.btn_start_bench = QPushButton("▶️ Benchmark starten")
        self.btn_start_bench.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        gpu_select.addWidget(self.btn_start_bench)
        
        layout.addLayout(gpu_select)
        
        # Benchmark Results
        self.bench_results = QTableWidget()
        self.bench_results.setColumnCount(6)
        self.bench_results.setHorizontalHeaderLabels([
            "Profile", "Hashrate", "Power", "Temp", "Effizienz", "Stabil"
        ])
        self.bench_results.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.bench_results.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                color: white;
            }
        """)
        layout.addWidget(self.bench_results)
        
        # Empfehlung
        self.lbl_bench_recommendation = QLabel("")
        self.lbl_bench_recommendation.setStyleSheet(
            "color: #2ecc71; font-size: 14px; font-weight: bold; padding: 10px;"
        )
        layout.addWidget(self.lbl_bench_recommendation)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Erstellt Settings-Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Temperatur-Grenzen
        temp_group = QGroupBox("Temperatur-Grenzen")
        temp_group.setStyleSheet("QGroupBox { color: white; }")
        temp_layout = QGridLayout(temp_group)
        
        temp_layout.addWidget(QLabel("Ziel-Temperatur:"), 0, 0)
        self.spin_target_temp = QSpinBox()
        self.spin_target_temp.setRange(50, 80)
        self.spin_target_temp.setValue(68)
        self.spin_target_temp.setSuffix(" °C")
        temp_layout.addWidget(self.spin_target_temp, 0, 1)
        
        temp_layout.addWidget(QLabel("Max-Temperatur:"), 1, 0)
        self.spin_max_temp = QSpinBox()
        self.spin_max_temp.setRange(70, 90)
        self.spin_max_temp.setValue(80)
        self.spin_max_temp.setSuffix(" °C")
        temp_layout.addWidget(self.spin_max_temp, 1, 1)
        
        temp_layout.addWidget(QLabel("Kritische Temperatur:"), 2, 0)
        self.spin_critical_temp = QSpinBox()
        self.spin_critical_temp.setRange(80, 95)
        self.spin_critical_temp.setValue(85)
        self.spin_critical_temp.setSuffix(" °C")
        temp_layout.addWidget(self.spin_critical_temp, 2, 1)
        
        layout.addWidget(temp_group)
        
        # Optimierungs-Einstellungen
        opt_group = QGroupBox("Optimierung")
        opt_group.setStyleSheet("QGroupBox { color: white; }")
        opt_layout = QGridLayout(opt_group)
        
        opt_layout.addWidget(QLabel("Update-Intervall:"), 0, 0)
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(1, 60)
        self.spin_interval.setValue(5)
        self.spin_interval.setSuffix(" Sek")
        opt_layout.addWidget(self.spin_interval, 0, 1)
        
        opt_layout.addWidget(QLabel("Profil-Cooldown:"), 1, 0)
        self.spin_cooldown = QSpinBox()
        self.spin_cooldown.setRange(10, 120)
        self.spin_cooldown.setValue(30)
        self.spin_cooldown.setSuffix(" Sek")
        opt_layout.addWidget(self.spin_cooldown, 1, 1)
        
        self.chk_auto_switch_coin = QCheckBox("Automatisch besten Coin wählen")
        self.chk_auto_switch_coin.setChecked(False)
        opt_layout.addWidget(self.chk_auto_switch_coin, 2, 0, 1, 2)
        
        layout.addWidget(opt_group)
        
        layout.addStretch()
        
        # Speichern Button
        btn_save = QPushButton("💾 Einstellungen speichern")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
            }
        """)
        layout.addWidget(btn_save)
        
        return widget
    
    def _connect_signals(self):
        """Verbindet Signals"""
        # Optimizer Callbacks
        self.optimizer.on_profile_change = self._on_profile_changed
        self.optimizer.on_thermal_warning = self._on_thermal_warning
        self.optimizer.on_optimization = self._on_optimization
    
    def _refresh_gpus(self):
        """Erkennt und lädt alle GPUs"""
        # GPUs vom Profit Manager holen
        self.profit_manager.detect_gpus()
        
        # Alte Cards entfernen
        for card in self.gpu_cards.values():
            card.deleteLater()
        self.gpu_cards.clear()
        
        # Neue Cards erstellen
        for idx, gpu in self.profit_manager.gpus.items():
            card = GPUCardWidget(idx, gpu.hashrate_no_name, self)
            card.profile_changed.connect(self._on_card_profile_changed)
            card.mode_changed.connect(self._on_card_mode_changed)
            card.benchmark_requested.connect(self._on_benchmark_requested)
            
            self.gpu_cards[idx] = card
            self.gpu_layout.addWidget(card)
            
            # Initialen State setzen
            if idx not in self.optimizer.gpu_states:
                self.optimizer.update_gpu_state(
                    gpu_index=idx,
                    gpu_name=gpu.name,
                    temperature=0,
                    power_draw=0,
                    hashrate=0
                )
        
        # Benchmark GPU-Combo aktualisieren
        self.combo_bench_gpu.clear()
        for idx, gpu in self.profit_manager.gpus.items():
            self.combo_bench_gpu.addItem(f"GPU {idx}: {gpu.hashrate_no_name}", idx)
        
        self.lbl_status.setText(f"{len(self.gpu_cards)} GPU(s) erkannt")
    
    def _update_all(self):
        """Aktualisiert alle Anzeigen"""
        if not self.chk_global_auto.isChecked():
            return
        
        total_hashrate = 0
        total_power = 0
        
        for idx, card in self.gpu_cards.items():
            if idx in self.optimizer.gpu_states:
                state = self.optimizer.gpu_states[idx]
                stability = self.optimizer.get_hashrate_stability(idx)
                trend = self.optimizer.get_temp_trend(idx)
                
                card.update_state(state, stability, trend)
                
                total_hashrate += state.hashrate
                total_power += state.power_draw
                
                # OC-Settings aktualisieren
                if idx in self.profit_manager.gpus:
                    gpu = self.profit_manager.gpus[idx]
                    if state.current_coin and state.current_coin in gpu.coin_profiles:
                        oc = gpu.get_oc_for_coin(state.current_coin)
                        if oc:
                            card.update_oc_settings(oc)
        
        # Totals aktualisieren
        self.lbl_total_hashrate.setText(f"Total: {total_hashrate:.2f} MH/s")
        self.lbl_total_power.setText(f"Power: {total_power} W")
        
        if total_power > 0:
            avg_eff = total_hashrate / total_power
            self.lbl_avg_efficiency.setText(f"Eff: {avg_eff:.4f} H/W")
        
        # Effizienz-Ranking aktualisieren
        ranking = self.optimizer.get_efficiency_ranking()
        self.efficiency_widget.update_ranking(ranking)
        
        # Auto-Optimize wenn aktiviert
        if self.chk_global_auto.isChecked():
            self.optimizer.optimize_all()
    
    @Slot(int, str)
    def _on_card_profile_changed(self, gpu_index: int, profile: str):
        """Wenn Benutzer Profile manuell ändert"""
        if gpu_index in self.optimizer.gpu_states:
            self.optimizer.gpu_states[gpu_index].current_profile = profile
            logger.info(f"GPU {gpu_index}: Manuell auf {profile.upper()} gesetzt")
            
            if gpu_index in self.gpu_cards:
                self.gpu_cards[gpu_index].show_action(f"Profile → {profile.upper()}")
    
    @Slot(int, str)
    def _on_card_mode_changed(self, gpu_index: int, mode: str):
        """Wenn Benutzer Mode ändert"""
        mode_enum = PerformanceMode(mode)
        self.optimizer.set_performance_mode(gpu_index, mode_enum)
        
        if gpu_index in self.gpu_cards:
            self.gpu_cards[gpu_index].show_action(f"Mode → {mode.upper()}")
    
    @Slot(int)
    def _on_benchmark_requested(self, gpu_index: int):
        """Startet Benchmark für GPU"""
        self.tabs.setCurrentIndex(2)  # Benchmark Tab
        self.combo_bench_gpu.setCurrentIndex(
            self.combo_bench_gpu.findData(gpu_index)
        )
    
    def _on_profile_changed(self, gpu_index: int, old_profile: str, new_profile: str):
        """Callback wenn Optimizer Profile ändert"""
        if gpu_index in self.gpu_cards:
            self.gpu_cards[gpu_index].show_action(
                f"Auto: {old_profile.upper()} → {new_profile.upper()}"
            )
    
    def _on_thermal_warning(self, gpu_index: int, temp: int, level: str):
        """Callback bei Temperatur-Warnung"""
        if gpu_index in self.gpu_cards:
            if level == "critical":
                self.gpu_cards[gpu_index].show_action(f"⚠️ KRITISCH! {temp}°C")
            else:
                self.gpu_cards[gpu_index].show_action(f"⚠️ Zu heiß: {temp}°C")
    
    def _on_optimization(self, result):
        """Callback bei Optimierung"""
        self.lbl_status.setText(
            f"GPU {result.gpu_index}: {result.old_profile} → {result.new_profile}"
        )
    
    def update_from_gpu_monitor(self, gpu_stats: List):
        """
        Aktualisiert Optimizer mit echten GPU-Daten vom GPU Monitor
        
        Args:
            gpu_stats: Liste von GPU-Statistiken vom gpu_monitor.py
        """
        for stats in gpu_stats:
            idx = getattr(stats, 'index', 0)
            
            self.optimizer.update_gpu_state(
                gpu_index=idx,
                gpu_name=getattr(stats, 'name', ''),
                temperature=getattr(stats, 'temperature', 0),
                power_draw=getattr(stats, 'power_draw', 0),
                hashrate=getattr(stats, 'hashrate', 0),
                hashrate_unit=getattr(stats, 'hashrate_unit', 'MH/s'),
                fan_speed=getattr(stats, 'fan_speed', 0),
                core_clock=getattr(stats, 'core_clock', 0),
                mem_clock=getattr(stats, 'mem_clock', 0),
                current_coin=getattr(stats, 'current_coin', '')
            )


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark Theme
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    widget = GPUOptimizerWidget()
    widget.setWindowTitle("GPU Auto-Optimizer")
    widget.resize(900, 700)
    widget.show()
    
    # Simuliere GPU-Daten
    optimizer = get_gpu_optimizer()
    
    def simulate_gpu():
        import random
        for i in range(2):
            temp = random.randint(55, 78)
            optimizer.update_gpu_state(
                gpu_index=i,
                gpu_name=f"RTX 308{i} Laptop" if i == 0 else f"RTX 307{i}",
                temperature=temp,
                power_draw=random.randint(90, 130),
                hashrate=random.uniform(28, 35),
                current_coin="RVN"
            )
    
    # Simulations-Timer
    sim_timer = QTimer()
    sim_timer.timeout.connect(simulate_gpu)
    sim_timer.start(3000)
    simulate_gpu()
    
    sys.exit(app.exec())
