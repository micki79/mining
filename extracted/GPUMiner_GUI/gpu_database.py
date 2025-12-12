#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Konfiguration - ALLE GPUs mit OC-Settings
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Datenquelle: hashrate.no Community-Benchmarks
"""

import json
import logging
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ============================================================================
# GPU OC PROFILE DATABASE
# ============================================================================

# Alle NVIDIA und AMD GPUs mit OC-Settings pro Algorithmus
# Format: gpu_name -> algorithm -> settings

GPU_OC_DATABASE = {
    # ==========================================================================
    # NVIDIA RTX 40 SERIES
    # ==========================================================================
    "RTX 4090": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 75, "fan": 75, "hash": 75.0,  "power": 320, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1500, "pl": 70, "fan": 70, "hash": 330.0, "power": 280, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1500, "pl": 65, "fan": 65, "hash": 135.0, "power": 250, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 1050.0,"power": 220, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 70, "hash": 5.5,   "power": 280, "unit": "GH/s"},
        "octopus":     {"core": -100,"mem": 1200, "pl": 70, "fan": 70, "hash": 130.0, "power": 290, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 80, "fan": 75, "hash": 125.0, "power": 310, "unit": "Sol/s"},
    },
    "RTX 4080 Super": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 75, "fan": 70, "hash": 58.0,  "power": 240, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1400, "pl": 70, "fan": 70, "hash": 270.0, "power": 220, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1400, "pl": 65, "fan": 65, "hash": 105.0, "power": 200, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 820.0, "power": 180, "unit": "MH/s"},
    },
    "RTX 4080": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 75, "fan": 70, "hash": 55.0,  "power": 230, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1400, "pl": 70, "fan": 70, "hash": 260.0, "power": 210, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1400, "pl": 65, "fan": 65, "hash": 100.0, "power": 195, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 780.0, "power": 175, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 70, "hash": 4.0,   "power": 210, "unit": "GH/s"},
        "octopus":     {"core": -100,"mem": 1200, "pl": 70, "fan": 70, "hash": 95.0,  "power": 220, "unit": "MH/s"},
    },
    "RTX 4070 Ti Super": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 80, "fan": 70, "hash": 48.0,  "power": 180, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1300, "pl": 70, "fan": 65, "hash": 220.0, "power": 160, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1300, "pl": 65, "fan": 65, "hash": 88.0,  "power": 150, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 680.0, "power": 140, "unit": "MH/s"},
    },
    "RTX 4070 Ti": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 80, "fan": 70, "hash": 45.0,  "power": 170, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1300, "pl": 70, "fan": 65, "hash": 205.0, "power": 155, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1300, "pl": 65, "fan": 65, "hash": 82.0,  "power": 145, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 640.0, "power": 135, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 70, "hash": 3.0,   "power": 160, "unit": "GH/s"},
    },
    "RTX 4070 Super": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 80, "fan": 68, "hash": 38.0,  "power": 145, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1200, "pl": 70, "fan": 65, "hash": 185.0, "power": 130, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1200, "pl": 65, "fan": 60, "hash": 72.0,  "power": 120, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 560.0, "power": 115, "unit": "MH/s"},
    },
    "RTX 4070": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 85, "fan": 65, "hash": 35.0,  "power": 130, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1200, "pl": 70, "fan": 65, "hash": 170.0, "power": 120, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1200, "pl": 65, "fan": 60, "hash": 68.0,  "power": 110, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 520.0, "power": 105, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 65, "hash": 2.5,   "power": 120, "unit": "GH/s"},
    },
    "RTX 4060 Ti": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 85, "fan": 65, "hash": 28.0,  "power": 115, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1100, "pl": 70, "fan": 60, "hash": 140.0, "power": 100, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 60, "hash": 55.0,  "power": 95,  "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 420.0, "power": 90,  "unit": "MH/s"},
    },
    "RTX 4060": {
        "kawpow":      {"core": 150, "mem": 500,  "pl": 85, "fan": 65, "hash": 23.0,  "power": 95,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1000, "pl": 70, "fan": 60, "hash": 115.0, "power": 85,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1000, "pl": 65, "fan": 60, "hash": 45.0,  "power": 80,  "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 60, "fan": 60, "hash": 350.0, "power": 75,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # NVIDIA RTX 30 SERIES
    # ==========================================================================
    "RTX 3090 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 75, "fan": 80, "hash": 60.0,  "power": 310, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1200, "pl": 70, "fan": 75, "hash": 290.0, "power": 280, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1200, "pl": 65, "fan": 70, "hash": 130.0, "power": 260, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 70, "hash": 650.0, "power": 230, "unit": "MH/s"},
    },
    "RTX 3090": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 75, "fan": 80, "hash": 55.0,  "power": 290, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1100, "pl": 70, "fan": 75, "hash": 270.0, "power": 260, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 70, "hash": 125.0, "power": 250, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 70, "hash": 600.0, "power": 220, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 75, "hash": 3.8,   "power": 260, "unit": "GH/s"},
        "octopus":     {"core": -100,"mem": 1000, "pl": 70, "fan": 75, "hash": 95.0,  "power": 270, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 80, "fan": 75, "hash": 105.0, "power": 280, "unit": "Sol/s"},
    },
    "RTX 3080 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 75, "fan": 75, "hash": 50.0,  "power": 250, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1100, "pl": 70, "fan": 70, "hash": 260.0, "power": 230, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 70, "hash": 115.0, "power": 220, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 65, "hash": 550.0, "power": 190, "unit": "MH/s"},
    },
    "RTX 3080 12GB": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 75, "fan": 75, "hash": 48.0,  "power": 240, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1100, "pl": 70, "fan": 70, "hash": 270.0, "power": 220, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 70, "hash": 105.0, "power": 210, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 65, "hash": 520.0, "power": 180, "unit": "MH/s"},
    },
    "RTX 3080": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 75, "fan": 75, "hash": 45.0,  "power": 220, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1000, "pl": 70, "fan": 70, "hash": 260.0, "power": 200, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 70, "hash": 98.0,  "power": 200, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 65, "hash": 480.0, "power": 170, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 70, "hash": 3.2,   "power": 210, "unit": "GH/s"},
        "octopus":     {"core": -100,"mem": 1000, "pl": 70, "fan": 70, "hash": 85.0,  "power": 210, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 80, "fan": 70, "hash": 85.0,  "power": 220, "unit": "Sol/s"},
    },
    # ==========================================================================
    # NVIDIA LAPTOP GPUs (Mobile)
    # ==========================================================================
    "RTX 3080 Laptop": {
        "kawpow":      {"core": 50,  "mem": 400,  "pl": 80, "fan": 80, "hash": 32.0,  "power": 115, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 75, "fan": 75, "hash": 180.0, "power": 105, "unit": "MH/s"},
        "etchash":     {"core": -150,"mem": 900,  "pl": 70, "fan": 75, "hash": 72.0,  "power": 100, "unit": "MH/s"},
        "kheavyhash":  {"core": 150, "mem": 0,    "pl": 60, "fan": 70, "hash": 320.0, "power": 90,  "unit": "MH/s"},
        "blake3":      {"core": 50,  "mem": 400,  "pl": 75, "fan": 75, "hash": 2.2,   "power": 110, "unit": "GH/s"},
        "octopus":     {"core": -50, "mem": 800,  "pl": 75, "fan": 75, "hash": 60.0,  "power": 110, "unit": "MH/s"},
        "equihash125": {"core": 100, "mem": 0,    "pl": 85, "fan": 80, "hash": 55.0,  "power": 115, "unit": "Sol/s"},
        "firopow":     {"core": 50,  "mem": 400,  "pl": 80, "fan": 80, "hash": 22.0,  "power": 110, "unit": "MH/s"},
        "beamhashiii": {"core": 0,   "mem": 500,  "pl": 75, "fan": 75, "hash": 28.0,  "power": 100, "unit": "Sol/s"},
    },
    "RTX 3070 Laptop": {
        "kawpow":      {"core": 50,  "mem": 400,  "pl": 85, "fan": 75, "hash": 25.0,  "power": 95,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 700,  "pl": 75, "fan": 72, "hash": 140.0, "power": 85,  "unit": "MH/s"},
        "etchash":     {"core": -150,"mem": 800,  "pl": 70, "fan": 70, "hash": 55.0,  "power": 80,  "unit": "MH/s"},
        "kheavyhash":  {"core": 150, "mem": 0,    "pl": 60, "fan": 68, "hash": 260.0, "power": 75,  "unit": "MH/s"},
        "blake3":      {"core": 50,  "mem": 400,  "pl": 75, "fan": 72, "hash": 1.8,   "power": 90,  "unit": "GH/s"},
        "octopus":     {"core": -50, "mem": 700,  "pl": 75, "fan": 72, "hash": 48.0,  "power": 90,  "unit": "MH/s"},
        "equihash125": {"core": 100, "mem": 0,    "pl": 85, "fan": 75, "hash": 45.0,  "power": 95,  "unit": "Sol/s"},
    },
    "RTX 3060 Laptop": {
        "kawpow":      {"core": 50,  "mem": 400,  "pl": 85, "fan": 70, "hash": 18.0,  "power": 75,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 600,  "pl": 75, "fan": 68, "hash": 100.0, "power": 65,  "unit": "MH/s"},
        "etchash":     {"core": -150,"mem": 700,  "pl": 70, "fan": 68, "hash": 38.0,  "power": 60,  "unit": "MH/s"},
        "kheavyhash":  {"core": 150, "mem": 0,    "pl": 60, "fan": 65, "hash": 180.0, "power": 55,  "unit": "MH/s"},
    },
    "RTX 3070 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 35.0,  "power": 170, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1000, "pl": 70, "fan": 68, "hash": 195.0, "power": 150, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1000, "pl": 65, "fan": 65, "hash": 80.0,  "power": 145, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 60, "hash": 400.0, "power": 130, "unit": "MH/s"},
    },
    "RTX 3070": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 30.0,  "power": 140, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1000, "pl": 70, "fan": 65, "hash": 170.0, "power": 120, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 60, "hash": 61.0,  "power": 115, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 60, "hash": 350.0, "power": 105, "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 65, "hash": 2.2,   "power": 130, "unit": "GH/s"},
        "octopus":     {"core": -100,"mem": 1000, "pl": 70, "fan": 65, "hash": 58.0,  "power": 135, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 85, "fan": 70, "hash": 55.0,  "power": 150, "unit": "Sol/s"},
    },
    "RTX 3060 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 28.0,  "power": 130, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 1000, "pl": 70, "fan": 65, "hash": 155.0, "power": 110, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1100, "pl": 65, "fan": 60, "hash": 58.0,  "power": 105, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 60, "hash": 320.0, "power": 95,  "unit": "MH/s"},
        "blake3":      {"core": 100, "mem": 500,  "pl": 70, "fan": 65, "hash": 2.0,   "power": 115, "unit": "GH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 85, "fan": 70, "hash": 50.0,  "power": 130, "unit": "Sol/s"},
    },
    "RTX 3060": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 68, "hash": 23.0,  "power": 115, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 900,  "pl": 70, "fan": 65, "hash": 125.0, "power": 100, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 1000, "pl": 65, "fan": 60, "hash": 45.0,  "power": 95,  "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 60, "hash": 260.0, "power": 85,  "unit": "MH/s"},
    },
    "RTX 3050": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 85, "fan": 65, "hash": 15.0,  "power": 85,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 60, "hash": 80.0,  "power": 75,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 800,  "pl": 65, "fan": 60, "hash": 28.0,  "power": 70,  "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 60, "hash": 165.0, "power": 60,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # NVIDIA RTX 20 SERIES
    # ==========================================================================
    "RTX 2080 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 32.0,  "power": 180, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 70, "hash": 165.0, "power": 160, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 900,  "pl": 65, "fan": 65, "hash": 56.0,  "power": 150, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 65, "hash": 340.0, "power": 140, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 85, "fan": 70, "hash": 55.0,  "power": 170, "unit": "Sol/s"},
    },
    "RTX 2080 Super": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 28.0,  "power": 165, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 70, "hash": 145.0, "power": 145, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 900,  "pl": 65, "fan": 65, "hash": 45.0,  "power": 140, "unit": "MH/s"},
        "kheavyhash":  {"core": 200, "mem": 0,    "pl": 55, "fan": 65, "hash": 290.0, "power": 125, "unit": "MH/s"},
    },
    "RTX 2080": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 70, "hash": 26.0,  "power": 155, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 70, "hash": 135.0, "power": 140, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 900,  "pl": 65, "fan": 65, "hash": 43.0,  "power": 135, "unit": "MH/s"},
    },
    "RTX 2070 Super": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 68, "hash": 24.0,  "power": 145, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 65, "hash": 130.0, "power": 125, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 900,  "pl": 65, "fan": 65, "hash": 42.0,  "power": 120, "unit": "MH/s"},
    },
    "RTX 2070": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 68, "hash": 22.0,  "power": 130, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 800,  "pl": 70, "fan": 65, "hash": 120.0, "power": 115, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 900,  "pl": 65, "fan": 65, "hash": 38.0,  "power": 110, "unit": "MH/s"},
    },
    "RTX 2060 Super": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 65, "hash": 20.0,  "power": 125, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 700,  "pl": 70, "fan": 65, "hash": 105.0, "power": 105, "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 800,  "pl": 65, "fan": 60, "hash": 35.0,  "power": 100, "unit": "MH/s"},
    },
    "RTX 2060": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 65, "hash": 18.0,  "power": 110, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 700,  "pl": 70, "fan": 65, "hash": 95.0,  "power": 95,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 800,  "pl": 65, "fan": 60, "hash": 32.0,  "power": 90,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # NVIDIA GTX 16 SERIES
    # ==========================================================================
    "GTX 1660 Ti": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 65, "hash": 14.0,  "power": 85,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 600,  "pl": 70, "fan": 60, "hash": 75.0,  "power": 75,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 700,  "pl": 65, "fan": 60, "hash": 28.0,  "power": 70,  "unit": "MH/s"},
    },
    "GTX 1660 Super": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 65, "hash": 13.5,  "power": 80,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 600,  "pl": 70, "fan": 60, "hash": 72.0,  "power": 70,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 700,  "pl": 65, "fan": 60, "hash": 31.0,  "power": 75,  "unit": "MH/s"},
    },
    "GTX 1660": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 80, "fan": 65, "hash": 12.0,  "power": 75,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 500,  "pl": 70, "fan": 60, "hash": 65.0,  "power": 65,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 600,  "pl": 65, "fan": 60, "hash": 25.0,  "power": 65,  "unit": "MH/s"},
    },
    "GTX 1650 Super": {
        "kawpow":      {"core": 100, "mem": 500,  "pl": 85, "fan": 65, "hash": 10.0,  "power": 70,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 500,  "pl": 70, "fan": 60, "hash": 55.0,  "power": 60,  "unit": "MH/s"},
        "etchash":     {"core": -200,"mem": 600,  "pl": 65, "fan": 60, "hash": 18.0,  "power": 55,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # NVIDIA GTX 10 SERIES
    # ==========================================================================
    "GTX 1080 Ti": {
        "kawpow":      {"core": 100, "mem": 400,  "pl": 80, "fan": 70, "hash": 20.0,  "power": 160, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 500,  "pl": 70, "fan": 70, "hash": 105.0, "power": 140, "unit": "MH/s"},
        "etchash":     {"core": -100,"mem": 600,  "pl": 65, "fan": 65, "hash": 45.0,  "power": 135, "unit": "MH/s"},
        "equihash125": {"core": 150, "mem": 0,    "pl": 85, "fan": 70, "hash": 50.0,  "power": 155, "unit": "Sol/s"},
    },
    "GTX 1080": {
        "kawpow":      {"core": 100, "mem": 400,  "pl": 80, "fan": 70, "hash": 16.0,  "power": 130, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 500,  "pl": 70, "fan": 68, "hash": 85.0,  "power": 115, "unit": "MH/s"},
        "etchash":     {"core": -100,"mem": 500,  "pl": 65, "fan": 65, "hash": 32.0,  "power": 110, "unit": "MH/s"},
    },
    "GTX 1070 Ti": {
        "kawpow":      {"core": 100, "mem": 400,  "pl": 80, "fan": 68, "hash": 15.0,  "power": 115, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 500,  "pl": 70, "fan": 65, "hash": 80.0,  "power": 100, "unit": "MH/s"},
        "etchash":     {"core": -100,"mem": 500,  "pl": 65, "fan": 65, "hash": 30.0,  "power": 100, "unit": "MH/s"},
    },
    "GTX 1070": {
        "kawpow":      {"core": 100, "mem": 400,  "pl": 80, "fan": 65, "hash": 14.0,  "power": 105, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 400,  "pl": 70, "fan": 65, "hash": 72.0,  "power": 95,  "unit": "MH/s"},
        "etchash":     {"core": -100,"mem": 500,  "pl": 65, "fan": 60, "hash": 28.0,  "power": 90,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # AMD RADEON RX 7000 SERIES
    # ==========================================================================
    "RX 7900 XTX": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 70, "hash": 48.0,  "power": 275, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 70, "hash": 300.0, "power": 250, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 105.0, "power": 220, "unit": "MH/s"},
        "kheavyhash":  {"core": 50,  "mem": 0,    "pl": 55, "fan": 60, "hash": 700.0, "power": 180, "unit": "MH/s"},
        "equihash144": {"core": 0,   "mem": 0,    "pl": 80, "fan": 70, "hash": 176.0, "power": 270, "unit": "Sol/s"},
    },
    "RX 7900 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 70, "hash": 42.0,  "power": 250, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 70, "hash": 270.0, "power": 230, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 92.0,  "power": 200, "unit": "MH/s"},
        "kheavyhash":  {"core": 50,  "mem": 0,    "pl": 55, "fan": 60, "hash": 620.0, "power": 165, "unit": "MH/s"},
    },
    "RX 7800 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 68, "hash": 35.0,  "power": 200, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 200.0, "power": 180, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 68.0,  "power": 160, "unit": "MH/s"},
    },
    "RX 7700 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 65, "hash": 30.0,  "power": 175, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 170.0, "power": 155, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 55.0,  "power": 140, "unit": "MH/s"},
    },
    "RX 7600": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 22.0,  "power": 130, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 125.0, "power": 115, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 42.0,  "power": 105, "unit": "MH/s"},
    },
    
    # ==========================================================================
    # AMD RADEON RX 6000 SERIES
    # ==========================================================================
    "RX 6950 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 70, "hash": 38.0,  "power": 220, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 70, "hash": 235.0, "power": 200, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 65.0,  "power": 175, "unit": "MH/s"},
    },
    "RX 6900 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 70, "hash": 35.0,  "power": 200, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 70, "hash": 220.0, "power": 185, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 62.0,  "power": 160, "unit": "MH/s"},
        "equihash144": {"core": 0,   "mem": 0,    "pl": 80, "fan": 70, "hash": 140.0, "power": 190, "unit": "Sol/s"},
    },
    "RX 6800 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 70, "hash": 32.0,  "power": 190, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 68, "hash": 200.0, "power": 170, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 65, "hash": 58.0,  "power": 150, "unit": "MH/s"},
    },
    "RX 6800": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 68, "hash": 28.0,  "power": 170, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 175.0, "power": 155, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 52.0,  "power": 135, "unit": "MH/s"},
    },
    "RX 6750 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 65, "hash": 26.0,  "power": 150, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 145.0, "power": 135, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 42.0,  "power": 120, "unit": "MH/s"},
    },
    "RX 6700 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 65, "hash": 24.0,  "power": 135, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 135.0, "power": 120, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 40.0,  "power": 110, "unit": "MH/s"},
    },
    "RX 6650 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 20.0,  "power": 120, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 110.0, "power": 105, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 32.0,  "power": 95,  "unit": "MH/s"},
    },
    "RX 6600 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 18.0,  "power": 105, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 100.0, "power": 95,  "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 30.0,  "power": 85,  "unit": "MH/s"},
    },
    "RX 6600": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 15.0,  "power": 95,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 85.0,  "power": 85,  "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 28.0,  "power": 80,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # AMD RADEON RX 5000 SERIES
    # ==========================================================================
    "RX 5700 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 65, "hash": 20.0,  "power": 145, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 120.0, "power": 130, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 55.0,  "power": 120, "unit": "MH/s"},
    },
    "RX 5700": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 75, "fan": 65, "hash": 18.0,  "power": 135, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 65, "hash": 110.0, "power": 120, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 50.0,  "power": 110, "unit": "MH/s"},
    },
    "RX 5600 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 16.0,  "power": 115, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 90.0,  "power": 100, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 40.0,  "power": 95,  "unit": "MH/s"},
    },
    "RX 5500 XT": {
        "kawpow":      {"core": 0,   "mem": 50,   "pl": 80, "fan": 65, "hash": 12.0,  "power": 95,  "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 100,  "pl": 70, "fan": 60, "hash": 65.0,  "power": 85,  "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 100,  "pl": 65, "fan": 60, "hash": 27.0,  "power": 80,  "unit": "MH/s"},
    },
    
    # ==========================================================================
    # AMD RADEON RX VEGA / 500 SERIES
    # ==========================================================================
    "RX Vega 64": {
        "kawpow":      {"core": 0,   "mem": 0,    "pl": 75, "fan": 70, "hash": 20.0,  "power": 200, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 0,    "pl": 70, "fan": 70, "hash": 110.0, "power": 180, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 0,    "pl": 65, "fan": 65, "hash": 42.0,  "power": 165, "unit": "MH/s"},
    },
    "RX Vega 56": {
        "kawpow":      {"core": 0,   "mem": 0,    "pl": 75, "fan": 70, "hash": 18.0,  "power": 175, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 0,    "pl": 70, "fan": 70, "hash": 95.0,  "power": 160, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 0,    "pl": 65, "fan": 65, "hash": 38.0,  "power": 145, "unit": "MH/s"},
    },
    "RX 580 8GB": {
        "kawpow":      {"core": 0,   "mem": 0,    "pl": 80, "fan": 65, "hash": 11.0,  "power": 110, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 0,    "pl": 75, "fan": 65, "hash": 58.0,  "power": 100, "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 0,    "pl": 70, "fan": 60, "hash": 30.0,  "power": 95,  "unit": "MH/s"},
    },
    "RX 570 8GB": {
        "kawpow":      {"core": 0,   "mem": 0,    "pl": 80, "fan": 65, "hash": 10.0,  "power": 100, "unit": "MH/s"},
        "autolykos2":  {"core": 0,   "mem": 0,    "pl": 75, "fan": 65, "hash": 52.0,  "power": 90,  "unit": "MH/s"},
        "etchash":     {"core": 0,   "mem": 0,    "pl": 70, "fan": 60, "hash": 28.0,  "power": 85,  "unit": "MH/s"},
    },
}


# ============================================================================
# GPU DATABASE HELPER
# ============================================================================

def get_all_gpus() -> List[str]:
    """Gibt alle GPUs zurück"""
    return list(GPU_OC_DATABASE.keys())


def get_nvidia_gpus() -> List[str]:
    """Gibt alle NVIDIA GPUs zurück"""
    return [gpu for gpu in GPU_OC_DATABASE.keys() if gpu.startswith(("RTX", "GTX"))]


def get_amd_gpus() -> List[str]:
    """Gibt alle AMD GPUs zurück"""
    return [gpu for gpu in GPU_OC_DATABASE.keys() if gpu.startswith("RX")]


def get_oc_settings(gpu_name: str, algorithm: str) -> Optional[Dict]:
    """Gibt OC-Settings für GPU und Algorithmus zurück"""
    # GPU Name normalisieren
    normalized = normalize_gpu_name(gpu_name)
    
    if normalized in GPU_OC_DATABASE:
        settings = GPU_OC_DATABASE[normalized].get(algorithm.lower())
        if settings:
            return {
                "core_offset": settings["core"],
                "memory_offset": settings["mem"],
                "power_limit_percent": settings["pl"],
                "fan_speed": settings["fan"],
                "expected_hashrate": settings["hash"],
                "expected_power": settings["power"],
                "hashrate_unit": settings["unit"],
            }
    return None


def normalize_gpu_name(gpu_name: str) -> str:
    """Normalisiert GPU-Namen für Matching"""
    name = gpu_name.upper()
    
    # NVIDIA Patterns
    nvidia_patterns = [
        ("GEFORCE RTX 4090", "RTX 4090"),
        ("GEFORCE RTX 4080 SUPER", "RTX 4080 Super"),
        ("GEFORCE RTX 4080", "RTX 4080"),
        ("GEFORCE RTX 4070 TI SUPER", "RTX 4070 Ti Super"),
        ("GEFORCE RTX 4070 TI", "RTX 4070 Ti"),
        ("GEFORCE RTX 4070 SUPER", "RTX 4070 Super"),
        ("GEFORCE RTX 4070", "RTX 4070"),
        ("GEFORCE RTX 4060 TI", "RTX 4060 Ti"),
        ("GEFORCE RTX 4060", "RTX 4060"),
        ("GEFORCE RTX 3090 TI", "RTX 3090 Ti"),
        ("GEFORCE RTX 3090", "RTX 3090"),
        ("GEFORCE RTX 3080 TI", "RTX 3080 Ti"),
        ("GEFORCE RTX 3080 12GB", "RTX 3080 12GB"),
        ("GEFORCE RTX 3080", "RTX 3080"),
        ("GEFORCE RTX 3070 TI", "RTX 3070 Ti"),
        ("GEFORCE RTX 3070", "RTX 3070"),
        ("GEFORCE RTX 3060 TI", "RTX 3060 Ti"),
        ("GEFORCE RTX 3060", "RTX 3060"),
        ("GEFORCE RTX 3050", "RTX 3050"),
        ("GEFORCE RTX 2080 TI", "RTX 2080 Ti"),
        ("GEFORCE RTX 2080 SUPER", "RTX 2080 Super"),
        ("GEFORCE RTX 2080", "RTX 2080"),
        ("GEFORCE RTX 2070 SUPER", "RTX 2070 Super"),
        ("GEFORCE RTX 2070", "RTX 2070"),
        ("GEFORCE RTX 2060 SUPER", "RTX 2060 Super"),
        ("GEFORCE RTX 2060", "RTX 2060"),
        ("GEFORCE GTX 1660 TI", "GTX 1660 Ti"),
        ("GEFORCE GTX 1660 SUPER", "GTX 1660 Super"),
        ("GEFORCE GTX 1660", "GTX 1660"),
        ("GEFORCE GTX 1650 SUPER", "GTX 1650 Super"),
        ("GEFORCE GTX 1080 TI", "GTX 1080 Ti"),
        ("GEFORCE GTX 1080", "GTX 1080"),
        ("GEFORCE GTX 1070 TI", "GTX 1070 Ti"),
        ("GEFORCE GTX 1070", "GTX 1070"),
    ]
    
    # AMD Patterns
    amd_patterns = [
        ("RADEON RX 7900 XTX", "RX 7900 XTX"),
        ("RADEON RX 7900 XT", "RX 7900 XT"),
        ("RADEON RX 7800 XT", "RX 7800 XT"),
        ("RADEON RX 7700 XT", "RX 7700 XT"),
        ("RADEON RX 7600", "RX 7600"),
        ("RADEON RX 6950 XT", "RX 6950 XT"),
        ("RADEON RX 6900 XT", "RX 6900 XT"),
        ("RADEON RX 6800 XT", "RX 6800 XT"),
        ("RADEON RX 6800", "RX 6800"),
        ("RADEON RX 6750 XT", "RX 6750 XT"),
        ("RADEON RX 6700 XT", "RX 6700 XT"),
        ("RADEON RX 6650 XT", "RX 6650 XT"),
        ("RADEON RX 6600 XT", "RX 6600 XT"),
        ("RADEON RX 6600", "RX 6600"),
        ("RADEON RX 5700 XT", "RX 5700 XT"),
        ("RADEON RX 5700", "RX 5700"),
        ("RADEON RX 5600 XT", "RX 5600 XT"),
        ("RADEON RX 5500 XT", "RX 5500 XT"),
        ("RADEON RX VEGA 64", "RX Vega 64"),
        ("RADEON RX VEGA 56", "RX Vega 56"),
        ("RADEON RX 580", "RX 580 8GB"),
        ("RADEON RX 570", "RX 570 8GB"),
    ]
    
    for pattern, normalized in nvidia_patterns + amd_patterns:
        if pattern in name:
            return normalized
    
    # Fallback: Einfache Extraktion
    for gpu in GPU_OC_DATABASE.keys():
        if gpu.upper().replace(" ", "") in name.replace(" ", ""):
            return gpu
    
    return gpu_name


def get_algorithms_for_gpu(gpu_name: str) -> List[str]:
    """Gibt alle unterstützten Algorithmen für eine GPU zurück"""
    normalized = normalize_gpu_name(gpu_name)
    if normalized in GPU_OC_DATABASE:
        return list(GPU_OC_DATABASE[normalized].keys())
    return []


def get_expected_hashrate(gpu_name: str, algorithm: str) -> Optional[float]:
    """Gibt die erwartete Hashrate zurück"""
    settings = get_oc_settings(gpu_name, algorithm)
    if settings:
        return settings["expected_hashrate"]
    return None


# ============================================================================
# LIVE UPDATE FROM HASHRATE.NO
# ============================================================================

class HashrateNoUpdater:
    """Aktualisiert GPU-Daten von hashrate.no"""
    
    API_URL = "https://hashrate.no/api/v2"
    CACHE_FILE = "gpu_cache.json"
    
    def __init__(self, api_key: str = None, cache_dir: str = "."):
        self.api_key = api_key
        self.cache_path = Path(cache_dir) / self.CACHE_FILE
        self.last_update = None
    
    def fetch_benchmarks(self, coin: str = None) -> Optional[Dict]:
        """Holt Benchmark-Daten von hashrate.no"""
        if not self.api_key:
            logger.warning("Kein hashrate.no API-Key - nutze lokale Daten")
            return None
        
        try:
            params = {"apiKey": self.api_key}
            if coin:
                params["coin"] = coin
            
            response = requests.get(
                f"{self.API_URL}/benchmarks",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Fehler beim Abrufen von hashrate.no: {e}")
            return None
    
    def update_local_database(self) -> bool:
        """Aktualisiert die lokale Datenbank mit hashrate.no Daten"""
        data = self.fetch_benchmarks()
        if not data:
            return False
        
        # Cache speichern
        try:
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "updated": datetime.now().isoformat(),
                    "data": data
                }, f, indent=2)
            self.last_update = datetime.now()
            logger.info("GPU-Datenbank aktualisiert von hashrate.no")
            return True
        except Exception as e:
            logger.error(f"Fehler beim Speichern des Cache: {e}")
            return False


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("\n=== GPU DATABASE ===")
    print(f"NVIDIA GPUs: {len(get_nvidia_gpus())}")
    print(f"AMD GPUs: {len(get_amd_gpus())}")
    print(f"Total: {len(get_all_gpus())}")
    
    print("\n=== BEISPIEL: RTX 3070 ===")
    for algo in get_algorithms_for_gpu("RTX 3070"):
        settings = get_oc_settings("RTX 3070", algo)
        print(f"  {algo}: {settings['expected_hashrate']} {settings['hashrate_unit']} @ {settings['expected_power']}W")
    
    print("\n=== GPU NAME MATCHING ===")
    test_names = [
        "NVIDIA GeForce RTX 3070",
        "AMD Radeon RX 6800 XT",
        "GeForce GTX 1080 Ti",
    ]
    for name in test_names:
        normalized = normalize_gpu_name(name)
        print(f"  {name} -> {normalized}")
