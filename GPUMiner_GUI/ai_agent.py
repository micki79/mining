#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Agent System für GPU Mining Profit Switcher
Ein intelligenter Agent der Fehler erkennt, löst und aus Erfahrung lernt.

Features:
- Multi-LLM Support (GROQ, Gemini, DeepSeek, HuggingFace, OpenRouter)
- Automatische Fehlererkennung und -behebung
- Web-Suche nach Lösungen
- Windows System-Eingriff (OC, Prozesse, Registry)
- Lernfähigkeit mit lokaler Wissensbasis
- Chat-Interface für User-Interaktion

Author: GPU Mining Profit Switcher Team
Version: 1.0.0
"""

import os
import sys
import json
import time
import logging
import sqlite3
import hashlib
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import deque
import traceback

# HTTP Requests
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# BeautifulSoup für Web Scraping
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# KONFIGURATION UND KONSTANTEN
# ============================================================================

class LLMProvider(Enum):
    """Unterstützte LLM Provider"""
    GROQ = "groq"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"
    LOCAL = "local"  # Für zukünftige lokale Modelle


class ErrorSeverity(Enum):
    """Schweregrad von Fehlern"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActionType(Enum):
    """Arten von System-Aktionen"""
    RESTART_MINER = "restart_miner"
    ADJUST_OC = "adjust_oc"
    KILL_PROCESS = "kill_process"
    CHANGE_POOL = "change_pool"
    REDUCE_POWER = "reduce_power"
    INCREASE_FAN = "increase_fan"
    CHANGE_ALGO = "change_algo"
    NOTIFY_USER = "notify_user"
    WEB_SEARCH = "web_search"
    APPLY_FIX = "apply_fix"


@dataclass
class LLMConfig:
    """Konfiguration für einen LLM Provider"""
    provider: LLMProvider
    api_key: str
    model: str = ""
    endpoint: str = ""
    enabled: bool = True
    priority: int = 1  # Niedrigere Zahl = höhere Priorität
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class DetectedError:
    """Ein erkannter Fehler"""
    id: str
    timestamp: datetime
    severity: ErrorSeverity
    category: str  # z.B. "GPU", "Miner", "Pool", "OC"
    message: str
    details: Dict[str, Any]
    gpu_index: int = -1  # -1 = alle GPUs
    source: str = ""  # z.B. "gpu_monitor", "miner_api", "log_parser"
    resolved: bool = False
    resolution: str = ""


@dataclass
class Solution:
    """Eine Lösung für einen Fehler"""
    id: str
    error_pattern: str  # Regex Pattern
    category: str
    solution_steps: List[str]
    actions: List[ActionType]
    success_rate: float = 0.0
    times_applied: int = 0
    times_successful: int = 0
    source: str = "learned"  # "builtin", "learned", "web"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentAction:
    """Eine ausgeführte Aktion"""
    id: str
    timestamp: datetime
    action_type: ActionType
    target: str  # z.B. GPU Index, Prozess Name
    parameters: Dict[str, Any]
    result: str
    success: bool
    error_id: str = ""


# ============================================================================
# AI AGENT KERN
# ============================================================================

