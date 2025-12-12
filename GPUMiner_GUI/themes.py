#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dark Mining Theme - Professionelles HiveOS-ähnliches Design
Teil des GPU Mining Profit Switcher V11.0 Ultimate

Features:
- Dunkles Farbschema optimiert für Mining-Dashboards
- Mining-spezifische Farben (Hashrate grün, Temp-Gradienten)
- Widget-Styles für alle Qt-Komponenten
- Konsistentes Look & Feel
"""

from typing import Dict

# Mining-spezifische Farbpalette
COLORS = {
    # Basis-Farben (Dunkel)
    'background': '#1a1a2e',           # Haupt-Hintergrund
    'background_alt': '#16213e',       # Alternative (Cards, Panels)
    'background_dark': '#0f0f1a',      # Dunklerer Hintergrund
    'surface': '#1e2746',              # Surface (Widgets)
    'surface_light': '#2a3f5f',        # Hellere Surface
    'card_bg': '#1e2746',              # Card Hintergrund (für Börsen-Tab etc.)
    
    # Text-Farben
    'text_primary': '#ffffff',          # Primärer Text
    'text_secondary': '#b8c5d6',        # Sekundärer Text
    'text_muted': '#6c7a89',            # Gedämpfter Text
    'text_disabled': '#4a5568',         # Deaktivierter Text
    
    # Akzent-Farben
    'accent': '#0f3460',               # Primärer Akzent
    'accent_light': '#1a4a7a',         # Heller Akzent
    'accent_hover': '#245080',         # Hover-Zustand
    
    # Mining-spezifische Farben
    'hashrate': '#00ff88',             # Hashrate (Grün)
    'hashrate_dark': '#00cc6a',        # Hashrate dunkel
    'power': '#00bfff',                # Power (Blau)
    'efficiency': '#ffd700',           # Effizienz (Gold)
    
    # Temperatur-Gradient
    'temp_cold': '#00bfff',            # Kalt (<40°C)
    'temp_cool': '#00ff88',            # Kühl (40-60°C)
    'temp_normal': '#88ff00',          # Normal (60-70°C)
    'temp_warm': '#ffff00',            # Warm (70-75°C)
    'temp_hot': '#ff8800',             # Heiß (75-80°C)
    'temp_critical': '#ff4444',        # Kritisch (>80°C)
    
    # Status-Farben
    'success': '#00ff88',              # Erfolg
    'warning': '#ffa500',              # Warnung
    'error': '#ff4444',                # Fehler
    'info': '#00bfff',                 # Info
    
    # Share-Status
    'accepted': '#00ff88',             # Accepted Shares
    'rejected': '#ff4444',             # Rejected Shares
    'stale': '#ffa500',                # Stale Shares
    
    # UI-Elemente
    'border': '#2d3f5f',               # Rahmen
    'border_light': '#3d5080',         # Heller Rahmen
    'scrollbar': '#3d5080',            # Scrollbar
    'scrollbar_hover': '#4d6090',      # Scrollbar Hover
    'selection': '#0f3460',            # Auswahl
    'highlight': '#1a5090',            # Highlight
    
    # Button-Farben
    'button_primary': '#0f3460',       # Primärer Button
    'button_primary_hover': '#1a5090', # Primärer Button Hover
    'button_success': '#1e6e40',       # Erfolg-Button
    'button_success_hover': '#2a8a50', # Erfolg-Button Hover
    'button_danger': '#8b2020',        # Gefahr-Button
    'button_danger_hover': '#a52828',  # Gefahr-Button Hover
}

def get_temp_color(temp: int) -> str:
    """
    Gibt die passende Farbe für eine Temperatur zurück.
    
    Args:
        temp: Temperatur in °C
        
    Returns:
        Hex-Farbcode
    """
    if temp < 40:
        return COLORS['temp_cold']
    elif temp < 60:
        return COLORS['temp_cool']
    elif temp < 70:
        return COLORS['temp_normal']
    elif temp < 75:
        return COLORS['temp_warm']
    elif temp < 80:
        return COLORS['temp_hot']
    else:
        return COLORS['temp_critical']


def get_hashrate_color(hashrate: float, expected: float = 0) -> str:
    """
    Gibt die passende Farbe für eine Hashrate zurück.
    
    Args:
        hashrate: Aktuelle Hashrate
        expected: Erwartete Hashrate (für Vergleich)
        
    Returns:
        Hex-Farbcode
    """
    if expected > 0:
        ratio = hashrate / expected
        if ratio >= 0.95:
            return COLORS['hashrate']  # Gut
        elif ratio >= 0.85:
            return COLORS['warning']   # Warnung
        else:
            return COLORS['error']     # Schlecht
    return COLORS['hashrate']


# Haupt-Stylesheet für die gesamte Anwendung
MAIN_STYLESHEET = f"""
/* ========== Globale Styles ========== */
QMainWindow, QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}

/* ========== Labels ========== */
QLabel {{
    color: {COLORS['text_primary']};
    padding: 2px;
}}

QLabel[class="title"] {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['hashrate']};
}}

QLabel[class="subtitle"] {{
    font-size: 14px;
    color: {COLORS['text_secondary']};
}}

QLabel[class="value"] {{
    font-size: 16px;
    font-weight: bold;
}}

QLabel[class="hashrate"] {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS['hashrate']};
}}

