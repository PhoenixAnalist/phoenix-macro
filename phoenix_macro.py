#!/usr/bin/env python3
"""
Phoenix Macro Recorder
Mouse & Keyboard macro recorder and player with Phoenix-themed UI.
Usage: python phoenix_macro.py
Build: see build.bat (Windows)
"""
import sys
import os
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QFrame,
    QDialog, QLineEdit, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject
from PyQt5.QtGui import (
    QFont, QColor, QLinearGradient, QPainter, QBrush, QPen,
    QIcon, QPixmap, QRadialGradient, QPainterPath
)

# ── pynput import with graceful fallback ──────────────────────────────────────
try:
    from pynput import mouse as pm, keyboard as pk
    from pynput.mouse import Controller as MC, Button
    from pynput.keyboard import Controller as KC, Key
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

# ── Paths (works both from source and from PyInstaller --onefile bundle) ──────
if getattr(sys, 'frozen', False):
    BASE_DIR   = Path(sys.executable).parent
    BUNDLE_DIR = Path(getattr(sys, '_MEIPASS', BASE_DIR))
else:
    BASE_DIR   = Path(__file__).parent
    BUNDLE_DIR = BASE_DIR

SCRIPTS_DIR   = BASE_DIR / "scripts"
SETTINGS_FILE = BASE_DIR / "phoenix_settings.json"
SCRIPTS_DIR.mkdir(exist_ok=True)

# Clean up leftover _MEI* extraction folders from previous runs.
if getattr(sys, 'frozen', False):
    import shutil
    _current_mei = str(getattr(sys, '_MEIPASS', ''))
    for _p in BASE_DIR.glob('_MEI*'):
        if _p.is_dir() and str(_p) != _current_mei:
            try:
                shutil.rmtree(_p, ignore_errors=True)
            except Exception:
                pass

# ── Version & Update ──────────────────────────────────────────────────────────
VERSION     = "1.6.2"
GITHUB_REPO = "PhoenixAnalist/phoenix-macro"

_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ── Pynput key map ────────────────────────────────────────────────────────────
if HAS_PYNPUT:
    PYNPUT_KEY_MAP = {
        'Key.space': Key.space, 'Key.enter': Key.enter,
        'Key.return': Key.enter, 'Key.tab': Key.tab,
        'Key.backspace': Key.backspace, 'Key.delete': Key.delete,
        'Key.esc': Key.esc, 'Key.escape': Key.esc,
        'Key.shift': Key.shift, 'Key.shift_l': Key.shift_l,
        'Key.shift_r': Key.shift_r,
        'Key.ctrl': Key.ctrl, 'Key.ctrl_l': Key.ctrl_l,
        'Key.ctrl_r': Key.ctrl_r,
        'Key.alt': Key.alt, 'Key.alt_l': Key.alt_l,
        'Key.alt_r': Key.alt_r, 'Key.alt_gr': Key.alt_gr,
        'Key.cmd': Key.cmd, 'Key.cmd_l': Key.cmd_l,
        'Key.cmd_r': Key.cmd_r,
        'Key.up': Key.up, 'Key.down': Key.down,
        'Key.left': Key.left, 'Key.right': Key.right,
        'Key.home': Key.home, 'Key.end': Key.end,
        'Key.page_up': Key.page_up, 'Key.page_down': Key.page_down,
        'Key.insert': Key.insert, 'Key.caps_lock': Key.caps_lock,
        'Key.num_lock': Key.num_lock,
        'Key.f1': Key.f1,  'Key.f2': Key.f2,  'Key.f3': Key.f3,
        'Key.f4': Key.f4,  'Key.f5': Key.f5,  'Key.f6': Key.f6,
        'Key.f7': Key.f7,  'Key.f8': Key.f8,  'Key.f9': Key.f9,
        'Key.f10': Key.f10, 'Key.f11': Key.f11, 'Key.f12': Key.f12,
        'Key.print_screen': Key.print_screen,
        'Key.scroll_lock': Key.scroll_lock, 'Key.pause': Key.pause,
        'Key.media_play_pause': Key.media_play_pause,
        'Key.media_volume_up': Key.media_volume_up,
        'Key.media_volume_down': Key.media_volume_down,
        'Key.media_volume_mute': Key.media_volume_mute,
        'Key.media_next': Key.media_next,
        'Key.media_previous': Key.media_previous,
    }
else:
    PYNPUT_KEY_MAP = {}


def parse_pynput_key(s: str):
    if not s:
        return None
    if len(s) == 1:
        return s
    return PYNPUT_KEY_MAP.get(s)


def key_to_display(s: str) -> str:
    if not s:
        return "—"
    if len(s) == 1:
        return s.upper()
    return s.replace('Key.', '').upper().replace('_', ' ')


# ─────────────────────────────────────────────────────────────────────────────
# Theme system
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    'Phoenix Fire': {
        'BG':          '#090909',
        'BG_TOP':      '#200a00',
        'BG_MID':      '#0f0400',
        'SURF':        '#111111',
        'SURF2':       '#1a1108',
        'BORDER':      '#2d1a00',
        'ACCENT1':     '#cc2800',
        'ACCENT2':     '#e85a00',
        'ACCENT3':     '#ff9a00',
        'TEXT':        '#f2e8d9',
        'DIM':         '#6a5a45',
        'STATE1':      '#ff2020',
        'STATE1_DARK': '#550000',
        'STATE2':      '#ffaa00',
        'BTN1A':       '#7a1200',
        'BTN1B':       '#4a0800',
        'BTN1H':       '#aa1800',
        'BTN2A':       '#4a2800',
        'BTN2B':       '#2d1800',
        'BTN2H':       '#663a00',
    },
    'Midnight Ocean': {
        'BG':          '#030c18',
        'BG_TOP':      '#00101e',
        'BG_MID':      '#001525',
        'SURF':        '#061a2d',
        'SURF2':       '#0a2038',
        'BORDER':      '#0d3555',
        'ACCENT1':     '#00c8e8',   # vivid cyan — primary interactive
        'ACCENT2':     '#e89a28',   # warm amber — secondary highlights
        'ACCENT3':     '#c0eeff',   # pale ice blue — light labels
        'TEXT':        '#e8f4fc',
        'DIM':         '#4a7a99',
        'STATE1':      '#00deff',   # bright cyan (recording)
        'STATE1_DARK': '#001c2a',
        'STATE2':      '#e89a28',   # amber (playing/loop)
        'BTN1A':       '#004d6a',   # deep teal
        'BTN1B':       '#002d44',
        'BTN1H':       '#00698a',
        'BTN2A':       '#002244',   # dark navy
        'BTN2B':       '#001228',
        'BTN2H':       '#003366',
    },
    'Neon Storm': {
        'BG':          '#050508',
        'BG_TOP':      '#0d0018',
        'BG_MID':      '#080010',
        'SURF':        '#0d0020',
        'SURF2':       '#120030',
        'BORDER':      '#3d0060',
        'ACCENT1':     '#f02090',   # hot pink/magenta — primary interactive
        'ACCENT2':     '#00eecc',   # electric cyan — secondary highlights
        'ACCENT3':     '#bbff44',   # neon yellow-green — light labels
        'TEXT':        '#f0e8ff',
        'DIM':         '#7755aa',
        'STATE1':      '#ff2299',   # hot pink (recording)
        'STATE1_DARK': '#330020',
        'STATE2':      '#00eecc',   # electric cyan (playing/loop)
        'BTN1A':       '#880055',   # deep magenta
        'BTN1B':       '#550033',
        'BTN1H':       '#aa0066',
        'BTN2A':       '#003344',   # deep cyan-navy (contrasts BTN1)
        'BTN2B':       '#001e28',
        'BTN2H':       '#004455',
    },
}

# Active palette — mutated by _load_theme()
_T: dict = dict(THEMES['Phoenix Fire'])


def _c(k: str) -> str:
    return _T.get(k, '#000000')


def _load_theme(name: str):
    global _T
    palette = THEMES.get(name, THEMES['Phoenix Fire'])
    _T.clear()
    _T.update(palette)


# ── Stylesheet functions (re-evaluated each call → always use current theme) ──

def _btn_base() -> str:
    return """
    border-radius: 20px;
    padding: 14px 28px;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 2px;
    """


def _btn_sm_base() -> str:
    return """
    border-radius: 12px;
    padding: 8px 18px;
    font-size: 12px;
    letter-spacing: 1px;
    """


def _app_style() -> str:
    return f"""
QMainWindow, QWidget {{
    color: {_c('TEXT')};
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QListWidget {{
    background-color: {_c('SURF')};
    border: 1px solid {_c('BORDER')};
    border-radius: 10px;
    padding: 4px;
    outline: none;
    color: {_c('TEXT')};
    font-size: 13px;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 2px;
    border-left: 3px solid transparent;
}}
QListWidget::item:selected {{
    background-color: {_c('BTN2B')};
    border-left: 3px solid {_c('ACCENT2')};
    color: {_c('ACCENT3')};
}}
QListWidget::item:hover:!selected {{
    background-color: {_c('SURF2')};
    border-left: 3px solid {_c('BORDER')};
}}
QScrollBar:vertical {{
    background: {_c('SURF')};
    width: 7px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {_c('BORDER')};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {_c('ACCENT1')};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QFrame[frameShape="4"] {{
    color: {_c('BORDER')};
    background: {_c('BORDER')};
    max-height: 1px;
}}
"""


def _btn_create_idle() -> str:
    return f"""
QPushButton {{
    {_btn_base()}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN1A')}, stop:1 {_c('BTN1B')});
    color: {_c('TEXT')};
    border: 1px solid {_c('ACCENT1')};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN1H')}, stop:1 {_c('BTN1A')});
    border-color: {_c('ACCENT2')};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('ACCENT1')}, stop:1 {_c('BTN1A')});
}}
"""


