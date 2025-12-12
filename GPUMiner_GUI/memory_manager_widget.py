#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Manager Widget - GUI für automatische Speicher-Optimierung
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Zeigt aktuellen Speicher-Status
- Prüft Mining-Anforderungen
- Automatische Pagefile-Anpassung
- Neustart-Planung mit Countdown
- AI-Empfehlungen

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QGroupBox, QFrame,
    QProgressBar, QMessageBox, QDialog,
    QTextEdit, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class RestartCountdownDialog(QDialog):
    """Dialog mit Countdown vor Neustart"""
    
    cancelled = Signal()
    restart_now = Signal()
    
    def __init__(self, seconds: int = 60, parent=None):
        super().__init__(parent)
        self.remaining = seconds
        self.setWindowTitle("⚠️ PC-Neustart geplant")
        self.setModal(True)
        self.setFixedSize(400, 250)
        self.setup_ui()
        
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start(1000)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Warnung
        warning = QLabel("⚠️ NEUSTART ERFORDERLICH")
        warning.setFont(QFont("", 16, QFont.Bold))
        warning.setStyleSheet("color: #FFA500;")
        warning.setAlignment(Qt.AlignCenter)
        layout.addWidget(warning)
        
        # Erklärung
        explanation = QLabel(
            "Der virtuelle Speicher wurde für Mining optimiert.\n"
            "Ein Neustart ist erforderlich, um die Änderungen anzuwenden."
        )
        explanation.setAlignment(Qt.AlignCenter)
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Countdown
        self.countdown_label = QLabel(f"Neustart in {self.remaining} Sekunden...")
        self.countdown_label.setFont(QFont("", 14, QFont.Bold))
        self.countdown_label.setStyleSheet("color: #f44336;")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.countdown_label)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setMaximum(self.remaining)
        self.progress.setValue(self.remaining)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 5px;
                background: #2b2b2b;
            }
            QProgressBar::chunk {
                background: #f44336;
            }
        """)
        layout.addWidget(self.progress)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("❌ Abbrechen")
        self.cancel_btn.setStyleSheet("background: #4CAF50; padding: 10px; font-weight: bold;")
        self.cancel_btn.clicked.connect(self.cancel_restart)
        btn_layout.addWidget(self.cancel_btn)
        
        self.now_btn = QPushButton("🔄 Jetzt Neustarten")
        self.now_btn.setStyleSheet("background: #f44336; padding: 10px; font-weight: bold;")
        self.now_btn.clicked.connect(self.do_restart_now)
        btn_layout.addWidget(self.now_btn)
        
        layout.addLayout(btn_layout)
        
        # Hinweis
        note = QLabel("💡 Mining startet nach Neustart automatisch")
        note.setStyleSheet("color: #888; font-size: 10px;")
        note.setAlignment(Qt.AlignCenter)
        layout.addWidget(note)
    
    def update_countdown(self):
        self.remaining -= 1
        self.countdown_label.setText(f"Neustart in {self.remaining} Sekunden...")
        self.progress.setValue(self.remaining)
        
        if self.remaining <= 0:
            self.timer.stop()
            self.restart_now.emit()
            self.accept()
    
    def cancel_restart(self):
        self.timer.stop()
        self.cancelled.emit()
        self.reject()
    
    def do_restart_now(self):
        self.timer.stop()
        self.restart_now.emit()
        self.accept()


class MemoryStatusCard(QFrame):
    """Status-Karte für Speicher-Anzeige"""
    
    def __init__(self, title: str, icon: str, color: str, parent=None):
        super().__init__(parent)
        self.color = color
        self.setup_ui(title, icon)
    
    def setup_ui(self, title: str, icon: str):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet(f"""
            MemoryStatusCard {{
                background: #2b2b2b;
                border: 1px solid {self.color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Icon + Title
        header = QLabel(f"{icon} {title}")
        header.setStyleSheet(f"color: {self.color}; font-size: 11px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Value
        self.value_label = QLabel("-")
        self.value_label.setFont(QFont("", 16, QFont.Bold))
        self.value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.value_label)
        
        # Subtitle
        self.subtitle_label = QLabel("")
        self.subtitle_label.setStyleSheet("color: #888; font-size: 10px;")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)
    
    def set_value(self, value: str, subtitle: str = ""):
        self.value_label.setText(value)
        self.subtitle_label.setText(subtitle)


class MemoryManagerWidget(QWidget):
    """
    Haupt-Widget für Speicher-Management
    
    Features:
    - Status-Anzeige (RAM, Pagefile, Disk)
    - Mining-Anforderungen berechnen
    - Auto-Optimierung mit Neustart
    """
    
    # Signals
    optimization_started = Signal()
    optimization_completed = Signal(bool, str)  # success, message
    restart_scheduled = Signal(int)  # seconds
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._memory_manager = None
        self._memory_ai = None
        self._gpu_count = 1
        self._coins = []
        
        self.setup_ui()
        
        # Auto-Update Timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update_status)
        self._update_timer.start(5000)  # 5 Sekunden
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === HEADER ===
        header = QHBoxLayout()
        
        title = QLabel("💾 Speicher-Manager")
        title.setFont(QFont("", 14, QFont.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        # Refresh Button
        self.refresh_btn = QPushButton("🔄 Aktualisieren")
        self.refresh_btn.clicked.connect(self.update_status)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # === STATUS CARDS ===
        cards_layout = QHBoxLayout()
        
        self.ram_card = MemoryStatusCard("RAM", "🧠", "#2196F3")
        cards_layout.addWidget(self.ram_card)
        
        self.pagefile_card = MemoryStatusCard("Pagefile", "💾", "#4CAF50")
        cards_layout.addWidget(self.pagefile_card)
        
        self.virtual_card = MemoryStatusCard("Virtual", "📊", "#9C27B0")
        cards_layout.addWidget(self.virtual_card)
        
        self.disk_card = MemoryStatusCard("Disk frei", "💿", "#FFA500")
        cards_layout.addWidget(self.disk_card)
        
        layout.addLayout(cards_layout)
        
        # === MINING REQUIREMENTS ===
        req_group = QGroupBox("Mining-Anforderungen")
        req_layout = QVBoxLayout(req_group)
        
        # GPU Count + Coins anzeigen
        info_layout = QHBoxLayout()
        
        self.gpu_info_label = QLabel("GPUs: -")
        self.gpu_info_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self.gpu_info_label)
        
        self.coins_info_label = QLabel("Coins: -")
        info_layout.addWidget(self.coins_info_label)
        
        info_layout.addStretch()
        req_layout.addLayout(info_layout)
        
        # Requirements Display
        self.req_display = QTextEdit()
        self.req_display.setReadOnly(True)
        self.req_display.setMaximumHeight(120)
        self.req_display.setStyleSheet("""
            QTextEdit {
                background: #1e1e1e;
                border: 1px solid #404040;
                border-radius: 4px;
                font-family: monospace;
            }
        """)
        req_layout.addWidget(self.req_display)
        
        layout.addWidget(req_group)
        
        # === AI EMPFEHLUNG ===
        ai_group = QGroupBox("🤖 AI-Analyse")
        ai_layout = QVBoxLayout(ai_group)
        
        # Status
        status_layout = QHBoxLayout()
        
        self.status_icon = QLabel("⚪")
        self.status_icon.setFont(QFont("", 20))
        status_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("Warte auf Analyse...")
        self.status_label.setFont(QFont("", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        ai_layout.addLayout(status_layout)
        
        # Empfehlung
        self.recommendation_label = QLabel("")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setStyleSheet("padding: 10px; background: #2b2b2b; border-radius: 4px;")
        ai_layout.addWidget(self.recommendation_label)
        
        layout.addWidget(ai_group)
        
        # === ACTIONS ===
        action_group = QGroupBox("Aktionen")
        action_layout = QVBoxLayout(action_group)
        
        # Auto-Optimize Toggle
        auto_layout = QHBoxLayout()
        
        self.auto_check = QCheckBox("🔄 Automatisch optimieren wenn nötig")
        self.auto_check.setToolTip("Bei kritischem Speichermangel automatisch Pagefile erhöhen und neustarten")
        auto_layout.addWidget(self.auto_check)
        
        auto_layout.addStretch()
        
        auto_layout.addWidget(QLabel("Restart-Delay:"))
        self.restart_delay_spin = QSpinBox()
        self.restart_delay_spin.setRange(30, 300)
        self.restart_delay_spin.setValue(60)
        self.restart_delay_spin.setSuffix(" Sek")
        auto_layout.addWidget(self.restart_delay_spin)
        
        action_layout.addLayout(auto_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("🔍 Analysieren")
        self.analyze_btn.setStyleSheet("padding: 8px 16px;")
        self.analyze_btn.clicked.connect(self.run_analysis)
        btn_layout.addWidget(self.analyze_btn)
        
        self.optimize_btn = QPushButton("⚡ Jetzt Optimieren")
        self.optimize_btn.setStyleSheet("background: #4CAF50; padding: 8px 16px; font-weight: bold;")
        self.optimize_btn.clicked.connect(self.run_optimization)
        self.optimize_btn.setEnabled(False)
        btn_layout.addWidget(self.optimize_btn)
        
        action_layout.addLayout(btn_layout)
        
        layout.addWidget(action_group)
        
        # Stretch
        layout.addStretch()
    
    def set_managers(self, memory_manager, memory_ai):
        """Setzt die Manager-Referenzen"""
        self._memory_manager = memory_manager
        self._memory_ai = memory_ai
        self.update_status()
    
    def set_mining_config(self, gpu_count: int, coins: List[str]):
        """Setzt aktuelle Mining-Konfiguration"""
        self._gpu_count = gpu_count
        self._coins = coins
        
        self.gpu_info_label.setText(f"GPUs: {gpu_count}")
        self.coins_info_label.setText(f"Coins: {', '.join(coins) if coins else '-'}")
        
        self.update_requirements()
    
    def update_status(self):
        """Aktualisiert Speicher-Status"""
        if not self._memory_manager:
            return
        
        try:
            info = self._memory_manager.get_system_memory_info()
            
            # RAM
            self.ram_card.set_value(
                f"{info.total_ram_mb // 1024} GB",
                f"{info.available_ram_mb // 1024} GB frei ({100 - info.ram_percent_used:.0f}%)"
            )
            
            # Pagefile
            self.pagefile_card.set_value(
                f"{info.pagefile_total_mb // 1024} GB",
                f"{info.pagefile_free_mb // 1024} GB frei"
            )
            
            # Virtual
            self.virtual_card.set_value(
                f"{info.total_virtual_mb // 1024} GB",
                f"{info.available_virtual_mb // 1024} GB verfügbar"
            )
            
            # Disk
            self.disk_card.set_value(
                f"{info.pagefile_disk_free_mb // 1024} GB",
                f"auf {info.pagefile_disk}"
            )
            
        except Exception as e:
            logger.error(f"Status-Update Fehler: {e}")
    
    def update_requirements(self):
        """Aktualisiert Mining-Anforderungen"""
        if not self._memory_manager or not self._coins:
            self.req_display.setText("Keine Mining-Konfiguration gesetzt.")
            return
        
        try:
            req = self._memory_manager.calculate_mining_requirements(self._gpu_count, self._coins)
            self.req_display.setText(req.explanation)
        except Exception as e:
            self.req_display.setText(f"Fehler: {e}")
    
    def run_analysis(self):
        """Führt AI-Analyse durch"""
        if not self._memory_ai or not self._coins:
            QMessageBox.warning(self, "Fehler", "Mining-Konfiguration nicht gesetzt!")
            return
        
        try:
            evaluation = self._memory_ai.evaluate_situation(self._gpu_count, self._coins)
            
            # Status-Icon aktualisieren
            if evaluation["severity"] == "info":
                self.status_icon.setText("✅")
                self.status_label.setText(f"Status: {evaluation['status']}")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            elif evaluation["severity"] == "warning":
                self.status_icon.setText("⚠️")
                self.status_label.setText(f"Status: {evaluation['status']}")
                self.status_label.setStyleSheet("color: #FFA500; font-weight: bold;")
            else:  # critical
                self.status_icon.setText("🚨")
                self.status_label.setText(f"Status: {evaluation['status']}")
                self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            
            # Empfehlung
            self.recommendation_label.setText(evaluation["recommendation"])
            
            # Optimize-Button
            self.optimize_btn.setEnabled(evaluation["action_needed"])
            
            # Bei kritisch und Auto-Optimize: automatisch starten
            if evaluation["severity"] == "critical" and self.auto_check.isChecked():
                reply = QMessageBox.question(
                    self,
                    "🚨 Kritischer Speichermangel",
                    "Speicher ist kritisch niedrig für Mining!\n\n"
                    "Soll automatisch optimiert und neugestartet werden?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.run_optimization()
            
        except Exception as e:
            self.status_icon.setText("❌")
            self.status_label.setText("Analyse fehlgeschlagen")
            self.recommendation_label.setText(str(e))
            logger.error(f"Analyse Fehler: {e}")
    
    def run_optimization(self):
        """Führt Speicher-Optimierung durch"""
        if not self._memory_manager:
            return
        
        # Bestätigung
        reply = QMessageBox.warning(
            self,
            "⚠️ Speicher-Optimierung",
            "Diese Aktion wird:\n\n"
            "1. Den virtuellen Speicher (Pagefile) erhöhen\n"
            "2. Einen PC-NEUSTART durchführen\n\n"
            "Alle ungespeicherten Arbeiten gehen verloren!\n\n"
            "Fortfahren?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        self.optimization_started.emit()
        
        try:
            # Analyse für neue Größe
            decision = self._memory_manager.analyze_and_decide(self._gpu_count, self._coins)
            
            if not decision.can_auto_fix:
                QMessageBox.critical(
                    self,
                    "❌ Optimierung nicht möglich",
                    f"{decision.reason}\n\n"
                    "Bitte manuell beheben:\n" + "\n".join(decision.steps)
                )
                self.optimization_completed.emit(False, decision.reason)
                return
            
            # Pagefile ändern
            success, msg = self._memory_manager.apply_pagefile_change(decision.new_pagefile_mb)
            
            if not success:
                QMessageBox.critical(self, "❌ Fehler", f"Pagefile-Änderung fehlgeschlagen:\n{msg}")
                self.optimization_completed.emit(False, msg)
                return
            
            # Neustart planen
            delay = self.restart_delay_spin.value()
            
            restart_success, restart_msg = self._memory_manager.schedule_restart(delay)
            
            if restart_success:
                self.restart_scheduled.emit(delay)
                
                # Countdown Dialog
                dialog = RestartCountdownDialog(delay, self)
                dialog.cancelled.connect(self._on_restart_cancelled)
                dialog.restart_now.connect(self._on_restart_now)
                dialog.exec()
            else:
                QMessageBox.warning(
                    self,
                    "⚠️ Neustart-Planung fehlgeschlagen",
                    f"{restart_msg}\n\nBitte PC manuell neustarten!"
                )
            
            self.optimization_completed.emit(True, msg)
            
        except Exception as e:
            logger.error(f"Optimierung Fehler: {e}")
            QMessageBox.critical(self, "❌ Fehler", str(e))
            self.optimization_completed.emit(False, str(e))
    
    def _on_restart_cancelled(self):
        """Neustart wurde abgebrochen"""
        if self._memory_manager:
            self._memory_manager.cancel_restart()
        
        QMessageBox.information(
            self,
            "Neustart abgebrochen",
            "Der Neustart wurde abgebrochen.\n\n"
            "⚠️ WICHTIG: Bitte starten Sie den PC manuell neu,\n"
            "damit die Speicher-Änderungen wirksam werden!"
        )
    
    def _on_restart_now(self):
        """Sofort neustarten"""
        # Nichts zu tun - System startet bereits neu
        pass
    
    def check_before_mining(self) -> bool:
        """
        Prüft Speicher vor Mining-Start
        
        Returns:
            True wenn Mining starten kann, False wenn Optimierung nötig
        """
        if not self._memory_ai or not self._coins:
            return True  # Keine Prüfung möglich
        
        evaluation = self._memory_ai.evaluate_situation(self._gpu_count, self._coins)
        
        if evaluation["severity"] == "critical":
            reply = QMessageBox.question(
                self,
                "🚨 Speicher-Problem",
                f"{evaluation['recommendation']}\n\n"
                "Mining könnte fehlschlagen.\n"
                "Soll der Speicher jetzt optimiert werden?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.run_optimization()
                return False
        
        return True


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
    
    # Memory Manager importieren
    try:
        from system_memory_manager import get_memory_manager, get_memory_ai
        manager = get_memory_manager()
        ai = get_memory_ai()
    except ImportError:
        manager = None
        ai = None
        print("⚠️ system_memory_manager nicht gefunden")
    
    widget = MemoryManagerWidget()
    widget.setWindowTitle("Memory Manager Test")
    widget.resize(600, 500)
    
    if manager and ai:
        widget.set_managers(manager, ai)
        widget.set_mining_config(2, ["RVN", "ERG", "GRIN"])
    
    widget.show()
    sys.exit(app.exec())
