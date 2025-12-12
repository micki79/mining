#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Code Repair - Automatische Python-Fehlerbehebung
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Erkennt Python Exceptions/Tracebacks automatisch
- Analysiert betroffene Code-Dateien
- Generiert Fixes mit LLM (GROQ/DeepSeek/Gemini)
- Wendet Fixes automatisch an
- Erstellt Backups vor jeder Änderung
- Neustart NUR das Programm (nicht PC)
- Vollständige Dokumentation aller Änderungen

Sicherheit:
- Backup vor jeder Code-Änderung
- Syntax-Validierung vor Anwendung
- Rollback bei Fehlern
- Alle Änderungen werden dokumentiert

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import os
import re
import sys
import json
import time
import shutil
import logging
import hashlib
import subprocess
import threading
import ast
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


# ============================================================
# ENUMS & DATA CLASSES
# ============================================================

class RepairStatus(Enum):
    """Status einer Reparatur"""
    DETECTED = "detected"
    ANALYZING = "analyzing"
    FIX_GENERATED = "fix_generated"
    APPLYING = "applying"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ErrorSeverity(Enum):
    """Schweregrad des Fehlers"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DetectedError:
    """Ein erkannter Python-Fehler"""
    id: str
    timestamp: datetime
    error_type: str  # z.B. "TypeError", "KeyError"
    message: str
    file_path: str
    line_number: int
    full_traceback: str
    code_context: str = ""  # Zeilen um den Fehler herum
    severity: str = "error"
    auto_fixable: bool = True


@dataclass
class CodeFix:
    """Ein generierter Fix"""
    error_id: str
    file_path: str
    original_code: str
    fixed_code: str
    explanation: str
    confidence: float  # 0.0 - 1.0
    llm_provider: str
    generated_at: datetime


@dataclass
class RepairAction:
    """Eine durchgeführte Reparatur-Aktion"""
    id: str
    timestamp: datetime
    error: DetectedError
    fix: Optional[CodeFix]
    status: str
    backup_path: str = ""
    error_message: str = ""
    restart_required: bool = False
    restart_performed: bool = False


@dataclass
class RepairSettings:
    """Einstellungen für Code-Repair"""
    enabled: bool = True
    auto_apply: bool = True  # Automatisch anwenden
    auto_restart: bool = True  # Automatisch Programm neustarten nach Fix
    min_confidence: float = 0.7  # Mindest-Konfidenz für Auto-Apply
    backup_enabled: bool = True
    max_retries: int = 3
    syntax_check: bool = True  # Syntax vor Anwendung prüfen
    
    # LLM Settings
    llm_provider: str = "groq"  # groq, gemini, deepseek
    llm_timeout: int = 30
    
    # Pfade
    backup_dir: str = "code_backups"
    log_dir: str = "repair_logs"
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'RepairSettings':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================
# ERROR DETECTOR
# ============================================================

class ErrorDetector:
    """Erkennt Python-Fehler in Logs und Output"""
    
    # Regex Patterns für verschiedene Fehlertypen
    TRACEBACK_PATTERN = re.compile(
        r'Traceback \(most recent call last\):\n(.*?)(\w+Error|\w+Exception): (.+?)(?=\n(?!  )|\Z)',
        re.DOTALL
    )
    
    SIMPLE_ERROR_PATTERN = re.compile(
        r'(\w+Error|\w+Exception): (.+?)$',
        re.MULTILINE
    )
    
    FILE_LINE_PATTERN = re.compile(
        r'File "(.+?)", line (\d+)',
        re.MULTILINE
    )
    
    # Fehler die automatisch gefixt werden können
    FIXABLE_ERRORS = {
        "SyntaxError": True,
        "IndentationError": True,
        "TabError": True,
        "NameError": True,
        "TypeError": True,
        "KeyError": True,
        "AttributeError": True,
        "IndexError": True,
        "ImportError": True,
        "ModuleNotFoundError": True,
        "ValueError": True,
        "ZeroDivisionError": True,
        "FileNotFoundError": True,
        "UnboundLocalError": True,
        "KeyboardInterrupt": False,  # User-initiated
        "SystemExit": False,
        "PermissionError": False,  # Nicht automatisch fixbar
        "OSError": False,
        "RuntimeError": True,
        "RecursionError": False,
        "MemoryError": False,
    }
    
    def __init__(self):
        self.detected_errors: List[DetectedError] = []
        self._error_hashes: set = set()  # Duplikat-Erkennung
    
    def _generate_error_id(self, error_type: str, file_path: str, line_number: int, message: str) -> str:
        """Generiert eindeutige Error-ID"""
        hash_input = f"{error_type}:{file_path}:{line_number}:{message[:50]}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def parse_traceback(self, text: str) -> Optional[DetectedError]:
        """Parst einen vollständigen Traceback"""
        match = self.TRACEBACK_PATTERN.search(text)
        if not match:
            return None
        
        traceback_body = match.group(1)
        error_type = match.group(2)
        message = match.group(3).strip()
        
        # Datei und Zeile extrahieren (letzter Eintrag)
        file_matches = self.FILE_LINE_PATTERN.findall(traceback_body)
        
        if file_matches:
            # Letzter Eintrag ist normalerweise der Fehlerort
            file_path, line_number = file_matches[-1]
            line_number = int(line_number)
        else:
            file_path = ""
            line_number = 0
        
        # Duplikat-Check
        error_hash = self._generate_error_id(error_type, file_path, line_number, message)
        if error_hash in self._error_hashes:
            return None
        self._error_hashes.add(error_hash)
        
        # Code-Kontext laden
        code_context = ""
        if file_path and Path(file_path).exists():
            code_context = self._get_code_context(file_path, line_number)
        
        # Prüfen ob fixbar
        auto_fixable = self.FIXABLE_ERRORS.get(error_type, False)
        
        # Severity bestimmen
        if error_type in ["MemoryError", "RecursionError", "SystemExit"]:
            severity = ErrorSeverity.CRITICAL.value
        elif error_type in ["SyntaxError", "IndentationError"]:
            severity = ErrorSeverity.ERROR.value
        else:
            severity = ErrorSeverity.WARNING.value
        
        error = DetectedError(
            id=error_hash,
            timestamp=datetime.now(),
            error_type=error_type,
            message=message,
            file_path=file_path,
            line_number=line_number,
            full_traceback=text,
            code_context=code_context,
            severity=severity,
            auto_fixable=auto_fixable
        )
        
        self.detected_errors.append(error)
        logger.warning(f"🐛 Fehler erkannt: {error_type} in {file_path}:{line_number}")
        
        return error
    
    def _get_code_context(self, file_path: str, line_number: int, context_lines: int = 10) -> str:
        """Lädt Code-Kontext um eine Zeile herum"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)
            
            context = []
            for i in range(start, end):
                prefix = ">>> " if i == line_number - 1 else "    "
                context.append(f"{i+1:4d}{prefix}{lines[i].rstrip()}")
            
            return "\n".join(context)
            
        except Exception as e:
            logger.error(f"Code-Kontext laden fehlgeschlagen: {e}")
            return ""
    
    def clear_cache(self):
        """Löscht den Duplikat-Cache"""
        self._error_hashes.clear()
        self.detected_errors.clear()


