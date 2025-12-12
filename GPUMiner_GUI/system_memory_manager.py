#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
System Memory Manager - Automatische Pagefile/Swap Anpassung für Mining
Teil des GPU Mining Profit Switcher V12.8 Ultimate

Features:
- Prüft RAM und virtuellen Speicher
- Berechnet Mining-Anforderungen basierend auf GPU-Anzahl und Coins
- Passt Pagefile (Windows) / Swap (Linux) automatisch an
- Führt bei Bedarf PC-Neustart durch
- Befolgt Mining-Richtlinien für Speicher

MINING-RICHTLINIEN:
- ETH/ETC DAG: ~5-6 GB pro GPU
- RVN/KAWPOW: ~3-4 GB pro GPU
- ERG/Autolykos: ~2-3 GB pro GPU
- Minimum Pagefile: GPU_Anzahl × 8GB + 8GB Reserve
- Empfohlen: 1.5× bis 2× physischen RAM als Pagefile
- Windows: Pagefile auf schnellster SSD/NVMe

REGELN: NEVER omit anything. ONLY add/fix what I say. ALWAYS ask before changing anything!
"""

import os
import sys
import json
import logging
import platform
import subprocess
import ctypes
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryAction(Enum):
    """Mögliche Aktionen"""
    NONE = "none"
    INCREASE_PAGEFILE = "increase_pagefile"
    DECREASE_PAGEFILE = "decrease_pagefile"  # Normalerweise nicht nötig
    RESTART_REQUIRED = "restart_required"
    INSUFFICIENT_DISK = "insufficient_disk"
    ADMIN_REQUIRED = "admin_required"


@dataclass
class MemoryRequirements:
    """Speicher-Anforderungen für Mining"""
    gpu_count: int
    coins_mining: List[str]
    
    # Berechnete Werte
    min_pagefile_mb: int = 0
    recommended_pagefile_mb: int = 0
    dag_size_total_mb: int = 0
    system_reserve_mb: int = 8192  # 8 GB Reserve
    
    # Erklärung
    explanation: str = ""


@dataclass
class SystemMemoryInfo:
    """Aktuelle System-Speicher-Informationen"""
    # Physischer RAM
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    used_ram_mb: int = 0
    ram_percent_used: float = 0.0
    
    # Virtueller Speicher (Pagefile/Swap)
    pagefile_total_mb: int = 0
    pagefile_used_mb: int = 0
    pagefile_free_mb: int = 0
    
    # Kombiniert
    total_virtual_mb: int = 0
    available_virtual_mb: int = 0
    
    # Disk für Pagefile
    pagefile_disk: str = ""
    pagefile_disk_free_mb: int = 0


@dataclass
class MemoryDecision:
    """Entscheidung des AI Memory Managers"""
    action: MemoryAction
    current_pagefile_mb: int
    required_pagefile_mb: int
    new_pagefile_mb: int
    needs_restart: bool
    can_auto_fix: bool
    
    # Details
    reason: str = ""
    steps: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.warnings is None:
            self.warnings = []


class SystemMemoryManager:
    """
    Intelligenter Speicher-Manager für Mining
    
    Prüft und optimiert automatisch den virtuellen Speicher
    basierend auf Mining-Anforderungen und System-Ressourcen.
    """
    
    # DAG/Memory-Anforderungen pro Algorithmus (in MB pro GPU)
    ALGO_MEMORY_REQUIREMENTS = {
        # Hoher Speicherbedarf
        "etchash": 6144,      # ~6 GB - ETC DAG
        "ethash": 6144,       # ~6 GB - ETH DAG (historisch)
        "octopus": 5120,      # ~5 GB - CFX
        
        # Mittlerer Speicherbedarf
        "kawpow": 4096,       # ~4 GB - RVN
        "firopow": 4096,      # ~4 GB - FIRO
        "autolykos2": 3072,   # ~3 GB - ERG
        "nexapow": 3072,      # ~3 GB - NEXA
        
        # Niedriger Speicherbedarf
        "kheavyhash": 2048,   # ~2 GB - KAS
        "blake3": 2048,       # ~2 GB - ALPH, IRON
        "cuckatoo32": 8192,   # ~8 GB - GRIN (Graph-basiert, braucht viel!)
        "equihash125": 2048,  # ~2 GB - FLUX
        "beamhashiii": 2048,  # ~2 GB - BEAM
        "dynexsolve": 4096,   # ~4 GB - DNX
        
        # Default für unbekannte
        "default": 4096,      # ~4 GB als sicherer Default
    }
    
    # Coin zu Algorithmus Mapping
    COIN_ALGORITHMS = {
        "RVN": "kawpow",
        "ERG": "autolykos2",
        "ETC": "etchash",
        "FLUX": "equihash125",
        "KAS": "kheavyhash",
        "ALPH": "blake3",
        "IRON": "blake3",
        "GRIN": "cuckatoo32",
        "BEAM": "beamhashiii",
        "CFX": "octopus",
        "NEXA": "nexapow",
        "DNX": "dynexsolve",
        "FIRO": "firopow",
        "CLORE": "kawpow",
    }
    
    # Mindest-Pagefile pro GPU-Anzahl (in MB)
    MIN_PAGEFILE_PER_GPU = {
        1: 16384,   # 16 GB für 1 GPU
        2: 24576,   # 24 GB für 2 GPUs
        3: 32768,   # 32 GB für 3 GPUs
        4: 40960,   # 40 GB für 4 GPUs
        5: 49152,   # 48 GB für 5 GPUs
        6: 57344,   # 56 GB für 6 GPUs
        7: 65536,   # 64 GB für 7 GPUs
        8: 73728,   # 72 GB für 8 GPUs
        9: 81920,   # 80 GB für 9 GPUs
    }
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.is_linux = platform.system() == "Linux"
        self._last_check = None
        self._cached_info: Optional[SystemMemoryInfo] = None
        
        # Callbacks
        self.on_decision: Optional[callable] = None
        self.on_action_required: Optional[callable] = None
        self.on_restart_required: Optional[callable] = None
    
    def get_system_memory_info(self) -> SystemMemoryInfo:
        """Sammelt aktuelle System-Speicher-Informationen"""
        info = SystemMemoryInfo()
        
        try:
            import psutil
            
            # RAM
            mem = psutil.virtual_memory()
            info.total_ram_mb = mem.total // (1024 * 1024)
            info.available_ram_mb = mem.available // (1024 * 1024)
            info.used_ram_mb = mem.used // (1024 * 1024)
            info.ram_percent_used = mem.percent
            
            # Swap/Pagefile
            swap = psutil.swap_memory()
            info.pagefile_total_mb = swap.total // (1024 * 1024)
            info.pagefile_used_mb = swap.used // (1024 * 1024)
            info.pagefile_free_mb = swap.free // (1024 * 1024)
            
            # Kombiniert
            info.total_virtual_mb = info.total_ram_mb + info.pagefile_total_mb
            info.available_virtual_mb = info.available_ram_mb + info.pagefile_free_mb
            
            # Pagefile Disk (Windows)
            if self.is_windows:
                info.pagefile_disk = "C:"  # Standard
                try:
                    disk = psutil.disk_usage("C:\\")
                    info.pagefile_disk_free_mb = disk.free // (1024 * 1024)
                except:
                    pass
            else:
                # Linux: Swap ist meist auf Root-Partition
                info.pagefile_disk = "/"
                try:
                    disk = psutil.disk_usage("/")
                    info.pagefile_disk_free_mb = disk.free // (1024 * 1024)
                except:
                    pass
            
        except ImportError:
            logger.error("psutil nicht installiert - kann Speicher nicht prüfen")
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Speicher-Info: {e}")
        
        self._cached_info = info
        self._last_check = datetime.now()
        
        return info
    
    def calculate_mining_requirements(self, gpu_count: int, coins: List[str]) -> MemoryRequirements:
        """
        Berechnet Speicher-Anforderungen für Mining
        
        Args:
            gpu_count: Anzahl der GPUs
            coins: Liste der zu minenden Coins
            
        Returns:
            MemoryRequirements mit berechneten Werten
        """
        req = MemoryRequirements(
            gpu_count=gpu_count,
            coins_mining=coins
        )
        
        # Höchste DAG-Größe finden (für worst case)
        max_dag_per_gpu = 0
        max_dag_coin = ""
        
        for coin in coins:
            algo = self.COIN_ALGORITHMS.get(coin, "default")
            dag_size = self.ALGO_MEMORY_REQUIREMENTS.get(algo, self.ALGO_MEMORY_REQUIREMENTS["default"])
            if dag_size > max_dag_per_gpu:
                max_dag_per_gpu = dag_size
                max_dag_coin = coin
        
        # Falls keine Coins angegeben, Default verwenden
        if max_dag_per_gpu == 0:
            max_dag_per_gpu = self.ALGO_MEMORY_REQUIREMENTS["default"]
            max_dag_coin = "Unknown"
        
        # Gesamt DAG-Größe
        req.dag_size_total_mb = max_dag_per_gpu * gpu_count
        
        # Minimum Pagefile nach Tabelle
        req.min_pagefile_mb = self.MIN_PAGEFILE_PER_GPU.get(
            gpu_count, 
            self.MIN_PAGEFILE_PER_GPU[9] + ((gpu_count - 9) * 8192)
        )
        
        # Empfohlenes Pagefile: DAG + Reserve + 50% Extra
        calculated = req.dag_size_total_mb + req.system_reserve_mb
        req.recommended_pagefile_mb = int(calculated * 1.5)
        
        # Minimum sollte nicht unter Empfehlung sein
        if req.min_pagefile_mb < req.recommended_pagefile_mb:
            req.min_pagefile_mb = req.recommended_pagefile_mb
        
        # Erklärung
        req.explanation = (
            f"Mining {len(coins)} Coin(s) auf {gpu_count} GPU(s):\n"
            f"- Höchster DAG ({max_dag_coin}): {max_dag_per_gpu} MB pro GPU\n"
            f"- Gesamt DAG für alle GPUs: {req.dag_size_total_mb} MB\n"
            f"- System-Reserve: {req.system_reserve_mb} MB\n"
            f"- Empfohlenes Pagefile: {req.recommended_pagefile_mb} MB ({req.recommended_pagefile_mb // 1024} GB)\n"
            f"- Minimum Pagefile: {req.min_pagefile_mb} MB ({req.min_pagefile_mb // 1024} GB)"
        )
        
        return req
    
    def analyze_and_decide(self, gpu_count: int, coins: List[str]) -> MemoryDecision:
        """
        Analysiert System und trifft Entscheidung über Pagefile-Anpassung
        
        Args:
            gpu_count: Anzahl der GPUs
            coins: Liste der zu minenden Coins
            
        Returns:
            MemoryDecision mit Aktion und Details
        """
        # System-Info sammeln
        sys_info = self.get_system_memory_info()
        
        # Anforderungen berechnen
        requirements = self.calculate_mining_requirements(gpu_count, coins)
        
        logger.info(f"📊 Speicher-Analyse:\n{requirements.explanation}")
        logger.info(f"💾 Aktuell: RAM {sys_info.total_ram_mb}MB, Pagefile {sys_info.pagefile_total_mb}MB")
        
        # Entscheidung initialisieren
        decision = MemoryDecision(
            action=MemoryAction.NONE,
            current_pagefile_mb=sys_info.pagefile_total_mb,
            required_pagefile_mb=requirements.min_pagefile_mb,
            new_pagefile_mb=sys_info.pagefile_total_mb,
            needs_restart=False,
            can_auto_fix=False
        )
        
        # === PRÜFUNG 1: Ist genug Pagefile vorhanden? ===
        if sys_info.pagefile_total_mb >= requirements.min_pagefile_mb:
            decision.reason = (
                f"✅ Pagefile ausreichend: {sys_info.pagefile_total_mb} MB "
                f"(benötigt: {requirements.min_pagefile_mb} MB)"
            )
            logger.info(decision.reason)
            return decision
        
        # === PAGEFILE ZU KLEIN - Muss erhöht werden ===
        decision.action = MemoryAction.INCREASE_PAGEFILE
        decision.new_pagefile_mb = requirements.recommended_pagefile_mb
        decision.needs_restart = True
        
        # === PRÜFUNG 2: Genug Disk-Speicher für größeres Pagefile? ===
        additional_needed = decision.new_pagefile_mb - sys_info.pagefile_total_mb
        
        if sys_info.pagefile_disk_free_mb < additional_needed + 10240:  # +10GB Puffer
            decision.action = MemoryAction.INSUFFICIENT_DISK
            decision.can_auto_fix = False
            decision.reason = (
                f"❌ Nicht genug Disk-Speicher für Pagefile!\n"
                f"Benötigt: {additional_needed} MB zusätzlich\n"
                f"Verfügbar auf {sys_info.pagefile_disk}: {sys_info.pagefile_disk_free_mb} MB"
            )
            decision.warnings.append("Bitte Festplattenspeicher freigeben oder Pagefile auf andere Disk verschieben!")
            logger.error(decision.reason)
            return decision
        
        # === PRÜFUNG 3: Admin-Rechte vorhanden? (Windows) ===
        if self.is_windows and not self._is_admin():
            decision.action = MemoryAction.ADMIN_REQUIRED
            decision.can_auto_fix = False
            decision.reason = (
                f"⚠️ Admin-Rechte erforderlich für Pagefile-Änderung!\n"
                f"Aktuell: {sys_info.pagefile_total_mb} MB\n"
                f"Benötigt: {requirements.min_pagefile_mb} MB"
            )
            decision.steps = [
                "1. Programm als Administrator neu starten",
                "2. Oder manuell: Systemsteuerung → System → Erweiterte Systemeinstellungen",
                "3. → Leistung → Einstellungen → Erweitert → Virtueller Arbeitsspeicher",
                f"4. Größe auf {decision.new_pagefile_mb} MB ({decision.new_pagefile_mb // 1024} GB) setzen"
            ]
            logger.warning(decision.reason)
            return decision
        
        # === KANN AUTOMATISCH BEHOBEN WERDEN ===
        decision.can_auto_fix = True
        decision.reason = (
            f"⚠️ Pagefile zu klein für Mining!\n"
            f"Aktuell: {sys_info.pagefile_total_mb} MB ({sys_info.pagefile_total_mb // 1024} GB)\n"
            f"Benötigt: {requirements.min_pagefile_mb} MB ({requirements.min_pagefile_mb // 1024} GB)\n"
            f"Wird erhöht auf: {decision.new_pagefile_mb} MB ({decision.new_pagefile_mb // 1024} GB)"
        )
        
        decision.steps = [
            f"1. Pagefile wird von {sys_info.pagefile_total_mb} MB auf {decision.new_pagefile_mb} MB erhöht",
            "2. System wird für Änderung vorbereitet",
            "3. PC wird neugestartet um Änderung anzuwenden",
            "4. Nach Neustart ist Mining-Speicher optimal konfiguriert"
        ]
        
        decision.warnings = [
            "⚠️ PC-NEUSTART ERFORDERLICH!",
            "Alle ungespeicherten Arbeiten werden verloren gehen.",
            "Mining wird nach Neustart automatisch fortgesetzt."
        ]
        
        logger.warning(decision.reason)
        
        # Callback
        if self.on_decision:
            self.on_decision(decision)
        
        return decision
    
    def _is_admin(self) -> bool:
        """Prüft ob Programm mit Admin-Rechten läuft (Windows)"""
        if not self.is_windows:
            return os.geteuid() == 0  # Linux root check
        
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def apply_pagefile_change(self, new_size_mb: int) -> Tuple[bool, str]:
        """
        Wendet Pagefile-Änderung an
        
        Args:
            new_size_mb: Neue Pagefile-Größe in MB
            
        Returns:
            (success, message)
        """
        if self.is_windows:
            return self._apply_pagefile_windows(new_size_mb)
        elif self.is_linux:
            return self._apply_swap_linux(new_size_mb)
        else:
            return False, "Nicht unterstütztes Betriebssystem"
    
    def _apply_pagefile_windows(self, new_size_mb: int) -> Tuple[bool, str]:
        """
        Ändert Windows Pagefile über WMI/PowerShell
        
        Args:
            new_size_mb: Neue Größe in MB
            
        Returns:
            (success, message)
        """
        if not self._is_admin():
            return False, "Admin-Rechte erforderlich!"
        
        try:
            # PowerShell-Befehl für Pagefile-Änderung
            # Schritt 1: Automatische Verwaltung deaktivieren
            ps_disable_auto = """
            $System = Get-WmiObject Win32_ComputerSystem -EnableAllPrivileges
            $System.AutomaticManagedPagefile = $false
            $System.Put() | Out-Null
            """
            
            # Schritt 2: Aktuelles Pagefile löschen und neues setzen
            ps_set_pagefile = f"""
            $PageFile = Get-WmiObject Win32_PageFileSetting
            if ($PageFile) {{
                $PageFile.Delete()
            }}
            Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{{
                Name = "C:\\pagefile.sys"
                InitialSize = {new_size_mb}
                MaximumSize = {new_size_mb}
            }} | Out-Null
            """
            
            # Ausführen
            logger.info(f"🔧 Setze Windows Pagefile auf {new_size_mb} MB...")
            
            # Disable auto management
            result1 = subprocess.run(
                ["powershell", "-Command", ps_disable_auto],
                capture_output=True,
                text=True
            )
            
            if result1.returncode != 0:
                logger.warning(f"Auto-Management Warnung: {result1.stderr}")
            
            # Set new pagefile
            result2 = subprocess.run(
                ["powershell", "-Command", ps_set_pagefile],
                capture_output=True,
                text=True
            )
            
            if result2.returncode != 0:
                return False, f"Pagefile-Fehler: {result2.stderr}"
            
            logger.info(f"✅ Windows Pagefile auf {new_size_mb} MB gesetzt")
            return True, f"Pagefile erfolgreich auf {new_size_mb} MB gesetzt. NEUSTART ERFORDERLICH!"
            
        except Exception as e:
            logger.error(f"Windows Pagefile Fehler: {e}")
            return False, str(e)
    
    def _apply_swap_linux(self, new_size_mb: int) -> Tuple[bool, str]:
        """
        Ändert Linux Swap-Größe
        
        Args:
            new_size_mb: Neue Größe in MB
            
        Returns:
            (success, message)
        """
        if os.geteuid() != 0:
            return False, "Root-Rechte erforderlich (sudo)!"
        
        try:
            swap_file = "/swapfile"
            
            # Aktuellen Swap deaktivieren
            subprocess.run(["swapoff", "-a"], check=False)
            
            # Altes Swapfile löschen wenn vorhanden
            if os.path.exists(swap_file):
                os.remove(swap_file)
            
            # Neues Swapfile erstellen
            logger.info(f"🔧 Erstelle Linux Swapfile mit {new_size_mb} MB...")
            
            # dd zum Erstellen
            subprocess.run([
                "dd", "if=/dev/zero", f"of={swap_file}",
                "bs=1M", f"count={new_size_mb}"
            ], check=True, capture_output=True)
            
            # Berechtigungen setzen
            os.chmod(swap_file, 0o600)
            
            # Als Swap formatieren
            subprocess.run(["mkswap", swap_file], check=True, capture_output=True)
            
            # Aktivieren
            subprocess.run(["swapon", swap_file], check=True, capture_output=True)
            
            # In /etc/fstab eintragen für Persistenz
            fstab_line = f"{swap_file} none swap sw 0 0\n"
            with open("/etc/fstab", "r") as f:
                fstab = f.read()
            
            if swap_file not in fstab:
                with open("/etc/fstab", "a") as f:
                    f.write(fstab_line)
            
            logger.info(f"✅ Linux Swap auf {new_size_mb} MB gesetzt")
            return True, f"Swap erfolgreich auf {new_size_mb} MB gesetzt"
            
        except Exception as e:
            logger.error(f"Linux Swap Fehler: {e}")
            return False, str(e)
    
    def schedule_restart(self, delay_seconds: int = 60) -> Tuple[bool, str]:
        """
        Plant einen System-Neustart
        
        Args:
            delay_seconds: Verzögerung in Sekunden
            
        Returns:
            (success, message)
        """
        if self.is_windows:
            try:
                # Windows Restart mit Verzögerung
                subprocess.run([
                    "shutdown", "/r", "/t", str(delay_seconds),
                    "/c", "Mining Speicher-Optimierung - Neustart erforderlich"
                ], check=True)
                
                msg = f"PC-Neustart in {delay_seconds} Sekunden geplant"
                logger.info(f"🔄 {msg}")
                
                if self.on_restart_required:
                    self.on_restart_required(delay_seconds)
                
                return True, msg
                
            except Exception as e:
                return False, f"Restart-Fehler: {e}"
                
        elif self.is_linux:
            try:
                subprocess.run([
                    "shutdown", "-r", f"+{delay_seconds // 60}",
                    "Mining Speicher-Optimierung"
                ], check=True)
                
                msg = f"PC-Neustart in {delay_seconds // 60} Minuten geplant"
                logger.info(f"🔄 {msg}")
                
                if self.on_restart_required:
                    self.on_restart_required(delay_seconds)
                
                return True, msg
                
            except Exception as e:
                return False, f"Restart-Fehler: {e}"
        
        return False, "Nicht unterstütztes OS"
    
    def cancel_restart(self) -> Tuple[bool, str]:
        """Bricht geplanten Neustart ab"""
        try:
            if self.is_windows:
                subprocess.run(["shutdown", "/a"], check=True)
            else:
                subprocess.run(["shutdown", "-c"], check=True)
            
            logger.info("⏹️ Geplanter Neustart abgebrochen")
            return True, "Neustart abgebrochen"
            
        except Exception as e:
            return False, f"Abbruch-Fehler: {e}"
    
    def auto_optimize_for_mining(self, gpu_count: int, coins: List[str], 
                                  auto_restart: bool = False) -> Tuple[bool, MemoryDecision]:
        """
        Vollautomatische Speicher-Optimierung für Mining
        
        Args:
            gpu_count: Anzahl der GPUs
            coins: Zu minende Coins
            auto_restart: Automatisch neustarten wenn nötig
            
        Returns:
            (success, decision)
        """
        logger.info(f"🔍 Prüfe Speicher für {gpu_count} GPUs, Coins: {coins}")
        
        # Analyse durchführen
        decision = self.analyze_and_decide(gpu_count, coins)
        
        # Wenn keine Aktion nötig
        if decision.action == MemoryAction.NONE:
            return True, decision
        
        # Wenn nicht automatisch behebbar
        if not decision.can_auto_fix:
            if self.on_action_required:
                self.on_action_required(decision)
            return False, decision
        
        # Pagefile-Änderung anwenden
        if decision.action == MemoryAction.INCREASE_PAGEFILE:
            success, msg = self.apply_pagefile_change(decision.new_pagefile_mb)
            
            if not success:
                decision.reason += f"\n\n❌ Fehler: {msg}"
                return False, decision
            
            decision.reason += f"\n\n✅ {msg}"
            
            # Neustart wenn gewünscht
            if auto_restart and decision.needs_restart:
                restart_success, restart_msg = self.schedule_restart(60)
                if restart_success:
                    decision.reason += f"\n🔄 {restart_msg}"
                else:
                    decision.reason += f"\n⚠️ Neustart-Fehler: {restart_msg}"
                    decision.warnings.append("Bitte PC manuell neustarten!")
        
        return True, decision
    
    def get_summary_string(self) -> str:
        """Gibt eine Zusammenfassung des Speicher-Status zurück"""
        info = self.get_system_memory_info()
        
        return (
            f"💾 SPEICHER-STATUS\n"
            f"{'='*40}\n"
            f"RAM: {info.total_ram_mb // 1024} GB total, {info.available_ram_mb // 1024} GB frei\n"
            f"Pagefile: {info.pagefile_total_mb // 1024} GB total, {info.pagefile_free_mb // 1024} GB frei\n"
            f"Virtual Total: {info.total_virtual_mb // 1024} GB\n"
            f"Disk frei ({info.pagefile_disk}): {info.pagefile_disk_free_mb // 1024} GB\n"
            f"{'='*40}"
        )


# ============================================================================
# AI DECISION HELPER
# ============================================================================

class MiningMemoryAI:
    """
    AI-Entscheidungshelfer für Speicher-Management
    
    Analysiert System und Mining-Anforderungen und trifft
    intelligente Entscheidungen über Speicher-Anpassungen.
    """
    
    def __init__(self, memory_manager: SystemMemoryManager):
        self.manager = memory_manager
        self._decision_log: List[Dict] = []
    
    def evaluate_situation(self, gpu_count: int, coins: List[str]) -> Dict[str, Any]:
        """
        Evaluiert die aktuelle Situation und gibt Empfehlung
        
        Returns:
            Dict mit Analyse und Empfehlung
        """
        sys_info = self.manager.get_system_memory_info()
        requirements = self.manager.calculate_mining_requirements(gpu_count, coins)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "gpu_count": gpu_count,
            "coins": coins,
            "system": {
                "ram_gb": sys_info.total_ram_mb // 1024,
                "pagefile_gb": sys_info.pagefile_total_mb // 1024,
                "disk_free_gb": sys_info.pagefile_disk_free_mb // 1024,
            },
            "requirements": {
                "min_pagefile_gb": requirements.min_pagefile_mb // 1024,
                "recommended_gb": requirements.recommended_pagefile_mb // 1024,
                "dag_total_gb": requirements.dag_size_total_mb // 1024,
            },
            "status": "OK",
            "action_needed": False,
            "recommendation": "",
            "severity": "info",  # info, warning, critical
        }
        
        # Bewertung
        current = sys_info.pagefile_total_mb
        needed = requirements.min_pagefile_mb
        
        if current >= needed:
            result["status"] = "OK"
            result["recommendation"] = "Speicher ist ausreichend für Mining konfiguriert."
            result["severity"] = "info"
            
        elif current >= needed * 0.8:
            result["status"] = "MARGINAL"
            result["action_needed"] = True
            result["recommendation"] = (
                f"Speicher knapp! Aktuell {current // 1024} GB, empfohlen {needed // 1024} GB. "
                f"Mining könnte instabil sein."
            )
            result["severity"] = "warning"
            
        else:
            result["status"] = "INSUFFICIENT"
            result["action_needed"] = True
            result["recommendation"] = (
                f"KRITISCH: Nur {current // 1024} GB Pagefile, benötigt {needed // 1024} GB! "
                f"Mining wird wahrscheinlich fehlschlagen. Automatische Anpassung empfohlen."
            )
            result["severity"] = "critical"
        
        self._decision_log.append(result)
        return result
    
    def should_auto_fix(self, evaluation: Dict) -> bool:
        """Entscheidet ob automatisch behoben werden soll"""
        return evaluation["severity"] == "critical" and evaluation["action_needed"]
    
    def get_action_plan(self, evaluation: Dict) -> List[str]:
        """Generiert einen Aktionsplan basierend auf Evaluation"""
        plan = []
        
        if evaluation["status"] == "OK":
            plan.append("✅ Keine Aktion erforderlich")
            
        elif evaluation["status"] == "MARGINAL":
            plan.append("⚠️ Empfohlen: Pagefile erhöhen für stabileres Mining")
            plan.append(f"   → Ziel: {evaluation['requirements']['recommended_gb']} GB")
            plan.append("   → Kann im laufenden Betrieb problematisch werden")
            plan.append("   → Manueller Eingriff empfohlen")
            
        elif evaluation["status"] == "INSUFFICIENT":
            plan.append("🚨 KRITISCH: Sofortige Aktion erforderlich!")
            plan.append(f"   → Pagefile auf {evaluation['requirements']['recommended_gb']} GB erhöhen")
            plan.append("   → Automatische Anpassung wird durchgeführt")
            plan.append("   → PC-Neustart erforderlich")
            plan.append("   → Mining startet nach Neustart automatisch")
        
        return plan


# ============================================================================
# SINGLETON
# ============================================================================

_memory_manager: Optional[SystemMemoryManager] = None
_memory_ai: Optional[MiningMemoryAI] = None

def get_memory_manager() -> SystemMemoryManager:
    """Gibt Singleton-Instanz zurück"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = SystemMemoryManager()
    return _memory_manager

