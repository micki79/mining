#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Portfolio Widget - GUI für Portfolio Manager
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Portfolio-Übersicht mit Positionen und P&L
- Activity Log mit Checkboxen zum Abhaken
- Settings für Stop-Loss, Trailing Stop, Auto-Sell
- Exchange-Konfiguration
- Trading-Historie
- Mining-Statistiken

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import sys
import logging
from datetime import datetime
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QGroupBox, QLineEdit, QDoubleSpinBox,
    QSpinBox, QCheckBox, QComboBox, QTextEdit, QScrollArea,
    QHeaderView, QFrame, QSplitter, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)

# Import Portfolio Manager
try:
    from portfolio_manager import (
        get_portfolio_manager, PortfolioManager, PortfolioSettings,
        Exchange, MiningDeposit, TradeOrder
    )
    PORTFOLIO_AVAILABLE = True
except ImportError:
    PORTFOLIO_AVAILABLE = False
    logger.warning("Portfolio Manager nicht verfügbar")


class PortfolioWidget(QWidget):
    """
    Portfolio Management Widget
    
    Zeigt:
    - Portfolio-Übersicht (Coins, Mengen, Werte, P&L)
    - Activity Log (alle Aktionen mit Checkboxen)
    - Settings (Stop-Loss, Trailing Stop, Auto-Sell)
    - Trading-Historie
    """
    
    # Signals
    alert_triggered = Signal(str, str)  # level, message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.portfolio_manager: Optional[PortfolioManager] = None
        
        if PORTFOLIO_AVAILABLE:
            self.portfolio_manager = get_portfolio_manager()
            self._setup_callbacks()
        
        self._setup_ui()
        self._setup_timer()
    
    def _setup_callbacks(self):
        """Registriert Callbacks beim Portfolio Manager"""
        if self.portfolio_manager:
            self.portfolio_manager.on_alert = self._on_alert
            self.portfolio_manager.on_deposit = self._on_deposit
            self.portfolio_manager.on_trade = self._on_trade
            self.portfolio_manager.on_price_update = self._on_price_update
    
    def _setup_timer(self):
        """Timer für UI Updates"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(5000)  # Alle 5 Sekunden
    
    def _setup_ui(self):
        """Erstellt die UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        
        # Tab 1: Portfolio Übersicht
        self.overview_tab = self._create_overview_tab()
        self.tabs.addTab(self.overview_tab, "💰 Portfolio")
        
        # Tab 2: Activity Log
        self.activity_tab = self._create_activity_tab()
        self.tabs.addTab(self.activity_tab, "📋 Activity Log")
        
        # Tab 3: Settings
        self.settings_tab = self._create_settings_tab()
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        # Tab 4: Trading Historie
        self.history_tab = self._create_history_tab()
        self.tabs.addTab(self.history_tab, "📈 Trading")
        
        layout.addWidget(self.tabs)
        
        # Initial Update
        self.update_ui()
    
    def _create_header(self) -> QWidget:
        """Erstellt den Header mit Gesamtwert und Controls"""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout(frame)
        
        # Portfolio-Wert
        value_group = QVBoxLayout()
        self.total_value_label = QLabel("$0.00")
        self.total_value_label.setFont(QFont("Consolas", 24, QFont.Bold))
        self.total_value_label.setStyleSheet("color: #00ff00;")
        value_group.addWidget(QLabel("Portfolio Wert:"))
        value_group.addWidget(self.total_value_label)
        layout.addLayout(value_group)
        
        # P&L
        pnl_group = QVBoxLayout()
        self.pnl_label = QLabel("$0.00 (0.0%)")
        self.pnl_label.setFont(QFont("Consolas", 16))
        pnl_group.addWidget(QLabel("Unrealized P&L:"))
        pnl_group.addWidget(self.pnl_label)
        layout.addLayout(pnl_group)
        
        layout.addStretch()
        
        # Status
        status_group = QVBoxLayout()
        self.status_label = QLabel("⏹️ Gestoppt")
        self.status_label.setFont(QFont("Consolas", 12))
        status_group.addWidget(QLabel("Monitoring:"))
        status_group.addWidget(self.status_label)
        layout.addLayout(status_group)
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("▶️ Starten")
        self.start_btn.clicked.connect(self.start_monitoring)
        self.start_btn.setMinimumWidth(120)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stoppen")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        layout.addLayout(btn_layout)
        
        return frame
    
    def _create_overview_tab(self) -> QWidget:
        """Erstellt den Portfolio-Übersicht Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Positionen Tabelle
        positions_group = QGroupBox("📊 Positionen")
        positions_layout = QVBoxLayout(positions_group)
        
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(7)
        self.positions_table.setHorizontalHeaderLabels([
            "Coin", "Menge", "Avg. Cost", "Aktueller Preis", 
            "Wert (USD)", "P&L", "P&L %"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.positions_table.setAlternatingRowColors(True)
        positions_layout.addWidget(self.positions_table)
        
        layout.addWidget(positions_group)
        
        # Marktdaten
        market_group = QGroupBox("📈 Marktdaten")
        market_layout = QHBoxLayout(market_group)
        
        self.market_info = QTextEdit()
        self.market_info.setReadOnly(True)
        self.market_info.setMaximumHeight(150)
        self.market_info.setFont(QFont("Consolas", 10))
        market_layout.addWidget(self.market_info)
        
        layout.addWidget(market_group)
        
        return widget
    
    def _create_activity_tab(self) -> QWidget:
        """Erstellt den Activity Log Tab mit Checkboxen"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Alle", "Code Repair", "Portfolio", "Trades", "Unbestätigt"])
        self.filter_combo.currentTextChanged.connect(self.update_activity_log)
        filter_layout.addWidget(self.filter_combo)
        
        filter_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Aktualisieren")
        self.refresh_btn.clicked.connect(self.update_activity_log)
        filter_layout.addWidget(self.refresh_btn)
        
        self.ack_all_btn = QPushButton("✅ Alle abhaken")
        self.ack_all_btn.clicked.connect(self.acknowledge_all)
        filter_layout.addWidget(self.ack_all_btn)
        
        layout.addLayout(filter_layout)
        
        # Activity Tabelle
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(6)
        self.activity_table.setHorizontalHeaderLabels([
            "✓", "Zeitpunkt", "Typ", "Beschreibung", "Status", "ID"
        ])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.setColumnWidth(0, 30)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.cellChanged.connect(self._on_checkbox_changed)
        layout.addWidget(self.activity_table)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Erstellt den Settings Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stop-Loss Settings
        sl_group = QGroupBox("🛑 Stop-Loss Settings")
        sl_layout = QGridLayout(sl_group)
        
        sl_layout.addWidget(QLabel("Stop-Loss (%):"), 0, 0)
        self.stop_loss_spin = QDoubleSpinBox()
        self.stop_loss_spin.setRange(5, 50)
        self.stop_loss_spin.setValue(15)
        self.stop_loss_spin.setSuffix(" %")
        sl_layout.addWidget(self.stop_loss_spin, 0, 1)
        
        self.trailing_check = QCheckBox("Trailing Stop aktivieren")
        self.trailing_check.setChecked(True)
        sl_layout.addWidget(self.trailing_check, 1, 0, 1, 2)
        
        sl_layout.addWidget(QLabel("Trailing Aktivierung (+%):"), 2, 0)
        self.trailing_activation_spin = QDoubleSpinBox()
        self.trailing_activation_spin.setRange(5, 100)
        self.trailing_activation_spin.setValue(15)
        self.trailing_activation_spin.setSuffix(" %")
        sl_layout.addWidget(self.trailing_activation_spin, 2, 1)
        
        sl_layout.addWidget(QLabel("Trailing Distance (%):"), 3, 0)
        self.trailing_distance_spin = QDoubleSpinBox()
        self.trailing_distance_spin.setRange(5, 30)
        self.trailing_distance_spin.setValue(10)
        self.trailing_distance_spin.setSuffix(" %")
        sl_layout.addWidget(self.trailing_distance_spin, 3, 1)
        
        layout.addWidget(sl_group)
        
        # Auto-Sell Settings
        auto_group = QGroupBox("💰 Auto-Sell Settings")
        auto_layout = QGridLayout(auto_group)
        
        self.auto_sell_check = QCheckBox("Auto-Sell aktivieren")
        self.auto_sell_check.setChecked(True)
        auto_layout.addWidget(self.auto_sell_check, 0, 0, 1, 2)
        
        auto_layout.addWidget(QLabel("Auto-Sell Anteil (%):"), 1, 0)
        self.auto_sell_spin = QDoubleSpinBox()
        self.auto_sell_spin.setRange(10, 100)
        self.auto_sell_spin.setValue(60)
        self.auto_sell_spin.setSuffix(" %")
        auto_layout.addWidget(self.auto_sell_spin, 1, 1)
        
        auto_layout.addWidget(QLabel("Min. Haltezeit (Stunden):"), 2, 0)
        self.min_hold_spin = QDoubleSpinBox()
        self.min_hold_spin.setRange(0, 48)
        self.min_hold_spin.setValue(2)
        self.min_hold_spin.setSuffix(" h")
        auto_layout.addWidget(self.min_hold_spin, 2, 1)
        
        auto_layout.addWidget(QLabel("Stablecoin:"), 3, 0)
        self.stablecoin_combo = QComboBox()
        self.stablecoin_combo.addItems(["USDT", "USDC"])
        auto_layout.addWidget(self.stablecoin_combo, 3, 1)
        
        layout.addWidget(auto_group)
        
        # Exchange Settings
        exchange_group = QGroupBox("🔗 Exchange Settings")
        exchange_layout = QGridLayout(exchange_group)
        
        exchange_layout.addWidget(QLabel("Primäre Börse:"), 0, 0)
        self.exchange_combo = QComboBox()
        self.exchange_combo.addItems(["CoinEx", "Gate.io"])
        exchange_layout.addWidget(self.exchange_combo, 0, 1)
        
        exchange_layout.addWidget(QLabel("API Key:"), 1, 0)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("API Key eingeben...")
        exchange_layout.addWidget(self.api_key_edit, 1, 1)
        
        exchange_layout.addWidget(QLabel("API Secret:"), 2, 0)
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.Password)
        self.api_secret_edit.setPlaceholderText("API Secret eingeben...")
        exchange_layout.addWidget(self.api_secret_edit, 2, 1)
        
        self.save_exchange_btn = QPushButton("💾 Exchange speichern")
        self.save_exchange_btn.clicked.connect(self.save_exchange_settings)
        exchange_layout.addWidget(self.save_exchange_btn, 3, 0, 1, 2)
        
        layout.addWidget(exchange_group)
        
        # Save Button
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        
        self.save_settings_btn = QPushButton("💾 Settings speichern")
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.save_settings_btn.setMinimumWidth(200)
        save_layout.addWidget(self.save_settings_btn)
        
        layout.addLayout(save_layout)
        layout.addStretch()
        
        # Load current settings
        self._load_settings()
        
        return widget
    
    def _create_history_tab(self) -> QWidget:
        """Erstellt den Trading Historie Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Statistiken
        stats_group = QGroupBox("📊 Trading Statistiken")
        stats_layout = QGridLayout(stats_group)
        
        self.trades_count_label = QLabel("0")
        self.trades_volume_label = QLabel("$0.00")
        self.trades_profit_label = QLabel("$0.00")
        
        stats_layout.addWidget(QLabel("Anzahl Trades:"), 0, 0)
        stats_layout.addWidget(self.trades_count_label, 0, 1)
        stats_layout.addWidget(QLabel("Gesamtvolumen:"), 0, 2)
        stats_layout.addWidget(self.trades_volume_label, 0, 3)
        stats_layout.addWidget(QLabel("Gesamtprofit:"), 0, 4)
        stats_layout.addWidget(self.trades_profit_label, 0, 5)
        
        layout.addWidget(stats_group)
        
        # Trading Tabelle
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(8)
        self.trades_table.setHorizontalHeaderLabels([
            "Zeit", "Coin", "Seite", "Menge", "Preis", "Total", "Grund", "Status"
        ])
        self.trades_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.trades_table.setAlternatingRowColors(True)
        layout.addWidget(self.trades_table)
        
        return widget
    
    def _load_settings(self):
        """Lädt aktuelle Settings in die UI"""
        if not self.portfolio_manager:
            return
        
        settings = self.portfolio_manager.settings
        
        self.stop_loss_spin.setValue(settings.stop_loss_percent)
        self.trailing_check.setChecked(settings.trailing_stop_enabled)
        self.trailing_activation_spin.setValue(settings.trailing_stop_activation)
        self.trailing_distance_spin.setValue(settings.trailing_stop_distance)
        
        self.auto_sell_check.setChecked(settings.auto_sell_enabled)
        self.auto_sell_spin.setValue(settings.auto_sell_percent)
        self.min_hold_spin.setValue(settings.min_hold_hours)
        
        idx = self.stablecoin_combo.findText(settings.preferred_stablecoin)
        if idx >= 0:
            self.stablecoin_combo.setCurrentIndex(idx)
        
        idx = self.exchange_combo.findText(settings.primary_exchange.capitalize())
        if idx >= 0:
            self.exchange_combo.setCurrentIndex(idx)
    
    def save_settings(self):
        """Speichert Settings"""
        if not self.portfolio_manager:
            return
        
        self.portfolio_manager.settings.stop_loss_percent = self.stop_loss_spin.value()
        self.portfolio_manager.settings.trailing_stop_enabled = self.trailing_check.isChecked()
        self.portfolio_manager.settings.trailing_stop_activation = self.trailing_activation_spin.value()
        self.portfolio_manager.settings.trailing_stop_distance = self.trailing_distance_spin.value()
        
        self.portfolio_manager.settings.auto_sell_enabled = self.auto_sell_check.isChecked()
        self.portfolio_manager.settings.auto_sell_percent = self.auto_sell_spin.value()
        self.portfolio_manager.settings.min_hold_hours = self.min_hold_spin.value()
        self.portfolio_manager.settings.preferred_stablecoin = self.stablecoin_combo.currentText()
        self.portfolio_manager.settings.primary_exchange = self.exchange_combo.currentText().lower()
        
        self.portfolio_manager.save_config()
        
        QMessageBox.information(self, "Gespeichert", "Settings wurden gespeichert!")
    
    def save_exchange_settings(self):
        """Speichert Exchange Credentials"""
        if not self.portfolio_manager:
            return
        
        exchange_name = self.exchange_combo.currentText().lower()
        api_key = self.api_key_edit.text()
        api_secret = self.api_secret_edit.text()
        
        if not api_key or not api_secret:
            QMessageBox.warning(self, "Fehler", "API Key und Secret erforderlich!")
            return
        
        try:
            exchange = Exchange(exchange_name)
            self.portfolio_manager.add_exchange(exchange, api_key, api_secret)
            
            # Clear inputs
            self.api_key_edit.clear()
            self.api_secret_edit.clear()
            
            QMessageBox.information(self, "Gespeichert", f"{exchange_name.capitalize()} wurde hinzugefügt!")
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Fehler: {e}")
    
    def start_monitoring(self):
        """Startet Portfolio Monitoring"""
        if self.portfolio_manager:
            self.portfolio_manager.start_monitoring(interval=60.0)
            self.status_label.setText("✅ Aktiv")
            self.status_label.setStyleSheet("color: #00ff00;")
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            logger.info("💰 Portfolio Monitoring gestartet")
    
    def stop_monitoring(self):
        """Stoppt Portfolio Monitoring"""
        if self.portfolio_manager:
            self.portfolio_manager.stop_monitoring()
            self.status_label.setText("⏹️ Gestoppt")
            self.status_label.setStyleSheet("color: #ff6666;")
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            logger.info("💰 Portfolio Monitoring gestoppt")
    
    def update_ui(self):
        """Aktualisiert die gesamte UI"""
        self._update_portfolio_overview()
        self._update_trading_history()
        
        # Activity Log nur aktualisieren wenn Tab aktiv
        if self.tabs.currentIndex() == 1:
            self.update_activity_log()
    
    def _update_portfolio_overview(self):
        """Aktualisiert Portfolio-Übersicht"""
        if not self.portfolio_manager:
            return
        
        try:
            summary = self.portfolio_manager.get_portfolio_summary()
            
            # Gesamtwert
            total_value = summary.get("total_value_usd", 0)
            self.total_value_label.setText(f"${total_value:.2f}")
            
            # P&L
            pnl = summary.get("total_unrealized_pnl", 0)
            pnl_percent = summary.get("total_unrealized_pnl_percent", 0)
            
            if pnl >= 0:
                self.pnl_label.setText(f"+${pnl:.2f} (+{pnl_percent:.1f}%)")
                self.pnl_label.setStyleSheet("color: #00ff00;")
            else:
                self.pnl_label.setText(f"-${abs(pnl):.2f} ({pnl_percent:.1f}%)")
                self.pnl_label.setStyleSheet("color: #ff6666;")
            
            # Positionen Tabelle
            positions = summary.get("positions", {})
            self.positions_table.setRowCount(len(positions))
            
            for row, (coin, data) in enumerate(positions.items()):
                self.positions_table.setItem(row, 0, QTableWidgetItem(coin))
                self.positions_table.setItem(row, 1, QTableWidgetItem(f"{data['amount']:.6f}"))
                self.positions_table.setItem(row, 2, QTableWidgetItem(f"${data['avg_cost']:.4f}"))
                self.positions_table.setItem(row, 3, QTableWidgetItem(f"${data['current_price']:.4f}"))
                self.positions_table.setItem(row, 4, QTableWidgetItem(f"${data['value_usd']:.2f}"))
                
                pnl_item = QTableWidgetItem(f"${data['unrealized_pnl']:.2f}")
                pnl_item.setForeground(QColor("#00ff00" if data['unrealized_pnl'] >= 0 else "#ff6666"))
                self.positions_table.setItem(row, 5, pnl_item)
                
                pnl_pct_item = QTableWidgetItem(f"{data['unrealized_pnl_percent']:.1f}%")
                pnl_pct_item.setForeground(QColor("#00ff00" if data['unrealized_pnl_percent'] >= 0 else "#ff6666"))
                self.positions_table.setItem(row, 6, pnl_pct_item)
            
            # Marktdaten
            market_info = []
            for coin, data in self.portfolio_manager.market_data.items():
                price = data.price_usd
                change = data.price_change_24h
                market_info.append(f"{coin}: ${price:.4f} ({change:+.1f}%)")
            
            self.market_info.setText("\n".join(market_info) if market_info else "Keine Marktdaten verfügbar")
            
        except Exception as e:
            logger.error(f"Portfolio Update Fehler: {e}")
    
    def _update_trading_history(self):
        """Aktualisiert Trading-Historie"""
        if not self.portfolio_manager:
            return
        
        try:
            trades = self.portfolio_manager.get_trade_history(limit=100)
            
            self.trades_table.setRowCount(len(trades))
            
            total_volume = 0
            
            for row, trade in enumerate(trades):
                self.trades_table.setItem(row, 0, QTableWidgetItem(str(trade.get("created_at", ""))[:19]))
                self.trades_table.setItem(row, 1, QTableWidgetItem(trade.get("coin", "")))
                
                side_item = QTableWidgetItem(trade.get("side", "").upper())
                side_item.setForeground(QColor("#00ff00" if trade.get("side") == "buy" else "#ff6666"))
                self.trades_table.setItem(row, 2, side_item)
                
                self.trades_table.setItem(row, 3, QTableWidgetItem(f"{trade.get('amount', 0):.6f}"))
                self.trades_table.setItem(row, 4, QTableWidgetItem(f"${trade.get('price', 0):.4f}"))
                self.trades_table.setItem(row, 5, QTableWidgetItem(f"${trade.get('total_usd', 0):.2f}"))
                self.trades_table.setItem(row, 6, QTableWidgetItem(trade.get("reason", "")))
                self.trades_table.setItem(row, 7, QTableWidgetItem(trade.get("status", "")))
                
                total_volume += trade.get("total_usd", 0)
            
            self.trades_count_label.setText(str(len(trades)))
            self.trades_volume_label.setText(f"${total_volume:.2f}")
            
        except Exception as e:
            logger.error(f"Trading History Update Fehler: {e}")
    
    def update_activity_log(self):
        """Aktualisiert Activity Log"""
        if not self.portfolio_manager:
            return
        
        try:
            # Block signals während Update
            self.activity_table.blockSignals(True)
            
            # Aktivitäten sammeln
            activities = []
            
            # Portfolio Aktivitäten
            for item in self.portfolio_manager.get_activity_log(limit=50):
                activities.append({
                    "timestamp": item.get("timestamp", ""),
                    "type": f"💰 {item.get('action_type', 'Portfolio')}",
                    "description": item.get("description", ""),
                    "status": "completed",
                    "acknowledged": item.get("acknowledged", False),
                    "id": str(item.get("id", "")),
                    "source": "portfolio"
                })
            
            # Code Repair Aktivitäten (wenn verfügbar)
            try:
                from code_repair import get_repair_manager
                repair = get_repair_manager()
                for item in repair.get_history(limit=50):
                    activities.append({
                        "timestamp": item.get("timestamp", ""),
                        "type": "🔧 Code Repair",
                        "description": f"{item.get('error_type', '')}: {str(item.get('error_message', ''))[:40]}",
                        "status": item.get("status", ""),
                        "acknowledged": item.get("acknowledged", False),
                        "id": item.get("id", ""),
                        "source": "code_repair"
                    })
            except:
                pass
            
            # Filter anwenden
            filter_text = self.filter_combo.currentText()
            if filter_text == "Code Repair":
                activities = [a for a in activities if "Code Repair" in a["type"]]
            elif filter_text == "Portfolio":
                activities = [a for a in activities if "Portfolio" in a["type"] or "💰" in a["type"]]
            elif filter_text == "Trades":
                activities = [a for a in activities if "Trade" in a["type"] or "TRADE" in a["type"]]
            elif filter_text == "Unbestätigt":
                activities = [a for a in activities if not a["acknowledged"]]
            
            # Sortieren
            activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            # Tabelle füllen
            self.activity_table.setRowCount(len(activities))
            
            for row, activity in enumerate(activities):
                # Checkbox
                checkbox = QTableWidgetItem()
                checkbox.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                checkbox.setCheckState(Qt.Checked if activity["acknowledged"] else Qt.Unchecked)
                checkbox.setData(Qt.UserRole, {"id": activity["id"], "source": activity["source"]})
                self.activity_table.setItem(row, 0, checkbox)
                
                # Timestamp
                self.activity_table.setItem(row, 1, QTableWidgetItem(str(activity["timestamp"])[:19]))
                
                # Typ
                self.activity_table.setItem(row, 2, QTableWidgetItem(activity["type"]))
                
                # Beschreibung
                self.activity_table.setItem(row, 3, QTableWidgetItem(activity["description"]))
                
                # Status
                status_item = QTableWidgetItem(activity["status"])
                if activity["status"] == "success":
                    status_item.setForeground(QColor("#00ff00"))
                elif activity["status"] == "failed":
                    status_item.setForeground(QColor("#ff6666"))
                self.activity_table.setItem(row, 4, status_item)
                
                # ID (versteckt)
                self.activity_table.setItem(row, 5, QTableWidgetItem(activity["id"]))
            
            # Signals wieder aktivieren
            self.activity_table.blockSignals(False)
            
        except Exception as e:
            logger.error(f"Activity Log Update Fehler: {e}")
            self.activity_table.blockSignals(False)
    
    def _on_checkbox_changed(self, row: int, column: int):
        """Callback wenn Checkbox geändert wird"""
        if column != 0:
            return
        
        item = self.activity_table.item(row, 0)
        if not item:
            return
        
        data = item.data(Qt.UserRole)
        if not data:
            return
        
        is_checked = item.checkState() == Qt.Checked
        
        if is_checked:
            activity_id = data.get("id", "")
            source = data.get("source", "")
            
            if source == "portfolio" and self.portfolio_manager:
                try:
                    self.portfolio_manager.db.acknowledge_activity(int(activity_id))
                except:
                    pass
            elif source == "code_repair":
                try:
                    from code_repair import get_repair_manager
                    repair = get_repair_manager()
                    repair.acknowledge(activity_id)
                except:
                    pass
    
    def acknowledge_all(self):
        """Hakt alle Aktivitäten ab"""
        for row in range(self.activity_table.rowCount()):
            item = self.activity_table.item(row, 0)
            if item and item.checkState() == Qt.Unchecked:
                item.setCheckState(Qt.Checked)
    
    # Callbacks
    def _on_alert(self, level: str, message: str):
        """Portfolio Alert Callback"""
        self.alert_triggered.emit(level, message)
        logger.info(f"💰 Alert [{level}]: {message}")
    
    def _on_deposit(self, deposit):
        """Mining Deposit Callback"""
        logger.info(f"💰 Neue Einzahlung: {deposit.amount:.6f} {deposit.coin}")
        self.update_ui()
    
    def _on_trade(self, trade):
        """Trade Executed Callback"""
        logger.info(f"📈 Trade: {trade.side.upper()} {trade.amount} {trade.coin}")
        self.update_ui()
    
    def _on_price_update(self, prices: Dict[str, float]):
        """Price Update Callback"""
        self._update_portfolio_overview()


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    widget = PortfolioWidget()
    widget.setWindowTitle("💰 Portfolio Manager Test")
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec())