# ============================================================
# FIX GENERATOR (LLM-basiert)
# ============================================================

class FixGenerator:
    """Generiert Code-Fixes mit LLM (GROQ, DeepSeek, Gemini)"""
    
    # LLM API Konfigurationen
    LLM_CONFIGS = {
        "groq": {
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "model": "llama-3.3-70b-versatile",
            "api_key_env": "GROQ_API_KEY"
        },
        "deepseek": {
            "url": "https://api.deepseek.com/v1/chat/completions",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY"
        },
        "gemini": {
            "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            "model": "gemini-pro",
            "api_key_env": "GEMINI_API_KEY"
        }
    }
    
    SYSTEM_PROMPT = """Du bist ein erfahrener Python-Entwickler der Code-Fehler analysiert und behebt.

Deine Aufgabe:
1. Analysiere den Fehler und den Code-Kontext
2. Identifiziere die Ursache
3. Generiere einen minimalen Fix

WICHTIGE REGELN:
- Ändere NUR was nötig ist um den Fehler zu beheben
- Behalte den restlichen Code EXAKT bei
- Keine unnötigen Optimierungen oder Refactoring
- Füge hilfreiche Kommentare zum Fix hinzu
- Behalte alle Importe und Funktionen bei
- Gib IMMER den VOLLSTÄNDIGEN Code der Datei zurück

Antwortformat (JSON):
{
    "analysis": "Kurze Analyse des Problems",
    "fix_explanation": "Was der Fix macht",
    "fixed_code": "Der VOLLSTÄNDIGE korrigierte Code der Datei",
    "confidence": 0.0-1.0
}

WICHTIG: "fixed_code" muss den GESAMTEN Dateiinhalt enthalten, nicht nur die geänderte Zeile!"""
    
    def __init__(self, provider: str = "groq"):
        self.provider = provider
        self.api_keys: Dict[str, str] = {}
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Lädt API Keys aus Config oder Umgebung"""
        # Versuche aus ai_agent_config.json zu laden
        try:
            config_paths = ["ai_agent_config.json", "config/ai_agent_config.json"]
            for config_path in config_paths:
                if Path(config_path).exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        
                    for provider, data in config.get("llm_configs", {}).items():
                        if "api_key" in data and data["api_key"]:
                            self.api_keys[provider] = data["api_key"]
                    
                    if self.api_keys:
                        logger.info(f"🔑 API Keys geladen: {list(self.api_keys.keys())}")
                    break
        except Exception as e:
            logger.warning(f"API Keys aus Config laden fehlgeschlagen: {e}")
        
        # Fallback: Umgebungsvariablen
        for provider, config in self.LLM_CONFIGS.items():
            if provider not in self.api_keys:
                env_key = config.get("api_key_env", "")
                if env_key and os.environ.get(env_key):
                    self.api_keys[provider] = os.environ[env_key]
    
    def set_api_key(self, provider: str, api_key: str):
        """Setzt API Key für einen Provider"""
        self.api_keys[provider] = api_key
    
    def generate_fix(self, error: DetectedError, timeout: int = 30) -> Optional[CodeFix]:
        """Generiert einen Fix für den Fehler"""
        if not requests:
            logger.error("❌ requests Modul nicht verfügbar")
            return None
        
        if self.provider not in self.api_keys:
            logger.error(f"❌ Kein API Key für {self.provider}")
            return None
        
        # Prompt erstellen
        user_prompt = self._build_prompt(error)
        
        try:
            if self.provider == "gemini":
                response = self._call_gemini(user_prompt, timeout)
            else:
                response = self._call_openai_compatible(user_prompt, timeout)
            
            if response:
                return self._parse_response(error, response)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Fix-Generierung fehlgeschlagen: {e}")
            return None
    
    def _build_prompt(self, error: DetectedError) -> str:
        """Erstellt den Prompt für das LLM"""
        # Vollständige Datei laden wenn möglich
        full_code = ""
        if error.file_path and Path(error.file_path).exists():
            try:
                with open(error.file_path, 'r', encoding='utf-8') as f:
                    full_code = f.read()
            except:
                pass
        
        prompt = f"""FEHLER: {error.error_type}: {error.message}

