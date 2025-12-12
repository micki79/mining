#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-GPU Mining Widget - GUI für individuelles GPU-Mining
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Dashboard: Gesamt-Profit, aktive GPUs, Status
- Tabelle: Jede GPU mit Coin, Hashrate, Profit, Status
- Start/Stop pro GPU oder alle
- Live-Updates
- Profit-Vergleich

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QFrame, QProgressBar, QComboBox,
    QCheckBox, QSpinBox, QMessageBox, QHeaderView,
    QSplitter, QScrollArea, QToolButton
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor, QBrush

logger = logging.getLogger(__name__)


class GPUStatusCard(QFrame):
    """Status-Karte für eine einzelne GPU"""
    
    start_clicked = Signal(int)  # gpu_index
    stop_clicked = Signal(int)   # gpu_index
    
    def __init__(self, gpu_index: int, gpu_name: str, parent=None):
        super().__init__(parent)
        self.gpu_index = gpu_index
        self.gpu_name = gpu_name
        self.is_mining = False
        self.setup_ui()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            GPUStatusCard {
                background: #2b2b2b;
                border: 1px solid #404040;
                border-radius: 8px;
                padding: 8px;
            }
            GPUStatusCard[mining="true"] {
                border: 2px solid #4CAF50;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Header: GPU Name + Status
        header = QHBoxLayout()
        
        self.gpu_label = QLabel(f"GPU {self.gpu_index}")
        self.gpu_label.setFont(QFont("", 11, QFont.Bold))
        header.addWidget(self.gpu_label)
        
        self.status_label = QLabel("⚪ Idle")
        self.status_label.setStyleSheet("color: #888;")
        header.addStretch()
        header.addWidget(self.status_label)
        
        layout.addLayout(header)
        
        # GPU Model
        self.model_label = QLabel(self.gpu_name)
        self.model_label.setStyleSheet("color: #aaa; font-size: 10px;")
        self.model_label.setWordWrap(True)
        layout.addWidget(self.model_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #404040;")
        layout.addWidget(line)
        
        # Mining Info Grid
        info_grid = QGridLayout()
        info_grid.setSpacing(2)
        
        # Coin
        info_grid.addWidget(QLabel("Coin:"), 0, 0)
        self.coin_label = QLabel("-")
        self.coin_label.setFont(QFont("", 10, QFont.Bold))
        self.coin_label.setStyleSheet("color: #FFA500;")
        info_grid.addWidget(self.coin_label, 0, 1)
        
        # Hashrate
        info_grid.addWidget(QLabel("Hashrate:"), 1, 0)
        self.hashrate_label = QLabel("-")
        self.hashrate_label.setStyleSheet("color: #00BCD4;")
        info_grid.addWidget(self.hashrate_label, 1, 1)
        
        # Profit
        info_grid.addWidget(QLabel("Profit:"), 2, 0)
        self.profit_label = QLabel("-")
        self.profit_label.setStyleSheet("color: #4CAF50;")
        info_grid.addWidget(self.profit_label, 2, 1)
        
        # Shares
        info_grid.addWidget(QLabel("Shares:"), 3, 0)
        self.shares_label = QLabel("-")
        info_grid.addWidget(self.shares_label, 3, 1)
        
        layout.addLayout(info_grid)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start")
        self.start_btn.setStyleSheet("background: #4CAF50; color: white; padding: 4px 8px;")
        self.start_btn.clicked.connect(lambda: self.start_clicked.emit(self.gpu_index))
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setStyleSheet("background: #f44336; color: white; padding: 4px 8px;")
        self.stop_btn.clicked.connect(lambda: self.stop_clicked.emit(self.gpu_index))
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
    
    def set_mining_status(self, is_mining: bool, coin: str = "", hashrate: float = 0.0, 
                          hashrate_unit: str = "MH/s", profit: float = 0.0,
                          accepted: int = 0, rejected: int = 0):
        """Aktualisiert Mining-Status"""
        self.is_mining = is_mining
        
        if is_mining:
            self.status_label.setText("🟢 Mining")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.setProperty("mining", "true")
            self.coin_label.setText(coin)
            self.hashrate_label.setText(f"{hashrate:.2f} {hashrate_unit}")
            self.profit_label.setText(f"${profit:.2f}/Tag")
            self.shares_label.setText(f"✅ {accepted} / ❌ {rejected}")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
        else:
            self.status_label.setText("⚪ Idle")
            self.status_label.setStyleSheet("color: #888;")
            self.setProperty("mining", "false")
            self.coin_label.setText("-")
            self.hashrate_label.setText("-")
            self.profit_label.setText("-")
            self.shares_label.setText("-")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
        
        # Style refresh
        self.style().unpolish(self)
        self.style().polish(self)
    
    def set_expected_profit(self, coin: str, profit: float):
        """Zeigt erwarteten Profit (vor Mining-Start)"""
        if not self.is_mining:
            self.coin_label.setText(f"{coin} (best)")
            self.profit_label.setText(f"~${profit:.2f}/Tag")


class MultiGPUDashboard(QWidget):
    """Dashboard für Gesamt-Übersicht"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(20)
        
        # Stat Cards
        self.gpu_count_card = self._create_stat_card("🎮 GPUs", "0", "#2196F3")
        layout.addWidget(self.gpu_count_card)
        
        self.mining_count_card = self._create_stat_card("⛏️ Mining", "0", "#4CAF50")
        layout.addWidget(self.mining_count_card)
        
        self.total_hashrate_card = self._create_stat_card("📊 Hashrate", "-", "#00BCD4")
        layout.addWidget(self.total_hashrate_card)
        
        self.total_profit_card = self._create_stat_card("💰 Profit/Tag", "$0.00", "#FFA500")
        layout.addWidget(self.total_profit_card)
        
        self.efficiency_card = self._create_stat_card("⚡ Effizienz", "-", "#9C27B0")
        layout.addWidget(self.efficiency_card)
    
    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        """Erstellt eine Statistik-Karte"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: #2b2b2b;
                border: 1px solid {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {color}; font-size: 11px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("", 16, QFont.Bold))
        value_label.setStyleSheet("color: white;")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setObjectName("value")
        layout.addWidget(value_label)
        
        return card
    
    def _get_value_label(self, card: QFrame) -> QLabel:
        """Holt Value-Label aus Karte"""
        return card.findChild(QLabel, "value")
    
    def update_stats(self, gpu_count: int, mining_count: int, 
                     total_profit: float, total_power: float = 0):
        """Aktualisiert Dashboard-Statistiken"""
        self._get_value_label(self.gpu_count_card).setText(str(gpu_count))
        self._get_value_label(self.mining_count_card).setText(str(mining_count))
        self._get_value_label(self.total_profit_card).setText(f"${total_profit:.2f}")
        
        if total_power > 0:
            efficiency = total_profit / (total_power / 1000 * 24)  # $/kWh
            self._get_value_label(self.efficiency_card).setText(f"${efficiency:.3f}/kWh")


class MultiGPUTable(QTableWidget):
    """Tabelle mit allen GPUs und Details"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        # Spalten
        columns = [
            "GPU", "Modell", "Status", "Coin", "Algorithmus",
            "Hashrate", "Profit/Tag", "Shares", "Pool", "Miner"
        ]
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        
        # Header Style
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Modell
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setEditTriggers(QTableWidget.NoEditTriggers)
        
        self.setStyleSheet("""
            QTableWidget {
                background: #1e1e1e;
                gridline-color: #404040;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background: #404040;
            }
            QHeaderView::section {
                background: #2b2b2b;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #404040;
            }
        """)
    
    def update_gpu_data(self, gpu_data: List[Dict]):
        """Aktualisiert Tabellen-Daten"""
        self.setRowCount(len(gpu_data))
        
        for row, data in enumerate(gpu_data):
            # GPU Index
            self.setItem(row, 0, QTableWidgetItem(f"GPU {data.get('index', row)}"))
            
            # Modell
            self.setItem(row, 1, QTableWidgetItem(data.get('model', 'Unknown')))
            
            # Status
            status = data.get('status', 'Idle')
            status_item = QTableWidgetItem(status)
            if status == "Mining":
                status_item.setForeground(QBrush(QColor("#4CAF50")))
            elif status == "Error":
                status_item.setForeground(QBrush(QColor("#f44336")))
            else:
                status_item.setForeground(QBrush(QColor("#888")))
            self.setItem(row, 2, status_item)
            
            # Coin
            coin_item = QTableWidgetItem(data.get('coin', '-'))
            coin_item.setForeground(QBrush(QColor("#FFA500")))
            self.setItem(row, 3, coin_item)
            
            # Algorithmus
            self.setItem(row, 4, QTableWidgetItem(data.get('algorithm', '-')))
            
            # Hashrate
            hashrate = data.get('hashrate', 0)
            unit = data.get('hashrate_unit', 'MH/s')
            hr_item = QTableWidgetItem(f"{hashrate:.2f} {unit}" if hashrate > 0 else "-")
            hr_item.setForeground(QBrush(QColor("#00BCD4")))
            self.setItem(row, 5, hr_item)
            
            # Profit
            profit = data.get('profit', 0)
            profit_item = QTableWidgetItem(f"${profit:.2f}" if profit > 0 else "-")
            profit_item.setForeground(QBrush(QColor("#4CAF50")))
            self.setItem(row, 6, profit_item)
            
            # Shares
            accepted = data.get('accepted', 0)
            rejected = data.get('rejected', 0)
            self.setItem(row, 7, QTableWidgetItem(f"{accepted}/{rejected}"))
            
            # Pool
            self.setItem(row, 8, QTableWidgetItem(data.get('pool', '-')))
            
            # Miner
            self.setItem(row, 9, QTableWidgetItem(data.get('miner', '-')))


class MultiGPUMiningWidget(QWidget):
    """
    Haupt-Widget für Multi-GPU Mining
    
    Kombiniert:
    - Dashboard mit Gesamt-Stats
    - GPU-Karten für jede GPU
    - Detail-Tabelle
    - Steuerungs-Buttons
    """
    
    # Signals
    mining_started = Signal()
    mining_stopped = Signal()
    gpu_switched = Signal(int, str, str)  # gpu_index, old_coin, new_coin
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._gpu_cards: Dict[int, GPUStatusCard] = {}
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_display)
        
        # Manager (werden extern gesetzt)
        self._miner_manager = None
        self._switcher = None
        self._profit_calculator = None
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        title = QLabel("🎮 Multi-GPU Mining")
        title.setFont(QFont("", 16, QFont.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Auto-Switch Toggle
        self.auto_switch_check = QCheckBox("🔄 Auto-Switch")
        self.auto_switch_check.setToolTip("Automatisch zum profitabelsten Coin wechseln")
        self.auto_switch_check.toggled.connect(self._toggle_auto_switch)
        header.addWidget(self.auto_switch_check)
        
        # Refresh Button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._refresh_profits)
        header.addWidget(refresh_btn)
        
        layout.addLayout(header)
        
        # === DASHBOARD ===
        self.dashboard = MultiGPUDashboard()
        layout.addWidget(self.dashboard)
        
        # === CONTROL BUTTONS ===
        controls = QHBoxLayout()
        
        self.start_all_btn = QPushButton("▶️ Alle Starten (Optimal)")
        self.start_all_btn.setStyleSheet("background: #4CAF50; color: white; padding: 8px 16px; font-weight: bold;")
        self.start_all_btn.clicked.connect(self._start_all_optimal)
        controls.addWidget(self.start_all_btn)
        
        self.stop_all_btn = QPushButton("⏹️ Alle Stoppen")
        self.stop_all_btn.setStyleSheet("background: #f44336; color: white; padding: 8px 16px; font-weight: bold;")
        self.stop_all_btn.clicked.connect(self._stop_all)
        self.stop_all_btn.setEnabled(False)
        controls.addWidget(self.stop_all_btn)
        
        controls.addStretch()
        
        # Profit Threshold
        controls.addWidget(QLabel("Switch bei:"))
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(1, 50)
        self.threshold_spin.setValue(5)
        self.threshold_spin.setSuffix("% Profit-Diff")
        controls.addWidget(self.threshold_spin)
        
        layout.addLayout(controls)
        
        # === GPU CARDS ===
        cards_group = QGroupBox("GPU Status")
        cards_layout = QHBoxLayout(cards_group)
        
        # Scroll Area für GPU Cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(220)
        
        self.cards_container = QWidget()
        self.cards_grid = QHBoxLayout(self.cards_container)
        self.cards_grid.setSpacing(10)
        scroll.setWidget(self.cards_container)
        
        cards_layout.addWidget(scroll)
        layout.addWidget(cards_group)
        
        # === DETAIL TABLE ===
        table_group = QGroupBox("Details")
        table_layout = QVBoxLayout(table_group)
        
        self.gpu_table = MultiGPUTable()
        table_layout.addWidget(self.gpu_table)
        
        layout.addWidget(table_group)
        
        # Stretch am Ende
        layout.addStretch()
    
    def set_managers(self, miner_manager, switcher, profit_calculator):
        """Setzt die Manager-Referenzen"""
        self._miner_manager = miner_manager
        self._switcher = switcher
        self._profit_calculator = profit_calculator
        
        # Callbacks setzen
        if miner_manager:
            miner_manager.on_miner_started = self._on_miner_started
            miner_manager.on_miner_stopped = self._on_miner_stopped
            miner_manager.on_miner_error = self._on_miner_error
            miner_manager.on_stats_update = self._on_stats_update
        
        if switcher:
            switcher.on_switch = self._on_coin_switch
    
    def setup_gpus(self, gpus: List[tuple]):
        """
        Initialisiert GPU-Karten
        
        Args:
            gpus: Liste von (index, name) Tupeln
        """
        # Alte Karten entfernen
        for card in self._gpu_cards.values():
            card.deleteLater()
        self._gpu_cards.clear()
        
        # Neue Karten erstellen
        for gpu_index, gpu_name in gpus:
            card = GPUStatusCard(gpu_index, gpu_name)
            card.start_clicked.connect(self._start_single_gpu)
            card.stop_clicked.connect(self._stop_single_gpu)
            self._gpu_cards[gpu_index] = card
            self.cards_grid.addWidget(card)
        
        # Dashboard aktualisieren
        self.dashboard.update_stats(len(gpus), 0, 0.0)
        
        # Erwartete Profits berechnen
        self._refresh_profits()
    
    def _refresh_profits(self):
        """Aktualisiert erwartete Profits für alle GPUs"""
        if not self._profit_calculator:
            return
        
        try:
            self._profit_calculator.fetch_coin_prices()
            
            for gpu_idx, card in self._gpu_cards.items():
                if not card.is_mining:
                    gpu_info = self._profit_calculator.calculate_best_coin_for_gpu(
                        gpu_idx, card.gpu_name
                    )
                    if gpu_info.best_coin:
                        card.set_expected_profit(gpu_info.best_coin, gpu_info.best_profit_usd)
            
            # Tabelle aktualisieren
            self._update_table()
            
        except Exception as e:
            logger.error(f"Profit-Refresh Fehler: {e}")
    
    def _start_all_optimal(self):
        """Startet Mining auf allen GPUs mit optimalem Coin"""
        if not self._switcher:
            QMessageBox.warning(self, "Fehler", "Switcher nicht initialisiert!")
            return
        
        # GPU Infos setzen
        gpu_infos = [(idx, card.gpu_name) for idx, card in self._gpu_cards.items()]
        self._switcher.set_gpu_infos(gpu_infos)
        
        # Wallets laden
        wallets = self._load_wallets()
        if not wallets:
            QMessageBox.warning(self, "Fehler", "Keine Wallets konfiguriert!\nBitte im Wallets-Tab einrichten.")
            return
        self._switcher.set_wallets(wallets)
        
        # Starten
        success = self._switcher.start_all_optimal()
        
        if success:
            self.start_all_btn.setEnabled(False)
            self.stop_all_btn.setEnabled(True)
            self._update_timer.start(2000)  # 2s Updates
            self.mining_started.emit()
            
            # Monitoring starten
            if self._miner_manager:
                self._miner_manager.start_monitoring(interval=5.0)
        else:
            QMessageBox.warning(self, "Fehler", "Mining konnte nicht gestartet werden!")
    
    def _stop_all(self):
        """Stoppt alle Miner"""
        if self._switcher:
            self._switcher.stop_all()
        
        if self._miner_manager:
            self._miner_manager.stop_monitoring()
        
        self._update_timer.stop()
        self.start_all_btn.setEnabled(True)
        self.stop_all_btn.setEnabled(False)
        
        # Cards zurücksetzen
        for card in self._gpu_cards.values():
            card.set_mining_status(False)
        
        self.mining_stopped.emit()
    
    def _start_single_gpu(self, gpu_index: int):
        """Startet Mining auf einer einzelnen GPU"""
        if not self._switcher or not self._profit_calculator:
            return
        
        card = self._gpu_cards.get(gpu_index)
        if not card:
            return
        
        # Wallets laden
        wallets = self._load_wallets()
        if not wallets:
            QMessageBox.warning(self, "Fehler", "Keine Wallets konfiguriert!")
            return
        self._switcher.set_wallets(wallets)
        
        # GPU Info setzen
        self._switcher.set_gpu_infos([(gpu_index, card.gpu_name)])
        
        # Config berechnen
        configs = self._switcher.calculate_optimal_configs()
        if configs:
            self._miner_manager.start_gpu_miner(configs[0])
            
            if not self._update_timer.isActive():
                self._update_timer.start(2000)
                self._miner_manager.start_monitoring(interval=5.0)
    
    def _stop_single_gpu(self, gpu_index: int):
        """Stoppt Mining auf einer einzelnen GPU"""
        if self._miner_manager:
            self._miner_manager.stop_gpu_miner(gpu_index)
    
    def _toggle_auto_switch(self, enabled: bool):
        """Aktiviert/Deaktiviert Auto-Switching"""
        if not self._switcher:
            return
        
        if enabled:
            threshold = self.threshold_spin.value() / 100.0
            self._switcher._profit_threshold = threshold
            self._switcher.start_auto_switching(check_interval=180.0)
        else:
            self._switcher.stop_auto_switching()
    
    def _load_wallets(self) -> Dict[str, str]:
        """Lädt Wallets aus wallets.json"""
        import json
        from pathlib import Path
        
        wallets = {}
        
        try:
            wallets_file = Path("wallets.json")
            if wallets_file.exists():
                with open(wallets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wallets = data.get("wallets", {})
        except Exception as e:
            logger.error(f"Wallets laden fehlgeschlagen: {e}")
        
        return wallets
    
    def _update_display(self):
        """Periodisches Update der Anzeige"""
        if not self._miner_manager:
            return
        
        all_status = self._miner_manager.get_all_status()
        
        total_profit = 0.0
        mining_count = 0
        
        for gpu_idx, status in all_status.items():
            if gpu_idx in self._gpu_cards:
                card = self._gpu_cards[gpu_idx]
                
                if status.is_running:
                    mining_count += 1
                    card.set_mining_status(
                        is_mining=True,
                        coin=status.config.coin,
                        hashrate=status.current_hashrate,
                        hashrate_unit=status.hashrate_unit,
                        profit=status.config.expected_profit_usd,
                        accepted=status.accepted_shares,
                        rejected=status.rejected_shares
                    )
                    total_profit += status.config.expected_profit_usd
                else:
                    card.set_mining_status(False)
        
        # Dashboard aktualisieren
        self.dashboard.update_stats(
            gpu_count=len(self._gpu_cards),
            mining_count=mining_count,
            total_profit=total_profit
        )
        
        # Tabelle aktualisieren
        self._update_table()
        
        # Buttons
        self.stop_all_btn.setEnabled(mining_count > 0)
        self.start_all_btn.setEnabled(mining_count < len(self._gpu_cards))
    
    def _update_table(self):
        """Aktualisiert die Detail-Tabelle"""
        if not self._miner_manager:
            return
        
        all_status = self._miner_manager.get_all_status()
        table_data = []
        
        for gpu_idx, card in self._gpu_cards.items():
            status = all_status.get(gpu_idx)
            
            if status and status.is_running:
                data = {
                    'index': gpu_idx,
                    'model': status.config.gpu_model,
                    'status': 'Mining',
                    'coin': status.config.coin,
                    'algorithm': status.config.algorithm,
                    'hashrate': status.current_hashrate,
                    'hashrate_unit': status.hashrate_unit,
                    'profit': status.config.expected_profit_usd,
                    'accepted': status.accepted_shares,
                    'rejected': status.rejected_shares,
                    'pool': status.config.pool_name,
                    'miner': status.config.miner_type.value,
                }
            else:
                # Erwartete Werte zeigen
                if self._profit_calculator:
                    gpu_info = self._profit_calculator.calculate_best_coin_for_gpu(
                        gpu_idx, card.gpu_name
                    )
                    data = {
                        'index': gpu_idx,
                        'model': gpu_info.gpu_model,
                        'status': 'Idle',
                        'coin': f"{gpu_info.best_coin} (best)",
                        'algorithm': gpu_info.best_algorithm,
                        'hashrate': gpu_info.best_hashrate,
                        'hashrate_unit': gpu_info.best_hashrate_unit,
                        'profit': gpu_info.best_profit_usd,
                        'accepted': 0,
                        'rejected': 0,
                        'pool': gpu_info.best_pool_name,
                        'miner': gpu_info.best_miner,
                    }
                else:
                    data = {
                        'index': gpu_idx,
                        'model': card.gpu_name,
                        'status': 'Idle',
                        'coin': '-',
                        'algorithm': '-',
                        'hashrate': 0,
                        'hashrate_unit': 'MH/s',
                        'profit': 0,
                        'accepted': 0,
                        'rejected': 0,
                        'pool': '-',
                        'miner': '-',
                    }
            
            table_data.append(data)
        
        self.gpu_table.update_gpu_data(table_data)
    
    # === CALLBACKS ===
    
    def _on_miner_started(self, gpu_index: int, config):
        """Callback: Miner gestartet"""
        logger.info(f"GUI: GPU {gpu_index} Mining gestartet - {config.coin}")
    
    def _on_miner_stopped(self, gpu_index: int, reason: str):
        """Callback: Miner gestoppt"""
        logger.info(f"GUI: GPU {gpu_index} Mining gestoppt - {reason}")
        
        if gpu_index in self._gpu_cards:
            self._gpu_cards[gpu_index].set_mining_status(False)
    
    def _on_miner_error(self, gpu_index: int, error: str):
        """Callback: Miner Fehler"""
        logger.error(f"GUI: GPU {gpu_index} Fehler - {error}")
        
        # Notification
        QMessageBox.warning(self, f"GPU {gpu_index} Fehler", error)
    
    def _on_stats_update(self, gpu_index: int, status):
        """Callback: Stats Update"""
        # Wird durch Timer-Update abgedeckt
        pass
    
    def _on_coin_switch(self, gpu_index: int, old_coin: str, new_coin: str):
        """Callback: Coin gewechselt"""
        logger.info(f"GUI: GPU {gpu_index} Switch {old_coin} → {new_coin}")
        self.gpu_switched.emit(gpu_index, old_coin, new_coin)
    
    # === CLEANUP ===
    
    def cleanup(self):
        """Cleanup beim Beenden"""
        self._update_timer.stop()
        
        if self._switcher:
            self._switcher.stop_auto_switching()
        
        if self._miner_manager:
            self._miner_manager.stop_monitoring()
            self._miner_manager.stop_all_miners("Application Exit")


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    logging.basicConfig(level=logging.INFO)
    
    app = QApplication(sys.argv)
    
    # Dark Theme
    app.setStyleSheet("""
        QWidget {
            background: #1e1e1e;
            color: white;
        }
    """)
    
    widget = MultiGPUMiningWidget()
    widget.setWindowTitle("Multi-GPU Mining Test")
    widget.resize(1000, 700)
    
    # Test GPUs
    test_gpus = [
        (0, "NVIDIA GeForce RTX 3080 Laptop GPU"),
        (1, "NVIDIA GeForce RTX 3070"),
        (2, "NVIDIA GeForce RTX 3060"),
    ]
    widget.setup_gpus(test_gpus)
    
    widget.show()
    sys.exit(app.exec())