/* ========== Buttons ========== */
QPushButton {{
    background-color: {COLORS['button_primary']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 24px;
}}

QPushButton:hover {{
    background-color: {COLORS['button_primary_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent']};
}}

QPushButton:disabled {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_disabled']};
    border-color: {COLORS['border']};
}}

QPushButton[class="success"] {{
    background-color: {COLORS['button_success']};
}}

QPushButton[class="success"]:hover {{
    background-color: {COLORS['button_success_hover']};
}}

QPushButton[class="danger"] {{
    background-color: {COLORS['button_danger']};
}}

QPushButton[class="danger"]:hover {{
    background-color: {COLORS['button_danger_hover']};
}}

/* ========== Input-Felder ========== */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
    selection-background-color: {COLORS['selection']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['accent_light']};
}}

QLineEdit:disabled {{
    background-color: {COLORS['background_dark']};
    color: {COLORS['text_disabled']};
}}

/* ========== ComboBox ========== */
QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_light']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['selection']};
}}

/* ========== TabWidget ========== */
QTabWidget::pane {{
    background-color: {COLORS['background_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
}}

QTabBar::tab {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {COLORS['background_alt']};
    color: {COLORS['text_primary']};
    border-bottom: 2px solid {COLORS['hashrate']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_light']};
}}

/* ========== Table ========== */
QTableWidget, QTableView {{
    background-color: {COLORS['background_alt']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['selection']};
    alternate-background-color: {COLORS['surface']};
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {COLORS['selection']};
}}

QHeaderView::section {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 8px;
    font-weight: bold;
}}

/* ========== ScrollBar ========== */
QScrollBar:vertical {{
    background-color: {COLORS['background_dark']};
    width: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['scrollbar']};
    border-radius: 6px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['background_dark']};
    height: 12px;
    border-radius: 6px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['scrollbar']};
    border-radius: 6px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

/* ========== GroupBox ========== */
QGroupBox {{
    background-color: {COLORS['background_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 4px 8px;
    color: {COLORS['text_primary']};
    font-weight: bold;
}}

/* ========== ProgressBar ========== */
QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['text_primary']};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['hashrate']};
    border-radius: 3px;
}}

/* ========== Slider ========== */
QSlider::groove:horizontal {{
    background-color: {COLORS['surface']};
    height: 8px;
    border-radius: 4px;
}}

QSlider::handle:horizontal {{
    background-color: {COLORS['accent_light']};
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}}

QSlider::handle:horizontal:hover {{
    background-color: {COLORS['hashrate']};
}}

/* ========== CheckBox & RadioButton ========== */
QCheckBox, QRadioButton {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator:unchecked {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 4px;
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['hashrate']};
    border: 2px solid {COLORS['hashrate']};
    border-radius: 4px;
}}

QRadioButton::indicator:unchecked {{
    background-color: {COLORS['surface']};
    border: 2px solid {COLORS['border']};
    border-radius: 9px;
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['hashrate']};
    border: 2px solid {COLORS['hashrate']};
    border-radius: 9px;
}}

/* ========== TextEdit / PlainTextEdit ========== */
QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['background_dark']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
}}

/* ========== Menu ========== */
QMenuBar {{
    background-color: {COLORS['background']};
    color: {COLORS['text_primary']};
    border-bottom: 1px solid {COLORS['border']};
}}

QMenuBar::item:selected {{
    background-color: {COLORS['selection']};
}}

QMenu {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
}}

QMenu::item:selected {{
    background-color: {COLORS['selection']};
}}

QMenu::separator {{
    background-color: {COLORS['border']};
    height: 1px;
    margin: 4px 8px;
}}

/* ========== StatusBar ========== */
QStatusBar {{
    background-color: {COLORS['background_dark']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
}}

/* ========== ToolTip ========== */
QToolTip {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    padding: 4px 8px;
}}

/* ========== Splitter ========== */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}
"""


def apply_theme(app):
    """
    Wendet das Dark Mining Theme auf eine QApplication an.
    
    Args:
        app: QApplication Instanz
    """
    app.setStyleSheet(MAIN_STYLESHEET)


# Chart-Farben für pyqtgraph
CHART_COLORS = {
    'hashrate': '#00ff88',
    'temperature': '#ff4444',
    'power': '#00bfff',
    'fan': '#ffd700',
    'grid': '#2d3f5f',
    'background': '#1a1a2e',
    'text': '#ffffff',
}


def get_chart_pen(color_name: str, width: int = 2):
    """
    Gibt einen pyqtgraph Pen für Charts zurück.
    
    Args:
        color_name: Name der Farbe aus CHART_COLORS
        width: Linienbreite
        
    Returns:
        pyqtgraph.mkPen
    """
    try:
        import pyqtgraph as pg
        color = CHART_COLORS.get(color_name, CHART_COLORS['hashrate'])
        return pg.mkPen(color=color, width=width)
    except ImportError:
        return None


# Standalone Test
if __name__ == "__main__":
    print("=" * 60)
    print("Mining Theme Test")
    print("=" * 60)
    
    print("\n📊 Farbpalette:")
    for name, color in list(COLORS.items())[:10]:
        print(f"   {name}: {color}")
    print("   ...")
    
    print("\n🌡️ Temperatur-Farben:")
    for temp in [30, 50, 65, 72, 78, 85]:
        color = get_temp_color(temp)
        print(f"   {temp}°C: {color}")
    
    print("\n✅ Theme bereit")