def _btn_create_rec() -> str:
    return f"""
QPushButton {{
    {_btn_base()}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('STATE1')}, stop:1 {_c('BTN1B')});
    color: #ffffff;
    border: 2px solid {_c('STATE1')};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('STATE1')}, stop:1 {_c('BTN1A')});
}}
"""


def _btn_start_idle() -> str:
    return f"""
QPushButton {{
    {_btn_base()}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2A')}, stop:1 {_c('BTN2B')});
    color: {_c('ACCENT3')};
    border: 1px solid {_c('ACCENT2')};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2H')}, stop:1 {_c('BTN2A')});
    border-color: {_c('ACCENT3')};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2H')}, stop:1 {_c('BTN2A')});
}}
QPushButton:disabled {{
    background: {_c('SURF')};
    color: {_c('DIM')};
    border-color: {_c('BORDER')};
    border-radius: 20px;
}}
"""


def _btn_start_playing() -> str:
    return f"""
QPushButton {{
    {_btn_base()}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2H')}, stop:1 {_c('BTN2A')});
    color: {_c('ACCENT3')};
    border: 2px solid {_c('ACCENT2')};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('ACCENT2')}, stop:1 {_c('BTN2A')});
}}
"""


def _btn_delete() -> str:
    return f"""
QPushButton {{
    {_btn_sm_base()}
    background: {_c('SURF')};
    color: {_c('DIM')};
    border: 1px solid {_c('BORDER')};
}}
QPushButton:hover {{
    background: {_c('BTN1B')};
    color: {_c('ACCENT1')};
    border-color: {_c('ACCENT1')};
}}
QPushButton:disabled {{
    color: {_c('BORDER')};
    border-color: {_c('SURF2')};
    background: {_c('SURF')};
}}
"""


def _btn_update() -> str:
    return f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2A')}, stop:1 {_c('BTN2B')});
    color: {_c('ACCENT3')};
    border: 1px solid {_c('ACCENT2')};
    border-radius: 12px;
    padding: 8px 18px;
    font-size: 12px;
    letter-spacing: 1px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2H')}, stop:1 {_c('BTN2A')});
    border-color: {_c('ACCENT3')};
    color: #ffffff;
}}
QPushButton:disabled {{
    color: {_c('DIM')};
    border-color: {_c('BORDER')};
    background: {_c('SURF')};
}}
"""


def _btn_dialog_ok() -> str:
    return f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN1A')}, stop:1 {_c('BTN1B')});
    color: {_c('TEXT')};
    border: 1px solid {_c('ACCENT1')};
    border-radius: 12px;
    padding: 6px 22px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN1H')}, stop:1 {_c('BTN1A')});
    border-color: {_c('ACCENT2')};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('ACCENT1')}, stop:1 {_c('BTN1B')});
}}
"""


def _btn_loop_inactive() -> str:
    return f"""
QPushButton {{
    background: {_c('SURF')};
    color: {_c('DIM')};
    border: 1px solid {_c('BORDER')};
    border-radius: 8px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    min-width: 28px;
}}
QPushButton:hover {{
    background: {_c('SURF2')};
    color: {_c('TEXT')};
    border-color: {_c('ACCENT1')};
}}
QPushButton:disabled {{
    color: {_c('BORDER')};
    border-color: {_c('SURF')};
    background: {_c('SURF')};
}}
"""


