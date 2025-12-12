#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flight Sheets System - Mining-Konfigurationen wie HiveOS
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- One-Click Mining-Konfigurationen
- Coin + Pool + Wallet + Miner Kombinationen
- Import/Export von Flight Sheets
- Vorlagen für gängige Coins
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


# Algorithmus-Mapping
COIN_ALGORITHMS = {
    "RVN": "kawpow",
    "ERG": "autolykos2",
    "FLUX": "equihash125",
    "ETC": "etchash",
    "KASPA": "kheavyhash",
    "KAS": "kheavyhash",
    "NEXA": "nexapow",
    "ALPH": "blake3",
    "ZEPH": "randomx",
    "XMR": "randomx",  # CPU Mining!
    "CLORE": "kawpow",
    "DNX": "dynexsolve",
    "CFX": "octopus",
    "FIRO": "firopow",
    "RXD": "sha512256d",
    "XNA": "kawpow",
    "BTG": "equihash144",
    "BEAM": "beamhash3",
    "KLS": "karlsenhash",
}

# Pool-Vorlagen
DEFAULT_POOLS = {
    "RVN": [
        {"name": "2miners", "url": "stratum+tcp://rvn.2miners.com:6060"},
        {"name": "Flypool", "url": "stratum+tcp://stratum-ravencoin.flypool.org:3333"},
        {"name": "HeroMiners", "url": "stratum+tcp://rvn.herominers.com:1140"},
    ],
    "ERG": [
        {"name": "2miners", "url": "stratum+tcp://erg.2miners.com:8888"},
        {"name": "HeroMiners", "url": "stratum+tcp://ergo.herominers.com:1180"},
        {"name": "Nanopool", "url": "stratum+tcp://ergo-eu1.nanopool.org:11111"},
    ],
    "FLUX": [
        {"name": "2miners", "url": "stratum+tcp://flux.2miners.com:9090"},
        {"name": "Flexpool", "url": "stratum+tcp://flux-eu.flexpool.io:4400"},
        {"name": "HeroMiners", "url": "stratum+tcp://flux.herominers.com:1200"},
    ],
    "ETC": [
        {"name": "2miners", "url": "stratum+tcp://etc.2miners.com:1010"},
        {"name": "Ethermine", "url": "stratum+tcp://eu1-etc.ethermine.org:4444"},
        {"name": "F2Pool", "url": "stratum+tcp://etc.f2pool.com:8118"},
    ],
    "KASPA": [
        {"name": "Acc-pool", "url": "stratum+tcp://de.kaspa.acc-pool.pw:16061"},
        {"name": "HeroMiners", "url": "stratum+tcp://kaspa.herominers.com:1206"},
        {"name": "K1Pool", "url": "stratum+tcp://kas.k1pool.com:7772"},
    ],
    "XMR": [
        {"name": "2miners", "url": "stratum+tcp://xmr.2miners.com:2222"},
        {"name": "MoneroOcean", "url": "stratum+tcp://gulf.moneroocean.stream:10128"},
        {"name": "P2Pool", "url": "stratum+tcp://p2pool.io:3333"},
        {"name": "HeroMiners", "url": "stratum+tcp://monero.herominers.com:1111"},
        {"name": "SupportXMR", "url": "stratum+tcp://pool.supportxmr.com:3333"},
    ],
    "ZEPH": [
        {"name": "HeroMiners", "url": "stratum+tcp://zephyr.herominers.com:1123"},
        {"name": "K1Pool", "url": "stratum+tcp://zeph.k1pool.com:7800"},
    ],
}

# Miner-Kompatibilität
MINER_ALGORITHMS = {
    "trex": ["kawpow", "etchash", "autolykos2", "blake3", "kheavyhash", "octopus", "firopow"],
    "nbminer": ["kawpow", "etchash", "autolykos2", "kheavyhash"],
    "gminer": ["kawpow", "etchash", "autolykos2", "equihash125", "kheavyhash", "blake3"],
    "lolminer": ["etchash", "autolykos2", "equihash125", "kheavyhash", "beamhash3", "nexapow"],
    "teamredminer": ["kawpow", "etchash", "autolykos2", "kheavyhash"],
    "phoenixminer": ["etchash"],
    "rigel": ["kawpow", "etchash", "autolykos2", "kheavyhash", "sha512256d", "nexapow"],
    "bzminer": ["kawpow", "etchash", "autolykos2", "kheavyhash", "blake3", "sha512256d", "dynexsolve"],
    "srbminer": ["kawpow", "etchash", "autolykos2", "kheavyhash", "blake3", "randomx"],
    "xmrig": ["randomx", "ghostrider", "cn-heavy"],  # CPU Miner!
}


