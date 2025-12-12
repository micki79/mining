#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Tray Icon - Minimieren ins System Tray
Teil des GPU Mining Profit Switcher V11.0 Ultimate
"""

import logging
from typing import Optional, Callable

try:
    from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
    from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
    from PySide6.QtCore import QObject, Signal
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MiningTrayIcon(QSystemTrayIcon if PYSIDE_AVAILABLE else object):
    """
    System Tray Icon für die Mining-GUI.
    
    Features:
    - Minimieren ins Tray
    - Quick Stats im Tooltip
    - Rechtsklick-Menü
    - Desktop-Benachrichtigungen
    """
    
    # Signals
    if PYSIDE_AVAILABLE:
        show_requested = Signal()
        start_requested = Signal()
        stop_requested = Signal()
        quit_requested = Signal()
    
    def __init__(self, parent=None):
        if not PYSIDE_AVAILABLE:
            logger.error("PySide6 nicht verfügbar")
            return
        
        super().__init__(parent)
        
        self._mining = False
        self._hashrate = 0.0
        self._temperature = 0
        self._power = 0
        
        # Icon erstellen
        self._create_icon()
        
        # Menü erstellen
        self._create_menu()
        
        # Tooltip
        self.setToolTip("GPU Mining Profit Switcher\nStatus: Idle")
        
        # Doppelklick -> Fenster zeigen
        self.activated.connect(self._on_activated)
    
    def _create_icon(self):
        """Erstellt das Tray-Icon"""
        # Einfaches Mining-Icon (grüner Kreis mit "M")
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Hintergrund-Kreis
        painter.setBrush(QColor('#1a1a2e'))
        painter.setPen(QColor('#00ff88'))
        painter.drawEllipse(4, 4, 56, 56)
        
        # "M" für Mining
        painter.setPen(QColor('#00ff88'))
        font = QFont('Arial', 28, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x84, "M")  # AlignCenter
        
        painter.end()
        
        self.setIcon(QIcon(pixmap))
    
    def _create_menu(self):
        """Erstellt das Kontextmenü"""
        menu = QMenu()
        
        # Show Dashboard
        show_action = QAction("📊 Dashboard anzeigen", menu)
        show_action.triggered.connect(self._on_show)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Start Mining
        self._start_action = QAction("▶️ Mining starten", menu)
        self._start_action.triggered.connect(self._on_start)
        menu.addAction(self._start_action)
        
        # Stop Mining
        self._stop_action = QAction("⏹️ Mining stoppen", menu)
        self._stop_action.triggered.connect(self._on_stop)
        self._stop_action.setEnabled(False)
        menu.addAction(self._stop_action)
        
        menu.addSeparator()
        
        # Quick Stats (nur Anzeige)
        self._stats_action = QAction("📈 Hashrate: -- MH/s", menu)
        self._stats_action.setEnabled(False)
        menu.addAction(self._stats_action)
        
        self._temp_action = QAction("🌡️ Temp: --°C", menu)
        self._temp_action.setEnabled(False)
        menu.addAction(self._temp_action)
        
        menu.addSeparator()
        
        # Quit
        quit_action = QAction("❌ Beenden", menu)
        quit_action.triggered.connect(self._on_quit)
        menu.addAction(quit_action)
        
        self.setContextMenu(menu)
    
    def _on_activated(self, reason):
        """Handler für Tray-Icon Aktivierung"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._on_show()
    
    def _on_show(self):
        """Zeigt das Hauptfenster"""
        self.show_requested.emit()
    
    def _on_start(self):
        """Startet Mining"""
        self.start_requested.emit()
    
    def _on_stop(self):
        """Stoppt Mining"""
        self.stop_requested.emit()
    
    def _on_quit(self):
        """Beendet die Anwendung"""
        self.quit_requested.emit()
    
    def update_stats(self, hashrate: float, temperature: int, power: float):
        """
        Aktualisiert die Stats im Menü und Tooltip.
        
        Args:
            hashrate: Hashrate in MH/s
            temperature: Temperatur in °C
            power: Power in Watt
        """
        self._hashrate = hashrate
        self._temperature = temperature
        self._power = power
        
        # Menü-Einträge aktualisieren
        self._stats_action.setText(f"📈 Hashrate: {hashrate:.2f} MH/s")
        self._temp_action.setText(f"🌡️ Temp: {temperature}°C | ⚡ {power:.0f}W")
        
        # Tooltip aktualisieren
        status = "Mining" if self._mining else "Idle"
        tooltip = f"GPU Mining Profit Switcher\n"
        tooltip += f"Status: {status}\n"
        if self._mining:
            tooltip += f"Hashrate: {hashrate:.2f} MH/s\n"
            tooltip += f"Temp: {temperature}°C | Power: {power:.0f}W"
        self.setToolTip(tooltip)
    
    def set_mining_state(self, mining: bool):
        """Setzt den Mining-Status"""
        self._mining = mining
        self._start_action.setEnabled(not mining)
        self._stop_action.setEnabled(mining)
        
        # Tooltip aktualisieren
        status = "Mining" if mining else "Idle"
        self.setToolTip(f"GPU Mining Profit Switcher\nStatus: {status}")
    
    def show_notification(self, title: str, message: str, icon_type: int = None):
        """
        Zeigt eine Desktop-Benachrichtigung.
        
        Args:
            title: Titel der Benachrichtigung
            message: Nachrichtentext
            icon_type: QSystemTrayIcon.Information/Warning/Critical
        """
        if icon_type is None:
            icon_type = QSystemTrayIcon.Information
        
        if self.supportsMessages():
            self.showMessage(title, message, icon_type, 5000)
    
    def notify_high_temp(self, gpu_index: int, temperature: int):
        """Benachrichtigung bei hoher Temperatur"""
        self.show_notification(
            "⚠️ Hohe Temperatur",
            f"GPU {gpu_index} erreicht {temperature}°C!",
            QSystemTrayIcon.Warning
        )
    
    def notify_low_hashrate(self, gpu_index: int, hashrate: float, expected: float):
        """Benachrichtigung bei niedriger Hashrate"""
        percent = (hashrate / expected * 100) if expected > 0 else 0
        self.show_notification(
            "⚠️ Niedrige Hashrate",
            f"GPU {gpu_index}: {hashrate:.2f} MH/s ({percent:.0f}% erwartet)",
            QSystemTrayIcon.Warning
        )
    
    def notify_miner_stopped(self, reason: str = ""):
        """Benachrichtigung wenn Miner stoppt"""
        msg = "Der Mining-Prozess wurde beendet"
        if reason:
            msg += f"\nGrund: {reason}"
        self.show_notification(
            "⏹️ Mining gestoppt",
            msg,
            QSystemTrayIcon.Information
        )
    
    def notify_miner_started(self, coin: str, pool: str):
        """Benachrichtigung wenn Miner startet"""
        self.show_notification(
            "▶️ Mining gestartet",
            f"Mining {coin} auf {pool}",
            QSystemTrayIcon.Information
        )
    
    def notify_coin_switch(self, old_coin: str, new_coin: str, reason: str = ""):
        """Benachrichtigung bei Coin-Wechsel"""
        msg = f"Wechsel von {old_coin} zu {new_coin}"
        if reason:
            msg += f"\n{reason}"
        self.show_notification(
            "🔄 Coin gewechselt",
            msg,
            QSystemTrayIcon.Information
        )
