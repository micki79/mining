#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Auto-Optimizer - Automatisches Temperatur & Leistungs-Management
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Echtzeit Temperatur-Überwachung
- Automatische OC-Anpassung bei Überhitzung
- Effizienz-Optimierung (Hash pro Watt)
- Auto-Tuning für optimale Performance
- Multi-GPU Support
"""

import json
import logging
import time
import threading
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import statistics

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS & DATACLASSES
# ============================================================================

class ThermalState(Enum):
    """Thermischer Zustand der GPU"""
    COLD = "cold"           # < 50°C - Kann mehr!
    COOL = "cool"           # 50-60°C - Optimal für HIGH
    OPTIMAL = "optimal"     # 60-70°C - Perfekt für MEDIUM
    WARM = "warm"           # 70-80°C - Sollte runter
    HOT = "hot"             # 80-85°C - Muss runter!
    CRITICAL = "critical"   # > 85°C - NOTFALL!


class PerformanceMode(Enum):
    """Performance-Modus"""
    EFFICIENCY = "efficiency"   # Beste Hash/Watt
    BALANCED = "balanced"       # Balance aus Hash und Temp
    PERFORMANCE = "performance" # Maximale Hashrate


@dataclass
class GPUState:
    """Aktueller Zustand einer GPU"""
    index: int
    name: str
    temperature: int = 0
    fan_speed: int = 0
    power_draw: int = 0
    power_limit: int = 100
    core_clock: int = 0
    mem_clock: int = 0
    hashrate: float = 0.0
    hashrate_unit: str = "MH/s"
    efficiency: float = 0.0  # Hash pro Watt
    thermal_state: ThermalState = ThermalState.OPTIMAL
    current_coin: str = ""
    current_profile: str = "medium"
    last_update: datetime = field(default_factory=datetime.now)


@dataclass
class OptimizationResult:
    """Ergebnis einer Optimierung"""
    gpu_index: int
    action: str  # "increase", "decrease", "maintain", "emergency"
    old_profile: str
    new_profile: str
    reason: str
    temp_before: int
    temp_target: int
    hashrate_change: float = 0.0


@dataclass
class BenchmarkResult:
    """Ergebnis eines Benchmarks"""
    gpu_index: int
    coin: str
    algorithm: str
    profile: str
    hashrate: float
    hashrate_unit: str
    power_draw: int
    temperature: int
    efficiency: float  # Hash/Watt
    duration_seconds: int
    timestamp: str
    stable: bool = True


# ============================================================================
# TEMPERATUR-GRENZEN
# ============================================================================

THERMAL_LIMITS = {
    # GPU-Typ: (target, max_safe, critical)
    "default": (68, 80, 85),
    "laptop": (70, 83, 88),
    "desktop": (65, 78, 83),
    "3090": (70, 83, 90),  # 3090 läuft heißer
    "4090": (65, 78, 85),
}

def get_thermal_limits(gpu_name: str) -> Tuple[int, int, int]:
    """Gibt Temperatur-Grenzen für eine GPU zurück"""
    gpu_lower = gpu_name.lower()
    
    if "laptop" in gpu_lower:
        return THERMAL_LIMITS["laptop"]
    elif "3090" in gpu_lower:
        return THERMAL_LIMITS["3090"]
    elif "4090" in gpu_lower:
        return THERMAL_LIMITS["4090"]
    else:
        return THERMAL_LIMITS["desktop"]


# ============================================================================
# GPU AUTO-OPTIMIZER
# ============================================================================

class GPUAutoOptimizer:
    """
    Automatische GPU-Optimierung für Mining
    
    Features:
    - Echtzeit-Temperatur-Management
    - Automatische OC-Anpassung
    - Effizienz-Tracking
    - Auto-Benchmark
    """
    
    def __init__(self, 
                 update_interval: float = 5.0,
                 config_path: str = "gpu_optimizer_config.json"):
        
        self.update_interval = update_interval
        self.config_path = Path(config_path)
        
        # GPU States
        self.gpu_states: Dict[int, GPUState] = {}
        
        # Performance Mode pro GPU
        self.performance_modes: Dict[int, PerformanceMode] = {}
        
        # Benchmark History
        self.benchmark_history: Dict[str, List[BenchmarkResult]] = {}
        
        # Temperatur-Historie für Trend-Analyse
        self.temp_history: Dict[int, List[Tuple[datetime, int]]] = {}
        self.temp_history_max = 60  # Letzte 60 Messungen
        
        # Hashrate-Historie für Stabilität
        self.hashrate_history: Dict[int, List[float]] = {}
        self.hashrate_history_max = 20
        
        # Callbacks
        self.on_profile_change: Optional[Callable] = None
        self.on_thermal_warning: Optional[Callable] = None
        self.on_optimization: Optional[Callable] = None
        
        # Monitoring Thread
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Cooldown für Profile-Wechsel (verhindert Ping-Pong)
        self._last_profile_change: Dict[int, datetime] = {}
        self._profile_cooldown = 30  # Sekunden
        
        self._load_config()
    
    def _load_config(self):
        """Lädt Konfiguration"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    # Performance Modes laden
                    for idx_str, mode in data.get("performance_modes", {}).items():
                        self.performance_modes[int(idx_str)] = PerformanceMode(mode)
                    # Benchmark History laden
                    self.benchmark_history = data.get("benchmark_history", {})
            except Exception as e:
                logger.error(f"Config laden fehlgeschlagen: {e}")
    
    def _save_config(self):
        """Speichert Konfiguration"""
        try:
            data = {
                "performance_modes": {str(k): v.value for k, v in self.performance_modes.items()},
                "benchmark_history": self.benchmark_history,
                "last_saved": datetime.now().isoformat()
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Config speichern fehlgeschlagen: {e}")
    
    # =========================================================================
    # GPU MONITORING
    # =========================================================================
    
    def update_gpu_state(self, gpu_index: int, 
                         temperature: int, 
                         power_draw: int,
                         hashrate: float,
                         hashrate_unit: str = "MH/s",
                         fan_speed: int = 0,
                         core_clock: int = 0,
                         mem_clock: int = 0,
                         current_coin: str = "",
                         gpu_name: str = ""):
        """
        Aktualisiert den Zustand einer GPU
        """
        # State erstellen/aktualisieren
        if gpu_index not in self.gpu_states:
            self.gpu_states[gpu_index] = GPUState(
                index=gpu_index,
                name=gpu_name or f"GPU {gpu_index}"
            )
        
        state = self.gpu_states[gpu_index]
        state.temperature = temperature
        state.power_draw = power_draw
        state.hashrate = hashrate
        state.hashrate_unit = hashrate_unit
        state.fan_speed = fan_speed
        state.core_clock = core_clock
        state.mem_clock = mem_clock
        state.current_coin = current_coin
        state.last_update = datetime.now()
        
        # Effizienz berechnen
        if power_draw > 0:
            state.efficiency = hashrate / power_draw
        
        # Thermal State bestimmen
        state.thermal_state = self._get_thermal_state(gpu_index, temperature)
        
        # History aktualisieren
        self._update_temp_history(gpu_index, temperature)
        self._update_hashrate_history(gpu_index, hashrate)
        
        return state
    
    def _get_thermal_state(self, gpu_index: int, temp: int) -> ThermalState:
        """Bestimmt den thermischen Zustand"""
        gpu_name = self.gpu_states.get(gpu_index, GPUState(0, "")).name
        target, max_safe, critical = get_thermal_limits(gpu_name)
        
        if temp >= critical:
            return ThermalState.CRITICAL
        elif temp >= max_safe:
            return ThermalState.HOT
        elif temp >= target + 5:
            return ThermalState.WARM
        elif temp >= target - 10:
            return ThermalState.OPTIMAL
        elif temp >= 50:
            return ThermalState.COOL
        else:
            return ThermalState.COLD
    
    def _update_temp_history(self, gpu_index: int, temp: int):
        """Aktualisiert Temperatur-Historie"""
        if gpu_index not in self.temp_history:
            self.temp_history[gpu_index] = []
        
        self.temp_history[gpu_index].append((datetime.now(), temp))
        
        # Auf max Größe begrenzen
        if len(self.temp_history[gpu_index]) > self.temp_history_max:
            self.temp_history[gpu_index] = self.temp_history[gpu_index][-self.temp_history_max:]
    
    def _update_hashrate_history(self, gpu_index: int, hashrate: float):
        """Aktualisiert Hashrate-Historie"""
        if gpu_index not in self.hashrate_history:
            self.hashrate_history[gpu_index] = []
        
        self.hashrate_history[gpu_index].append(hashrate)
        
        if len(self.hashrate_history[gpu_index]) > self.hashrate_history_max:
            self.hashrate_history[gpu_index] = self.hashrate_history[gpu_index][-self.hashrate_history_max:]
    
    # =========================================================================
    # TEMPERATUR-ANALYSE
    # =========================================================================
    
    def get_temp_trend(self, gpu_index: int) -> str:
        """
        Analysiert Temperatur-Trend
        
        Returns:
            "rising", "falling", "stable"
        """
        if gpu_index not in self.temp_history:
            return "stable"
        
        history = self.temp_history[gpu_index]
        if len(history) < 5:
            return "stable"
        
        # Letzte 5 vs vorherige 5 Messungen
        recent = [t for _, t in history[-5:]]
        previous = [t for _, t in history[-10:-5]] if len(history) >= 10 else recent
        
        avg_recent = statistics.mean(recent)
        avg_previous = statistics.mean(previous)
        
        diff = avg_recent - avg_previous
        
        if diff > 3:
            return "rising"
        elif diff < -3:
            return "falling"
        else:
            return "stable"
    
    def get_hashrate_stability(self, gpu_index: int) -> float:
        """
        Berechnet Hashrate-Stabilität (0-100%)
        
        100% = perfekt stabil
        0% = sehr instabil
        """
        if gpu_index not in self.hashrate_history:
            return 100.0
        
        history = self.hashrate_history[gpu_index]
        if len(history) < 3:
            return 100.0
        
        # Coefficient of Variation (CV)
        mean = statistics.mean(history)
        if mean == 0:
            return 100.0
        
        stdev = statistics.stdev(history) if len(history) > 1 else 0
        cv = (stdev / mean) * 100
        
        # CV in Stabilität umrechnen (0-5% CV = 100% stabil)
        stability = max(0, 100 - (cv * 20))
        return round(stability, 1)
    
    # =========================================================================
    # AUTOMATISCHE OPTIMIERUNG
    # =========================================================================
    
    def optimize(self, gpu_index: int) -> Optional[OptimizationResult]:
        """
        Führt automatische Optimierung für eine GPU durch
        
        Returns:
            OptimizationResult oder None wenn keine Änderung nötig
        """
        if gpu_index not in self.gpu_states:
            return None
        
        state = self.gpu_states[gpu_index]
        mode = self.performance_modes.get(gpu_index, PerformanceMode.BALANCED)
        
        # Cooldown prüfen
        if gpu_index in self._last_profile_change:
            since_change = (datetime.now() - self._last_profile_change[gpu_index]).seconds
            if since_change < self._profile_cooldown:
                return None  # Noch in Cooldown
        
        # Aktuelle Werte
        temp = state.temperature
        thermal = state.thermal_state
        trend = self.get_temp_trend(gpu_index)
        stability = self.get_hashrate_stability(gpu_index)
        current_profile = state.current_profile
        
        # Ziel-Temperatur
        gpu_name = state.name
        target_temp, max_safe, critical = get_thermal_limits(gpu_name)
        
        # Entscheidungslogik
        new_profile = current_profile
        action = "maintain"
        reason = ""
        
        # KRITISCH - Sofort runter!
        if thermal == ThermalState.CRITICAL:
            new_profile = "low"
            action = "emergency"
            reason = f"KRITISCH! {temp}°C >= {critical}°C"
            logger.warning(f"GPU {gpu_index}: {reason}")
            
            if self.on_thermal_warning:
                self.on_thermal_warning(gpu_index, temp, "critical")
        
        # ZU HEISS - Runterschalten
        elif thermal == ThermalState.HOT:
            if current_profile == "high":
                new_profile = "medium"
                action = "decrease"
                reason = f"Zu heiß ({temp}°C >= {max_safe}°C) - High→Medium"
            elif current_profile == "medium":
                new_profile = "low"
                action = "decrease"
                reason = f"Immer noch heiß ({temp}°C) - Medium→Low"
            
            if self.on_thermal_warning:
                self.on_thermal_warning(gpu_index, temp, "hot")
        
        # WARM - Eventuell runter
        elif thermal == ThermalState.WARM:
            if trend == "rising" and current_profile != "low":
                # Temperatur steigt noch
                if current_profile == "high":
                    new_profile = "medium"
                    action = "decrease"
                    reason = f"Temp steigt ({temp}°C, Trend: ↑) - High→Medium"
        
        # OPTIMAL - Perfekt
        elif thermal == ThermalState.OPTIMAL:
            # Hier bleiben wir, außer wir sind auf LOW und könnten hoch
            if mode == PerformanceMode.PERFORMANCE:
                if current_profile == "low" and trend != "rising":
                    new_profile = "medium"
                    action = "increase"
                    reason = f"Temp OK ({temp}°C), Performance-Mode - Low→Medium"
        
        # KÜHL - Können hochschalten
        elif thermal in [ThermalState.COOL, ThermalState.COLD]:
            if mode == PerformanceMode.PERFORMANCE:
                if current_profile == "low":
                    new_profile = "medium"
                    action = "increase"
                    reason = f"Kühl ({temp}°C), kann mehr - Low→Medium"
                elif current_profile == "medium" and thermal == ThermalState.COLD:
                    new_profile = "high"
                    action = "increase"
                    reason = f"Sehr kühl ({temp}°C), maximiere - Medium→High"
            
            elif mode == PerformanceMode.BALANCED:
                if current_profile == "low" and stability > 95:
                    new_profile = "medium"
                    action = "increase"
                    reason = f"Kühl & stabil ({temp}°C, {stability}%) - Low→Medium"
        
        # Effizienz-Modus: Immer auf Low bleiben
        if mode == PerformanceMode.EFFICIENCY:
            if new_profile != "low":
                new_profile = "low"
                action = "efficiency"
                reason = "Effizienz-Modus aktiv - bleibe auf Low"
        
        # Keine Änderung nötig
        if new_profile == current_profile:
            return None
        
        # Änderung durchführen
        result = OptimizationResult(
            gpu_index=gpu_index,
            action=action,
            old_profile=current_profile,
            new_profile=new_profile,
            reason=reason,
            temp_before=temp,
            temp_target=target_temp
        )
        
        # State aktualisieren
        state.current_profile = new_profile
        self._last_profile_change[gpu_index] = datetime.now()
        
        logger.info(f"GPU {gpu_index}: {current_profile} → {new_profile} ({reason})")
        
        # Callback
        if self.on_profile_change:
            self.on_profile_change(gpu_index, current_profile, new_profile)
        
        if self.on_optimization:
            self.on_optimization(result)
        
        return result
    
    def optimize_all(self) -> List[OptimizationResult]:
        """Optimiert alle GPUs"""
        results = []
        for gpu_index in self.gpu_states:
            result = self.optimize(gpu_index)
            if result:
                results.append(result)
        return results
    
    # =========================================================================
    # EFFIZIENZ-BERECHNUNG
    # =========================================================================
    
    def get_efficiency_ranking(self) -> List[Dict]:
        """
        Gibt Ranking aller GPUs nach Effizienz zurück
        
        Returns:
            Liste sortiert nach Hash/Watt
        """
        ranking = []
        
        for idx, state in self.gpu_states.items():
            if state.power_draw > 0:
                ranking.append({
                    "gpu_index": idx,
                    "name": state.name,
                    "hashrate": state.hashrate,
                    "hashrate_unit": state.hashrate_unit,
                    "power": state.power_draw,
                    "efficiency": state.efficiency,
                    "temperature": state.temperature,
                    "profile": state.current_profile,
                    "coin": state.current_coin
                })
        
        ranking.sort(key=lambda x: x["efficiency"], reverse=True)
        return ranking
    
    def get_optimal_profile_for_efficiency(self, gpu_index: int, coin: str) -> str:
        """
        Findet das effizienteste Profile für einen Coin
        
        Basierend auf Benchmark-History
        """
        key = f"{gpu_index}_{coin}"
        
        if key not in self.benchmark_history:
            return "medium"  # Default
        
        benchmarks = self.benchmark_history[key]
        if not benchmarks:
            return "medium"
        
        # Finde bestes Hash/Watt Verhältnis
        best = max(benchmarks, key=lambda b: b.get("efficiency", 0))
        return best.get("profile", "medium")
    
    # =========================================================================
    # AUTO-BENCHMARK
    # =========================================================================
    
    def run_auto_benchmark(self, gpu_index: int, coin: str, 
                           miner_controller=None,
                           duration_per_profile: int = 60) -> List[BenchmarkResult]:
        """
        Führt automatischen Benchmark für alle Profile durch
        
        Args:
            gpu_index: GPU Index
            coin: Coin zu benchmarken
            miner_controller: Controller um Miner zu steuern
            duration_per_profile: Sekunden pro Profile
            
        Returns:
            Liste mit Benchmark-Ergebnissen für Low/Medium/High
        """
        results = []
        profiles = ["low", "medium", "high"]
        
        logger.info(f"GPU {gpu_index}: Starte Auto-Benchmark für {coin}")
        
        for profile in profiles:
            logger.info(f"  Testing {profile.upper()} profile...")
            
            # Profile setzen (hier müsste der OC-Manager aufgerufen werden)
            if miner_controller:
                # miner_controller.apply_oc_profile(gpu_index, coin, profile)
                pass
            
            # Warten bis stabil
            time.sleep(10)
            
            # Messen über duration_per_profile Sekunden
            measurements = []
            power_measurements = []
            temp_measurements = []
            
            start = time.time()
            while time.time() - start < duration_per_profile:
                if gpu_index in self.gpu_states:
                    state = self.gpu_states[gpu_index]
                    measurements.append(state.hashrate)
                    power_measurements.append(state.power_draw)
                    temp_measurements.append(state.temperature)
                time.sleep(5)
            
            if measurements:
                avg_hashrate = statistics.mean(measurements)
                avg_power = statistics.mean(power_measurements) if power_measurements else 100
                avg_temp = int(statistics.mean(temp_measurements)) if temp_measurements else 65
                
                # Stabilität prüfen
                stability = self.get_hashrate_stability(gpu_index)
                stable = stability > 90
                
                result = BenchmarkResult(
                    gpu_index=gpu_index,
                    coin=coin,
                    algorithm="",  # TODO: von Coin ableiten
                    profile=profile,
                    hashrate=round(avg_hashrate, 2),
                    hashrate_unit=self.gpu_states[gpu_index].hashrate_unit if gpu_index in self.gpu_states else "MH/s",
                    power_draw=int(avg_power),
                    temperature=avg_temp,
                    efficiency=round(avg_hashrate / avg_power, 4) if avg_power > 0 else 0,
                    duration_seconds=duration_per_profile,
                    timestamp=datetime.now().isoformat(),
                    stable=stable
                )
                
                results.append(result)
                logger.info(f"    {profile}: {avg_hashrate:.1f} @ {avg_power:.0f}W = {result.efficiency:.4f} eff")
        
        # Ergebnisse speichern
        key = f"{gpu_index}_{coin}"
        self.benchmark_history[key] = [
            {
                "profile": r.profile,
                "hashrate": r.hashrate,
                "power": r.power_draw,
                "temp": r.temperature,
                "efficiency": r.efficiency,
                "stable": r.stable,
                "timestamp": r.timestamp
            }
            for r in results
        ]
        self._save_config()
        
        # Bestes Profile empfehlen
        if results:
            best = max(results, key=lambda r: r.efficiency)
            logger.info(f"  EMPFEHLUNG: {best.profile.upper()} ({best.efficiency:.4f} Hash/W)")
        
        return results
    
    # =========================================================================
    # MONITORING THREAD
    # =========================================================================
    
    def start_monitoring(self):
        """Startet den Monitoring-Thread"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("GPU Auto-Optimizer Monitoring gestartet")
    
    def stop_monitoring(self):
        """Stoppt den Monitoring-Thread"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)
        logger.info("GPU Auto-Optimizer Monitoring gestoppt")
    
    def _monitor_loop(self):
        """Haupt-Monitoring-Schleife"""
        while self._running:
            try:
                # Alle GPUs optimieren
                results = self.optimize_all()
                
                # Kurze Pause
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Monitor-Fehler: {e}")
                time.sleep(1)
    
    # =========================================================================
    # PERFORMANCE MODE
    # =========================================================================
    
    def set_performance_mode(self, gpu_index: int, mode: PerformanceMode):
        """Setzt Performance-Modus für eine GPU"""
        self.performance_modes[gpu_index] = mode
        self._save_config()
        logger.info(f"GPU {gpu_index}: Performance-Modus auf {mode.value} gesetzt")
    
    def get_performance_mode(self, gpu_index: int) -> PerformanceMode:
        """Gibt aktuellen Performance-Modus zurück"""
        return self.performance_modes.get(gpu_index, PerformanceMode.BALANCED)
    
    # =========================================================================
    # REPORTS
    # =========================================================================
    
    def print_status_report(self):
        """Druckt Status-Report aller GPUs"""
        print("\n" + "="*80)
        print("GPU AUTO-OPTIMIZER STATUS")
        print("="*80)
        
        for idx, state in self.gpu_states.items():
            mode = self.performance_modes.get(idx, PerformanceMode.BALANCED)
            trend = self.get_temp_trend(idx)
            stability = self.get_hashrate_stability(idx)
            
            trend_icon = {"rising": "↑", "falling": "↓", "stable": "→"}[trend]
            thermal_icon = {
                ThermalState.COLD: "❄️",
                ThermalState.COOL: "🔵",
                ThermalState.OPTIMAL: "🟢",
                ThermalState.WARM: "🟡",
                ThermalState.HOT: "🟠",
                ThermalState.CRITICAL: "🔴"
            }[state.thermal_state]
            
            print(f"\n┌─ GPU {idx}: {state.name}")
            print(f"│  Coin: {state.current_coin or 'Idle'}")
            print(f"│  Profile: {state.current_profile.upper()} | Mode: {mode.value}")
            print(f"│")
            print(f"│  {thermal_icon} Temp: {state.temperature}°C {trend_icon} ({state.thermal_state.value})")
            print(f"│  ⚡ Power: {state.power_draw}W")
            print(f"│  💨 Fan: {state.fan_speed}%")
            print(f"│")
            print(f"│  📊 Hashrate: {state.hashrate:.2f} {state.hashrate_unit}")
            print(f"│  📈 Effizienz: {state.efficiency:.4f} {state.hashrate_unit}/W")
            print(f"│  📉 Stabilität: {stability:.1f}%")
            print(f"└─")
        
        print("\n" + "="*80)


# ============================================================================
# SINGLETON
# ============================================================================

_optimizer: Optional[GPUAutoOptimizer] = None

def get_gpu_optimizer() -> GPUAutoOptimizer:
    """Gibt die globale Optimizer-Instanz zurück"""
    global _optimizer
    if _optimizer is None:
        _optimizer = GPUAutoOptimizer()
    return _optimizer


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    optimizer = GPUAutoOptimizer()
    
    # Simuliere GPU-Updates
    print("Simuliere GPU-Monitoring...")
    
    # GPU 0: RTX 3080 Laptop - wird warm
    for temp in [55, 60, 65, 70, 73, 76, 78, 80, 82, 78, 75, 72, 70]:
        optimizer.update_gpu_state(
            gpu_index=0,
            gpu_name="NVIDIA GeForce RTX 3080 Laptop GPU",
            temperature=temp,
            power_draw=115,
            hashrate=32.0,
            current_coin="RVN"
        )
        
        # Optimierung durchführen
        result = optimizer.optimize(0)
        if result:
            print(f"  Temp {temp}°C: {result.old_profile} → {result.new_profile} ({result.reason})")
        else:
            state = optimizer.gpu_states[0]
            print(f"  Temp {temp}°C: Bleibe auf {state.current_profile} ({state.thermal_state.value})")
        
        time.sleep(0.1)
    
    # Status Report
    optimizer.print_status_report()