@dataclass
class FlightSheet:
    """Ein Flight Sheet (Mining-Konfiguration)"""
    id: str
    name: str
    coin: str
    algorithm: str
    wallet: str
    pool_url: str
    pool_name: str = ""
    pool_backup: str = ""
    miner: str = "trex"
    worker_name: str = "rig"
    password: str = "x"
    extra_args: str = ""
    oc_profile: str = ""  # Name des OC-Profils
    enabled_gpus: List[int] = field(default_factory=list)  # Leer = alle GPUs
    mining_type: str = "gpu"  # "gpu" oder "cpu"
    created: str = ""
    modified: str = ""
    notes: str = ""
    
    def __post_init__(self):
        if not self.created:
            self.created = time.strftime('%Y-%m-%d %H:%M:%S')
        if not self.algorithm and self.coin:
            self.algorithm = COIN_ALGORITHMS.get(self.coin.upper(), "")
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlightSheet':
        """Erstellt FlightSheet aus Dict, ignoriert unbekannte Felder"""
        from dataclasses import fields as dc_fields
        # Nur bekannte Felder übernehmen
        valid_fields = {f.name for f in dc_fields(cls)}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
        return cls(**filtered_data)
    
    def get_compatible_miners(self) -> List[str]:
        """Gibt kompatible Miner für diesen Algorithmus zurück"""
        compatible = []
        for miner, algos in MINER_ALGORITHMS.items():
            if self.algorithm in algos:
                compatible.append(miner)
        return compatible