DATEI: {error.file_path}
ZEILE: {error.line_number}

TRACEBACK:
{error.full_traceback}

CODE-KONTEXT (Zeile {error.line_number} markiert mit >>>):
{error.code_context}

"""
        
        if full_code:
            prompt += f"""VOLLSTÄNDIGER CODE DER DATEI:
```python
{full_code}
```

"""
        
        prompt += """Analysiere den Fehler und generiere einen Fix.
Antworte NUR mit dem JSON-Format wie im System-Prompt beschrieben.
WICHTIG: "fixed_code" muss den GESAMTEN Dateiinhalt enthalten!"""
        
        return prompt
    
    def _call_openai_compatible(self, prompt: str, timeout: int) -> Optional[str]:
        """Ruft OpenAI-kompatible API auf (GROQ, DeepSeek)"""
        config = self.LLM_CONFIGS.get(self.provider, {})
        api_key = self.api_keys.get(self.provider, "")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config.get("model", ""),
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 8000,
            "temperature": 0.2
        }
        
        response = requests.post(
            config.get("url", ""),
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        else:
            logger.error(f"LLM API Fehler: {response.status_code} - {response.text[:200]}")
            return None
    
    def _call_gemini(self, prompt: str, timeout: int) -> Optional[str]:
        """Ruft Gemini API auf"""
        api_key = self.api_keys.get("gemini", "")
        url = f"{self.LLM_CONFIGS['gemini']['url']}?key={api_key}"
        
        data = {
            "contents": [{
                "parts": [
                    {"text": f"{self.SYSTEM_PROMPT}\n\n{prompt}"}
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8000
            }
        }
        
        response = requests.post(url, json=data, timeout=timeout)
        
        if response.status_code == 200:
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        else:
            logger.error(f"Gemini API Fehler: {response.status_code}")
        
        return None
    
    def _parse_response(self, error: DetectedError, response: str) -> Optional[CodeFix]:
        """Parst die LLM-Antwort"""
        try:
            # JSON aus Antwort extrahieren
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match:
                logger.warning("Kein JSON in LLM-Antwort gefunden")
                return None
            
            data = json.loads(json_match.group())
            
            # Vollständige Datei laden für Vergleich
            original_code = ""
            if error.file_path and Path(error.file_path).exists():
                with open(error.file_path, 'r', encoding='utf-8') as f:
                    original_code = f.read()
            
            fixed_code = data.get("fixed_code", "")
            
            # Code aus Markdown-Block extrahieren falls vorhanden
            if "```python" in fixed_code:
                code_match = re.search(r'```python\n([\s\S]*?)\n```', fixed_code)
                if code_match:
                    fixed_code = code_match.group(1)
            elif "```" in fixed_code:
                code_match = re.search(r'```\n?([\s\S]*?)\n?```', fixed_code)
                if code_match:
                    fixed_code = code_match.group(1)
            
            fix = CodeFix(
                error_id=error.id,
                file_path=error.file_path,
                original_code=original_code,
                fixed_code=fixed_code,
                explanation=data.get("fix_explanation", data.get("analysis", "")),
                confidence=float(data.get("confidence", 0.5)),
                llm_provider=self.provider,
                generated_at=datetime.now()
            )
            
            logger.info(f"✨ Fix generiert: Konfidenz {fix.confidence:.0%}")
            return fix
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Fehler: {e}")
            return None
        except Exception as e:
            logger.error(f"Response Parse Fehler: {e}")
            return None


# ============================================================
# CODE PATCHER
# ============================================================

class CodePatcher:
    """Wendet Code-Fixes an und verwaltet Backups"""
    
    def __init__(self, backup_dir: str = "code_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
    
    def validate_syntax(self, code: str) -> Tuple[bool, str]:
        """Validiert Python-Syntax"""
        try:
            ast.parse(code)
            return True, "Syntax OK"
        except SyntaxError as e:
            return False, f"Syntax Error: {e.msg} (Zeile {e.lineno})"
    
    def create_backup(self, file_path: str) -> str:
        """Erstellt ein Backup der Datei"""
        source = Path(file_path)
        if not source.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{source.stem}_{timestamp}{source.suffix}.bak"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(source, backup_path)
        logger.info(f"💾 Backup erstellt: {backup_path}")
        
        return str(backup_path)
    
    def apply_fix(self, fix: CodeFix, syntax_check: bool = True) -> Tuple[bool, str]:
        """Wendet einen Fix an"""
        if not fix.file_path or not fix.fixed_code:
            return False, "Fix unvollständig (Pfad oder Code fehlt)"
        
        # Syntax prüfen
        if syntax_check:
            valid, msg = self.validate_syntax(fix.fixed_code)
            if not valid:
                return False, f"Fix hat Syntax-Fehler: {msg}"
        
        try:
            # Backup erstellen
            backup_path = self.create_backup(fix.file_path)
            
            # Fix anwenden
            with open(fix.file_path, 'w', encoding='utf-8') as f:
                f.write(fix.fixed_code)
            
            logger.info(f"✅ Fix angewendet: {fix.file_path}")
            return True, backup_path
            
        except Exception as e:
            logger.error(f"❌ Fix anwenden fehlgeschlagen: {e}")
            return False, str(e)
    
    def rollback(self, file_path: str, backup_path: str) -> bool:
        """Stellt Backup wieder her"""
        try:
            shutil.copy2(backup_path, file_path)
            logger.info(f"🔄 Rollback durchgeführt: {file_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Rollback fehlgeschlagen: {e}")
            return False
    
    def get_latest_backup(self, file_path: str) -> Optional[str]:
        """Findet das neueste Backup für eine Datei"""
        source = Path(file_path)
        backups = sorted(self.backup_dir.glob(f"{source.stem}_*.bak"), reverse=True)
        return str(backups[0]) if backups else None


# ============================================================
# REPAIR DATABASE
# ============================================================

class RepairDatabase:
    """SQLite Datenbank für Repair-Historie"""
    
    def __init__(self, db_path: str = "repair_history.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialisiert die Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Repair Actions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repair_actions (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                file_path TEXT,
                line_number INTEGER,
                fix_explanation TEXT,
                confidence REAL,
                status TEXT,
                backup_path TEXT,
                llm_provider TEXT,
                acknowledged INTEGER DEFAULT 0,
                acknowledged_at TEXT
            )
        """)
        
        # Daily Stats
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                errors_detected INTEGER DEFAULT 0,
                fixes_applied INTEGER DEFAULT 0,
                fixes_successful INTEGER DEFAULT 0,
                fixes_failed INTEGER DEFAULT 0,
                rollbacks INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Repair-Datenbank initialisiert: {self.db_path}")
    
    def log_action(self, action: RepairAction):
        """Loggt eine Reparatur-Aktion"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO repair_actions
            (id, timestamp, error_type, error_message, file_path, line_number, 
             fix_explanation, confidence, status, backup_path, llm_provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            action.id,
            action.timestamp.isoformat(),
            action.error.error_type,
            action.error.message,
            action.error.file_path,
            action.error.line_number,
            action.fix.explanation if action.fix else "",
            action.fix.confidence if action.fix else 0,
            action.status,
            action.backup_path,
            action.fix.llm_provider if action.fix else ""
        ))
        
        # Daily Stats aktualisieren
        today = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,))
        
        if action.status == RepairStatus.DETECTED.value:
            cursor.execute("UPDATE daily_stats SET errors_detected = errors_detected + 1 WHERE date = ?", (today,))
        elif action.status == RepairStatus.SUCCESS.value:
            cursor.execute("UPDATE daily_stats SET fixes_applied = fixes_applied + 1, fixes_successful = fixes_successful + 1 WHERE date = ?", (today,))
        elif action.status == RepairStatus.FAILED.value:
            cursor.execute("UPDATE daily_stats SET fixes_failed = fixes_failed + 1 WHERE date = ?", (today,))
        elif action.status == RepairStatus.ROLLED_BACK.value:
            cursor.execute("UPDATE daily_stats SET rollbacks = rollbacks + 1 WHERE date = ?", (today,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📝 Aktion geloggt: {action.id} - {action.status}")
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Holt Repair-Historie"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM repair_actions ORDER BY timestamp DESC LIMIT ?
        """, (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def get_unacknowledged(self) -> List[Dict]:
        """Holt unbestätigte Reparaturen (für Checkbox)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM repair_actions WHERE acknowledged = 0 ORDER BY timestamp DESC
        """)
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def acknowledge(self, action_id: str):
        """Bestätigt eine Reparatur (Checkbox abhaken)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE repair_actions SET acknowledged = 1, acknowledged_at = ? WHERE id = ?
        """, (datetime.now().isoformat(), action_id))
        
        conn.commit()
        conn.close()
    
    def get_stats(self, days: int = 30) -> Dict:
        """Holt Statistiken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(errors_detected), 0) as total_errors,
                COALESCE(SUM(fixes_applied), 0) as total_fixes,
                COALESCE(SUM(fixes_successful), 0) as successful,
                COALESCE(SUM(fixes_failed), 0) as failed,
                COALESCE(SUM(rollbacks), 0) as rollbacks
            FROM daily_stats WHERE date >= ?
        """, (start_date,))
        
        row = cursor.fetchone()
        conn.close()
        
        total_fixes = row[1] or 0
        successful = row[2] or 0
        
        return {
            "period_days": days,
            "total_errors": row[0] or 0,
            "total_fixes": total_fixes,
            "successful": successful,
            "failed": row[3] or 0,
            "rollbacks": row[4] or 0,
            "success_rate": (successful / total_fixes * 100) if total_fixes > 0 else 0
        }