def get_memory_ai() -> MiningMemoryAI:
    """Gibt Singleton-Instanz zurück"""
    global _memory_ai
    if _memory_ai is None:
        _memory_ai = MiningMemoryAI(get_memory_manager())
    return _memory_ai


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=" * 70)
    print("💾 System Memory Manager Test")
    print("=" * 70)
    
    manager = get_memory_manager()
    ai = get_memory_ai()
    
    # System-Info
    print("\n" + manager.get_summary_string())
    
    # Test-Szenarios
    test_cases = [
        (1, ["RVN"]),
        (2, ["RVN", "ERG"]),
        (4, ["GRIN", "KAS", "ERG", "RVN"]),
        (6, ["ETC", "RVN", "ERG", "KAS", "FLUX", "BEAM"]),
    ]
    
    print("\n📊 Mining-Anforderungen:")
    for gpu_count, coins in test_cases:
        req = manager.calculate_mining_requirements(gpu_count, coins)
        print(f"\n  {gpu_count} GPUs, Coins: {coins}")
        print(f"    Min Pagefile: {req.min_pagefile_mb // 1024} GB")
        print(f"    Empfohlen: {req.recommended_pagefile_mb // 1024} GB")
    
    # AI Evaluation
    print("\n🤖 AI Evaluation (2 GPUs, RVN+ERG):")
    evaluation = ai.evaluate_situation(2, ["RVN", "ERG"])
    print(f"  Status: {evaluation['status']}")
    print(f"  Severity: {evaluation['severity']}")
    print(f"  Empfehlung: {evaluation['recommendation']}")
    
    print("\n📋 Aktionsplan:")
    for step in ai.get_action_plan(evaluation):
        print(f"  {step}")
    
    print("\n" + "=" * 70)
    print("✅ Test abgeschlossen!")
    print("=" * 70)