class FlightSheetManager:
    """
    Verwaltet Flight Sheets.
    
    Verwendung:
        manager = FlightSheetManager("flight_sheets.json")
        
        # Flight Sheet erstellen
        fs = FlightSheet(
            id="fs_rvn_1",
            name="RVN Mining",
            coin="RVN",
            wallet="RKsY5ySY...",
            pool_url="stratum+tcp://rvn.2miners.com:6060",
            miner="trex"
        )
        manager.add(fs)
        
        # Alle auflisten
        for fs in manager.list_all():
            print(fs.name)
        
        # Anwenden
        manager.apply("fs_rvn_1", miner_manager, oc_manager)
    """
    
    def __init__(self, storage_path: str = "flight_sheets.json"):
        """
        Initialisiert den Flight Sheet Manager.
        
        Args:
            storage_path: Pfad zur JSON-Datei
        """
        self.storage_path = Path(storage_path)
        self._sheets: Dict[str, FlightSheet] = {}
        self._active_id: Optional[str] = None
        
        self._load()
    
    def _load(self):
        """Lädt Flight Sheets aus Datei"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._sheets = {
                    sheet_id: FlightSheet.from_dict(sheet_data)
                    for sheet_id, sheet_data in data.get('sheets', {}).items()
                }
                self._active_id = data.get('active')
                
                logger.info(f"Geladen: {len(self._sheets)} Flight Sheets")
            except Exception as e:
                logger.error(f"Fehler beim Laden: {e}")
    
    def _save(self):
        """Speichert Flight Sheets"""
        try:
            data = {
                'sheets': {
                    sheet_id: sheet.to_dict()
                    for sheet_id, sheet in self._sheets.items()
                },
                'active': self._active_id,
                'updated': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Gespeichert: {len(self._sheets)} Flight Sheets")
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
    
    def add(self, sheet: FlightSheet) -> bool:
        """
        Fügt ein Flight Sheet hinzu.
        
        Args:
            sheet: FlightSheet Objekt
            
        Returns:
            True wenn erfolgreich
        """
        if not sheet.id:
            sheet.id = f"fs_{sheet.coin.lower()}_{int(time.time())}"
        
        self._sheets[sheet.id] = sheet
        self._save()
        logger.info(f"Flight Sheet hinzugefügt: {sheet.name}")
        return True
    
    def update(self, sheet_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aktualisiert ein Flight Sheet.
        
        Args:
            sheet_id: ID des Flight Sheets
            updates: Dict mit zu aktualisierenden Feldern
            
        Returns:
            True wenn erfolgreich
        """
        if sheet_id not in self._sheets:
            logger.error(f"Flight Sheet nicht gefunden: {sheet_id}")
            return False
        
        sheet = self._sheets[sheet_id]
        
        for key, value in updates.items():
            if hasattr(sheet, key):
                setattr(sheet, key, value)
        
        sheet.modified = time.strftime('%Y-%m-%d %H:%M:%S')
        self._save()
        
        logger.info(f"Flight Sheet aktualisiert: {sheet.name}")
        return True
    
    def delete(self, sheet_id: str) -> bool:
        """
        Löscht ein Flight Sheet.
        
        Args:
            sheet_id: ID des Flight Sheets
            
        Returns:
            True wenn erfolgreich
        """
        if sheet_id not in self._sheets:
            return False
        
        name = self._sheets[sheet_id].name
        del self._sheets[sheet_id]
        
        if self._active_id == sheet_id:
            self._active_id = None
        
        self._save()
        logger.info(f"Flight Sheet gelöscht: {name}")
        return True
    
    def get(self, sheet_id: str) -> Optional[FlightSheet]:
        """Gibt ein Flight Sheet zurück"""
        return self._sheets.get(sheet_id)
    
    def get_by_coin(self, coin: str) -> List[FlightSheet]:
        """Gibt alle Flight Sheets für einen Coin zurück"""
        return [
            sheet for sheet in self._sheets.values()
            if sheet.coin.upper() == coin.upper()
        ]
    
    def list_all(self) -> List[FlightSheet]:
        """Gibt alle Flight Sheets zurück"""
        return list(self._sheets.values())
    
    def get_active(self) -> Optional[FlightSheet]:
        """Gibt das aktive Flight Sheet zurück"""
        if self._active_id:
            return self._sheets.get(self._active_id)
        return None
    
    def set_active(self, sheet_id: str) -> bool:
        """Setzt ein Flight Sheet als aktiv"""
        if sheet_id not in self._sheets:
            return False
        
        self._active_id = sheet_id
        self._save()
        return True
    
    def apply(
        self, 
        sheet_id: str, 
        miner_manager, 
        oc_manager = None,
        auto_oc: bool = True
    ) -> bool:
        """
        Wendet ein Flight Sheet an (startet Mining).
        
        Args:
            sheet_id: ID des Flight Sheets
            miner_manager: MinerManager Instanz
            oc_manager: OverclockManager Instanz (optional)
            auto_oc: Automatisches Overclocking anwenden
            
        Returns:
            True wenn erfolgreich
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            logger.error(f"Flight Sheet nicht gefunden: {sheet_id}")
            return False
        
        logger.info(f"Wende Flight Sheet an: {sheet.name}")
        
        # Overclocking (wenn verfügbar und gewünscht)
        if oc_manager and auto_oc:
            try:
                if sheet.oc_profile:
                    # Benutzerdefiniertes Profil
                    oc_manager.apply_custom_profile(0, sheet.oc_profile)  # TODO: Alle GPUs
                else:
                    # Auto-OC basierend auf Coin
                    oc_manager.apply_auto_oc_all(sheet.coin)
                logger.info(f"Overclocking angewendet für {sheet.coin}")
            except Exception as e:
                logger.warning(f"Overclocking fehlgeschlagen: {e}")
        
        # Miner-Typ bestimmen
        from miner_api import MinerType
        miner_type_map = {
            "trex": MinerType.TREX,
            "nbminer": MinerType.NBMINER,
            "gminer": MinerType.GMINER,
            "lolminer": MinerType.LOLMINER,
            "teamredminer": MinerType.TEAMREDMINER,
            "phoenixminer": MinerType.PHOENIXMINER,
        }
        
        miner_type = miner_type_map.get(sheet.miner.lower())
        if not miner_type:
            logger.error(f"Unbekannter Miner: {sheet.miner}")
            return False
        
        # Extra-Args parsen
        extra_args = sheet.extra_args.split() if sheet.extra_args else None
        
        # Miner starten
        success = miner_manager.start_miner(
            miner_type=miner_type,
            algorithm=sheet.algorithm,
            pool_url=sheet.pool_url,
            wallet=sheet.wallet,
            worker=sheet.worker_name,
            extra_args=extra_args
        )
        
        if success:
            self._active_id = sheet_id
            self._save()
            logger.info(f"Mining gestartet: {sheet.coin} auf {sheet.pool_name or sheet.pool_url}")
        
        return success
    
    def stop(self, miner_manager) -> bool:
        """Stoppt das aktive Mining"""
        self._active_id = None
        self._save()
        return miner_manager.stop_current()
    
    def create_from_template(
        self,
        coin: str,
        wallet: str,
        name: str = "",
        pool_index: int = 0,
        miner: str = "trex",
        worker_name: str = "rig"
    ) -> Optional[FlightSheet]:
        """
        Erstellt ein Flight Sheet aus einer Vorlage.
        
        Args:
            coin: Coin-Symbol (z.B. "RVN")
            wallet: Wallet-Adresse
            name: Name des Flight Sheets
            pool_index: Index des Pools (0 = erster/default)
            miner: Miner-Name
            worker_name: Worker-Name
            
        Returns:
            FlightSheet oder None
        """
        coin = coin.upper()
        
        if coin not in DEFAULT_POOLS:
            logger.error(f"Keine Pool-Vorlage für {coin}")
            return None
        
        pools = DEFAULT_POOLS[coin]
        if pool_index >= len(pools):
            pool_index = 0
        
        pool = pools[pool_index]
        algorithm = COIN_ALGORITHMS.get(coin, "")
        
        if not algorithm:
            logger.error(f"Kein Algorithmus für {coin}")
            return None
        
        # Kompatiblen Miner wählen
        compatible = [m for m, algos in MINER_ALGORITHMS.items() if algorithm in algos]
        if miner not in compatible:
            miner = compatible[0] if compatible else "trex"
        
        sheet = FlightSheet(
            id=f"fs_{coin.lower()}_{int(time.time())}",
            name=name or f"{coin} Mining - {pool['name']}",
            coin=coin,
            algorithm=algorithm,
            wallet=wallet,
            pool_url=pool['url'],
            pool_name=pool['name'],
            miner=miner,
            worker_name=worker_name,
        )
        
        # Backup-Pool setzen
        if len(pools) > 1:
            backup_index = 1 if pool_index == 0 else 0
            sheet.pool_backup = pools[backup_index]['url']
        
        return sheet
    
    def export_sheet(self, sheet_id: str) -> Optional[str]:
        """Exportiert ein Flight Sheet als JSON-String"""
        sheet = self._sheets.get(sheet_id)
        if sheet:
            return json.dumps(sheet.to_dict(), indent=2)
        return None
    
    def import_sheet(self, json_data: str) -> Optional[FlightSheet]:
        """Importiert ein Flight Sheet aus JSON"""
        try:
            data = json.loads(json_data)
            sheet = FlightSheet.from_dict(data)
            
            # Neue ID generieren um Duplikate zu vermeiden
            sheet.id = f"fs_imported_{int(time.time())}"
            sheet.name = f"{sheet.name} (importiert)"
            
            self.add(sheet)
            return sheet
        except Exception as e:
            logger.error(f"Import fehlgeschlagen: {e}")
            return None
    
    @staticmethod
    def get_available_coins() -> List[str]:
        """Gibt alle verfügbaren Coins zurück"""
        return list(DEFAULT_POOLS.keys())
    
    @staticmethod
    def get_pools_for_coin(coin: str) -> List[Dict[str, str]]:
        """Gibt verfügbare Pools für einen Coin zurück"""
        return DEFAULT_POOLS.get(coin.upper(), [])
    
    @staticmethod
    def get_compatible_miners(algorithm: str) -> List[str]:
        """Gibt kompatible Miner für einen Algorithmus zurück"""
        return [
            miner for miner, algos in MINER_ALGORITHMS.items()
            if algorithm in algos
        ]


# Standalone Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Flight Sheet Manager Test")
    print("=" * 60)
    
    manager = FlightSheetManager("test_flight_sheets.json")
    
    # Verfügbare Coins
    print("\n📊 Verfügbare Coins:")
    for coin in manager.get_available_coins():
        pools = manager.get_pools_for_coin(coin)
        algo = COIN_ALGORITHMS.get(coin, "?")
        miners = manager.get_compatible_miners(algo)
        print(f"   {coin} ({algo})")
        print(f"      Pools: {[p['name'] for p in pools]}")
        print(f"      Miner: {miners}")
    
    # Flight Sheet aus Vorlage erstellen
    print("\n📝 Erstelle Flight Sheet aus Vorlage:")
    fs = manager.create_from_template(
        coin="RVN",
        wallet="RKsY5ySY3A1DaGjruhFpYbsaGGNbXGMfXe",
        worker_name="Rig_D"
    )
    
    if fs:
        print(f"   Name: {fs.name}")
        print(f"   Coin: {fs.coin}")
        print(f"   Pool: {fs.pool_name} ({fs.pool_url})")
        print(f"   Miner: {fs.miner}")
        print(f"   Algorithm: {fs.algorithm}")
        manager.add(fs)
    
    # Alle auflisten
    print("\n📋 Alle Flight Sheets:")
    for sheet in manager.list_all():
        print(f"   [{sheet.id}] {sheet.name} - {sheet.coin}")
    
    # Aufräumen
    import os
    if os.path.exists("test_flight_sheets.json"):
        os.remove("test_flight_sheets.json")
    
    print("\n✅ Test beendet")