class AIAgent:
    """
    Haupt-KI-Agent für das Mining System.
    
    Dieser Agent:
    - Überwacht das System kontinuierlich
    - Erkennt Fehler und Probleme
    - Findet Lösungen (eigene Wissensbasis + Web)
    - Führt Korrekturen automatisch durch
    - Lernt aus Erfahrung
    """
    
    def __init__(self, config_path: str = "ai_agent_config.json"):
        self.config_path = Path(config_path)
        self.db_path = Path("ai_agent_knowledge.db")
        
        # LLM Provider
        self.llm_configs: Dict[LLMProvider, LLMConfig] = {}
        self.active_provider: Optional[LLMProvider] = None
        
        # Wissensbasis
        self.builtin_solutions: List[Solution] = []
        self.learned_solutions: List[Solution] = []
        
        # Fehler-Queue
        self.error_queue: deque = deque(maxlen=100)
        self.action_history: deque = deque(maxlen=500)
        
        # Callbacks für System-Integration
        self.callbacks: Dict[str, Callable] = {}
        
        # Status
        self.is_running = False
        self.auto_fix_enabled = True
        self.learning_enabled = True
        
        # Chat-Historie
        self.chat_history: List[Dict[str, str]] = []
        
        # Monitoring Thread
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Initialisierung
        self._load_config()
        self._init_database()
        self._load_builtin_solutions()
        self._load_learned_solutions()
        
        logger.info("🤖 AI Agent initialisiert")
    
    # ========================================================================
    # KONFIGURATION
    # ========================================================================
    
    def _load_config(self):
        """Lädt die Konfiguration"""
        default_config = {
            "llm_providers": {
                "groq": {
                    "api_key": "",  # Set your Groq API key
                    "model": "llama-3.3-70b-versatile",
                    "endpoint": "https://api.groq.com/openai/v1/chat/completions",
                    "enabled": True,
                    "priority": 1
                },
                "gemini": {
                    "api_key": "",  # Set your Gemini API key
                    "model": "gemini-pro",
                    "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                    "enabled": True,
                    "priority": 2
                },
                "deepseek": {
                    "api_key": "",  # Set your DeepSeek API key
                    "model": "deepseek-chat",
                    "endpoint": "https://api.deepseek.com/v1/chat/completions",
                    "enabled": True,
                    "priority": 3
                },
                "huggingface": {
                    "api_key": "",  # Set your Hugging Face API key
                    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                    "endpoint": "https://api-inference.huggingface.co/models/",
                    "enabled": True,
                    "priority": 4
                },
                "openrouter": {
                    "api_key": "",  # Set your OpenRouter API key
                    "model": "meta-llama/llama-3.3-70b-instruct",
                    "endpoint": "https://openrouter.ai/api/v1/chat/completions",
                    "enabled": True,
                    "priority": 5
                }
            },
            "auto_fix_enabled": True,
            "learning_enabled": True,
            "monitor_interval": 5,
            "max_auto_actions_per_hour": 20,
            "require_confirmation_for": ["KILL_PROCESS", "ADJUST_OC"]
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    saved_config = json.load(f)
                    # Merge mit Default
                    for key in default_config:
                        if key not in saved_config:
                            saved_config[key] = default_config[key]
                    default_config = saved_config
            except Exception as e:
                logger.warning(f"Config laden fehlgeschlagen: {e}")
        
        # LLM Provider laden
        for provider_name, config in default_config.get("llm_providers", {}).items():
            try:
                provider = LLMProvider(provider_name)
                self.llm_configs[provider] = LLMConfig(
                    provider=provider,
                    api_key=config.get("api_key", ""),
                    model=config.get("model", ""),
                    endpoint=config.get("endpoint", ""),
                    enabled=config.get("enabled", True),
                    priority=config.get("priority", 10),
                    max_tokens=config.get("max_tokens", 4096),
                    temperature=config.get("temperature", 0.7)
                )
            except ValueError:
                logger.warning(f"Unbekannter Provider: {provider_name}")
        
        self.auto_fix_enabled = default_config.get("auto_fix_enabled", True)
        self.learning_enabled = default_config.get("learning_enabled", True)
        
        # Aktiven Provider setzen (höchste Priorität mit API-Key)
        self._select_active_provider()
        
        # Config speichern
        self.save_config()
    
    def save_config(self):
        """Speichert die Konfiguration"""
        config = {
            "llm_providers": {},
            "auto_fix_enabled": self.auto_fix_enabled,
            "learning_enabled": self.learning_enabled
        }
        
        for provider, llm_config in self.llm_configs.items():
            config["llm_providers"][provider.value] = {
                "api_key": llm_config.api_key,
                "model": llm_config.model,
                "endpoint": llm_config.endpoint,
                "enabled": llm_config.enabled,
                "priority": llm_config.priority,
                "max_tokens": llm_config.max_tokens,
                "temperature": llm_config.temperature
            }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _select_active_provider(self):
        """Wählt den aktiven LLM Provider"""
        available = [
            (p, c) for p, c in self.llm_configs.items()
            if c.enabled and c.api_key
        ]
        
        if available:
            # Nach Priorität sortieren
            available.sort(key=lambda x: x[1].priority)
            self.active_provider = available[0][0]
            logger.info(f"🤖 Aktiver LLM Provider: {self.active_provider.value}")
        else:
            self.active_provider = None
            logger.warning("⚠️ Kein LLM Provider verfügbar!")
    
    def set_api_key(self, provider: LLMProvider, api_key: str):
        """Setzt einen API-Key für einen Provider"""
        if provider in self.llm_configs:
            self.llm_configs[provider].api_key = api_key
            self._select_active_provider()
            self.save_config()
    
    # ========================================================================
    # DATENBANK (Wissensbasis)
    # ========================================================================
    
    def _init_database(self):
        """Initialisiert die SQLite Datenbank für die Wissensbasis"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Tabelle für gelernte Lösungen
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS solutions (
                id TEXT PRIMARY KEY,
                error_pattern TEXT,
                category TEXT,
                solution_steps TEXT,
                actions TEXT,
                success_rate REAL DEFAULT 0.0,
                times_applied INTEGER DEFAULT 0,
                times_successful INTEGER DEFAULT 0,
                source TEXT DEFAULT 'learned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabelle für Fehler-Historie
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_history (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                severity TEXT,
                category TEXT,
                message TEXT,
                details TEXT,
                gpu_index INTEGER,
                source TEXT,
                resolved INTEGER DEFAULT 0,
                resolution TEXT
            )
        ''')
        
        # Tabelle für Aktionen-Historie
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_history (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP,
                action_type TEXT,
                target TEXT,
                parameters TEXT,
                result TEXT,
                success INTEGER,
                error_id TEXT
            )
        ''')
        
        # Tabelle für Chat-Konversationen (für Kontext)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                role TEXT,
                content TEXT,
                context TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("📚 Wissensbasis initialisiert")
    
    def _load_learned_solutions(self):
        """Lädt gelernte Lösungen aus der Datenbank"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM solutions WHERE source = "learned"')
        rows = cursor.fetchall()
        
        for row in rows:
            try:
                solution = Solution(
                    id=row[0],
                    error_pattern=row[1],
                    category=row[2],
                    solution_steps=json.loads(row[3]),
                    actions=[ActionType(a) for a in json.loads(row[4])],
                    success_rate=row[5],
                    times_applied=row[6],
                    times_successful=row[7],
                    source=row[8],
                    created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
                )
                self.learned_solutions.append(solution)
            except Exception as e:
                logger.warning(f"Lösung laden fehlgeschlagen: {e}")
        
        conn.close()
        logger.info(f"📖 {len(self.learned_solutions)} gelernte Lösungen geladen")
    
    def _save_solution(self, solution: Solution):
        """Speichert eine Lösung in der Datenbank"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO solutions 
            (id, error_pattern, category, solution_steps, actions, success_rate, 
             times_applied, times_successful, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            solution.id,
            solution.error_pattern,
            solution.category,
            json.dumps(solution.solution_steps),
            json.dumps([a.value for a in solution.actions]),
            solution.success_rate,
            solution.times_applied,
            solution.times_successful,
            solution.source,
            solution.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _save_error(self, error: DetectedError):
        """Speichert einen Fehler in der Datenbank"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO error_history 
            (id, timestamp, severity, category, message, details, gpu_index, source, resolved, resolution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            error.id,
            error.timestamp.isoformat(),
            error.severity.value,
            error.category,
            error.message,
            json.dumps(error.details),
            error.gpu_index,
            error.source,
            1 if error.resolved else 0,
            error.resolution
        ))
        
        conn.commit()
        conn.close()
    
    # ========================================================================
    # BUILTIN LÖSUNGEN
    # ========================================================================
    
    def _load_builtin_solutions(self):
        """Lädt eingebaute Lösungen für häufige Probleme"""
        self.builtin_solutions = [
            # GPU Temperatur zu hoch
            Solution(
                id="builtin_temp_high",
                error_pattern=r"(temperature|temp).*(high|hot|over|exceed)",
                category="GPU",
                solution_steps=[
                    "Erhöhe Lüftergeschwindigkeit auf 90%",
                    "Reduziere Power Limit um 10%",
                    "Wenn weiterhin zu hoch: Reduziere Core Clock"
                ],
                actions=[ActionType.INCREASE_FAN, ActionType.REDUCE_POWER],
                success_rate=0.85,
                times_applied=0,
                source="builtin"
            ),
            
            # Miner crashed
            Solution(
                id="builtin_miner_crash",
                error_pattern=r"(miner|process).*(crash|stopped|exit|killed|terminated)",
                category="Miner",
                solution_steps=[
                    "Warte 5 Sekunden",
                    "Starte Miner neu",
                    "Wenn erneut crashed: Reduziere OC-Werte"
                ],
                actions=[ActionType.RESTART_MINER],
                success_rate=0.90,
                times_applied=0,
                source="builtin"
            ),
            
            # GPU nicht erkannt
            Solution(
                id="builtin_gpu_not_found",
                error_pattern=r"(gpu|device).*(not found|missing|unavailable|error)",
                category="GPU",
                solution_steps=[
                    "Überprüfe NVIDIA/AMD Treiber",
                    "Starte System neu",
                    "Überprüfe PCIe Verbindung"
                ],
                actions=[ActionType.NOTIFY_USER],
                success_rate=0.50,
                times_applied=0,
                source="builtin"
            ),
            
            # Pool Verbindungsfehler
            Solution(
                id="builtin_pool_error",
                error_pattern=r"(pool|stratum).*(connection|connect|failed|timeout|refused)",
                category="Pool",
                solution_steps=[
                    "Wechsle zu Backup-Pool",
                    "Überprüfe Internet-Verbindung",
                    "Versuche erneut in 30 Sekunden"
                ],
                actions=[ActionType.CHANGE_POOL],
                success_rate=0.80,
                times_applied=0,
                source="builtin"
            ),
            
            # Hashrate zu niedrig
            Solution(
                id="builtin_low_hashrate",
                error_pattern=r"(hashrate|hash).*(low|drop|decreased|below)",
                category="Performance",
                solution_steps=[
                    "Überprüfe GPU Temperaturen",
                    "Überprüfe Memory Errors",
                    "Reduziere Memory Clock leicht"
                ],
                actions=[ActionType.ADJUST_OC],
                success_rate=0.70,
                times_applied=0,
                source="builtin"
            ),
            
            # OC instabil
            Solution(
                id="builtin_oc_unstable",
                error_pattern=r"(oc|overclock|clock).*(unstable|crash|error|invalid)",
                category="OC",
                solution_steps=[
                    "Reduziere Memory Clock um 50MHz",
                    "Reduziere Core Clock um 25MHz",
                    "Wenn stabil: Erhöhe Power Limit leicht"
                ],
                actions=[ActionType.ADJUST_OC],
                success_rate=0.75,
                times_applied=0,
                source="builtin"
            ),
            
            # Shares rejected
            Solution(
                id="builtin_shares_rejected",
                error_pattern=r"(shares?).*(reject|invalid|stale)",
                category="Mining",
                solution_steps=[
                    "Überprüfe OC-Stabilität",
                    "Reduziere Memory Clock",
                    "Überprüfe Pool-Latenz"
                ],
                actions=[ActionType.ADJUST_OC],
                success_rate=0.65,
                times_applied=0,
                source="builtin"
            ),
            
            # Out of Memory
            Solution(
                id="builtin_oom",
                error_pattern=r"(memory|vram).*(out of|insufficient|not enough|allocation)",
                category="GPU",
                solution_steps=[
                    "Schließe andere GPU-Programme",
                    "Reduziere DAG-Größe wenn möglich",
                    "Wechsle zu Coin mit kleinerem DAG"
                ],
                actions=[ActionType.CHANGE_ALGO, ActionType.NOTIFY_USER],
                success_rate=0.60,
                times_applied=0,
                source="builtin"
            ),
            
            # Driver Crash
            Solution(
                id="builtin_driver_crash",
                error_pattern=r"(driver|nvml|amd).*(crash|error|failed|timeout)",
                category="System",
                solution_steps=[
                    "Warte 10 Sekunden auf Recovery",
                    "Wenn nicht recovered: Benachrichtige User",
                    "Empfehle Treiber-Neuinstallation"
                ],
                actions=[ActionType.NOTIFY_USER],
                success_rate=0.40,
                times_applied=0,
                source="builtin"
            ),
            
            # Power Limit erreicht
            Solution(
                id="builtin_power_limit",
                error_pattern=r"(power).*(limit|throttle|capped)",
                category="GPU",
                solution_steps=[
                    "Erhöhe Power Limit wenn möglich",
                    "Reduziere Core Clock für bessere Effizienz"
                ],
                actions=[ActionType.ADJUST_OC],
                success_rate=0.80,
                times_applied=0,
                source="builtin"
            )
        ]
        
        logger.info(f"📋 {len(self.builtin_solutions)} eingebaute Lösungen geladen")
    
    # ========================================================================
    # LLM INTEGRATION
    # ========================================================================
    
    def _call_llm(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """Ruft den aktiven LLM Provider auf"""
        if not self.active_provider or not REQUESTS_AVAILABLE:
            return None
        
        config = self.llm_configs.get(self.active_provider)
        if not config or not config.api_key:
            return None
        
        try:
            if self.active_provider == LLMProvider.GROQ:
                return self._call_groq(prompt, system_prompt, config)
            elif self.active_provider == LLMProvider.GEMINI:
                return self._call_gemini(prompt, system_prompt, config)
            elif self.active_provider == LLMProvider.DEEPSEEK:
                return self._call_deepseek(prompt, system_prompt, config)
            elif self.active_provider == LLMProvider.HUGGINGFACE:
                return self._call_huggingface(prompt, system_prompt, config)
            elif self.active_provider == LLMProvider.OPENROUTER:
                return self._call_openrouter(prompt, system_prompt, config)
            else:
                return None
        except Exception as e:
            logger.error(f"LLM Aufruf fehlgeschlagen ({self.active_provider.value}): {e}")
            # Versuche nächsten Provider
            return self._try_fallback_provider(prompt, system_prompt)
    
    def _call_groq(self, prompt: str, system_prompt: str, config: LLMConfig) -> Optional[str]:
        """Ruft GROQ API auf"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": config.model or "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        response = requests.post(config.endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _call_gemini(self, prompt: str, system_prompt: str, config: LLMConfig) -> Optional[str]:
        """Ruft Google Gemini API auf"""
        url = f"{config.endpoint}?key={config.api_key}"
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        data = {
            "contents": [{
                "parts": [{"text": full_prompt}]
            }],
            "generationConfig": {
                "maxOutputTokens": config.max_tokens,
                "temperature": config.temperature
            }
        }
        
        response = requests.post(url, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    
    def _call_deepseek(self, prompt: str, system_prompt: str, config: LLMConfig) -> Optional[str]:
        """Ruft DeepSeek API auf"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": config.model or "deepseek-chat",
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        response = requests.post(config.endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _call_huggingface(self, prompt: str, system_prompt: str, config: LLMConfig) -> Optional[str]:
        """Ruft HuggingFace Inference API auf"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        url = f"{config.endpoint}{config.model}"
        data = {
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": config.max_tokens,
                "temperature": config.temperature
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")
        return str(result)
    
    def _call_openrouter(self, prompt: str, system_prompt: str, config: LLMConfig) -> Optional[str]:
        """Ruft OpenRouter API auf"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://gpuminer.local",
            "X-Title": "GPU Mining Profit Switcher"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": config.model or "meta-llama/llama-3.3-70b-instruct",
            "messages": messages,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature
        }
        
        response = requests.post(config.endpoint, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]
    
    def _try_fallback_provider(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Versucht einen Fallback-Provider"""
        for provider, config in sorted(self.llm_configs.items(), key=lambda x: x[1].priority):
            if provider != self.active_provider and config.enabled and config.api_key:
                old_provider = self.active_provider
                self.active_provider = provider
                try:
                    result = self._call_llm(prompt, system_prompt)
                    if result:
                        logger.info(f"✅ Fallback zu {provider.value} erfolgreich")
                        return result
                except:
                    pass
                self.active_provider = old_provider
        return None
    
    # ========================================================================
    # WEB SUCHE
    # ========================================================================
    
    def web_search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """Sucht im Web nach Lösungen"""
        if not REQUESTS_AVAILABLE:
            return []
        
        results = []
        
        # DuckDuckGo Instant Answer API (keine API-Key nötig)
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": f"{query} mining GPU fix solution",
                "format": "json",
                "no_redirect": 1,
                "no_html": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Abstract (Zusammenfassung)
                if data.get("Abstract"):
                    results.append({
                        "title": data.get("Heading", "DuckDuckGo Result"),
                        "snippet": data.get("Abstract", ""),
                        "url": data.get("AbstractURL", ""),
                        "source": "duckduckgo"
                    })
                
                # Related Topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                            "source": "duckduckgo"
                        })
        except Exception as e:
            logger.warning(f"DuckDuckGo Suche fehlgeschlagen: {e}")
        
        # Falls LLM verfügbar, erweiterte Analyse
        if self.active_provider and len(results) > 0:
            analysis_prompt = f"""Analysiere diese Suchergebnisse für das Problem: "{query}"

Suchergebnisse:
{json.dumps(results, indent=2)}

Extrahiere die wichtigsten Lösungsschritte als JSON-Array:
["Schritt 1", "Schritt 2", ...]"""
            
            try:
                analysis = self._call_llm(analysis_prompt, 
                    "Du bist ein Mining-Experte. Antworte nur mit einem JSON-Array von Lösungsschritten.")
                if analysis:
                    # Versuche JSON zu parsen
                    steps = json.loads(analysis)
                    if isinstance(steps, list):
                        results.append({
                            "title": "KI-Analyse",
                            "snippet": "\n".join(steps),
                            "url": "",
                            "source": "ai_analysis"
                        })
            except:
                pass
        
        return results
    
    # ========================================================================
    # FEHLERERKENNUNG
    # ========================================================================
    
    def detect_error(self, message: str, category: str = "Unknown", 
                     severity: ErrorSeverity = ErrorSeverity.WARNING,
                     details: Dict = None, gpu_index: int = -1, source: str = "") -> DetectedError:
        """Erkennt und registriert einen Fehler"""
        error = DetectedError(
            id=hashlib.md5(f"{datetime.now().isoformat()}{message}".encode()).hexdigest()[:12],
            timestamp=datetime.now(),
            severity=severity,
            category=category,
            message=message,
            details=details or {},
            gpu_index=gpu_index,
            source=source
        )
        
        self.error_queue.append(error)
        self._save_error(error)
        
        logger.warning(f"⚠️ Fehler erkannt [{category}]: {message}")
        
        # Trigger Callback
        if "on_error" in self.callbacks:
            self.callbacks["on_error"](error)
        
        # Auto-Fix wenn aktiviert
        if self.auto_fix_enabled and severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            threading.Thread(target=self._auto_fix_error, args=(error,), daemon=True).start()
        
        return error
    
    def analyze_log_line(self, line: str, source: str = "miner") -> Optional[DetectedError]:
        """Analysiert eine Log-Zeile auf Fehler"""
        line_lower = line.lower()
        
        # Fehler-Patterns
        error_patterns = [
            (r"cuda error|nvml error|gpu error", "GPU", ErrorSeverity.ERROR),
            (r"temperature.*(\d+).*exceed|temp.*high|overheat", "GPU", ErrorSeverity.WARNING),
            (r"share.*rejected|invalid share", "Mining", ErrorSeverity.WARNING),
            (r"connection.*failed|cannot connect|timeout", "Pool", ErrorSeverity.ERROR),
            (r"out of memory|memory allocation|vram", "GPU", ErrorSeverity.ERROR),
            (r"crash|exception|fatal|abort", "System", ErrorSeverity.CRITICAL),
            (r"hashrate.*drop|hashrate.*low|0\.00.*h/s", "Performance", ErrorSeverity.WARNING),
            (r"driver.*error|driver.*crash", "System", ErrorSeverity.ERROR),
        ]
        
        for pattern, category, severity in error_patterns:
            if re.search(pattern, line_lower):
                return self.detect_error(
                    message=line.strip(),
                    category=category,
                    severity=severity,
                    details={"raw_line": line},
                    source=source
                )
        
        return None
    
    # ========================================================================
    # LÖSUNGSFINDUNG
    # ========================================================================
    
    def find_solution(self, error: DetectedError) -> Optional[Solution]:
        """Findet eine Lösung für einen Fehler"""
        # 1. Prüfe Builtin-Lösungen
        for solution in self.builtin_solutions:
            if re.search(solution.error_pattern, error.message, re.IGNORECASE):
                logger.info(f"✅ Builtin-Lösung gefunden: {solution.id}")
                return solution
        
        # 2. Prüfe gelernte Lösungen
        for solution in self.learned_solutions:
            if re.search(solution.error_pattern, error.message, re.IGNORECASE):
                if solution.success_rate > 0.5:  # Nur erfolgreiche Lösungen
                    logger.info(f"✅ Gelernte Lösung gefunden: {solution.id}")
                    return solution
        
        # 3. Frage LLM nach Lösung
        if self.active_provider:
            ai_solution = self._ask_llm_for_solution(error)
            if ai_solution:
                return ai_solution
        
        # 4. Web-Suche als letzter Ausweg
        web_results = self.web_search(f"{error.category} {error.message}")
        if web_results:
            return self._create_solution_from_web(error, web_results)
        
        return None
    
    def _ask_llm_for_solution(self, error: DetectedError) -> Optional[Solution]:
        """Fragt LLM nach einer Lösung"""
        system_prompt = """Du bist ein Experte für GPU Mining und Troubleshooting.
Analysiere Fehler und gib präzise, technische Lösungen.

Antworte IMMER im folgenden JSON-Format:
{
    "analysis": "Kurze Analyse des Problems",
    "steps": ["Schritt 1", "Schritt 2", ...],
    "actions": ["RESTART_MINER", "ADJUST_OC", "REDUCE_POWER", etc.],
    "confidence": 0.8
}

Verfügbare Aktionen:
- RESTART_MINER: Miner neustarten
- ADJUST_OC: Overclock-Werte anpassen
- KILL_PROCESS: Prozess beenden
- CHANGE_POOL: Pool wechseln
- REDUCE_POWER: Power Limit reduzieren
- INCREASE_FAN: Lüfter erhöhen
- CHANGE_ALGO: Algorithmus wechseln
- NOTIFY_USER: User benachrichtigen"""

        prompt = f"""Fehler im Mining-System:

Kategorie: {error.category}
Schweregrad: {error.severity.value}
Nachricht: {error.message}
Details: {json.dumps(error.details, indent=2)}
GPU Index: {error.gpu_index}

Was ist die beste Lösung?"""

        try:
            response = self._call_llm(prompt, system_prompt)
            if response:
                # Versuche JSON zu parsen
                # Suche nach JSON in der Antwort
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    data = json.loads(json_match.group())
                    
                    # Erstelle Solution
                    actions = []
                    for action_name in data.get("actions", []):
                        try:
                            actions.append(ActionType(action_name.lower()))
                        except ValueError:
                            pass
                    
                    if not actions:
                        actions = [ActionType.NOTIFY_USER]
                    
                    solution = Solution(
                        id=f"ai_{hashlib.md5(error.message.encode()).hexdigest()[:8]}",
                        error_pattern=re.escape(error.message[:50]),
                        category=error.category,
                        solution_steps=data.get("steps", [data.get("analysis", "Keine Lösung gefunden")]),
                        actions=actions,
                        success_rate=data.get("confidence", 0.5),
                        source="ai"
                    )
                    
                    logger.info(f"🤖 KI-Lösung generiert: {solution.id}")
                    return solution
        except Exception as e:
            logger.warning(f"KI-Lösungsfindung fehlgeschlagen: {e}")
        
        return None
    
    def _create_solution_from_web(self, error: DetectedError, 
                                   web_results: List[Dict]) -> Optional[Solution]:
        """Erstellt eine Lösung aus Web-Suchergebnissen"""
        steps = []
        for result in web_results[:3]:
            if result.get("snippet"):
                steps.append(result["snippet"][:200])
        
        if steps:
            solution = Solution(
                id=f"web_{hashlib.md5(error.message.encode()).hexdigest()[:8]}",
                error_pattern=re.escape(error.message[:50]),
                category=error.category,
                solution_steps=steps,
                actions=[ActionType.NOTIFY_USER],
                success_rate=0.3,  # Niedrige Konfidenz für Web-Lösungen
                source="web"
            )
            return solution
        
        return None
    
    # ========================================================================
    # AKTIONEN AUSFÜHREN
    # ========================================================================
    
    def execute_action(self, action_type: ActionType, target: str = "", 
                       parameters: Dict = None, error_id: str = "") -> AgentAction:
        """Führt eine System-Aktion aus"""
        action = AgentAction(
            id=hashlib.md5(f"{datetime.now().isoformat()}{action_type.value}".encode()).hexdigest()[:12],
            timestamp=datetime.now(),
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            result="",
            success=False,
            error_id=error_id
        )
        
        logger.info(f"🔧 Führe Aktion aus: {action_type.value} auf {target}")
        
        try:
            if action_type == ActionType.RESTART_MINER:
                action = self._action_restart_miner(action)
            elif action_type == ActionType.ADJUST_OC:
                action = self._action_adjust_oc(action)
            elif action_type == ActionType.KILL_PROCESS:
                action = self._action_kill_process(action)
            elif action_type == ActionType.REDUCE_POWER:
                action = self._action_reduce_power(action)
            elif action_type == ActionType.INCREASE_FAN:
                action = self._action_increase_fan(action)
            elif action_type == ActionType.CHANGE_POOL:
                action = self._action_change_pool(action)
            elif action_type == ActionType.NOTIFY_USER:
                action = self._action_notify_user(action)
            elif action_type == ActionType.WEB_SEARCH:
                action = self._action_web_search(action)
            else:
                action.result = f"Aktion {action_type.value} nicht implementiert"
                action.success = False
        except Exception as e:
            action.result = f"Fehler: {str(e)}"
            action.success = False
            logger.error(f"❌ Aktion fehlgeschlagen: {e}")
        
        self.action_history.append(action)
        
        # Callback
        if "on_action" in self.callbacks:
            self.callbacks["on_action"](action)
        
        return action
    
    def _action_restart_miner(self, action: AgentAction) -> AgentAction:
        """Startet den Miner neu"""
        if "restart_miner" in self.callbacks:
            try:
                self.callbacks["restart_miner"]()
                action.result = "Miner wird neugestartet"
                action.success = True
            except Exception as e:
                action.result = f"Neustart fehlgeschlagen: {e}"
                action.success = False
        else:
            action.result = "Kein Miner-Callback registriert"
            action.success = False
        return action
    
    def _action_adjust_oc(self, action: AgentAction) -> AgentAction:
        """Passt OC-Werte an"""
        params = action.parameters
        gpu_index = params.get("gpu_index", 0)
        
        if "adjust_oc" in self.callbacks:
            try:
                # Standardmäßig reduzieren wir bei Problemen
                core_delta = params.get("core_delta", -25)
                mem_delta = params.get("mem_delta", -50)
                
                self.callbacks["adjust_oc"](gpu_index, core_delta, mem_delta)
                action.result = f"OC angepasst: Core {core_delta:+d}, Mem {mem_delta:+d}"
                action.success = True
            except Exception as e:
                action.result = f"OC-Anpassung fehlgeschlagen: {e}"
                action.success = False
        else:
            action.result = "Kein OC-Callback registriert"
            action.success = False
        return action
    
    def _action_kill_process(self, action: AgentAction) -> AgentAction:
        """Beendet einen Prozess"""
        process_name = action.target or action.parameters.get("process_name", "")
        
        if not process_name:
            action.result = "Kein Prozessname angegeben"
            action.success = False
            return action
        
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    capture_output=True, text=True, timeout=10
                )
            else:
                result = subprocess.run(
                    ["pkill", "-f", process_name],
                    capture_output=True, text=True, timeout=10
                )
            
            if result.returncode == 0:
                action.result = f"Prozess {process_name} beendet"
                action.success = True
            else:
                action.result = f"Konnte Prozess nicht beenden: {result.stderr}"
                action.success = False
        except Exception as e:
            action.result = f"Fehler beim Beenden: {e}"
            action.success = False
        
        return action
    
    def _action_reduce_power(self, action: AgentAction) -> AgentAction:
        """Reduziert das Power Limit"""
        gpu_index = action.parameters.get("gpu_index", 0)
        reduction = action.parameters.get("reduction", 10)
        
        if "set_power_limit" in self.callbacks:
            try:
                self.callbacks["set_power_limit"](gpu_index, -reduction)
                action.result = f"Power Limit um {reduction}% reduziert"
                action.success = True
            except Exception as e:
                action.result = f"Power-Reduktion fehlgeschlagen: {e}"
                action.success = False
        else:
            action.result = "Kein Power-Callback registriert"
            action.success = False
        return action
    
    def _action_increase_fan(self, action: AgentAction) -> AgentAction:
        """Erhöht die Lüftergeschwindigkeit"""
        gpu_index = action.parameters.get("gpu_index", 0)
        fan_speed = action.parameters.get("fan_speed", 90)
        
        if "set_fan_speed" in self.callbacks:
            try:
                self.callbacks["set_fan_speed"](gpu_index, fan_speed)
                action.result = f"Lüfter auf {fan_speed}% gesetzt"
                action.success = True
            except Exception as e:
                action.result = f"Lüfter-Änderung fehlgeschlagen: {e}"
                action.success = False
        else:
            action.result = "Kein Fan-Callback registriert"
            action.success = False
        return action
    
    def _action_change_pool(self, action: AgentAction) -> AgentAction:
        """Wechselt den Pool"""
        if "change_pool" in self.callbacks:
            try:
                self.callbacks["change_pool"]()
                action.result = "Pool gewechselt"
                action.success = True
            except Exception as e:
                action.result = f"Pool-Wechsel fehlgeschlagen: {e}"
                action.success = False
        else:
            action.result = "Kein Pool-Callback registriert"
            action.success = False
        return action
    
    def _action_notify_user(self, action: AgentAction) -> AgentAction:
        """Benachrichtigt den User"""
        message = action.parameters.get("message", action.target)
        
        if "notify_user" in self.callbacks:
            try:
                self.callbacks["notify_user"](message)
                action.result = f"User benachrichtigt: {message[:50]}..."
                action.success = True
            except Exception as e:
                action.result = f"Benachrichtigung fehlgeschlagen: {e}"
                action.success = False
        else:
            logger.info(f"📢 User-Benachrichtigung: {message}")
            action.result = f"Log: {message[:50]}..."
            action.success = True
        return action
    
    def _action_web_search(self, action: AgentAction) -> AgentAction:
        """Führt eine Web-Suche durch"""
        query = action.target or action.parameters.get("query", "")
        results = self.web_search(query)
        
        if results:
            action.result = json.dumps(results, indent=2)
            action.success = True
        else:
            action.result = "Keine Ergebnisse gefunden"
            action.success = False
        return action
    
    # ========================================================================
    # AUTO-FIX
    # ========================================================================
    
    def _auto_fix_error(self, error: DetectedError):
        """Versucht automatisch einen Fehler zu beheben"""
        logger.info(f"🔧 Auto-Fix für Fehler: {error.id}")
        
        solution = self.find_solution(error)
        if not solution:
            logger.warning("❌ Keine Lösung gefunden")
            return
        
        logger.info(f"📋 Lösung gefunden: {solution.id}")
        logger.info(f"   Schritte: {solution.solution_steps}")
        
        # Führe Aktionen aus
        success_count = 0
        for action_type in solution.actions:
            action = self.execute_action(
                action_type=action_type,
                target=str(error.gpu_index) if error.gpu_index >= 0 else "",
                parameters={"gpu_index": error.gpu_index, "error": asdict(error)},
                error_id=error.id
            )
            if action.success:
                success_count += 1
        
        # Update Solution Statistics
        solution.times_applied += 1
        if success_count > 0:
            solution.times_successful += 1
        solution.success_rate = solution.times_successful / solution.times_applied
        
        # Speichere wenn gelernt
        if self.learning_enabled and solution.source in ["ai", "web"]:
            self.learned_solutions.append(solution)
            self._save_solution(solution)
            logger.info(f"📚 Lösung gelernt und gespeichert: {solution.id}")
        
        # Markiere Fehler als gelöst
        if success_count > 0:
            error.resolved = True
            error.resolution = f"Auto-Fix mit {solution.id}: {success_count}/{len(solution.actions)} Aktionen erfolgreich"
            self._save_error(error)
    
    # ========================================================================
    # CHAT INTERFACE
    # ========================================================================
    
    def chat(self, user_message: str) -> str:
        """Chat mit dem AI Agent"""
        if not self.active_provider:
            return "❌ Kein LLM Provider konfiguriert. Bitte API-Keys eingeben."
        
        # System Prompt für Chat
        system_prompt = """Du bist der AI Agent für das GPU Mining Profit Switcher System.
Du überwachst und optimierst Mining-Operationen.

Du hast Zugriff auf:
- GPU Monitoring (Temperatur, Power, Hashrate)
- Miner-Steuerung (Start, Stop, Restart)
- Overclock-Management
- Pool-Verwaltung
- Fehler-Historie und Lösungen

Aktuelle System-Infos werden dir bereitgestellt.
Antworte hilfreich, technisch präzise und auf Deutsch."""

        # Kontext zusammenstellen
        context = self._build_chat_context()
        
        full_prompt = f"""System-Kontext:
{context}

User-Nachricht: {user_message}

Antworte hilfreich und präzise."""

        # Chat Historie aktualisieren
        self.chat_history.append({"role": "user", "content": user_message})
        
        try:
            response = self._call_llm(full_prompt, system_prompt)
            if response:
                self.chat_history.append({"role": "assistant", "content": response})
                return response
            else:
                return "❌ Konnte keine Antwort generieren. Versuche einen anderen Provider."
        except Exception as e:
            return f"❌ Fehler bei der Antwort: {str(e)}"
    
    def _build_chat_context(self) -> str:
        """Baut den Kontext für den Chat"""
        context_parts = []
        
        # Letzte Fehler
        recent_errors = list(self.error_queue)[-5:]
        if recent_errors:
            context_parts.append("Letzte Fehler:")
            for error in recent_errors:
                context_parts.append(f"  - [{error.severity.value}] {error.category}: {error.message[:100]}")
        
        # Letzte Aktionen
        recent_actions = list(self.action_history)[-5:]
        if recent_actions:
            context_parts.append("\nLetzte Aktionen:")
            for action in recent_actions:
                context_parts.append(f"  - {action.action_type.value}: {action.result[:50]}")
        
        # GPU Status (wenn Callback vorhanden)
        if "get_gpu_status" in self.callbacks:
            try:
                gpu_status = self.callbacks["get_gpu_status"]()
                context_parts.append(f"\nGPU Status: {gpu_status}")
            except:
                pass
        
        # Mining Status (wenn Callback vorhanden)
        if "get_mining_status" in self.callbacks:
            try:
                mining_status = self.callbacks["get_mining_status"]()
                context_parts.append(f"\nMining Status: {mining_status}")
            except:
                pass
        
        return "\n".join(context_parts) if context_parts else "Keine aktuellen System-Daten verfügbar."
    
    # ========================================================================
    # CALLBACK REGISTRATION
    # ========================================================================
    
    def register_callback(self, name: str, callback: Callable):
        """Registriert einen Callback für System-Integration"""
        self.callbacks[name] = callback
        logger.debug(f"Callback registriert: {name}")
    
    def unregister_callback(self, name: str):
        """Entfernt einen Callback"""
        if name in self.callbacks:
            del self.callbacks[name]
    
    # ========================================================================
    # MONITORING
    # ========================================================================
    
    def start_monitoring(self, interval: float = 5.0):
        """Startet das kontinuierliche Monitoring"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, args=(interval,), daemon=True)
        self.monitor_thread.start()
        logger.info("🔍 AI Agent Monitoring gestartet")
    
    def stop_monitoring(self):
        """Stoppt das Monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("⏹️ AI Agent Monitoring gestoppt")
    
    def _monitoring_loop(self, interval: float):
        """Haupt-Monitoring-Schleife"""
        while self.is_running:
            try:
                # GPU Status prüfen
                if "check_gpu_health" in self.callbacks:
                    issues = self.callbacks["check_gpu_health"]()
                    for issue in issues:
                        self.detect_error(**issue)
                
                # Miner Status prüfen
                if "check_miner_health" in self.callbacks:
                    issues = self.callbacks["check_miner_health"]()
                    for issue in issues:
                        self.detect_error(**issue)
                
            except Exception as e:
                logger.error(f"Monitoring-Fehler: {e}")
            
            time.sleep(interval)
    
    # ========================================================================
    # STATISTIKEN
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Gibt Statistiken über den Agent zurück"""
        return {
            "total_errors_detected": len(list(self.error_queue)),
            "total_actions_executed": len(list(self.action_history)),
            "builtin_solutions": len(self.builtin_solutions),
            "learned_solutions": len(self.learned_solutions),
            "active_provider": self.active_provider.value if self.active_provider else None,
            "auto_fix_enabled": self.auto_fix_enabled,
            "learning_enabled": self.learning_enabled,
            "is_monitoring": self.is_running
        }


# ============================================================================
# SINGLETON INSTANZ
# ============================================================================

_agent_instance: Optional[AIAgent] = None

def get_ai_agent() -> AIAgent:
    """Gibt die Singleton-Instanz des AI Agents zurück"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AIAgent()
    return _agent_instance


# ============================================================================
# CODE REPAIR INTEGRATION
# ============================================================================

# Import Code Repair wenn verfügbar
try:
    from code_repair import get_repair_manager, CodeRepairManager, DetectedError as CodeError
    CODE_REPAIR_AVAILABLE = True
except ImportError:
    CODE_REPAIR_AVAILABLE = False
    logger.warning("Code Repair Modul nicht verfügbar")

# Import Portfolio Manager wenn verfügbar
try:
    from portfolio_manager import get_portfolio_manager, PortfolioManager
    PORTFOLIO_AVAILABLE = True
except ImportError:
    PORTFOLIO_AVAILABLE = False
    logger.warning("Portfolio Manager Modul nicht verfügbar")


class AIAgentWithCodeRepair:
    """
    Erweiterte AI Agent Klasse mit Code Repair und Portfolio Integration
    
    Diese Klasse erweitert den Standard AIAgent um:
    - Automatische Python-Fehlererkennung und -behebung
    - Portfolio-Überwachung und Alerts
    - Integration aller Subsysteme
    """
    
    def __init__(self):
        self.ai_agent = get_ai_agent()
        self.code_repair: Optional[CodeRepairManager] = None
        self.portfolio: Optional[PortfolioManager] = None
        
        # Code Repair initialisieren
        if CODE_REPAIR_AVAILABLE:
            self.code_repair = get_repair_manager()
            self.code_repair.on_error_detected = self._on_code_error
            self.code_repair.on_fix_applied = self._on_fix_applied
            self.code_repair.on_restart_required = self._on_restart_required
            logger.info("🔧 Code Repair in AI Agent integriert")
        
        # Portfolio Manager initialisieren
        if PORTFOLIO_AVAILABLE:
            self.portfolio = get_portfolio_manager()
            self.portfolio.on_alert = self._on_portfolio_alert
            self.portfolio.on_trade = self._on_trade_executed
            logger.info("💰 Portfolio Manager in AI Agent integriert")
    
    def _on_code_error(self, error):
        """Callback wenn Code-Fehler erkannt wird"""
        logger.warning(f"🐛 Code-Fehler erkannt: {error.error_type} in {error.file_path}")
        
        # AI Agent informieren
        self.ai_agent.detect_error(
            message=f"Python {error.error_type}: {error.message}",
            category="CODE",
            severity=ErrorSeverity.ERROR,
            context={"file": error.file_path, "line": error.line_number}
        )
    
    def _on_fix_applied(self, action):
        """Callback wenn Fix angewendet wurde"""
        if action.status == "success":
            logger.info(f"✅ Code-Fix erfolgreich: {action.fix.explanation if action.fix else 'N/A'}")
            
            # In Wissensbasis speichern
            if action.fix and action.error:
                self.ai_agent.knowledge_base.add_solution(
                    error_id=action.error.id,
                    solution_steps=[f"Fix angewendet: {action.fix.explanation}"],
                    actions_taken=["code_fix_applied"],
                    success_rating=1.0 if action.status == "success" else 0.0,
                    notes=f"LLM: {action.fix.llm_provider}, Konfidenz: {action.fix.confidence:.0%}"
                )
        else:
            logger.error(f"❌ Code-Fix fehlgeschlagen: {action.error_message}")
    
    def _on_restart_required(self):
        """Callback wenn Neustart erforderlich ist"""
        logger.info("🔄 Programm-Neustart durch Code Repair angefordert")
    
    def _on_portfolio_alert(self, level: str, message: str):
        """Callback für Portfolio-Alerts"""
        severity = ErrorSeverity.WARNING if level == "warning" else ErrorSeverity.INFO
        if level == "critical":
            severity = ErrorSeverity.CRITICAL
        
        self.ai_agent.detect_error(
            message=message,
            category="PORTFOLIO",
            severity=severity
        )
        logger.info(f"💰 Portfolio Alert [{level}]: {message}")
    
    def _on_trade_executed(self, trade):
        """Callback wenn Trade ausgeführt wurde"""
        logger.info(f"📈 Trade ausgeführt: {trade.side.upper()} {trade.amount} {trade.coin} @ ${trade.price:.4f}")
    
    def process_log_for_errors(self, log_text: str):
        """Verarbeitet Log-Text auf Code-Fehler"""
        if self.code_repair:
            self.code_repair.process_log_output(log_text)
    
    def get_portfolio_summary(self) -> Dict:
        """Gibt Portfolio-Zusammenfassung zurück"""
        if self.portfolio:
            return self.portfolio.get_portfolio_summary()
        return {}
    
    def get_repair_stats(self) -> Dict:
        """Gibt Code Repair Statistiken zurück"""
        if self.code_repair:
            return self.code_repair.get_stats()
        return {}
    
    def get_combined_activity_log(self, limit: int = 100) -> List[Dict]:
        """Kombiniertes Activity Log von allen Subsystemen"""
        logs = []
        
        # Code Repair Historie
        if self.code_repair:
            for item in self.code_repair.get_history(limit // 2):
                logs.append({
                    "timestamp": item.get("timestamp"),
                    "type": "CODE_REPAIR",
                    "description": f"{item.get('error_type')}: {item.get('error_message', '')[:50]}",
                    "status": item.get("status"),
                    "acknowledged": item.get("acknowledged", False)
                })
        
        # Portfolio Activity
        if self.portfolio:
            for item in self.portfolio.get_activity_log(limit // 2):
                logs.append({
                    "timestamp": item.get("timestamp"),
                    "type": item.get("action_type", "PORTFOLIO"),
                    "description": item.get("description", ""),
                    "status": "completed",
                    "acknowledged": item.get("acknowledged", False)
                })
        
        # Nach Timestamp sortieren
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return logs[:limit]


# Singleton für erweiterten Agent
_extended_agent: Optional[AIAgentWithCodeRepair] = None

def get_extended_ai_agent() -> AIAgentWithCodeRepair:
    """Gibt die erweiterte AI Agent Instanz zurück"""
    global _extended_agent
    if _extended_agent is None:
        _extended_agent = AIAgentWithCodeRepair()
    return _extended_agent


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("🤖 AI Agent Test")
    print("=" * 50)
    
    agent = get_ai_agent()
    
    # Zeige Statistiken
    stats = agent.get_statistics()
    print(f"\n📊 Statistiken:")
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # Test Error Detection
    print(f"\n🔍 Test Fehlererkennung:")
    error = agent.detect_error(
        message="GPU temperature exceeded 85°C",
        category="GPU",
        severity=ErrorSeverity.WARNING,
        gpu_index=0
    )
    print(f"   Fehler erkannt: {error.id}")
    
    # Test Solution Finding
    print(f"\n🔧 Test Lösungsfindung:")
    solution = agent.find_solution(error)
    if solution:
        print(f"   Lösung gefunden: {solution.id}")
        print(f"   Schritte: {solution.solution_steps}")
    
    # Test Chat (wenn LLM verfügbar)
    print(f"\n💬 Test Chat:")
    response = agent.chat("Was ist der aktuelle GPU-Status?")
    print(f"   Antwort: {response[:200]}...")
    
    print("\n✅ Test abgeschlossen!")