def _btn_loop_active() -> str:
    return f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {_c('BTN2A')}, stop:1 {_c('BTN2B')});
    color: {_c('ACCENT3')};
    border: 1px solid {_c('ACCENT2')};
    border-radius: 8px;
    padding: 3px 9px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    min-width: 28px;
}}
QPushButton:disabled {{
    color: {_c('DIM')};
    border-color: {_c('BORDER')};
    background: {_c('SURF2')};
}}
"""


# Fixed preview styles for theme selector buttons (always show their own colors)
_THEME_BTN_STYLES = {
    'Phoenix Fire': {
        'idle':   "background:#2d1000;color:#e85a00;border:2px solid #3d1800;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
        'active': "background:#4a1800;color:#ff9a00;border:2px solid #e85a00;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
    },
    'Midnight Ocean': {
        'idle':   "background:#001830;color:#00c8e8;border:2px solid #0d3555;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
        'active': "background:#004d6a;color:#c0eeff;border:2px solid #00c8e8;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
    },
    'Neon Storm': {
        'idle':   "background:#0d0018;color:#f02090;border:2px solid #3d0060;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
        'active': "background:#880055;color:#bbff44;border:2px solid #f02090;"
                  "border-radius:10px;padding:6px 12px;font-size:12px;font-weight:bold;",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Recorder
# ─────────────────────────────────────────────────────────────────────────────
class Recorder(QObject):
    """Captures global mouse and keyboard events into a list."""
    hotkey_stop = pyqtSignal()

    MOVE_INTERVAL = 0.033

    def __init__(self):
        super().__init__()
        self.events: list = []
        self._start: float = 0.0
        self._last_move: float = 0.0
        self._lock = threading.Lock()
        self._listeners: list = []
        self.recording = False
        self._stop_key_str = 'Key.f9'

    def start(self):
        self.events = []
        self._start = time.perf_counter()
        self._last_move = 0.0
        self.recording = True

        rec = self

        def on_move(x, y):
            now = time.perf_counter()
            if now - rec._last_move < rec.MOVE_INTERVAL:
                return
            rec._last_move = now
            rec._push({'type': 'move', 'x': x, 'y': y,
                       't': now - rec._start})

        def on_click(x, y, button, pressed):
            rec._push({'type': 'click', 'x': x, 'y': y,
                       'btn': str(button), 'dn': pressed,
                       't': time.perf_counter() - rec._start})

        def on_scroll(x, y, dx, dy):
            rec._push({'type': 'scroll', 'x': x, 'y': y,
                       'dx': dx, 'dy': dy,
                       't': time.perf_counter() - rec._start})

        def on_press(key):
            try:
                stop_key = parse_pynput_key(rec._stop_key_str)
                if stop_key is not None and key == stop_key:
                    rec.hotkey_stop.emit()
                    return
            except Exception:
                pass
            try:
                k = key.char
            except AttributeError:
                k = str(key)
            rec._push({'type': 'kdn', 'k': k,
                       't': time.perf_counter() - rec._start})

        def on_release(key):
            try:
                if key == Key.f9:
                    return
            except Exception:
                pass
            try:
                k = key.char
            except AttributeError:
                k = str(key)
            rec._push({'type': 'kup', 'k': k,
                       't': time.perf_counter() - rec._start})

        ml = pm.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        kl = pk.Listener(on_press=on_press, on_release=on_release)
        self._listeners = [ml, kl]
        ml.start()
        kl.start()

    def stop(self) -> list:
        self.recording = False
        for lst in self._listeners:
            try:
                lst.stop()
            except Exception:
                pass
        self._listeners = []
        return list(self.events)

    def save(self, name: str) -> Path:
        filepath = SCRIPTS_DIR / f"{name}.json"
        duration = round(self.events[-1]['t'], 3) if self.events else 0.0
        payload = {
            'name': name,
            'recorded_at': datetime.now().isoformat(timespec='seconds'),
            'event_count': len(self.events),
            'duration': duration,
            'events': self.events,
        }
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, separators=(',', ':'))
        return filepath

    def _push(self, event: dict):
        if self.recording:
            with self._lock:
                self.events.append(event)


# ─────────────────────────────────────────────────────────────────────────────
# Player
# ─────────────────────────────────────────────────────────────────────────────
class Player(QThread):
    progress = pyqtSignal(int, int)
    error    = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        try:
            with open(self.filepath, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            events = data['events']
            total  = len(events)
            mc = MC()
            kc = KC()
            t0 = time.perf_counter()

            for idx, ev in enumerate(events):
                if self._abort:
                    break

                wait = ev['t'] - (time.perf_counter() - t0)
                if wait > 0.0:
                    end = time.perf_counter() + wait
                    while time.perf_counter() < end and not self._abort:
                        time.sleep(min(0.04, end - time.perf_counter()))

                if self._abort:
                    break

                etype = ev['type']

                if etype == 'move':
                    mc.position = (ev['x'], ev['y'])
                elif etype == 'click':
                    mc.position = (ev['x'], ev['y'])
                    btn = self._btn(ev['btn'])
                    if ev['dn']:
                        mc.press(btn)
                    else:
                        mc.release(btn)
                elif etype == 'scroll':
                    mc.position = (ev['x'], ev['y'])
                    mc.scroll(ev['dx'], ev['dy'])
                elif etype == 'kdn':
                    key = self._key(ev['k'])
                    if key is not None:
                        kc.press(key)
                elif etype == 'kup':
                    key = self._key(ev['k'])
                    if key is not None:
                        kc.release(key)

                self.progress.emit(idx + 1, total)

        except Exception as exc:
            self.error.emit(str(exc))

        self.finished.emit()

    @staticmethod
    def _btn(s: str) -> Button:
        if 'right'  in s: return Button.right
        if 'middle' in s: return Button.middle
        return Button.left

    @staticmethod
    def _key(s: str):
        return parse_pynput_key(s)


# ─────────────────────────────────────────────────────────────────────────────
# GlobalHotkeys
# ─────────────────────────────────────────────────────────────────────────────
class GlobalHotkeys(QObject):
    hotkey_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._listener = None

    def start(self, key_str: str = 'Key.f10'):
        target = parse_pynput_key(key_str)
        obj = self

        def on_press(key):
            try:
                if key == target:
                    obj.hotkey_triggered.emit()
            except Exception:
                pass

        self._listener = pk.Listener(on_press=on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


# ─────────────────────────────────────────────────────────────────────────────
# UpdateChecker
# ─────────────────────────────────────────────────────────────────────────────
class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)

    def run(self):
        try:
            import urllib.request
            import ssl as _ssl

            try:
                import certifi
                ctx = _ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = _ssl.create_default_context()

            req = urllib.request.Request(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                headers={"User-Agent": "PhoenixMacro-Updater/1.0"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "").lstrip("v")
            if not tag:
                return

            url = next(
                (a["browser_download_url"]
                 for a in data.get("assets", [])
                 if a.get("name", "").lower().endswith(".exe")),
                None,
            )
            if not url:
                return

            def _ver(s):
                if not s:
                    return None
                try:
                    return tuple(int(x) for x in s.split("."))
                except Exception:
                    return None

            lv, rv = _ver(VERSION), _ver(tag)
            if lv is not None and rv is not None and rv > lv:
                self.update_available.emit(tag, url)

        except Exception:
            try:
                import traceback
                log = BASE_DIR / "phoenix_update.log"
                log.write_text(traceback.format_exc(), encoding="utf-8")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Downloader
# ─────────────────────────────────────────────────────────────────────────────
class Downloader(QThread):
    progress = pyqtSignal(int)
    done     = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self.url    = url
        self.dest   = dest
        self._abort = False

    def stop(self):
        self._abort = True

    def run(self):
        try:
            import urllib.request
            import ssl as _ssl

            try:
                import certifi
                ctx = _ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                ctx = _ssl.create_default_context()

            req = urllib.request.Request(
                self.url,
                headers={"User-Agent": "PhoenixMacro-Updater/1.0"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length") or 0)
                done  = 0
                with open(self.dest, "wb") as fh:
                    while not self._abort:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        fh.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progress.emit(min(99, done * 100 // total))

            if self._abort:
                try:
                    Path(self.dest).unlink(missing_ok=True)
                except Exception:
                    pass
                return

            dest_path = Path(self.dest)
            file_size = dest_path.stat().st_size
            with open(self.dest, "rb") as fh:
                magic = fh.read(2)
            if magic != b"MZ" or file_size < 1_000_000:
                dest_path.unlink(missing_ok=True)
                self.error.emit(
                    f"Downloaded file is invalid (size={file_size}, magic={magic!r}).\n"
                    "The file may have been blocked by antivirus or the download was corrupted.\n"
                    "Please download the update manually from GitHub."
                )
                return

            self.progress.emit(100)
            self.done.emit(self.dest)

        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# AppSettings
# ─────────────────────────────────────────────────────────────────────────────
class AppSettings:
    _DEFAULTS = {
        'hotkey_record_stop': 'Key.f9',
        'hotkey_play_toggle': 'Key.f10',
        'theme':              'Phoenix Fire',
    }

    def __init__(self):
        self._data = dict(self._DEFAULTS)
        self._load()

    def _load(self):
        try:
            if SETTINGS_FILE.exists():
                raw = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
                for k in self._DEFAULTS:
                    if k in raw:
                        self._data[k] = raw[k]
        except Exception:
            pass

    def save(self):
        try:
            SETTINGS_FILE.write_text(
                json.dumps(self._data, indent=2), encoding='utf-8')
        except Exception:
            pass

    def get(self, key: str) -> str:
        return self._data.get(key, self._DEFAULTS.get(key, ''))

    def set(self, key: str, value: str):
        if key in self._DEFAULTS:
            self._data[key] = value


# ─────────────────────────────────────────────────────────────────────────────
# NameDialog
# ─────────────────────────────────────────────────────────────────────────────
class NameDialog(QDialog):
    def __init__(self, parent=None, default: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Save Script")
        self.setModal(True)
        self.setFixedSize(420, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {_c('SURF')};
                border: 1px solid {_c('BORDER')};
            }}
            QLabel {{
                color: {_c('TEXT')};
                font-size: 13px;
                background: transparent;
            }}
            QLineEdit {{
                background-color: {_c('SURF2')};
                color: {_c('TEXT')};
                border: 1px solid {_c('BORDER')};
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 13px;
                selection-background-color: {_c('ACCENT1')};
            }}
            QLineEdit:focus {{
                border-color: {_c('ACCENT2')};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)

        self._lbl = QLabel("Enter a name for this script:")
        layout.addWidget(self._lbl)

        self._inp = QLineEdit(default)
        self._inp.selectAll()
        layout.addWidget(self._inp)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(_btn_delete())
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.setStyleSheet(_btn_dialog_ok())
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        row.addWidget(btn_save)

        layout.addLayout(row)
        self._inp.returnPressed.connect(self.accept)

    def get_name(self) -> str:
        return self._inp.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
# ConfirmDialog
# ─────────────────────────────────────────────────────────────────────────────
class ConfirmDialog(QDialog):
    def __init__(self, parent=None, title: str = "Confirm", message: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(380, 140)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(
            f"QDialog {{ background-color: {_c('SURF')}; border: 1px solid {_c('BORDER')}; }}"
            f"QLabel  {{ color: {_c('TEXT')}; font-size: 13px; background: transparent; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)
        layout.addWidget(QLabel(message))

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()

        btn_no = QPushButton("No")
        btn_no.setStyleSheet(_btn_delete())
        btn_no.setFixedHeight(36)
        btn_no.setCursor(Qt.PointingHandCursor)
        btn_no.clicked.connect(self.reject)
        row.addWidget(btn_no)

        btn_yes = QPushButton("Yes, Delete")
        btn_yes.setStyleSheet(_btn_dialog_ok())
        btn_yes.setFixedHeight(36)
        btn_yes.setCursor(Qt.PointingHandCursor)
        btn_yes.clicked.connect(self.accept)
        row.addWidget(btn_yes)

        layout.addLayout(row)


# ─────────────────────────────────────────────────────────────────────────────
# ActionEditorDialog
# ─────────────────────────────────────────────────────────────────────────────
class ActionEditorDialog(QDialog):
    def __init__(self, parent=None, filepath: str = ""):
        super().__init__(parent)
        self._filepath    = filepath
        self._events: list = []
        self._script_data: dict = {}

        self.setWindowTitle("Edit Script")
        self.setModal(True)
        self.resize(660, 520)
        self.setMinimumSize(520, 380)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog  {{ background: {_c('SURF')}; border: 1px solid {_c('BORDER')}; }}
            QLabel   {{ color: {_c('TEXT')}; font-size: 13px; background: transparent; }}
            QListWidget {{
                background: {_c('BG')};
                border: 1px solid {_c('BORDER')};
                border-radius: 8px;
                color: {_c('TEXT')};
                font-size: 12px;
                font-family: 'Courier New', Consolas, monospace;
                selection-background-color: {_c('BTN2B')};
                outline: none;
            }}
            QListWidget::item {{
                padding: 3px 10px;
                border-radius: 3px;
            }}
            QListWidget::item:selected {{
                background: {_c('BTN2B')};
                color: {_c('ACCENT3')};
                border-left: 3px solid {_c('ACCENT2')};
            }}
            QScrollBar:vertical {{
                background: {_c('SURF')}; width: 7px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {_c('BORDER')}; border-radius: 3px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        tr = QHBoxLayout()
        self._title_lbl = QLabel("SCRIPT EDITOR")
        self._title_lbl.setStyleSheet(
            f"color: {_c('ACCENT3')}; font-size: 14px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        tr.addWidget(self._title_lbl)
        tr.addStretch()
        self._count_lbl = QLabel("")
        self._count_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 11px; background: transparent;")
        tr.addWidget(self._count_lbl)
        lay.addLayout(tr)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        lay.addWidget(self._list)

        bot = QHBoxLayout()
        bot.setSpacing(10)

        self._btn_del_ev = QPushButton("✕  DELETE SELECTED")
        self._btn_del_ev.setStyleSheet(_btn_delete())
        self._btn_del_ev.setFixedHeight(34)
        self._btn_del_ev.setCursor(Qt.PointingHandCursor)
        self._btn_del_ev.setEnabled(False)
        self._btn_del_ev.clicked.connect(self._on_delete_selected)
        bot.addWidget(self._btn_del_ev)

        bot.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(_btn_delete())
        btn_cancel.setFixedHeight(34)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        bot.addWidget(btn_cancel)

        self._btn_save = QPushButton("Save Changes")
        self._btn_save.setStyleSheet(_btn_dialog_ok())
        self._btn_save.setFixedHeight(34)
        self._btn_save.setCursor(Qt.PointingHandCursor)
        self._btn_save.clicked.connect(self._on_save)
        bot.addWidget(self._btn_save)

        lay.addLayout(bot)

        self._list.itemSelectionChanged.connect(
            lambda: self._btn_del_ev.setEnabled(
                bool(self._list.selectedItems())))

        self._load_events()

    def _load_events(self):
        self._list.clear()
        try:
            with open(self._filepath, 'r', encoding='utf-8') as fh:
                self._script_data = json.load(fh)
            self._events = list(self._script_data.get('events', []))
            name = self._script_data.get('name', Path(self._filepath).stem)
            self._title_lbl.setText(f"EDIT:  {name}")
        except Exception as exc:
            self._events = []
            self._title_lbl.setText(f"ERROR: {exc}")

        self._rebuild_list()

    def _rebuild_list(self):
        self._list.clear()
        for i, ev in enumerate(self._events):
            item = QListWidgetItem(self._fmt(ev, i + 1))
            item.setData(Qt.UserRole, i)
            self._list.addItem(item)
        self._update_count()

    @staticmethod
    def _fmt(ev: dict, idx: int) -> str:
        t     = ev.get('t', 0.0)
        etype = ev.get('type', '?')
        if etype == 'move':
            return (f"  #{idx:5d}   {t:8.3f}s"
                    f"   MOVE           ({ev.get('x',0)}, {ev.get('y',0)})")
        if etype == 'click':
            b = ('RIGHT ' if 'right' in ev.get('btn', '')
                 else 'MIDDLE' if 'middle' in ev.get('btn', '')
                 else 'LEFT  ')
            a = '↓' if ev.get('dn') else '↑'
            return (f"  #{idx:5d}   {t:8.3f}s"
                    f"   CLICK {b} {a}   ({ev.get('x',0)}, {ev.get('y',0)})")
        if etype == 'scroll':
            return (f"  #{idx:5d}   {t:8.3f}s"
                    f"   SCROLL         ({ev.get('x',0)}, {ev.get('y',0)})"
                    f"  dy={ev.get('dy',0)}")
        if etype in ('kdn', 'kup'):
            a = '↓' if etype == 'kdn' else '↑'
            k = ev.get('k', '')
            k_d = (k.replace('Key.', '').upper()
                   if k.startswith('Key.') else (k.upper() if len(k) == 1 else k))
            return f"  #{idx:5d}   {t:8.3f}s   KEY {a}  {k_d}"
        return f"  #{idx:5d}   {t:8.3f}s   {etype}"

    def _update_count(self):
        total = len(self._events)
        dur   = self._events[-1]['t'] if self._events else 0.0
        self._count_lbl.setText(f"{total} events  ·  {dur:.1f}s")

    def _on_delete_selected(self):
        rows = sorted(
            {self._list.row(it) for it in self._list.selectedItems()},
            reverse=True)
        for r in rows:
            self._events.pop(r)
        self._rebuild_list()
        self._btn_del_ev.setEnabled(False)

    def _on_save(self):
        try:
            self._script_data['events']      = self._events
            self._script_data['event_count'] = len(self._events)
            self._script_data['duration'] = (
                round(self._events[-1]['t'], 3) if self._events else 0.0)
            with open(self._filepath, 'w', encoding='utf-8') as fh:
                json.dump(self._script_data, fh, separators=(',', ':'))
            self.accept()
        except Exception as exc:
            self._count_lbl.setText(f"Save error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# SettingsDialog
# ─────────────────────────────────────────────────────────────────────────────
class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()
    install_update = pyqtSignal(str, str)

    def __init__(self, parent=None, settings: 'AppSettings' = None,
                 update_info: tuple = None):
        super().__init__(parent)
        self._settings       = settings
        self._update_info    = update_info
        self._pending        = {
            'record_stop': settings.get('hotkey_record_stop') if settings else 'Key.f9',
            'play_toggle': settings.get('hotkey_play_toggle') if settings else 'Key.f10',
        }
        self._pending_theme    = settings.get('theme') if settings else 'Phoenix Fire'
        self._capture_target   = None
        self._capture_listener = None
        self._upd_checker      = None
        self._theme_btns: dict = {}

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(620, 530)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{ background: {_c('SURF')}; border: 1px solid {_c('BORDER')}; }}
            QLabel  {{ color: {_c('TEXT')}; font-size: 13px; background: transparent; }}
            QFrame  {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};
                       border-radius: 10px; }}
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(14)

        # Title
        ttl = QLabel("⚙  SETTINGS")
        ttl.setStyleSheet(
            f"color: {_c('ACCENT3')}; font-size: 15px; font-weight: bold;"
            f" letter-spacing: 3px; background: transparent;")
        lay.addWidget(ttl)

        # ── Theme section ──────────────────────────────────────────────────
        lay.addWidget(self._section_lbl("THEME"))
        theme_frame = QFrame()
        theme_frame.setStyleSheet(
            f"QFrame {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};"
            f" border-radius: 10px; }}"
            f"QLabel {{ background: transparent; color: {_c('DIM')};"
            f" font-size: 11px; border: none; }}")
        tf_lay = QVBoxLayout(theme_frame)
        tf_lay.setContentsMargins(14, 12, 14, 12)
        tf_lay.setSpacing(8)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(8)
        for name, icons in [('Phoenix Fire', '🔥'), ('Midnight Ocean', '🌊'), ('Neon Storm', '⚡')]:
            btn = QPushButton(f"{icons}  {name}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(38)
            btn.clicked.connect(lambda _, n=name: self._select_theme(n))
            self._theme_btns[name] = btn
            theme_row.addWidget(btn)
        tf_lay.addLayout(theme_row)

        theme_hint = QLabel("Applies immediately when you click Apply.")
        theme_hint.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 10px; letter-spacing: 1px;"
            f" background: transparent; border: none;")
        tf_lay.addWidget(theme_hint)
        lay.addWidget(theme_frame)

        self._refresh_theme_btns()

        # ── Hotkeys section ────────────────────────────────────────────────
        lay.addWidget(self._section_lbl("HOTKEYS"))
        hk = QFrame()
        hk.setStyleSheet(
            f"QFrame {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};"
            f" border-radius: 10px; }}"
            f"QLabel {{ background: transparent; color: {_c('TEXT')};"
            f" font-size: 12px; border: none; }}")
        hk_lay = QVBoxLayout(hk)
        hk_lay.setContentsMargins(16, 12, 16, 12)
        hk_lay.setSpacing(10)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Stop recording:"))
        r1.addStretch()
        self._btn_rec_key = self._hotkey_btn(
            self._pending['record_stop'], 'record_stop')
        r1.addWidget(self._btn_rec_key)
        hk_lay.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Start / stop playback:"))
        r2.addStretch()
        self._btn_play_key = self._hotkey_btn(
            self._pending['play_toggle'], 'play_toggle')
        r2.addWidget(self._btn_play_key)
        hk_lay.addLayout(r2)

        hint = QLabel("Click a key button, then press any keyboard key to rebind.")
        hint.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 10px; letter-spacing: 1px;"
            f" background: transparent; border: none;")
        hk_lay.addWidget(hint)
        lay.addWidget(hk)

        # ── Updates section ────────────────────────────────────────────────
        lay.addWidget(self._section_lbl("UPDATES"))
        upd = QFrame()
        upd.setStyleSheet(
            f"QFrame {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};"
            f" border-radius: 10px; }}"
            f"QLabel {{ background: transparent; color: {_c('TEXT')};"
            f" font-size: 12px; border: none; }}")
        upd_lay = QVBoxLayout(upd)
        upd_lay.setContentsMargins(16, 12, 16, 12)
        upd_lay.setSpacing(8)

        ver_row = QHBoxLayout()
        ver_row.addWidget(QLabel("Current version:"))
        ver_row.addStretch()
        vl = QLabel(f"v{VERSION}")
        vl.setStyleSheet(
            f"color: {_c('ACCENT3')}; font-size: 12px; background: transparent; border: none;")
        ver_row.addWidget(vl)
        upd_lay.addLayout(ver_row)

        chk_row = QHBoxLayout()
        self._upd_status = QLabel("—")
        self._upd_status.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 11px; background: transparent; border: none;")
        chk_row.addWidget(self._upd_status)
        chk_row.addStretch()
        self._btn_check = QPushButton("Check for Updates")
        self._btn_check.setStyleSheet(_btn_update())
        self._btn_check.setFixedHeight(32)
        self._btn_check.setMinimumWidth(160)
        self._btn_check.setCursor(Qt.PointingHandCursor)
        self._btn_check.clicked.connect(self._on_check_updates)
        chk_row.addWidget(self._btn_check)
        upd_lay.addLayout(chk_row)

        self._inst_widget = QWidget()
        self._inst_widget.setStyleSheet("background: transparent;")
        inst_row = QHBoxLayout(self._inst_widget)
        inst_row.setContentsMargins(0, 0, 0, 0)
        self._new_ver_lbl = QLabel("")
        self._new_ver_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 12px; background: transparent;")
        inst_row.addWidget(self._new_ver_lbl)
        inst_row.addStretch()
        self._btn_install = QPushButton("↑  Install Update")
        self._btn_install.setStyleSheet(_btn_dialog_ok())
        self._btn_install.setFixedHeight(32)
        self._btn_install.setMinimumWidth(160)
        self._btn_install.setCursor(Qt.PointingHandCursor)
        self._btn_install.clicked.connect(self._on_install)
        inst_row.addWidget(self._btn_install)
        self._inst_widget.setVisible(False)
        upd_lay.addWidget(self._inst_widget)

        lay.addWidget(upd)
        lay.addStretch()

        # Bottom buttons
        bot = QHBoxLayout()
        bot.setSpacing(10)
        bot.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(_btn_delete())
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self._on_cancel)
        bot.addWidget(btn_cancel)

        btn_apply = QPushButton("Apply")
        btn_apply.setStyleSheet(_btn_dialog_ok())
        btn_apply.setFixedHeight(36)
        btn_apply.setCursor(Qt.PointingHandCursor)
        btn_apply.clicked.connect(self._on_apply)
        bot.addWidget(btn_apply)

        lay.addLayout(bot)

        if update_info:
            self._show_update(update_info[0], update_info[1])

    # ── theme selector ─────────────────────────────────────────────────────
    def _select_theme(self, name: str):
        self._pending_theme = name
        self._refresh_theme_btns()

    def _refresh_theme_btns(self):
        for name, btn in self._theme_btns.items():
            styles = _THEME_BTN_STYLES.get(name, {})
            if name == self._pending_theme:
                btn.setStyleSheet(styles.get('active', ''))
            else:
                btn.setStyleSheet(styles.get('idle', ''))

    # ── helpers ────────────────────────────────────────────────────────────
    def _section_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 10px; font-weight: bold;"
            f" letter-spacing: 3px; background: transparent;")
        return lbl

    def _hotkey_btn(self, key_str: str, target_id: str) -> QPushButton:
        btn = QPushButton(key_to_display(key_str))
        btn.setStyleSheet(_btn_loop_inactive())
        btn.setFixedSize(88, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("tid", target_id)
        btn.clicked.connect(lambda: self._start_capture(target_id, btn))
        return btn

    # ── hotkey capture ─────────────────────────────────────────────────────
    def _start_capture(self, target_id: str, btn: QPushButton):
        if self._capture_listener:
            return
        self._capture_target = target_id
        btn.setText("Press a key…")
        btn.setStyleSheet(_btn_loop_active())

        dlg = self

        def on_press(key):
            try:
                if hasattr(key, 'char') and key.char and len(key.char) == 1:
                    ks = key.char
                else:
                    ks = str(key)
            except Exception:
                ks = str(key)
            QTimer.singleShot(0, lambda: dlg._apply_capture(ks, btn))
            return False

        if HAS_PYNPUT:
            self._capture_listener = pk.Listener(on_press=on_press)
            self._capture_listener.daemon = True
            self._capture_listener.start()
        else:
            btn.setText(key_to_display(self._pending.get(target_id, '')))
            btn.setStyleSheet(_btn_loop_inactive())

    def _apply_capture(self, key_str: str, btn: QPushButton):
        if self._capture_listener:
            try:
                self._capture_listener.stop()
            except Exception:
                pass
            self._capture_listener = None
        self._pending[self._capture_target] = key_str
        self._capture_target = None
        btn.setText(key_to_display(key_str))
        btn.setStyleSheet(_btn_loop_inactive())

    # ── update check ───────────────────────────────────────────────────────
    def _on_check_updates(self):
        self._btn_check.setEnabled(False)
        self._btn_check.setText("Checking…")
        self._upd_status.setText("Checking for updates…")
        self._inst_widget.setVisible(False)

        self._upd_checker = UpdateChecker()
        self._upd_checker.update_available.connect(self._on_update_found)
        self._upd_checker.finished.connect(self._on_check_done)
        self._upd_checker.start()

    def _on_check_done(self):
        self._btn_check.setEnabled(True)
        self._btn_check.setText("Check for Updates")
        if not self._inst_widget.isVisible():
            self._upd_status.setText("Up to date  ✓")

    def _on_update_found(self, version: str, url: str):
        self._show_update(version, url)

    def _show_update(self, version: str, url: str):
        self._upd_status.setText("")
        self._new_ver_lbl.setText(f"v{version} available")
        self._btn_install.setProperty("_url",     url)
        self._btn_install.setProperty("_version", version)
        self._inst_widget.setVisible(True)

    def _on_install(self):
        url     = self._btn_install.property("_url")
        version = self._btn_install.property("_version")
        if url:
            self.install_update.emit(version, url)
            self.accept()

    # ── apply / cancel ─────────────────────────────────────────────────────
    def _on_apply(self):
        self._stop_capture_if_active()
        if self._settings:
            self._settings.set('hotkey_record_stop', self._pending['record_stop'])
            self._settings.set('hotkey_play_toggle', self._pending['play_toggle'])
            self._settings.set('theme', self._pending_theme)
            self._settings.save()
        self.settings_saved.emit()
        self.accept()

    def _on_cancel(self):
        self._stop_capture_if_active()
        self.reject()

    def _stop_capture_if_active(self):
        if self._capture_listener:
            try:
                self._capture_listener.stop()
            except Exception:
                pass
            self._capture_listener = None

    def closeEvent(self, event):
        self._stop_capture_if_active()
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
class PhoenixMacro(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings  = AppSettings()
        _load_theme(self._settings.get('theme'))

        self._recorder  = Recorder() if HAS_PYNPUT else None
        self._player: Player | None = None
        self._recording = False
        self._playing   = False
        self._tick_t0   = 0.0
        self._update_info: tuple | None = None

        self._loop_count        = 1
        self._loop_current      = 0
        self._start_delay_s     = 3
        self._loop_delay_s      = 0
        self._loop_aborted      = False
        self._current_script    = ""

        self._countdown_val   = 0
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._countdown_tick)

        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_on = True

        if HAS_PYNPUT:
            self._recorder._stop_key_str = self._settings.get('hotkey_record_stop')
            self._recorder.hotkey_stop.connect(self._stop_recording)
            self._hotkeys = GlobalHotkeys()
            self._hotkeys.hotkey_triggered.connect(self._on_f10)
            self._hotkeys.start(self._settings.get('hotkey_play_toggle'))
        else:
            self._hotkeys = None

        self._build_ui()
        self._refresh_scripts()

        self._downloader: Downloader | None = None
        self._upd_checker = UpdateChecker()
        self._upd_checker.update_available.connect(self._on_update_available)
        self._upd_checker.start()

    # ── UI Construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self.setWindowTitle("Phoenix Macro")
        self.setMinimumSize(860, 500)
        self.resize(960, 560)
        self.setStyleSheet(_app_style())
        self.setWindowIcon(self._make_icon())

        self._root = QWidget()
        self._root.setObjectName("root")
        self._root.setStyleSheet(
            f"QWidget#root {{ background: qlineargradient("
            f"x1:0,y1:0,x2:1,y2:1, stop:0 {_c('BG_TOP')},"
            f" stop:0.5 {_c('BG_MID')}, stop:1 {_c('BG')}); }}")
        self.setCentralWidget(self._root)

        vbox = QVBoxLayout(self._root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # Full-width header
        self._header = self._build_header()
        vbox.addWidget(self._header)

        # Main horizontal split
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 16)
        body_lay.setSpacing(14)

        # Left panel (script library) — stretch 3
        self._left_frame = self._build_left_panel()
        body_lay.addWidget(self._left_frame, 3)

        # Right panel (controls) — stretch 2
        self._right_frame = self._build_right_panel()
        body_lay.addWidget(self._right_frame, 2)

        vbox.addWidget(body, 1)

    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setObjectName("hdr")
        hdr.setFixedHeight(76)
        hdr.setStyleSheet(f"""
            QWidget#hdr {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {_c('BG_TOP')}, stop:1 {_c('BG_MID')});
                border-bottom: 1px solid {_c('BORDER')};
            }}
        """)
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(22, 0, 18, 0)
        lay.setSpacing(14)

        # Flame emoji
        flame = QLabel("🔥")
        flame.setStyleSheet("font-size: 28px; background: transparent;")
        lay.addWidget(flame)

        # Title block
        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        title = QLabel("PHOENIX MACRO")
        title.setStyleSheet(f"""
            color: {_c('ACCENT3')};
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 5px;
            background: transparent;
        """)
        title_col.addWidget(title)

        sub = QLabel("MOUSE  &  KEYBOARD  RECORDER")
        sub.setStyleSheet(f"""
            color: {_c('DIM')};
            font-size: 9px;
            letter-spacing: 3px;
            background: transparent;
        """)
        title_col.addWidget(sub)

        lay.addLayout(title_col)
        lay.addStretch()

        # Version badge
        ver_lbl = QLabel(f"v{VERSION}")
        ver_lbl.setStyleSheet(f"""
            color: {_c('DIM')};
            font-size: 10px;
            background: transparent;
            padding: 2px 8px;
            border: 1px solid {_c('BORDER')};
            border-radius: 6px;
        """)
        lay.addWidget(ver_lbl)

        # Settings button
        self._btn_settings = QPushButton("⚙")
        self._btn_settings.setToolTip("Settings")
        self._btn_settings.setStyleSheet(self._settings_btn_style())
        self._btn_settings.setCursor(Qt.PointingHandCursor)
        self._btn_settings.clicked.connect(self._open_settings)
        lay.addWidget(self._btn_settings)

        return hdr

    def _settings_btn_style(self) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {_c('DIM')};
                border: 1px solid {_c('BORDER')};
                border-radius: 10px;
                font-size: 18px;
                padding: 2px 12px;
            }}
            QPushButton:hover {{
                color: {_c('ACCENT3')};
                border-color: {_c('ACCENT2')};
                background: {_c('SURF2')};
            }}
            QPushButton:pressed {{
                background: {_c('BTN2B')};
            }}
        """

    def _panel_style(self) -> str:
        return f"""
            QFrame {{
                background: {_c('SURF')};
                border: 1px solid {_c('BORDER')};
                border-radius: 14px;
            }}
        """

    def _build_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(self._panel_style())
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # ── Panel header row: title + script count badge ───────────────────
        hrow = QHBoxLayout()
        hrow.setSpacing(8)

        panel_title = QLabel("SCRIPT LIBRARY")
        panel_title.setStyleSheet(f"""
            color: {_c('ACCENT2')};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 3px;
            background: transparent;
        """)
        hrow.addWidget(panel_title)
        hrow.addStretch()

        self._script_count_badge = QLabel("0 scripts")
        self._script_count_badge.setStyleSheet(f"""
            color: {_c('DIM')};
            font-size: 10px;
            background: {_c('SURF2')};
            border: 1px solid {_c('BORDER')};
            border-radius: 8px;
            padding: 2px 8px;
        """)
        hrow.addWidget(self._script_count_badge)
        lay.addLayout(hrow)

        # ── Search box ─────────────────────────────────────────────────────
        self._search_inp = QLineEdit()
        self._search_inp.setPlaceholderText("Search scripts…")
        self._search_inp.setClearButtonEnabled(True)
        self._search_inp.setFixedHeight(32)
        self._search_inp.setStyleSheet(f"""
            QLineEdit {{
                background: {_c('BG')};
                color: {_c('TEXT')};
                border: 1px solid {_c('BORDER')};
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
                selection-background-color: {_c('ACCENT1')};
            }}
            QLineEdit:focus {{ border-color: {_c('ACCENT2')}; }}
        """)
        self._search_inp.textChanged.connect(self._on_search_changed)
        lay.addWidget(self._search_inp)

        # ── Script list ────────────────────────────────────────────────────
        self._list = QListWidget()
        self._list.setMinimumHeight(120)
        self._list.itemSelectionChanged.connect(self._on_sel_changed)
        self._list.itemDoubleClicked.connect(self._on_rename_script)
        lay.addWidget(self._list, 1)

        # ── Meta info ──────────────────────────────────────────────────────
        self._meta_lbl = QLabel("")
        self._meta_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 11px; "
            f"padding: 2px 4px; background: transparent;")
        lay.addWidget(self._meta_lbl)

        # ── Bottom action row ──────────────────────────────────────────────
        bot = QHBoxLayout()
        bot.setSpacing(8)

        self._btn_del = QPushButton("✕  DELETE")
        self._btn_del.setStyleSheet(_btn_delete())
        self._btn_del.setMinimumHeight(34)
        self._btn_del.setCursor(Qt.PointingHandCursor)
        self._btn_del.setEnabled(False)
        self._btn_del.clicked.connect(self._on_delete)
        bot.addWidget(self._btn_del)

        self._btn_edit = QPushButton("✎  EDIT SCRIPT")
        self._btn_edit.setStyleSheet(_btn_delete())
        self._btn_edit.setMinimumHeight(34)
        self._btn_edit.setCursor(Qt.PointingHandCursor)
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self._on_edit_script)
        bot.addWidget(self._btn_edit)

        bot.addStretch()
        lay.addLayout(bot)

        return frame

    def _build_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(self._panel_style())
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        # ── Status card ────────────────────────────────────────────────────
        self._status_card = self._build_status_card()
        lay.addWidget(self._status_card)

        # ── CREATE button ──────────────────────────────────────────────────
        self._btn_create = QPushButton("⬤   CREATE SCRIPT")
        self._btn_create.setStyleSheet(_btn_create_idle())
        self._btn_create.setMinimumHeight(50)
        self._btn_create.setCursor(Qt.PointingHandCursor)
        self._btn_create.clicked.connect(self._on_create)
        lay.addWidget(self._btn_create)

        # ── Loop / delay panel ─────────────────────────────────────────────
        self._loop_panel = self._build_loop_panel()
        lay.addWidget(self._loop_panel)

        # ── START button ───────────────────────────────────────────────────
        self._btn_start = QPushButton("▶   START SCRIPT")
        self._btn_start.setStyleSheet(_btn_start_idle())
        self._btn_start.setMinimumHeight(50)
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        lay.addWidget(self._btn_start)

        # ── Hint + progress row ────────────────────────────────────────────
        hint_row = QHBoxLayout()
        stop_key = key_to_display(self._settings.get('hotkey_record_stop'))
        play_key = key_to_display(self._settings.get('hotkey_play_toggle'))
        self._hint_lbl = QLabel(
            f"{stop_key} — stop rec   ·   {play_key} — play / stop")
        self._hint_lbl.setAlignment(Qt.AlignLeft)
        self._hint_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 10px; "
            f"letter-spacing: 1px; background: transparent;")
        hint_row.addWidget(self._hint_lbl)
        hint_row.addStretch()

        self._prog_lbl = QLabel("")
        self._prog_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 11px; background: transparent;")
        hint_row.addWidget(self._prog_lbl)
        lay.addLayout(hint_row)

        lay.addStretch()

        return frame

    def _build_loop_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background: {_c('BG')};
                border: 1px solid {_c('BORDER')};
                border-radius: 10px;
            }}
            QLabel {{
                color: {_c('DIM')};
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 2px;
                background: transparent;
                padding: 0;
            }}
        """)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(12, 9, 12, 9)
        pl.setSpacing(7)

        # REPEAT row
        r1 = QHBoxLayout()
        r1.setSpacing(5)
        r1.addWidget(QLabel("REPEAT"))

        self._loop_btns: list[QPushButton] = []
        for label, val in [("×1", 1), ("×3", 3), ("×5", 5), ("×10", 10), ("∞", 0)]:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("lv", val)
            btn.clicked.connect(lambda _, v=val: self._set_loop_count(v))
            self._loop_btns.append(btn)
            r1.addWidget(btn)
        r1.addStretch()
        pl.addLayout(r1)

        # START IN + LOOP GAP row
        r2 = QHBoxLayout()
        r2.setSpacing(5)
        r2.addWidget(QLabel("START IN"))

        self._start_delay_btns: list[QPushButton] = []
        for label, val in [("0s", 0), ("3s", 3), ("5s", 5)]:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("sv", val)
            btn.clicked.connect(lambda _, v=val: self._set_start_delay(v))
            self._start_delay_btns.append(btn)
            r2.addWidget(btn)

        sep = QLabel("·")
        sep.setStyleSheet(
            f"color: {_c('BORDER')}; font-size: 14px; background: transparent;"
            f" padding: 0 6px; letter-spacing: 0px;")
        r2.addWidget(sep)

        r2.addWidget(QLabel("LOOP GAP"))

        self._loop_delay_btns: list[QPushButton] = []
        for label, val in [("0s", 0), ("1s", 1), ("3s", 3)]:
            btn = QPushButton(label)
            btn.setFixedHeight(24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("dv", val)
            btn.clicked.connect(lambda _, v=val: self._set_loop_delay(v))
            self._loop_delay_btns.append(btn)
            r2.addWidget(btn)
        r2.addStretch()
        pl.addLayout(r2)

        self._set_loop_count(1)
        self._set_start_delay(3)
        self._set_loop_delay(0)

        return panel

    def _build_status_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {_c('BG')};
                border: 1px solid {_c('BORDER')};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 16, 10)
        layout.setSpacing(10)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 16px; background: transparent;")
        layout.addWidget(self._dot)

        col = QVBoxLayout()
        col.setSpacing(2)

        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setStyleSheet(f"""
            color: {_c('TEXT')};
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 2px;
            background: transparent;
        """)
        col.addWidget(self._status_lbl)

        self._status_detail = QLabel("Ready to record")
        self._status_detail.setStyleSheet(f"""
            color: {_c('DIM')};
            font-size: 11px;
            background: transparent;
        """)
        col.addWidget(self._status_detail)
        layout.addLayout(col)
        layout.addStretch()

        self._timer_lbl = QLabel("00:00")
        self._timer_lbl.setStyleSheet(f"""
            color: {_c('DIM')};
            font-size: 22px;
            font-family: 'Courier New', Consolas, monospace;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self._timer_lbl)

        return card

    # ── Apply theme styles (called when theme changes in settings) ─────────

    def _apply_theme_styles(self):
        _load_theme(self._settings.get('theme'))

        self.setStyleSheet(_app_style())
        self._root.setStyleSheet(
            f"QWidget#root {{ background: qlineargradient("
            f"x1:0,y1:0,x2:1,y2:1, stop:0 {_c('BG_TOP')},"
            f" stop:0.5 {_c('BG_MID')}, stop:1 {_c('BG')}); }}")

        # Header
        self._header.setStyleSheet(f"""
            QWidget#hdr {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {_c('BG_TOP')}, stop:1 {_c('BG_MID')});
                border-bottom: 1px solid {_c('BORDER')};
            }}
        """)

        # Panels
        self._left_frame.setStyleSheet(self._panel_style())
        self._right_frame.setStyleSheet(self._panel_style())

        # Status card + loop panel inner backgrounds
        self._status_card.setStyleSheet(f"""
            QFrame {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};
                      border-radius: 10px; }}
        """)
        self._loop_panel.setStyleSheet(f"""
            QFrame {{ background: {_c('BG')}; border: 1px solid {_c('BORDER')};
                      border-radius: 10px; }}
            QLabel {{ color: {_c('DIM')}; font-size: 10px; font-weight: bold;
                      letter-spacing: 2px; background: transparent; padding: 0; }}
        """)

        # Buttons — re-apply based on current state
        self._btn_create.setStyleSheet(
            _btn_create_rec() if self._recording else _btn_create_idle())
        playing_or_cd = self._playing or self._countdown_val > 0
        self._btn_start.setStyleSheet(
            _btn_start_playing() if playing_or_cd else _btn_start_idle())
        self._btn_del.setStyleSheet(_btn_delete())
        self._btn_edit.setStyleSheet(_btn_delete())
        self._btn_settings.setStyleSheet(self._settings_btn_style())

        # Status labels
        self._dot.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 16px; background: transparent;")
        self._status_lbl.setStyleSheet(f"""
            color: {_c('TEXT')}; font-size: 13px; font-weight: bold;
            letter-spacing: 2px; background: transparent;
        """)
        self._status_detail.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 11px; background: transparent;")
        self._timer_lbl.setStyleSheet(f"""
            color: {_c('DIM')}; font-size: 22px;
            font-family: 'Courier New', Consolas, monospace;
            font-weight: bold; background: transparent;
        """)
        self._meta_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 11px; "
            f"padding: 2px 4px; background: transparent;")
        self._hint_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 10px; "
            f"letter-spacing: 1px; background: transparent;")
        self._prog_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 11px; background: transparent;")

        # Script count badge
        self._script_count_badge.setStyleSheet(f"""
            color: {_c('DIM')}; font-size: 10px;
            background: {_c('SURF2')}; border: 1px solid {_c('BORDER')};
            border-radius: 8px; padding: 2px 8px;
        """)

        # Search input
        self._search_inp.setStyleSheet(f"""
            QLineEdit {{
                background: {_c('BG')};
                color: {_c('TEXT')};
                border: 1px solid {_c('BORDER')};
                border-radius: 10px;
                padding: 0 10px;
                font-size: 12px;
                selection-background-color: {_c('ACCENT1')};
            }}
            QLineEdit:focus {{ border-color: {_c('ACCENT2')}; }}
        """)

        # Loop toggle buttons
        for btn in self._loop_btns:
            active = btn.property("lv") == self._loop_count
            btn.setStyleSheet(_btn_loop_active() if active else _btn_loop_inactive())
        for btn in self._start_delay_btns:
            active = btn.property("sv") == self._start_delay_s
            btn.setStyleSheet(_btn_loop_active() if active else _btn_loop_inactive())
        for btn in self._loop_delay_btns:
            active = btn.property("dv") == self._loop_delay_s
            btn.setStyleSheet(_btn_loop_active() if active else _btn_loop_inactive())

    # ── Icon ───────────────────────────────────────────────────────────────
    @staticmethod
    def _make_icon() -> QIcon:
        ico_path = str(BUNDLE_DIR / "phoenix.ico")
        if os.path.isfile(ico_path):
            return QIcon(ico_path)
        px = QPixmap(64, 64)
        px.fill(Qt.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing)
        g = QRadialGradient(32, 44, 28)
        g.setColorAt(0.0, QColor("#ffaa00"))
        g.setColorAt(0.45, QColor("#e85a00"))
        g.setColorAt(1.0,  QColor("#5a0000"))
        p.setBrush(QBrush(g))
        p.setPen(Qt.NoPen)
        path = QPainterPath()
        path.moveTo(32, 4)
        path.cubicTo(50, 14, 58, 30, 50, 44)
        path.cubicTo(44, 54, 36, 58, 32, 62)
        path.cubicTo(28, 58, 20, 54, 14, 44)
        path.cubicTo(6,  30, 14, 14, 32, 4)
        p.drawPath(path)
        p.end()
        return QIcon(px)

    # ── Loop panel setters ─────────────────────────────────────────────────
    def _set_loop_count(self, n: int):
        self._loop_count = n
        for btn in self._loop_btns:
            btn.setStyleSheet(_btn_loop_active() if btn.property("lv") == n
                              else _btn_loop_inactive())

    def _set_start_delay(self, s: int):
        self._start_delay_s = s
        for btn in self._start_delay_btns:
            btn.setStyleSheet(_btn_loop_active() if btn.property("sv") == s
                              else _btn_loop_inactive())

    def _set_loop_delay(self, s: int):
        self._loop_delay_s = s
        for btn in self._loop_delay_btns:
            btn.setStyleSheet(_btn_loop_active() if btn.property("dv") == s
                              else _btn_loop_inactive())

    # ── Timer / Blink ──────────────────────────────────────────────────────
    def _tick(self):
        if self._countdown_val > 0:
            return
        elapsed = int(time.time() - self._tick_t0)
        m, s = divmod(elapsed, 60)
        self._timer_lbl.setText(f"{m:02d}:{s:02d}")
        if self._recording and self._recorder:
            n = len(self._recorder.events)
            self._status_detail.setText(f"{n} events captured")

    def _blink(self):
        self._blink_on = not self._blink_on
        colour = _c('STATE1') if self._blink_on else _c('STATE1_DARK')
        self._dot.setStyleSheet(
            f"color: {colour}; font-size: 16px; background: transparent;")

    # ── Script List ────────────────────────────────────────────────────────
    def _refresh_scripts(self):
        self._list.clear()
        scripts = sorted(SCRIPTS_DIR.glob("*.json"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
        for sp in scripts:
            try:
                with open(sp, 'r', encoding='utf-8') as fh:
                    d = json.load(fh)
                display = d.get('name', sp.stem)
                meta    = {'count': d.get('event_count', 0),
                           'dur':   d.get('duration', 0.0)}
            except Exception:
                display = sp.stem
                meta    = None

            item = QListWidgetItem(f"  {display}")
            item.setData(Qt.UserRole,     str(sp))
            item.setData(Qt.UserRole + 1, meta)
            self._list.addItem(item)

        n = self._list.count()
        self._script_count_badge.setText(f"{n} script{'s' if n != 1 else ''}")
        self._on_search_changed()

    def _on_sel_changed(self):
        sel = bool(self._list.selectedItems())
        active = self._recording or self._playing or self._countdown_val > 0
        self._btn_start.setEnabled(sel and not active)
        self._btn_del.setEnabled(sel and not active)
        self._btn_edit.setEnabled(sel and not active)

        if sel:
            meta = self._list.selectedItems()[0].data(Qt.UserRole + 1)
            if meta:
                self._meta_lbl.setText(
                    f"Events: {meta['count']}   Duration: {meta['dur']:.1f}s")
            else:
                self._meta_lbl.setText("")
        else:
            self._meta_lbl.setText("")

    def _on_search_changed(self, text: str = ""):
        q = (text if isinstance(text, str) else self._search_inp.text()).lower().strip()
        for i in range(self._list.count()):
            item = self._list.item(i)
            item.setHidden(bool(q) and q not in item.text().lower())
        self._on_sel_changed()

    def _on_rename_script(self, item):
        if self._recording or self._playing or self._countdown_val > 0:
            return
        fp = Path(item.data(Qt.UserRole))
        if not fp.exists():
            self._show_error("Script file not found.")
            self._refresh_scripts()
            return
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            current_name = data.get('name', fp.stem)
        except Exception:
            current_name = fp.stem

        dlg = NameDialog(self, current_name)
        dlg.setWindowTitle("Rename Script")
        if dlg.exec_() != QDialog.Accepted:
            return

        raw = dlg.get_name().strip()
        new_name = "".join(c for c in raw if c.isalnum() or c in " _-").strip()
        if not new_name or new_name == current_name:
            return

        new_fp = fp.parent / f"{new_name}.json"
        if new_fp.exists():
            self._show_error(f'A script named "{new_name}" already exists.')
            return

        try:
            data['name'] = new_name
            with open(fp, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)
            fp.rename(new_fp)
        except Exception as exc:
            self._show_error(f"Rename failed:\n{exc}")
            return

        self._refresh_scripts()
        new_fp_str = str(new_fp)
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.UserRole) == new_fp_str:
                self._list.setCurrentRow(i)
                break

    # ── Button Handlers ────────────────────────────────────────────────────
    def _on_create(self):
        if not HAS_PYNPUT:
            self._show_error(
                "pynput is not installed.\n\n"
                "Run:  pip install pynput\nthen restart Phoenix Macro.")
            return
        if not self._recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self._recording = True
        self._recorder.start()
        self._tick_t0 = time.time()
        self._ticker.start(200)
        self._blink_timer.start(500)

        self._btn_create.setText("⬛   STOP RECORDING")
        self._btn_create.setStyleSheet(_btn_create_rec())
        self._btn_start.setEnabled(False)
        self._btn_del.setEnabled(False)
        self._btn_edit.setEnabled(False)
        self._loop_panel.setEnabled(False)
        self._status_lbl.setText("RECORDING")
        self._status_lbl.setStyleSheet(
            f"color: {_c('STATE1')}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        self._status_detail.setText("0 events captured")
        self._timer_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 22px;"
            f" font-family: 'Courier New', Consolas, monospace;"
            f" font-weight: bold; background: transparent;")

    def _stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        events = self._recorder.stop()
        self._ticker.stop()
        self._blink_timer.stop()

        if not events:
            self._reset_ui()
            self._show_info("No events were captured.")
            return

        default = datetime.now().strftime("script_%Y%m%d_%H%M%S")
        dlg = NameDialog(self, default)
        if dlg.exec_() == QDialog.Accepted:
            raw  = dlg.get_name() or default
            name = "".join(c for c in raw if c.isalnum() or c in " _-").strip()
            if not name:
                name = default
            saved = self._recorder.save(name)
            self._refresh_scripts()
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.UserRole) == str(saved):
                    self._list.setCurrentRow(i)
                    break
        else:
            self._recorder.save(default)
            self._refresh_scripts()

        self._reset_ui()

    # ── Playback ───────────────────────────────────────────────────────────
    def _on_start(self):
        if self._playing or self._countdown_val > 0:
            self._cancel_all()
            return

        sel = self._list.selectedItems()
        if not sel:
            return
        fp = sel[0].data(Qt.UserRole)
        if not fp or not Path(fp).exists():
            self._show_error("Script file not found. Refreshing list.")
            self._refresh_scripts()
            return

        self._loop_aborted   = False
        self._loop_current   = 0
        self._current_script = fp
        self._begin_countdown(initial=True)

    def _on_f10(self):
        if self._recording:
            return
        self._on_start()

    def _cancel_all(self):
        self._loop_aborted = True
        self._countdown_timer.stop()
        self._countdown_val = 0
        if self._playing and self._player:
            self._player.stop()
        else:
            self._ticker.stop()
            self._reset_ui()

    # ── Countdown ──────────────────────────────────────────────────────────
    def _begin_countdown(self, initial: bool):
        delay = self._start_delay_s if initial else self._loop_delay_s

        self._btn_start.setText("⬛   STOP")
        self._btn_start.setStyleSheet(_btn_start_playing())
        self._btn_start.setEnabled(True)
        self._btn_create.setEnabled(False)
        self._btn_del.setEnabled(False)
        self._loop_panel.setEnabled(False)
        self._timer_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 22px;"
            f" font-family: 'Courier New', Consolas, monospace;"
            f" font-weight: bold; background: transparent;")

        if delay <= 0:
            self._start_playback_now()
            return

        self._countdown_val = delay
        self._tick_t0 = time.time()
        self._ticker.start(200)
        self._countdown_timer.start()
        self._update_countdown_ui()

    def _countdown_tick(self):
        self._countdown_val -= 1
        if self._countdown_val <= 0:
            self._countdown_timer.stop()
            self._countdown_val = 0
            self._start_playback_now()
        else:
            self._update_countdown_ui()

    def _update_countdown_ui(self):
        self._status_lbl.setText("STARTING")
        self._status_lbl.setStyleSheet(
            f"color: {_c('ACCENT2')}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        loop_hint = self._loop_hint(next_loop=True)
        detail = f"{loop_hint}  ·  " if loop_hint else ""
        self._status_detail.setText(f"{detail}Starting in {self._countdown_val}s…")
        self._timer_lbl.setText(f"  {self._countdown_val}s")

    def _loop_hint(self, next_loop: bool = False) -> str:
        if self._loop_count == 1:
            return ""
        idx = self._loop_current + (1 if next_loop else 0)
        total = "∞" if self._loop_count == 0 else str(self._loop_count)
        return f"Loop {idx}/{total}"

    def _start_playback_now(self):
        self._loop_current += 1
        self._playing  = True
        self._tick_t0  = time.time()
        if not self._ticker.isActive():
            self._ticker.start(200)

        hint = self._loop_hint()
        self._status_lbl.setText("PLAYING")
        self._status_lbl.setStyleSheet(
            f"color: {_c('ACCENT3')}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        prefix = f"{hint}  ·  " if hint else ""
        self._status_detail.setText(f"{prefix}Starting…")
        self._timer_lbl.setStyleSheet(
            f"color: {_c('STATE2')}; font-size: 22px;"
            f" font-family: 'Courier New', Consolas, monospace;"
            f" font-weight: bold; background: transparent;")
        self._dot.setStyleSheet(
            f"color: {_c('ACCENT3')}; font-size: 16px; background: transparent;")

        self._player = Player(self._current_script)
        self._player.progress.connect(self._on_play_progress)
        self._player.error.connect(self._on_play_error)
        self._player.finished.connect(self._on_play_done)
        self._player.start()

    def _on_play_progress(self, cur: int, total: int):
        pct  = int(cur / total * 100) if total else 0
        hint = self._loop_hint()
        prefix = f"{hint}  ·  " if hint else ""
        self._status_detail.setText(f"{prefix}Event  {cur} / {total}")
        self._prog_lbl.setText(f"{pct}%")

    def _on_play_error(self, msg: str):
        self._show_error(f"Playback error:\n{msg}")

    def _on_play_done(self):
        self._playing = False
        self._prog_lbl.setText("")

        if self._loop_aborted:
            self._loop_aborted = False
            self._ticker.stop()
            self._reset_ui()
            return

        more = (self._loop_count == 0) or (self._loop_current < self._loop_count)
        if more:
            self._begin_countdown(initial=False)
        else:
            self._ticker.stop()
            self._reset_ui()

    def _on_delete(self):
        sel = self._list.selectedItems()
        if not sel:
            return
        name = sel[0].text().strip()
        dlg  = ConfirmDialog(self, "Delete Script", f'Delete  "{name}" ?')
        if dlg.exec_() == QDialog.Accepted:
            fp = Path(sel[0].data(Qt.UserRole))
            try:
                fp.unlink(missing_ok=True)
            except Exception:
                pass
            self._refresh_scripts()

    # ── Update ─────────────────────────────────────────────────────────────
    def _on_update_available(self, version: str, url: str):
        self._update_info = (version, url)
        self._btn_settings.setText("⚙ ●")
        self._btn_settings.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_c('ACCENT2')};
                border: 1px solid {_c('ACCENT2')};
                border-radius: 10px;
                font-size: 16px;
                padding: 2px 12px;
            }}
            QPushButton:hover {{
                color: {_c('ACCENT3')};
                border-color: {_c('ACCENT3')};
                background: {_c('SURF2')};
            }}
            QPushButton:pressed {{ background: {_c('BTN2B')}; }}
        """)

    def _start_update(self, version: str, url: str):
        if self._downloader and self._downloader.isRunning():
            return
        dest = str(BASE_DIR / "PhoenixMacro_update.exe")
        self._downloader = Downloader(url, dest)
        self._downloader.progress.connect(self._on_dl_progress)
        self._downloader.done.connect(self._on_dl_done)
        self._downloader.error.connect(self._on_dl_error)
        self._downloader.start()
        self._prog_lbl.setText(f"Downloading v{version}  0%")

    def _on_dl_progress(self, pct: int):
        cur = self._prog_lbl.text()
        prefix = cur.rsplit("  ", 1)[0] if "  " in cur else "Downloading"
        self._prog_lbl.setText(f"{prefix}  {pct}%")

    def _on_dl_done(self, path: str):
        self._prog_lbl.setText("Applying update…")
        self._apply_update(path)

    def _on_dl_error(self, msg: str):
        self._prog_lbl.setText("")
        self._show_error(f"Download failed:\n{msg}")

    # ── Settings & Editor ──────────────────────────────────────────────────
    def _open_settings(self):
        if self._hotkeys:
            self._hotkeys.stop()

        dlg = SettingsDialog(self, self._settings, self._update_info)
        dlg.settings_saved.connect(self._on_settings_saved)
        dlg.install_update.connect(self._start_update)
        dlg.exec_()

        if self._hotkeys and HAS_PYNPUT:
            self._hotkeys.start(self._settings.get('hotkey_play_toggle'))

    def _on_settings_saved(self):
        stop_key = self._settings.get('hotkey_record_stop')
        play_key = self._settings.get('hotkey_play_toggle')
        if self._recorder:
            self._recorder._stop_key_str = stop_key
        self._hint_lbl.setText(
            f"{key_to_display(stop_key)} — stop rec   ·   "
            f"{key_to_display(play_key)} — play / stop")
        # Re-apply theme (may have changed)
        self._apply_theme_styles()

    def _on_edit_script(self):
        sel = self._list.selectedItems()
        if not sel:
            return
        fp = sel[0].data(Qt.UserRole)
        if not fp or not Path(fp).exists():
            self._show_error("Script file not found.")
            self._refresh_scripts()
            return
        dlg = ActionEditorDialog(self, fp)
        if dlg.exec_() == QDialog.Accepted:
            self._refresh_scripts()
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.UserRole) == fp:
                    self._list.setCurrentRow(i)
                    break

    def _apply_update(self, new_exe: str):
        if not getattr(sys, 'frozen', False):
            self._show_info(
                "Update downloaded.\n\n"
                f"Replace PhoenixMacro.exe manually with:\n{new_exe}")
            return

        current_exe = sys.executable
        bat_path = str(BASE_DIR / "_phoenix_update.bat")
        bat = (
            "@echo off\n"
            "timeout /t 4 /nobreak >nul\n"
            f"move /y \"{new_exe}\" \"{current_exe}\"\n"
            f"start \"\" \"{current_exe}\"\n"
            "del \"%~f0\"\n"
        )
        try:
            with open(bat_path, "w") as fh:
                fh.write(bat)
            subprocess.Popen(
                ["cmd", "/c", bat_path],
                creationflags=_NO_WIN,
                close_fds=True,
            )
        except Exception as exc:
            self._show_error(f"Could not launch update script:\n{exc}")
            return

        QApplication.instance().quit()

    # ── UI Helpers ─────────────────────────────────────────────────────────
    def _reset_ui(self):
        self._btn_create.setText("⬤   CREATE SCRIPT")
        self._btn_create.setStyleSheet(_btn_create_idle())
        self._btn_create.setEnabled(True)
        self._btn_start.setText("▶   START SCRIPT")
        self._btn_start.setStyleSheet(_btn_start_idle())
        self._loop_panel.setEnabled(True)
        self._status_lbl.setText("IDLE")
        self._status_lbl.setStyleSheet(
            f"color: {_c('TEXT')}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        self._status_detail.setText("Ready to record")
        self._timer_lbl.setText("00:00")
        self._timer_lbl.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 22px;"
            f" font-family: 'Courier New', Consolas, monospace;"
            f" font-weight: bold; background: transparent;")
        self._dot.setStyleSheet(
            f"color: {_c('DIM')}; font-size: 16px; background: transparent;")
        self._on_sel_changed()

    def _show_error(self, msg: str):
        dlg = QDialog(self)
        dlg.setWindowTitle("Error")
        dlg.setModal(True)
        dlg.setFixedSize(400, 150)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg.setStyleSheet(
            f"QDialog{{ background:{_c('SURF')}; border:1px solid {_c('BORDER')}; }}"
            f"QLabel{{ color:{_c('TEXT')}; font-size:13px; background:transparent; }}")
        vb = QVBoxLayout(dlg)
        vb.setContentsMargins(20, 18, 20, 18)
        vb.setSpacing(14)
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        vb.addWidget(lbl)
        r = QHBoxLayout()
        r.addStretch()
        ok = QPushButton("OK")
        ok.setStyleSheet(_btn_dialog_ok())
        ok.setFixedHeight(34)
        ok.clicked.connect(dlg.accept)
        r.addWidget(ok)
        vb.addLayout(r)
        dlg.exec_()

    def _show_info(self, msg: str):
        self._show_error(msg)

    # ── Window close ───────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._recording and self._recorder:
            self._recorder.stop()
        if self._playing and self._player:
            self._player.stop()
            self._player.wait(2000)
        if self._downloader and self._downloader.isRunning():
            self._downloader.stop()
            self._downloader.wait(2000)
        if self._hotkeys:
            self._hotkeys.stop()
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Phoenix Macro")
    app.setApplicationVersion(VERSION)

    if not HAS_PYNPUT:
        print("[WARNING] pynput is not installed — recording/playback disabled.")
        print("          Run:  pip install pynput")

    win = PhoenixMacro()
    win.show()

    if not HAS_PYNPUT:
        win._show_error(
            "pynput is not installed.\n\n"
            "Open a terminal and run:\n"
            "  pip install pynput\n\n"
            "Then restart Phoenix Macro.")

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