# ============================================================
# CODE REPAIR MANAGER
# ============================================================

class CodeRepairManager:
    """
    Haupt-Klasse für automatische Code-Reparatur
    
    Koordiniert:
    - Fehlererkennung
    - Fix-Generierung
    - Code-Patching
    - Logging
    - Programm-Neustart (NICHT PC!)
    """
    
    def __init__(self, config_path: str = "code_repair_config.json"):
        self.config_path = config_path
        self.settings = RepairSettings()
        
        # Komponenten
        self.detector = ErrorDetector()
        self.generator = FixGenerator(self.settings.llm_provider)
        self.patcher = CodePatcher(self.settings.backup_dir)
        self.db = RepairDatabase()
        
        # State
        self._running = False
        self._pending_fixes: List[Tuple[DetectedError, CodeFix]] = []
        self._processed_errors: set = set()
        
        # Callbacks für GUI
        self.on_error_detected: Optional[Callable[[DetectedError], None]] = None
        self.on_fix_generated: Optional[Callable[[CodeFix], None]] = None
        self.on_fix_applied: Optional[Callable[[RepairAction], None]] = None
        self.on_restart_required: Optional[Callable[[], None]] = None
        
        # Config laden
        self._load_config()
        
        logger.info("🔧 Code Repair Manager initialisiert")
    
    def _load_config(self):
        """Lädt Konfiguration"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.settings = RepairSettings.from_dict(data)
                
                # Generator aktualisieren
                self.generator.provider = self.settings.llm_provider
                
                logger.info("📂 Code Repair Config geladen")
        except Exception as e:
            logger.warning(f"Config laden fehlgeschlagen: {e}")
    
    def save_config(self):
        """Speichert Konfiguration"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
            logger.info("💾 Code Repair Config gespeichert")
        except Exception as e:
            logger.error(f"Config speichern fehlgeschlagen: {e}")
    
    def process_log_output(self, text: str) -> Optional[RepairAction]:
        """Verarbeitet Log-Output auf Fehler und repariert automatisch"""
        if not self.settings.enabled:
            return None
        
        # Traceback suchen
        error = self.detector.parse_traceback(text)
        
        if error:
            return self._handle_detected_error(error)
        
        return None
    
    def _handle_detected_error(self, error: DetectedError) -> Optional[RepairAction]:
        """Behandelt einen erkannten Fehler"""
        # Duplikat-Check
        error_key = f"{error.error_type}:{error.file_path}:{error.line_number}"
        if error_key in self._processed_errors:
            return None
        self._processed_errors.add(error_key)
        
        logger.warning(f"🐛 Fehler erkannt: {error.error_type} in {error.file_path}:{error.line_number}")
        
        # Callback für GUI
        if self.on_error_detected:
            self.on_error_detected(error)
        
        # Initial Action loggen
        action = RepairAction(
            id=error.id,
            timestamp=datetime.now(),
            error=error,
            fix=None,
            status=RepairStatus.DETECTED.value
        )
        self.db.log_action(action)
        
        # Auto-Fix wenn aktiviert und fixbar
        if self.settings.auto_apply and error.auto_fixable:
            return self._auto_repair(error)
        else:
            logger.info(f"⏸️ Manueller Fix erforderlich für {error.error_type}")
            return action
    
    def _auto_repair(self, error: DetectedError) -> Optional[RepairAction]:
        """Führt automatische Reparatur durch"""
        logger.info(f"🔄 Starte Auto-Repair für {error.error_type}...")
        
        # Fix generieren
        fix = self.generator.generate_fix(error, self.settings.llm_timeout)
        
        if not fix:
            logger.error("❌ Fix-Generierung fehlgeschlagen")
            action = RepairAction(
                id=f"{error.id}_failed",
                timestamp=datetime.now(),
                error=error,
                fix=None,
                status=RepairStatus.FAILED.value,
                error_message="Fix-Generierung fehlgeschlagen"
            )
            self.db.log_action(action)
            return action
        
        # Callback für GUI
        if self.on_fix_generated:
            self.on_fix_generated(fix)
        
        # Konfidenz prüfen
        if fix.confidence < self.settings.min_confidence:
            logger.warning(f"⚠️ Fix-Konfidenz zu niedrig: {fix.confidence:.0%} < {self.settings.min_confidence:.0%}")
            self._pending_fixes.append((error, fix))
            return None
        
        # Fix anwenden
        success, result = self.patcher.apply_fix(fix, self.settings.syntax_check)
        
        # Action erstellen
        action = RepairAction(
            id=f"{error.id}_fix",
            timestamp=datetime.now(),
            error=error,
            fix=fix,
            status=RepairStatus.SUCCESS.value if success else RepairStatus.FAILED.value,
            backup_path=result if success else "",
            error_message="" if success else result,
            restart_required=success
        )
        
        # Loggen
        self.db.log_action(action)
        
        # Callback für GUI
        if self.on_fix_applied:
            self.on_fix_applied(action)
        
        if success:
            logger.info(f"✅ Fix erfolgreich angewendet: {error.file_path}")
            
            # Auto-Restart wenn aktiviert
            if self.settings.auto_restart:
                self._trigger_program_restart()
        else:
            logger.error(f"❌ Fix fehlgeschlagen: {result}")
        
        return action
    
    def _trigger_program_restart(self):
        """Triggert Programm-Neustart (NUR das Programm, NICHT den PC!)"""
        logger.info("🔄 Programm-Neustart wird vorbereitet...")
        
        # Callback für GUI
        if self.on_restart_required:
            self.on_restart_required()
        
        # Kurz warten damit alles gespeichert wird
        time.sleep(2)
        
        try:
            python = sys.executable
            script = sys.argv[0]
            
            logger.info(f"🚀 Starte Programm neu: {python} {script}")
            
            # Neuen Prozess starten
            if sys.platform == "win32":
                # Windows: START Befehl
                subprocess.Popen(
                    f'start "" "{python}" "{script}"',
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Linux/Mac
                subprocess.Popen([python, script], start_new_session=True)
            
            # Aktuellen Prozess beenden
            logger.info("👋 Beende aktuellen Prozess...")
            os._exit(0)
            
        except Exception as e:
            logger.error(f"❌ Neustart fehlgeschlagen: {e}")
    
    def manual_repair(self, error: DetectedError) -> Optional[RepairAction]:
        """Manuelle Reparatur (von GUI aufgerufen)"""
        fix = self.generator.generate_fix(error, self.settings.llm_timeout)
        
        if not fix:
            return None
        
        success, result = self.patcher.apply_fix(fix, self.settings.syntax_check)
        
        action = RepairAction(
            id=f"{error.id}_manual",
            timestamp=datetime.now(),
            error=error,
            fix=fix,
            status=RepairStatus.SUCCESS.value if success else RepairStatus.FAILED.value,
            backup_path=result if success else "",
            error_message="" if success else result
        )
        
        self.db.log_action(action)
        
        if self.on_fix_applied:
            self.on_fix_applied(action)
        
        return action
    
    def rollback_last(self, file_path: str) -> bool:
        """Rollt letzte Änderung zurück"""
        backup_path = self.patcher.get_latest_backup(file_path)
        
        if not backup_path:
            logger.warning(f"Kein Backup gefunden für {file_path}")
            return False
        
        success = self.patcher.rollback(file_path, backup_path)
        
        if success:
            # Rollback loggen
            action = RepairAction(
                id=f"rollback_{datetime.now().timestamp()}",
                timestamp=datetime.now(),
                error=DetectedError(
                    id="rollback", timestamp=datetime.now(),
                    error_type="Rollback", message=f"Rollback für {file_path}",
                    file_path=file_path, line_number=0, full_traceback=""
                ),
                fix=None,
                status=RepairStatus.ROLLED_BACK.value,
                backup_path=backup_path
            )
            self.db.log_action(action)
        
        return success
    
    def get_pending_fixes(self) -> List[Tuple[DetectedError, CodeFix]]:
        """Gibt ausstehende Fixes zurück (niedrige Konfidenz)"""
        return self._pending_fixes.copy()
    
    def apply_pending_fix(self, error_id: str) -> bool:
        """Wendet einen ausstehenden Fix an"""
        for error, fix in self._pending_fixes:
            if error.id == error_id:
                success, _ = self.patcher.apply_fix(fix, self.settings.syntax_check)
                if success:
                    self._pending_fixes.remove((error, fix))
                return success
        return False
    
    def get_stats(self) -> Dict:
        """Gibt Statistiken zurück"""
        return self.db.get_stats()
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Gibt Reparatur-Historie zurück"""
        return self.db.get_history(limit)
    
    def get_unacknowledged(self) -> List[Dict]:
        """Gibt unbestätigte Reparaturen zurück"""
        return self.db.get_unacknowledged()
    
    def acknowledge(self, action_id: str):
        """Bestätigt eine Reparatur (Checkbox abhaken)"""
        self.db.acknowledge(action_id)
    
    def clear_cache(self):
        """Löscht den Fehler-Cache"""
        self.detector.clear_cache()
        self._processed_errors.clear()


# ============================================================
# SINGLETON
# ============================================================

_repair_manager: Optional[CodeRepairManager] = None

def get_repair_manager() -> CodeRepairManager:
    """Gibt Singleton-Instanz zurück"""
    global _repair_manager
    if _repair_manager is None:
        _repair_manager = CodeRepairManager()
    return _repair_manager


# ============================================================
# LOG INTERCEPTOR (für automatische Erkennung)
# ============================================================

class LogInterceptor(logging.Handler):
    """
    Fängt Log-Nachrichten ab und prüft auf Fehler
    
    Verwendung:
    ```python
    interceptor = LogInterceptor(get_repair_manager())
    logging.getLogger().addHandler(interceptor)
    ```
    """
    
    def __init__(self, repair_manager: CodeRepairManager):
        super().__init__()
        self.repair_manager = repair_manager
        self._buffer: List[str] = []
        self._buffer_size = 50
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self._buffer.append(msg)
            
            # Buffer begrenzen
            if len(self._buffer) > self._buffer_size:
                self._buffer.pop(0)
            
            # Auf Traceback prüfen
            if "Traceback" in msg or "Error:" in msg or "Exception:" in msg:
                full_text = "\n".join(self._buffer[-30:])  # Letzte 30 Zeilen
                self.repair_manager.process_log_output(full_text)
                
        except Exception:
            pass  # Fehler im Handler ignorieren


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 60)
    print("🔧 Code Repair Manager Test")
    print("=" * 60)
    
    # Test Error Detection
    detector = ErrorDetector()
    
    test_traceback = """
Traceback (most recent call last):
  File "test.py", line 42, in test_function
    result = data['key']
KeyError: 'key'
"""
    
    print("\n📝 Test Traceback:")
    print(test_traceback)
    
    error = detector.parse_traceback(test_traceback)
    if error:
        print(f"\n✅ Fehler erkannt:")
        print(f"   Typ: {error.error_type}")
        print(f"   Nachricht: {error.message}")
        print(f"   Datei: {error.file_path}")
        print(f"   Zeile: {error.line_number}")
        print(f"   Auto-fixbar: {error.auto_fixable}")
    
    print("\n📊 Statistiken:")
    manager = get_repair_manager()
    stats = manager.get_stats()
    print(f"   Erkannte Fehler: {stats['total_errors']}")
    print(f"   Angewendete Fixes: {stats['total_fixes']}")
    print(f"   Erfolgsrate: {stats['success_rate']:.1f}%")
    
    print("\n" + "=" * 60)
    print("✅ Test abgeschlossen!")
    print("=" * 60)
