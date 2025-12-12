#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent Widget für die Mining GUI
Bietet Chat-Interface, Fehler-Übersicht und Agent-Steuerung

Features:
- Chat mit dem AI Agent
- Echtzeit Fehler-Liste
- Aktions-Historie
- Provider-Auswahl
- Auto-Fix Toggle
"""

import sys
from datetime import datetime
from typing import Optional, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QTabWidget, QTableWidget, QTableWidgetItem,
        QPushButton, QLabel, QLineEdit, QComboBox,
        QTextEdit, QGroupBox, QSplitter, QCheckBox,
        QHeaderView, QAbstractItemView, QMessageBox,
        QProgressBar, QFrame, QScrollArea, QSizePolicy
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QThread
    from PySide6.QtGui import QFont, QColor, QTextCursor
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

# AI Agent Import
try:
    from ai_agent import (
        AIAgent, get_ai_agent, LLMProvider, ErrorSeverity,
        ActionType, DetectedError, AgentAction
    )
    AI_AGENT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ AI Agent nicht verfügbar: {e}")
    AI_AGENT_AVAILABLE = False

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
        "error": "#ff4444",
        "info": "#00aaff"
    }


class ChatBubble(QFrame):
    """Eine Chat-Nachricht als Bubble"""
    
    def __init__(self, message: str, is_user: bool = True, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Header (User oder AI)
        header = QLabel("👤 Du" if is_user else "🤖 AI Agent")
        header.setStyleSheet(f"color: {COLORS.get('text_secondary', '#a0a0a0')}; font-size: 11px;")
        layout.addWidget(header)
        
        # Nachricht
        text = QLabel(message)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text.setStyleSheet(f"""
            background-color: {'#2d5a8a' if is_user else '#3d3d5c'};
            color: {COLORS.get('text', '#ffffff')};
            padding: 10px;
            border-radius: 10px;
        """)
        layout.addWidget(text)
        
        # Styling
        self.setStyleSheet("background: transparent;")


class AIAgentWidget(QWidget):
    """
    Haupt-Widget für den AI Agent Tab
    """
    
    # Signals
    error_detected = Signal(dict)
    action_executed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # AI Agent
        self.agent: Optional[AIAgent] = None
        if AI_AGENT_AVAILABLE:
            self.agent = get_ai_agent()
            self._register_callbacks()
        
        # UI Setup
        self._setup_ui()
        
        # Timer für Updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_displays)
        self.update_timer.start(2000)  # Alle 2 Sekunden
        
        # Initial Update
        self._update_displays()
    
    def _setup_ui(self):
        """Erstellt die UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Haupt-Splitter (Chat links, Info rechts)
        splitter = QSplitter(Qt.Horizontal)
        
        # Linke Seite: Chat
        chat_widget = self._create_chat_panel()
        splitter.addWidget(chat_widget)
        
        # Rechte Seite: Tabs für Fehler/Aktionen/Settings
        right_tabs = QTabWidget()
        right_tabs.addTab(self._create_errors_panel(), "⚠️ Fehler")
        right_tabs.addTab(self._create_actions_panel(), "🔧 Aktionen")
        right_tabs.addTab(self._create_solutions_panel(), "📚 Lösungen")
        right_tabs.addTab(self._create_settings_panel(), "⚙️ Settings")
        splitter.addWidget(right_tabs)
        
        # Splitter-Verhältnis
        splitter.setSizes([500, 400])
        
        layout.addWidget(splitter)
    
    def _create_header(self) -> QWidget:
        """Erstellt den Header mit Status und Kontrollen"""
        header = QGroupBox("🤖 AI Agent Status")
        layout = QHBoxLayout(header)
        
        # Status-Anzeigen
        self.status_label = QLabel("⏸️ Inaktiv")
        self.status_label.setStyleSheet(f"color: {COLORS.get('warning', '#ffaa00')}; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        self.provider_label = QLabel("Provider: -")
        layout.addWidget(self.provider_label)
        
        self.stats_label = QLabel("Fehler: 0 | Aktionen: 0 | Lösungen: 0")
        layout.addWidget(self.stats_label)
        
        layout.addStretch()
        
        # Auto-Fix Toggle
        self.auto_fix_check = QCheckBox("🔧 Auto-Fix")
        self.auto_fix_check.setChecked(True)
        self.auto_fix_check.toggled.connect(self._toggle_auto_fix)
        layout.addWidget(self.auto_fix_check)
        
        # Learning Toggle
        self.learning_check = QCheckBox("📚 Lernen")
        self.learning_check.setChecked(True)
        self.learning_check.toggled.connect(self._toggle_learning)
        layout.addWidget(self.learning_check)
        
        # Start/Stop Button
        self.toggle_btn = QPushButton("▶️ Starten")
        self.toggle_btn.clicked.connect(self._toggle_monitoring)
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.get('success', '#00ff88')};
                color: black;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {COLORS.get('highlight', '#e94560')};
            }}
        """)
        layout.addWidget(self.toggle_btn)
        
        return header
    
    def _create_chat_panel(self) -> QWidget:
        """Erstellt das Chat-Panel"""
        panel = QGroupBox("💬 Chat mit AI Agent")
        layout = QVBoxLayout(panel)
        
        # Chat-Verlauf (scrollbar)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS.get('primary', '#1a1a2e')};
                border: 1px solid {COLORS.get('accent', '#0f3460')};
                border-radius: 5px;
            }}
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_container)
        layout.addWidget(self.chat_scroll)
        
        # Willkommensnachricht
        self._add_chat_message(
            "👋 Hallo! Ich bin dein AI Mining Agent. Ich überwache dein System, "
            "erkenne Probleme und helfe dir bei der Optimierung. Frag mich einfach!",
            is_user=False
        )
        
        # Eingabebereich
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Nachricht eingeben... (z.B. 'Warum ist meine GPU so heiß?')")
        self.chat_input.returnPressed.connect(self._send_chat)
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.get('secondary', '#16213e')};
                color: {COLORS.get('text', '#ffffff')};
                padding: 10px;
                border: 1px solid {COLORS.get('accent', '#0f3460')};
                border-radius: 5px;
            }}
        """)
        input_layout.addWidget(self.chat_input)
        
        send_btn = QPushButton("📤 Senden")
        send_btn.clicked.connect(self._send_chat)
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.get('highlight', '#e94560')};
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }}
        """)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        # Quick Actions
        quick_layout = QHBoxLayout()
        quick_actions = [
            ("🔍 GPU Status", "Was ist der aktuelle GPU-Status?"),
            ("⚠️ Probleme?", "Gibt es aktuelle Probleme im System?"),
            ("💡 Optimierung", "Wie kann ich mein Mining optimieren?"),
            ("📊 Statistik", "Zeige mir die Mining-Statistiken"),
        ]
        
        for text, prompt in quick_actions:
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, p=prompt: self._quick_action(p))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('accent', '#0f3460')};
                    color: {COLORS.get('text', '#ffffff')};
                    padding: 5px 10px;
                    border-radius: 3px;
                    font-size: 11px;
                }}
            """)
            quick_layout.addWidget(btn)
        
        layout.addLayout(quick_layout)
        
        return panel
    
    def _create_errors_panel(self) -> QWidget:
        """Erstellt das Fehler-Panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Fehler-Tabelle
        self.errors_table = QTableWidget()
        self.errors_table.setColumnCount(5)
        self.errors_table.setHorizontalHeaderLabels([
            "Zeit", "Schwere", "Kategorie", "Nachricht", "Status"
        ])
        self.errors_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.errors_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.errors_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS.get('primary', '#1a1a2e')};
                color: {COLORS.get('text', '#ffffff')};
                gridline-color: {COLORS.get('accent', '#0f3460')};
            }}
            QHeaderView::section {{
                background-color: {COLORS.get('secondary', '#16213e')};
                color: {COLORS.get('text', '#ffffff')};
                padding: 5px;
            }}
        """)
        layout.addWidget(self.errors_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ Löschen")
        clear_btn.clicked.connect(self._clear_errors)
        btn_layout.addWidget(clear_btn)
        
        fix_btn = QPushButton("🔧 Ausgewählten fixen")
        fix_btn.clicked.connect(self._fix_selected_error)
        btn_layout.addWidget(fix_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return panel
    
    def _create_actions_panel(self) -> QWidget:
        """Erstellt das Aktionen-Panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Aktionen-Tabelle
        self.actions_table = QTableWidget()
        self.actions_table.setColumnCount(5)
        self.actions_table.setHorizontalHeaderLabels([
            "Zeit", "Aktion", "Ziel", "Ergebnis", "Status"
        ])
        self.actions_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.actions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.actions_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS.get('primary', '#1a1a2e')};
                color: {COLORS.get('text', '#ffffff')};
                gridline-color: {COLORS.get('accent', '#0f3460')};
            }}
        """)
        layout.addWidget(self.actions_table)
        
        # Manuelle Aktionen
        manual_group = QGroupBox("🔧 Manuelle Aktionen")
        manual_layout = QGridLayout(manual_group)
        
        actions = [
            ("🔄 Miner Neustarten", ActionType.RESTART_MINER),
            ("❄️ Lüfter erhöhen", ActionType.INCREASE_FAN),
            ("⚡ Power reduzieren", ActionType.REDUCE_POWER),
            ("🔀 Pool wechseln", ActionType.CHANGE_POOL),
            ("🔍 Web-Suche", ActionType.WEB_SEARCH),
        ]
        
        for i, (text, action_type) in enumerate(actions):
            btn = QPushButton(text)
            btn.clicked.connect(lambda checked, at=action_type: self._manual_action(at))
            manual_layout.addWidget(btn, i // 3, i % 3)
        
        layout.addWidget(manual_group)
        
        return panel
    
    def _create_solutions_panel(self) -> QWidget:
        """Erstellt das Lösungen-Panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Info Label
        info = QLabel("📚 Gelernte Lösungen werden hier angezeigt. Der Agent lernt aus erfolgreichen Fixes.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {COLORS.get('text_secondary', '#a0a0a0')};")
        layout.addWidget(info)
        
        # Lösungen-Tabelle
        self.solutions_table = QTableWidget()
        self.solutions_table.setColumnCount(5)
        self.solutions_table.setHorizontalHeaderLabels([
            "ID", "Kategorie", "Pattern", "Erfolgsrate", "Anwendungen"
        ])
        self.solutions_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.solutions_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS.get('primary', '#1a1a2e')};
                color: {COLORS.get('text', '#ffffff')};
            }}
        """)
        layout.addWidget(self.solutions_table)
        
        return panel
    
    def _create_settings_panel(self) -> QWidget:
        """Erstellt das Settings-Panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # LLM Provider Settings
        provider_group = QGroupBox("🤖 LLM Provider")
        provider_layout = QGridLayout(provider_group)
        
        # Provider Auswahl
        provider_layout.addWidget(QLabel("Aktiver Provider:"), 0, 0)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["GROQ", "Gemini", "DeepSeek", "HuggingFace", "OpenRouter"])
        self.provider_combo.currentTextChanged.connect(self._change_provider)
        provider_layout.addWidget(self.provider_combo, 0, 1)
        
        # API Keys (mit * versteckt)
        self.api_key_inputs = {}
        providers = [
            ("GROQ", "groq"),
            ("Gemini", "gemini"),
            ("DeepSeek", "deepseek"),
            ("HuggingFace", "huggingface"),
            ("OpenRouter", "openrouter")
        ]
        
        for i, (name, key) in enumerate(providers, start=1):
            provider_layout.addWidget(QLabel(f"{name} API Key:"), i, 0)
            input_field = QLineEdit()
            input_field.setEchoMode(QLineEdit.Password)
            input_field.setPlaceholderText("API Key eingeben...")
            self.api_key_inputs[key] = input_field
            provider_layout.addWidget(input_field, i, 1)
        
        # API Keys laden wenn Agent verfügbar
        if self.agent:
            for provider, config in self.agent.llm_configs.items():
                key = provider.value
                if key in self.api_key_inputs and config.api_key:
                    self.api_key_inputs[key].setText(config.api_key[:10] + "..." if len(config.api_key) > 10 else config.api_key)
        
        # Save Button
        save_btn = QPushButton("💾 API Keys speichern")
        save_btn.clicked.connect(self._save_api_keys)
        provider_layout.addWidget(save_btn, len(providers) + 1, 0, 1, 2)
        
        layout.addWidget(provider_group)
        
        # Weitere Settings
        misc_group = QGroupBox("⚙️ Weitere Einstellungen")
        misc_layout = QVBoxLayout(misc_group)
        
        # Monitor Interval
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Monitor-Intervall (Sekunden):"))
        self.interval_spin = QLineEdit("5")
        self.interval_spin.setMaximumWidth(50)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch()
        misc_layout.addLayout(interval_layout)
        
        # Max Actions
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(QLabel("Max. Auto-Aktionen pro Stunde:"))
        self.max_actions_spin = QLineEdit("20")
        self.max_actions_spin.setMaximumWidth(50)
        actions_layout.addWidget(self.max_actions_spin)
        actions_layout.addStretch()
        misc_layout.addLayout(actions_layout)
        
        layout.addWidget(misc_group)
        layout.addStretch()
        
        return panel
    
    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================
    
    def _add_chat_message(self, message: str, is_user: bool = True):
        """Fügt eine Nachricht zum Chat hinzu"""
        # Entferne Stretch am Ende
        stretch_item = self.chat_layout.itemAt(self.chat_layout.count() - 1)
        if stretch_item:
            self.chat_layout.removeItem(stretch_item)
        
        # Füge Bubble hinzu
        bubble = ChatBubble(message, is_user)
        self.chat_layout.addWidget(bubble)
        
        # Füge Stretch wieder hinzu
        self.chat_layout.addStretch()
        
        # Scroll nach unten
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )
    
    def _send_chat(self):
        """Sendet eine Chat-Nachricht"""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # User-Nachricht hinzufügen
        self._add_chat_message(message, is_user=True)
        self.chat_input.clear()
        
        # Antwort vom Agent holen
        if self.agent:
            # Zeige "Denkt nach..." Animation
            self._add_chat_message("🤔 Denke nach...", is_user=False)
            
            # In separatem Thread ausführen
            from PySide6.QtCore import QThreadPool, QRunnable
            
            class ChatTask(QRunnable):
                def __init__(self, agent, message, callback):
                    super().__init__()
                    self.agent = agent
                    self.message = message
                    self.callback = callback
                
                def run(self):
                    response = self.agent.chat(self.message)
                    self.callback(response)
            
            def on_response(response):
                # Entferne "Denkt nach..."
                last_item = self.chat_layout.itemAt(self.chat_layout.count() - 2)
                if last_item and last_item.widget():
                    last_item.widget().deleteLater()
                
                # Füge echte Antwort hinzu
                self._add_chat_message(response, is_user=False)
            
            task = ChatTask(self.agent, message, on_response)
            QThreadPool.globalInstance().start(task)
        else:
            self._add_chat_message("❌ AI Agent nicht verfügbar. Bitte API-Keys konfigurieren.", is_user=False)
    
    def _quick_action(self, prompt: str):
        """Führt eine Quick Action aus"""
        self.chat_input.setText(prompt)
        self._send_chat()
    
    def _toggle_monitoring(self):
        """Startet/Stoppt das Monitoring"""
        if not self.agent:
            return
        
        if self.agent.is_running:
            self.agent.stop_monitoring()
            self.toggle_btn.setText("▶️ Starten")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('success', '#00ff88')};
                    color: black;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 5px;
                }}
            """)
            self.status_label.setText("⏸️ Inaktiv")
            self.status_label.setStyleSheet(f"color: {COLORS.get('warning', '#ffaa00')};")
        else:
            try:
                interval = float(self.interval_spin.text())
            except:
                interval = 5.0
            self.agent.start_monitoring(interval)
            self.toggle_btn.setText("⏹️ Stoppen")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('error', '#ff4444')};
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 5px;
                }}
            """)
            self.status_label.setText("🔍 Überwacht...")
            self.status_label.setStyleSheet(f"color: {COLORS.get('success', '#00ff88')};")
    
    def _toggle_auto_fix(self, checked: bool):
        """Toggle Auto-Fix"""
        if self.agent:
            self.agent.auto_fix_enabled = checked
            self.agent.save_config()
    
    def _toggle_learning(self, checked: bool):
        """Toggle Learning"""
        if self.agent:
            self.agent.learning_enabled = checked
            self.agent.save_config()
    
    def auto_start_monitoring(self, interval: float = 5.0):
        """
        Startet das Monitoring automatisch (für externe Aufrufe).
        Wird beim Mining-Start aufgerufen.
        """
        if not self.agent:
            return False
        
        if self.agent.is_running:
            logger.info("🤖 AI Agent läuft bereits")
            return True
        
        try:
            self.agent.start_monitoring(interval)
            self.toggle_btn.setText("⏹️ Stoppen")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('error', '#ff4444')};
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 5px;
                }}
            """)
            self.status_label.setText("🔍 Überwacht...")
            self.status_label.setStyleSheet(f"color: {COLORS.get('success', '#00ff88')};")
            logger.info(f"🤖 AI Agent Monitoring automatisch gestartet (Intervall: {interval}s)")
            return True
        except Exception as e:
            logger.error(f"🤖 AI Agent Start fehlgeschlagen: {e}")
            return False
    
    def auto_stop_monitoring(self):
        """
        Stoppt das Monitoring automatisch (für externe Aufrufe).
        Wird beim Mining-Stop aufgerufen.
        """
        if not self.agent or not self.agent.is_running:
            return
        
        try:
            self.agent.stop_monitoring()
            self.toggle_btn.setText("▶️ Starten")
            self.toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.get('success', '#00ff88')};
                    color: black;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 5px;
                }}
            """)
            self.status_label.setText("⏸️ Inaktiv")
            self.status_label.setStyleSheet(f"color: {COLORS.get('warning', '#ffaa00')};")
            logger.info("🤖 AI Agent Monitoring automatisch gestoppt")
        except Exception as e:
            logger.error(f"🤖 AI Agent Stop fehlgeschlagen: {e}")
        """Wechselt den aktiven Provider"""
        if not self.agent:
            return
        
        provider_map = {
            "GROQ": LLMProvider.GROQ,
            "Gemini": LLMProvider.GEMINI,
            "DeepSeek": LLMProvider.DEEPSEEK,
            "HuggingFace": LLMProvider.HUGGINGFACE,
            "OpenRouter": LLMProvider.OPENROUTER
        }
        
        if provider_name in provider_map:
            provider = provider_map[provider_name]
            if provider in self.agent.llm_configs:
                self.agent.active_provider = provider
                self._update_displays()
    
    def _save_api_keys(self):
        """Speichert die API Keys"""
        if not self.agent:
            return
        
        provider_map = {
            "groq": LLMProvider.GROQ,
            "gemini": LLMProvider.GEMINI,
            "deepseek": LLMProvider.DEEPSEEK,
            "huggingface": LLMProvider.HUGGINGFACE,
            "openrouter": LLMProvider.OPENROUTER
        }
        
        for key, input_field in self.api_key_inputs.items():
            api_key = input_field.text().strip()
            # Nur speichern wenn es kein Platzhalter ist
            if api_key and "..." not in api_key:
                if key in provider_map:
                    self.agent.set_api_key(provider_map[key], api_key)
        
        self.agent.save_config()
        QMessageBox.information(self, "Gespeichert", "API Keys wurden gespeichert!")
    
    def _clear_errors(self):
        """Löscht die Fehler-Liste"""
        if self.agent:
            self.agent.error_queue.clear()
        self.errors_table.setRowCount(0)
    
    def _fix_selected_error(self):
        """Versucht den ausgewählten Fehler zu fixen"""
        row = self.errors_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Fehler", "Bitte wähle einen Fehler aus!")
            return
        
        if not self.agent:
            return
        
        # Hole Fehler
        errors = list(self.agent.error_queue)
        if row < len(errors):
            error = errors[row]
            # Trigger Auto-Fix
            self.agent._auto_fix_error(error)
            self._update_displays()
    
    def _manual_action(self, action_type: ActionType):
        """Führt eine manuelle Aktion aus"""
        if not self.agent:
            return
        
        # Zeige Bestätigungsdialog für kritische Aktionen
        if action_type in [ActionType.KILL_PROCESS, ActionType.ADJUST_OC]:
            result = QMessageBox.question(
                self, "Bestätigung",
                f"Möchtest du wirklich '{action_type.value}' ausführen?",
                QMessageBox.Yes | QMessageBox.No
            )
            if result != QMessageBox.Yes:
                return
        
        # Web-Suche braucht Input
        if action_type == ActionType.WEB_SEARCH:
            from PySide6.QtWidgets import QInputDialog
            query, ok = QInputDialog.getText(self, "Web-Suche", "Suchbegriff:")
            if ok and query:
                action = self.agent.execute_action(action_type, target=query)
                self._add_chat_message(f"🔍 Web-Suche nach: {query}", is_user=True)
                if action.success:
                    self._add_chat_message(f"Ergebnisse:\n{action.result[:500]}...", is_user=False)
                else:
                    self._add_chat_message(f"❌ Keine Ergebnisse gefunden.", is_user=False)
            return
        
        # Aktion ausführen
        action = self.agent.execute_action(action_type)
        
        # Feedback
        if action.success:
            self._add_chat_message(f"✅ {action.action_type.value}: {action.result}", is_user=False)
        else:
            self._add_chat_message(f"❌ {action.action_type.value}: {action.result}", is_user=False)
        
        self._update_displays()
    
    # ========================================================================
    # UPDATES
    # ========================================================================
    
    def _update_displays(self):
        """Aktualisiert alle Anzeigen"""
        if not self.agent:
            return
        
        # Statistiken
        stats = self.agent.get_statistics()
        self.stats_label.setText(
            f"Fehler: {stats['total_errors_detected']} | "
            f"Aktionen: {stats['total_actions_executed']} | "
            f"Lösungen: {stats['builtin_solutions'] + stats['learned_solutions']}"
        )
        
        # Provider
        provider = stats['active_provider']
        self.provider_label.setText(f"Provider: {provider or 'Keiner'}")
        
        # Auto-Fix & Learning
        self.auto_fix_check.setChecked(stats['auto_fix_enabled'])
        self.learning_check.setChecked(stats['learning_enabled'])
        
        # Status
        if stats['is_monitoring']:
            self.status_label.setText("🔍 Überwacht...")
            self.status_label.setStyleSheet(f"color: {COLORS.get('success', '#00ff88')};")
        
        # Fehler-Tabelle
        self._update_errors_table()
        
        # Aktionen-Tabelle
        self._update_actions_table()
        
        # Lösungen-Tabelle
        self._update_solutions_table()
    
    def _update_errors_table(self):
        """Aktualisiert die Fehler-Tabelle"""
        if not self.agent:
            return
        
        errors = list(self.agent.error_queue)
        self.errors_table.setRowCount(len(errors))
        
        for i, error in enumerate(reversed(errors)):  # Neueste zuerst
            # Zeit
            time_item = QTableWidgetItem(error.timestamp.strftime("%H:%M:%S"))
            self.errors_table.setItem(i, 0, time_item)
            
            # Schwere
            severity_colors = {
                ErrorSeverity.INFO: COLORS.get('info', '#00aaff'),
                ErrorSeverity.WARNING: COLORS.get('warning', '#ffaa00'),
                ErrorSeverity.ERROR: COLORS.get('error', '#ff4444'),
                ErrorSeverity.CRITICAL: "#ff0000"
            }
            severity_item = QTableWidgetItem(error.severity.value.upper())
            severity_item.setForeground(QColor(severity_colors.get(error.severity, '#ffffff')))
            self.errors_table.setItem(i, 1, severity_item)
            
            # Kategorie
            self.errors_table.setItem(i, 2, QTableWidgetItem(error.category))
            
            # Nachricht
            self.errors_table.setItem(i, 3, QTableWidgetItem(error.message[:100]))
            
            # Status
            status = "✅ Gelöst" if error.resolved else "⏳ Offen"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(COLORS.get('success' if error.resolved else 'warning', '#ffaa00')))
            self.errors_table.setItem(i, 4, status_item)
    
    def _update_actions_table(self):
        """Aktualisiert die Aktionen-Tabelle"""
        if not self.agent:
            return
        
        actions = list(self.agent.action_history)
        self.actions_table.setRowCount(len(actions))
        
        for i, action in enumerate(reversed(actions)):  # Neueste zuerst
            self.actions_table.setItem(i, 0, QTableWidgetItem(action.timestamp.strftime("%H:%M:%S")))
            self.actions_table.setItem(i, 1, QTableWidgetItem(action.action_type.value))
            self.actions_table.setItem(i, 2, QTableWidgetItem(action.target or "-"))
            self.actions_table.setItem(i, 3, QTableWidgetItem(action.result[:50]))
            
            status = "✅" if action.success else "❌"
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(COLORS.get('success' if action.success else 'error', '#ff4444')))
            self.actions_table.setItem(i, 4, status_item)
    
    def _update_solutions_table(self):
        """Aktualisiert die Lösungen-Tabelle"""
        if not self.agent:
            return
        
        # Kombiniere builtin und learned
        solutions = self.agent.builtin_solutions + self.agent.learned_solutions
        self.solutions_table.setRowCount(len(solutions))
        
        for i, solution in enumerate(solutions):
            self.solutions_table.setItem(i, 0, QTableWidgetItem(solution.id))
            self.solutions_table.setItem(i, 1, QTableWidgetItem(solution.category))
            self.solutions_table.setItem(i, 2, QTableWidgetItem(solution.error_pattern[:50]))
            self.solutions_table.setItem(i, 3, QTableWidgetItem(f"{solution.success_rate:.0%}"))
            self.solutions_table.setItem(i, 4, QTableWidgetItem(str(solution.times_applied)))
    
    # ========================================================================
    # CALLBACKS
    # ========================================================================
    
    def _register_callbacks(self):
        """Registriert Callbacks für den AI Agent"""
        if not self.agent:
            return
        
        def on_error(error):
            self.error_detected.emit({"error": error})
            self._update_errors_table()
        
        def on_action(action):
            self.action_executed.emit({"action": action})
            self._update_actions_table()
        
        self.agent.register_callback("on_error", on_error)
        self.agent.register_callback("on_action", on_action)
    
    def register_gpu_callbacks(self, gpu_monitor):
        """Registriert GPU-bezogene Callbacks"""
        if not self.agent or not gpu_monitor:
            return
        
        def get_gpu_status():
            gpus = gpu_monitor.get_all_gpus()
            status_parts = []
            for gpu in gpus:
                status_parts.append(
                    f"GPU {gpu.index}: {gpu.name}, {gpu.temperature}°C, "
                    f"{gpu.power_draw}W, {gpu.fan_speed}%"
                )
            return "\n".join(status_parts)
        
        def check_gpu_health():
            issues = []
            gpus = gpu_monitor.get_all_gpus()
            for gpu in gpus:
                # Temperatur-Check
                if gpu.temperature > 85:
                    issues.append({
                        "message": f"GPU {gpu.index} Temperatur kritisch: {gpu.temperature}°C",
                        "category": "GPU",
                        "severity": ErrorSeverity.WARNING,
                        "gpu_index": gpu.index
                    })
                # Memory-Check
                if gpu.memory_used / gpu.memory_total > 0.95:
                    issues.append({
                        "message": f"GPU {gpu.index} VRAM fast voll",
                        "category": "GPU",
                        "severity": ErrorSeverity.WARNING,
                        "gpu_index": gpu.index
                    })
            return issues
        
        self.agent.register_callback("get_gpu_status", get_gpu_status)
        self.agent.register_callback("check_gpu_health", check_gpu_health)
    
    def register_miner_callbacks(self, miner_manager):
        """Registriert Miner-bezogene Callbacks"""
        if not self.agent or not miner_manager:
            return
        
        def restart_miner():
            miner_manager.restart_current()
        
        def get_mining_status():
            stats = miner_manager.get_stats()
            if stats:
                return f"Hashrate: {stats.hashrate}, Shares: A:{stats.accepted}/R:{stats.rejected}"
            return "Kein Miner aktiv"
        
        self.agent.register_callback("restart_miner", restart_miner)
        self.agent.register_callback("get_mining_status", get_mining_status)
    
    def register_oc_callbacks(self, oc_manager):
        """Registriert OC-bezogene Callbacks"""
        if not self.agent or not oc_manager:
            return
        
        def adjust_oc(gpu_index, core_delta, mem_delta):
            current = oc_manager.get_oc_settings(gpu_index)
            new_core = (current.get("core_clock", 0) or 0) + core_delta
            new_mem = (current.get("mem_clock", 0) or 0) + mem_delta
            oc_manager.apply_oc(gpu_index, core_clock=new_core, mem_clock=new_mem)
        
        def set_fan_speed(gpu_index, speed):
            oc_manager.set_fan_speed(gpu_index, speed)
        
        def set_power_limit(gpu_index, delta):
            current = oc_manager.get_power_limit(gpu_index)
            new_limit = current + delta
            oc_manager.set_power_limit(gpu_index, new_limit)
        
        self.agent.register_callback("adjust_oc", adjust_oc)
        self.agent.register_callback("set_fan_speed", set_fan_speed)
        self.agent.register_callback("set_power_limit", set_power_limit)
    
    # ========================================================================
    # CODE REPAIR INTEGRATION
    # ========================================================================
    
    def setup_code_repair_integration(self):
        """Initialisiert Code Repair Integration"""
        try:
            from code_repair import get_repair_manager
            self.repair_manager = get_repair_manager()
            
            # Callbacks setzen
            self.repair_manager.on_error_detected = self._on_code_error_detected
            self.repair_manager.on_fix_generated = self._on_fix_generated
            self.repair_manager.on_fix_applied = self._on_fix_applied
            self.repair_manager.on_restart_required = self._on_restart_required
            
            logger.info("🔧 Code Repair Integration aktiviert")
            return True
        except ImportError:
            logger.warning("Code Repair Modul nicht verfügbar")
            return False
    
    def _on_code_error_detected(self, error):
        """Callback wenn Code-Fehler erkannt wird"""
        self._add_chat_message(
            f"🐛 **Code-Fehler erkannt!**\n"
            f"**Typ:** {error.error_type}\n"
            f"**Datei:** {error.file_path}\n"
            f"**Zeile:** {error.line_number}\n"
            f"**Nachricht:** {error.message}",
            "agent"
        )
    
    def _on_fix_generated(self, fix):
        """Callback wenn Fix generiert wurde"""
        self._add_chat_message(
            f"✨ **Fix generiert!**\n"
            f"**Konfidenz:** {fix.confidence:.0%}\n"
            f"**Erklärung:** {fix.explanation}\n"
            f"**Provider:** {fix.llm_provider}",
            "agent"
        )
    
    def _on_fix_applied(self, action):
        """Callback wenn Fix angewendet wurde"""
        if action.status == "success":
            self._add_chat_message(
                f"✅ **Fix erfolgreich angewendet!**\n"
                f"**Backup:** {action.backup_path}",
                "agent"
            )
        else:
            self._add_chat_message(
                f"❌ **Fix fehlgeschlagen!**\n"
                f"**Fehler:** {action.error_message}",
                "agent"
            )
    
    def _on_restart_required(self):
        """Callback wenn Neustart erforderlich ist"""
        self._add_chat_message(
            "🔄 **Programm-Neustart erforderlich!**\n"
            "Das Programm wird in 3 Sekunden neu gestartet...",
            "agent"
        )
    
    # ========================================================================
    # PORTFOLIO INTEGRATION
    # ========================================================================
    
    def setup_portfolio_integration(self):
        """Initialisiert Portfolio Manager Integration"""
        try:
            from portfolio_manager import get_portfolio_manager
            self.portfolio_manager = get_portfolio_manager()
            
            # Callbacks setzen
            self.portfolio_manager.on_alert = self._on_portfolio_alert
            self.portfolio_manager.on_deposit = self._on_mining_deposit
            self.portfolio_manager.on_trade = self._on_trade_executed
            
            logger.info("💰 Portfolio Integration aktiviert")
            return True
        except ImportError:
            logger.warning("Portfolio Manager Modul nicht verfügbar")
            return False
    
    def _on_portfolio_alert(self, level: str, message: str):
        """Callback für Portfolio-Alerts"""
        emoji = "ℹ️" if level == "info" else "⚠️" if level == "warning" else "🚨"
        self._add_chat_message(f"{emoji} **Portfolio Alert:** {message}", "agent")
    
    def _on_mining_deposit(self, deposit):
        """Callback wenn Mining-Einzahlung erkannt wird"""
        self._add_chat_message(
            f"💰 **Neue Mining-Einzahlung!**\n"
            f"**Coin:** {deposit.coin}\n"
            f"**Menge:** {deposit.amount:.6f}\n"
            f"**Börse:** {deposit.exchange}\n"
            f"**Preis:** ${deposit.price_at_deposit:.4f}",
            "agent"
        )
    
    def _on_trade_executed(self, trade):
        """Callback wenn Trade ausgeführt wird"""
        self._add_chat_message(
            f"📈 **Trade ausgeführt!**\n"
            f"**{trade.side.upper()}:** {trade.amount:.6f} {trade.coin}\n"
            f"**Preis:** ${trade.price:.4f}\n"
            f"**Grund:** {trade.reason}\n"
            f"**Börse:** {trade.exchange}",
            "agent"
        )
    
    # ========================================================================
    # AUTO-START/STOP FÜR ALLE SUBSYSTEME
    # ========================================================================
    
    def auto_start_all_monitoring(self, mining_interval: float = 5.0, portfolio_interval: float = 60.0):
        """
        Startet alle Überwachungssysteme automatisch
        
        Args:
            mining_interval: Intervall für Mining-Monitoring in Sekunden
            portfolio_interval: Intervall für Portfolio-Monitoring in Sekunden
        """
        # AI Agent Monitoring starten
        self.auto_start_monitoring(mining_interval)
        
        # Code Repair Setup
        if hasattr(self, 'repair_manager') or self.setup_code_repair_integration():
            logger.info("🔧 Code Repair aktiv")
        
        # Portfolio Monitoring starten
        if hasattr(self, 'portfolio_manager') or self.setup_portfolio_integration():
            if hasattr(self, 'portfolio_manager') and self.portfolio_manager:
                self.portfolio_manager.start_monitoring(portfolio_interval)
                logger.info(f"💰 Portfolio Monitoring gestartet (Intervall: {portfolio_interval}s)")
    
    def auto_stop_all_monitoring(self):
        """Stoppt alle Überwachungssysteme"""
        # AI Agent Monitoring stoppen
        self.auto_stop_monitoring()
        
        # Portfolio Monitoring stoppen
        if hasattr(self, 'portfolio_manager') and self.portfolio_manager:
            self.portfolio_manager.stop_monitoring()
            logger.info("💰 Portfolio Monitoring gestoppt")
    
    def get_all_activity_log(self, limit: int = 100) -> list:
        """
        Holt kombiniertes Activity Log von allen Subsystemen
        
        Returns:
            Liste von Activity-Einträgen mit Typ, Beschreibung, Status, Checkbox
        """
        logs = []
        
        # Code Repair Historie
        if hasattr(self, 'repair_manager') and self.repair_manager:
            try:
                for item in self.repair_manager.get_history(limit // 3):
                    logs.append({
                        "timestamp": item.get("timestamp", ""),
                        "type": "🔧 Code Repair",
                        "description": f"{item.get('error_type', 'N/A')}: {str(item.get('error_message', ''))[:50]}",
                        "status": item.get("status", "unknown"),
                        "acknowledged": item.get("acknowledged", False),
                        "id": item.get("id", ""),
                        "source": "code_repair"
                    })
            except Exception as e:
                logger.error(f"Code Repair Log Fehler: {e}")
        
        # Portfolio Activity
        if hasattr(self, 'portfolio_manager') and self.portfolio_manager:
            try:
                for item in self.portfolio_manager.get_activity_log(limit // 3):
                    logs.append({
                        "timestamp": item.get("timestamp", ""),
                        "type": f"💰 {item.get('action_type', 'Portfolio')}",
                        "description": item.get("description", ""),
                        "status": "completed",
                        "acknowledged": item.get("acknowledged", False),
                        "id": str(item.get("id", "")),
                        "source": "portfolio"
                    })
            except Exception as e:
                logger.error(f"Portfolio Log Fehler: {e}")
        
        # Trading Historie
        if hasattr(self, 'portfolio_manager') and self.portfolio_manager:
            try:
                for item in self.portfolio_manager.get_trade_history(limit // 3):
                    pnl = ""
                    if item.get("total_usd"):
                        pnl = f" (${item['total_usd']:.2f})"
                    logs.append({
                        "timestamp": item.get("created_at", ""),
                        "type": f"📈 Trade",
                        "description": f"{item.get('side', '').upper()} {item.get('amount', 0):.4f} {item.get('coin', '')} @ ${item.get('price', 0):.4f}{pnl}",
                        "status": item.get("status", "unknown"),
                        "acknowledged": True,  # Trades sind automatisch acknowledged
                        "id": item.get("id", ""),
                        "source": "trade"
                    })
            except Exception as e:
                logger.error(f"Trade Log Fehler: {e}")
        
        # Nach Timestamp sortieren (neueste zuerst)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs[:limit]
    
    def acknowledge_activity(self, activity_id: str, source: str):
        """
        Markiert eine Aktivität als bestätigt (Checkbox abhaken)
        
        Args:
            activity_id: ID der Aktivität
            source: Quelle der Aktivität (code_repair, portfolio, trade)
        """
        if source == "code_repair" and hasattr(self, 'repair_manager') and self.repair_manager:
            self.repair_manager.acknowledge(activity_id)
        elif source == "portfolio" and hasattr(self, 'portfolio_manager') and self.portfolio_manager:
            try:
                self.portfolio_manager.db.acknowledge_activity(int(activity_id))
            except:
                pass


# ============================================================================
# STANDALONE TEST
# ============================================================================

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Dunkles Theme
    app.setStyle("Fusion")
    
    widget = AIAgentWidget()
    widget.setWindowTitle("🤖 AI Agent Test")
    widget.resize(1200, 800)
    widget.show()
    
    sys.exit(app.exec())
