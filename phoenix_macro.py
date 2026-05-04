#!/usr/bin/env python3
"""
Phoenix Macro Recorder
Mouse & Keyboard macro recorder and player with Phoenix-themed UI.
Usage: python phoenix_macro.py
Build: see build.bat (Windows)
"""
import sys
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
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

SCRIPTS_DIR = BASE_DIR / "scripts"
SCRIPTS_DIR.mkdir(exist_ok=True)

# ── Version & Update ──────────────────────────────────────────────────────────
VERSION     = "1.1.0"                        # bump this with each release tag
GITHUB_REPO = "PhoenixAnalist/phoenix-macro"

# subprocess.CREATE_NO_WINDOW is Windows-only
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# ── Phoenix Colour Palette ─────────────────────────────────────────────────────
BG       = "#090909"   # near-black window background
SURF     = "#111111"   # panel / card surface
SURF2    = "#1a1108"   # warmer dark surface (header underlay)
BORDER   = "#2d1a00"   # dark amber border
FIRE1    = "#cc2800"   # deep fire red
FIRE2    = "#e85a00"   # orange flame
FIRE3    = "#ff9a00"   # golden flame tip
GLOW     = "#ff6600"   # generic glow
TEXT     = "#f2e8d9"   # warm white
DIM      = "#6a5a45"   # dimmed text / inactive elements
RED_ACT  = "#ff2020"   # recording-active indicator
ORG_ACT  = "#ffaa00"   # playback-active indicator

# ── Button Stylesheets ─────────────────────────────────────────────────────────
_BTN_BASE = """
    border-radius: 10px;
    padding: 14px 28px;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 2px;
"""

BTN_CREATE_IDLE = f"""
QPushButton {{
    {_BTN_BASE}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #7a1200, stop:1 #4a0800);
    color: {TEXT};
    border: 1px solid {FIRE1};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #aa1800, stop:1 #7a1000);
    border-color: {FIRE2};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #cc2000, stop:1 #991800);
}}
"""

BTN_CREATE_REC = f"""
QPushButton {{
    {_BTN_BASE}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #cc0000, stop:1 #880000);
    color: #ffffff;
    border: 2px solid #ff2200;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #ff1100, stop:1 #aa0000);
}}
"""

BTN_START_IDLE = f"""
QPushButton {{
    {_BTN_BASE}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #4a2800, stop:1 #2d1800);
    color: {FIRE3};
    border: 1px solid {FIRE2};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #663a00, stop:1 #3d2200);
    border-color: {FIRE3};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #7a4800, stop:1 #4d2e00);
}}
QPushButton:disabled {{
    background: #181818;
    color: #3a3a3a;
    border-color: #252525;
}}
"""

BTN_START_PLAYING = f"""
QPushButton {{
    {_BTN_BASE}
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #553300, stop:1 #331f00);
    color: {FIRE3};
    border: 2px solid {FIRE2};
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #7a4d00, stop:1 #4d2e00);
}}
"""

BTN_DELETE = f"""
QPushButton {{
    background: #111111;
    color: {DIM};
    border: 1px solid #252525;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 12px;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background: #2a0a0a;
    color: {FIRE1};
    border-color: {FIRE1};
}}
QPushButton:disabled {{
    color: #2a2a2a;
    border-color: #1a1a1a;
}}
"""

BTN_UPDATE = f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #4a3000, stop:1 #2d1e00);
    color: {FIRE3};
    border: 1px solid {FIRE2};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 12px;
    letter-spacing: 1px;
    font-weight: bold;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #6a4400, stop:1 #3d2800);
    border-color: {FIRE3};
    color: #ffffff;
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #7a5000, stop:1 #4d3200);
}}
QPushButton:disabled {{
    color: {DIM};
    border-color: #252525;
    background: #111111;
}}
"""

# Compact variant for dialog buttons (smaller padding, fits in 36px height)
BTN_DIALOG_OK = f"""
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #7a1200, stop:1 #4a0800);
    color: {TEXT};
    border: 1px solid {FIRE1};
    border-radius: 7px;
    padding: 6px 22px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #aa1800, stop:1 #7a1000);
    border-color: {FIRE2};
}}
QPushButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #cc2000, stop:1 #991800);
}}
"""

APP_STYLE = f"""
QMainWindow, QWidget {{
    background-color: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', Arial, sans-serif;
}}
QWidget#root {{
    background-color: {BG};
}}
QListWidget {{
    background-color: {SURF};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    color: {TEXT};
    font-size: 13px;
}}
QListWidget::item {{
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 2px;
    border-left: 3px solid transparent;
}}
QListWidget::item:selected {{
    background-color: #2d1400;
    border-left: 3px solid {FIRE2};
    color: {FIRE3};
}}
QListWidget::item:hover:!selected {{
    background-color: #1d1100;
    border-left: 3px solid {BORDER};
}}
QScrollBar:vertical {{
    background: {SURF};
    width: 7px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {FIRE1};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QFrame[frameShape="4"] {{
    color: {BORDER};
    background: {BORDER};
    max-height: 1px;
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Recorder
# ─────────────────────────────────────────────────────────────────────────────
class Recorder(QObject):
    """Captures global mouse and keyboard events into a list.
    Emits hotkey_stop when F9 is pressed so the UI can stop recording
    from any window without needing focus on Phoenix Macro.
    Mouse-move events are throttled to ~30 fps to keep file sizes reasonable.
    """
    hotkey_stop = pyqtSignal()   # emitted when F9 pressed during recording

    MOVE_INTERVAL = 0.033  # seconds between successive mouse-move records

    def __init__(self):
        super().__init__()
        self.events: list = []
        self._start: float = 0.0
        self._last_move: float = 0.0
        self._lock = threading.Lock()
        self._listeners: list = []
        self.recording = False

    # ── public API ─────────────────────────────────────────────────────────
    def start(self):
        """Begin recording. Non-blocking; listeners run on daemon threads."""
        self.events = []
        self._start = time.perf_counter()
        self._last_move = 0.0
        self.recording = True

        rec = self  # closure reference

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
            # F9 = global stop-recording hotkey
            try:
                if key == Key.f9:
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
        """Stop recording and return the captured event list."""
        self.recording = False
        for lst in self._listeners:
            try:
                lst.stop()
            except Exception:
                pass
        self._listeners = []
        return list(self.events)

    def save(self, name: str) -> Path:
        """Persist events to SCRIPTS_DIR/<name>.json, return the path."""
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

    # ── internal ────────────────────────────────────────────────────────────
    def _push(self, event: dict):
        if self.recording:
            with self._lock:
                self.events.append(event)


# ─────────────────────────────────────────────────────────────────────────────
# Player  (QThread so the UI stays responsive during playback)
# ─────────────────────────────────────────────────────────────────────────────
class Player(QThread):
    """Replays a saved script with correct timing using pynput controllers."""
    progress = pyqtSignal(int, int)   # (current_event_index, total_events)
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

                # Sleep precisely until this event's timestamp
                wait = ev['t'] - (time.perf_counter() - t0)
                if wait > 0.0:
                    # Break sleep into small slices so abort is responsive
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

    # ── helpers ─────────────────────────────────────────────────────────────
    @staticmethod
    def _btn(s: str) -> Button:
        if 'right'  in s: return Button.right
        if 'middle' in s: return Button.middle
        return Button.left

    @staticmethod
    def _key(s: str):
        if not s:
            return None
        if len(s) == 1:
            return s
        # Map stored string representations back to pynput Key objects
        _MAP = {
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
            'Key.f10': Key.f10,'Key.f11': Key.f11,'Key.f12': Key.f12,
            'Key.print_screen': Key.print_screen,
            'Key.scroll_lock': Key.scroll_lock,
            'Key.pause': Key.pause,
            'Key.media_play_pause': Key.media_play_pause,
            'Key.media_volume_up': Key.media_volume_up,
            'Key.media_volume_down': Key.media_volume_down,
            'Key.media_volume_mute': Key.media_volume_mute,
            'Key.media_next': Key.media_next,
            'Key.media_previous': Key.media_previous,
        }
        return _MAP.get(s)


# ─────────────────────────────────────────────────────────────────────────────
# UpdateChecker  (runs once at startup, silently)
# ─────────────────────────────────────────────────────────────────────────────
class UpdateChecker(QThread):
    """Fetches the latest GitHub release and compares its tag with VERSION.
    Emits update_available only when a newer version exists and has an .exe asset.
    All network errors are swallowed — startup is never blocked.
    NOTE: the GitHub repo must be public for unauthenticated API access.
    """
    update_available = pyqtSignal(str, str)   # (new_version, download_url)

    def run(self):
        try:
            import urllib.request
            import ssl as _ssl

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

            # Find the Windows exe asset
            url = next(
                (a["browser_download_url"]
                 for a in data.get("assets", [])
                 if a.get("name", "").lower().endswith(".exe")),
                None,
            )
            if not url:
                return

            def _ver(s):
                try:
                    return tuple(int(x) for x in s.split("."))
                except Exception:
                    return (0,)

            if _ver(tag) > _ver(VERSION):
                self.update_available.emit(tag, url)

        except Exception:
            pass   # silently ignore any network / parse errors


# ─────────────────────────────────────────────────────────────────────────────
# Downloader  (background download with progress)
# ─────────────────────────────────────────────────────────────────────────────
class Downloader(QThread):
    """Downloads a URL to a local file, emitting integer progress (0-100)."""
    progress = pyqtSignal(int)   # 0-100 %
    done     = pyqtSignal(str)   # local path on success
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

            self.progress.emit(100)
            self.done.emit(self.dest)

        except Exception as exc:
            self.error.emit(str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# Custom dark-themed dialog for naming a saved script
# ─────────────────────────────────────────────────────────────────────────────
class NameDialog(QDialog):
    """Minimal dark dialog that asks the user for a script name."""
    def __init__(self, parent=None, default: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Save Script")
        self.setModal(True)
        self.setFixedSize(420, 160)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #131313;
                border: 1px solid {BORDER};
            }}
            QLabel {{
                color: {TEXT};
                font-size: 13px;
                background: transparent;
            }}
            QLineEdit {{
                background-color: #1c1c1c;
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 6px;
                padding: 9px 12px;
                font-size: 13px;
                selection-background-color: {FIRE1};
            }}
            QLineEdit:focus {{
                border-color: {FIRE2};
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
        btn_cancel.setStyleSheet(BTN_DELETE)
        btn_cancel.setFixedHeight(36)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.setStyleSheet(BTN_DIALOG_OK)
        btn_save.setFixedHeight(36)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.clicked.connect(self.accept)
        row.addWidget(btn_save)

        layout.addLayout(row)
        self._inp.returnPressed.connect(self.accept)

    def get_name(self) -> str:
        return self._inp.text().strip()


# ─────────────────────────────────────────────────────────────────────────────
# Confirm dialog (dark-themed replacement for QMessageBox)
# ─────────────────────────────────────────────────────────────────────────────
class ConfirmDialog(QDialog):
    def __init__(self, parent=None, title: str = "Confirm", message: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(380, 140)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(f"""
            QDialog {{ background-color: #131313; border: 1px solid {BORDER}; }}
            QLabel  {{ color: {TEXT}; font-size: 13px; background: transparent; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(16)
        layout.addWidget(QLabel(message))

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()

        btn_no = QPushButton("No")
        btn_no.setStyleSheet(BTN_DELETE)
        btn_no.setFixedHeight(36)
        btn_no.setCursor(Qt.PointingHandCursor)
        btn_no.clicked.connect(self.reject)
        row.addWidget(btn_no)

        btn_yes = QPushButton("Yes, Delete")
        btn_yes.setStyleSheet(BTN_DIALOG_OK)
        btn_yes.setFixedHeight(36)
        btn_yes.setCursor(Qt.PointingHandCursor)
        btn_yes.clicked.connect(self.accept)
        row.addWidget(btn_yes)

        layout.addLayout(row)


# ─────────────────────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────────────────────
class PhoenixMacro(QMainWindow):
    def __init__(self):
        super().__init__()
        self._recorder  = Recorder() if HAS_PYNPUT else None
        self._player: Player | None = None
        self._recording = False
        self._playing   = False
        self._tick_t0   = 0.0

        # Single 200 ms tick drives both recording timer and playback timer
        self._ticker = QTimer(self)
        self._ticker.timeout.connect(self._tick)

        # Blink timer for the recording dot indicator
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_on = True

        if HAS_PYNPUT:
            # Connect global F9 hotkey to stop recording
            self._recorder.hotkey_stop.connect(self._stop_recording)

        self._build_ui()
        self._refresh_scripts()

        # Check for updates in the background — does not block startup
        self._update_url  = ""
        self._downloader: Downloader | None = None
        self._upd_checker = UpdateChecker()
        self._upd_checker.update_available.connect(self._on_update_available)
        self._upd_checker.start()

    # ── UI Construction ────────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Phoenix Macro")
        self.setMinimumSize(500, 680)
        self.resize(520, 730)
        self.setStyleSheet(APP_STYLE)
        self.setWindowIcon(self._make_icon())

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────────────
        vbox.addWidget(self._build_header())

        # ── Content area ───────────────────────────────────────────────────
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(24, 20, 24, 24)
        cl.setSpacing(14)

        # Status card
        self._status_card = self._build_status_card()
        cl.addWidget(self._status_card)

        # CREATE / RECORD button
        self._btn_create = QPushButton("⬤   CREATE SCRIPT")
        self._btn_create.setStyleSheet(BTN_CREATE_IDLE)
        self._btn_create.setMinimumHeight(54)
        self._btn_create.setCursor(Qt.PointingHandCursor)
        self._btn_create.clicked.connect(self._on_create)
        cl.addWidget(self._btn_create)

        # Hint below Create button
        hint = QLabel("F9 — stop recording from any window")
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(f"color: {DIM}; font-size: 10px; letter-spacing: 1px; padding: 0;")
        cl.addWidget(hint)

        # Divider
        cl.addWidget(self._divider("SAVED SCRIPTS"))

        # Script list
        self._list = QListWidget()
        self._list.setMinimumHeight(180)
        self._list.itemSelectionChanged.connect(self._on_sel_changed)
        self._list.itemDoubleClicked.connect(self._on_start)
        cl.addWidget(self._list)

        # Script meta info
        self._meta_lbl = QLabel("")
        self._meta_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px; padding: 0 4px;")
        cl.addWidget(self._meta_lbl)

        # START / STOP PLAYBACK button
        self._btn_start = QPushButton("▶   START SCRIPT")
        self._btn_start.setStyleSheet(BTN_START_IDLE)
        self._btn_start.setMinimumHeight(54)
        self._btn_start.setCursor(Qt.PointingHandCursor)
        self._btn_start.setEnabled(False)
        self._btn_start.clicked.connect(self._on_start)
        cl.addWidget(self._btn_start)

        # Bottom row: delete + update (hidden until available) + progress
        bot = QHBoxLayout()
        bot.setSpacing(12)

        self._btn_del = QPushButton("✕  DELETE")
        self._btn_del.setStyleSheet(BTN_DELETE)
        self._btn_del.setMinimumHeight(36)
        self._btn_del.setCursor(Qt.PointingHandCursor)
        self._btn_del.setEnabled(False)
        self._btn_del.clicked.connect(self._on_delete)
        bot.addWidget(self._btn_del)

        self._btn_update = QPushButton("↑  UPDATE")
        self._btn_update.setStyleSheet(BTN_UPDATE)
        self._btn_update.setMinimumHeight(36)
        self._btn_update.setCursor(Qt.PointingHandCursor)
        self._btn_update.setVisible(False)
        self._btn_update.clicked.connect(self._on_update_click)
        bot.addWidget(self._btn_update)

        bot.addStretch()

        self._prog_lbl = QLabel("")
        self._prog_lbl.setStyleSheet(f"color: {DIM}; font-size: 11px;")
        bot.addWidget(self._prog_lbl)

        cl.addLayout(bot)
        vbox.addWidget(content)

    def _build_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setFixedHeight(115)
        hdr.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e0900, stop:0.6 #0f0400, stop:1 {BG});
            border-bottom: 1px solid {BORDER};
        """)
        layout = QVBoxLayout(hdr)
        layout.setContentsMargins(26, 14, 26, 10)
        layout.setSpacing(6)

        # Top row: flame icon + title + flame icon
        top = QHBoxLayout()
        top.setSpacing(14)

        lflame = QLabel("🔥")
        lflame.setStyleSheet("font-size: 30px; background: transparent;")
        top.addWidget(lflame)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)

        title = QLabel("PHOENIX MACRO")
        title.setStyleSheet(f"""
            color: {FIRE3};
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 5px;
            background: transparent;
        """)
        title_col.addWidget(title)

        sub = QLabel("MOUSE  &  KEYBOARD  RECORDER")
        sub.setStyleSheet(f"""
            color: {DIM};
            font-size: 10px;
            letter-spacing: 3px;
            background: transparent;
        """)
        title_col.addWidget(sub)

        top.addLayout(title_col)
        top.addStretch()

        rflame = QLabel("🔥")
        rflame.setStyleSheet("font-size: 30px; background: transparent;")
        top.addWidget(rflame)

        layout.addLayout(top)

        # Decorative divider
        deco = QLabel("━━━━ 🔥 ━━━ 🔥 ━━━ 🔥 ━━━━")
        deco.setAlignment(Qt.AlignCenter)
        deco.setStyleSheet(f"""
            color: {FIRE1};
            font-size: 10px;
            letter-spacing: 4px;
            background: transparent;
        """)
        layout.addWidget(deco)

        return hdr

    def _build_status_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {SURF};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 18, 12)
        layout.setSpacing(12)

        # Blinking dot
        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {DIM}; font-size: 16px; background: transparent;")
        layout.addWidget(self._dot)

        col = QVBoxLayout()
        col.setSpacing(3)

        self._status_lbl = QLabel("IDLE")
        self._status_lbl.setStyleSheet(f"""
            color: {TEXT};
            font-size: 13px;
            font-weight: bold;
            letter-spacing: 2px;
            background: transparent;
        """)
        col.addWidget(self._status_lbl)

        self._status_detail = QLabel("Ready to record")
        self._status_detail.setStyleSheet(f"""
            color: {DIM};
            font-size: 11px;
            background: transparent;
        """)
        col.addWidget(self._status_detail)
        layout.addLayout(col)
        layout.addStretch()

        # Elapsed timer display
        self._timer_lbl = QLabel("00:00")
        self._timer_lbl.setStyleSheet(f"""
            color: {DIM};
            font-size: 22px;
            font-family: 'Courier New', Consolas, monospace;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(self._timer_lbl)

        return card

    @staticmethod
    def _divider(text: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 6, 0, 2)
        h.setSpacing(8)

        for side in range(2):
            ln = QFrame()
            ln.setFrameShape(QFrame.HLine)
            h.addWidget(ln, 1)
            if side == 0:
                lbl = QLabel(text)
                lbl.setStyleSheet(f"""
                    color: {FIRE2};
                    font-size: 10px;
                    font-weight: bold;
                    letter-spacing: 3px;
                    background: transparent;
                    padding: 0 6px;
                """)
                h.addWidget(lbl)
        return w

    # ── Icon ───────────────────────────────────────────────────────────────
    @staticmethod
    def _make_icon() -> QIcon:
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

    # ── Timer / Blink ──────────────────────────────────────────────────────
    def _tick(self):
        """Update elapsed-time display every 200 ms while recording or playing."""
        elapsed = int(time.time() - self._tick_t0)
        m, s = divmod(elapsed, 60)
        self._timer_lbl.setText(f"{m:02d}:{s:02d}")
        if self._recording and self._recorder:
            n = len(self._recorder.events)
            self._status_detail.setText(f"{n} events captured")

    def _blink(self):
        self._blink_on = not self._blink_on
        colour = RED_ACT if self._blink_on else "#550000"
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

        self._on_sel_changed()

    def _on_sel_changed(self):
        sel = bool(self._list.selectedItems())
        active = self._recording or self._playing
        self._btn_start.setEnabled(sel and not active)
        self._btn_del.setEnabled(sel and not active)

        if sel:
            meta = self._list.selectedItems()[0].data(Qt.UserRole + 1)
            if meta:
                self._meta_lbl.setText(
                    f"Events: {meta['count']}   Duration: {meta['dur']:.1f}s")
            else:
                self._meta_lbl.setText("")
        else:
            self._meta_lbl.setText("")

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

        # UI updates
        self._btn_create.setText("⬛   STOP RECORDING")
        self._btn_create.setStyleSheet(BTN_CREATE_REC)
        self._btn_start.setEnabled(False)
        self._btn_del.setEnabled(False)
        self._status_lbl.setText("RECORDING")
        self._status_lbl.setStyleSheet(
            f"color: {RED_ACT}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        self._status_detail.setText("0 events captured")
        self._timer_lbl.setStyleSheet(
            f"color: {FIRE2}; font-size: 22px; font-family: 'Courier New',"
            f" Consolas, monospace; font-weight: bold; background: transparent;")

    def _stop_recording(self):
        """Stop recording and prompt the user to name the script."""
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
            # Sanitise: keep alphanumerics, spaces, hyphens, underscores
            name = "".join(c for c in raw if c.isalnum() or c in " _-").strip()
            if not name:
                name = default
            saved = self._recorder.save(name)
            self._refresh_scripts()
            # Auto-select the newly saved script
            for i in range(self._list.count()):
                if self._list.item(i).data(Qt.UserRole) == str(saved):
                    self._list.setCurrentRow(i)
                    break
        else:
            # Cancelled — save with default timestamp name anyway
            self._recorder.save(default)
            self._refresh_scripts()

        self._reset_ui()

    def _on_start(self):
        if self._playing:
            # Stop playback
            if self._player:
                self._player.stop()
            return

        sel = self._list.selectedItems()
        if not sel:
            return
        fp = sel[0].data(Qt.UserRole)
        if not fp or not Path(fp).exists():
            self._show_error("Script file not found. Refreshing list.")
            self._refresh_scripts()
            return

        self._playing = True
        self._tick_t0 = time.time()
        self._ticker.start(200)

        self._btn_start.setText("⬛   STOP")
        self._btn_start.setStyleSheet(BTN_START_PLAYING)
        self._btn_start.setEnabled(True)
        self._btn_create.setEnabled(False)
        self._btn_del.setEnabled(False)

        self._status_lbl.setText("PLAYING")
        self._status_lbl.setStyleSheet(
            f"color: {FIRE3}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        self._status_detail.setText("Starting…")
        self._timer_lbl.setStyleSheet(
            f"color: {ORG_ACT}; font-size: 22px; font-family: 'Courier New',"
            f" Consolas, monospace; font-weight: bold; background: transparent;")
        self._dot.setStyleSheet(
            f"color: {FIRE3}; font-size: 16px; background: transparent;")

        self._player = Player(fp)
        self._player.progress.connect(self._on_play_progress)
        self._player.error.connect(self._on_play_error)
        self._player.finished.connect(self._on_play_done)
        self._player.start()

    def _on_play_progress(self, cur: int, total: int):
        pct = int(cur / total * 100) if total else 0
        self._status_detail.setText(f"Event  {cur} / {total}")
        self._prog_lbl.setText(f"{pct}%")

    def _on_play_error(self, msg: str):
        self._show_error(f"Playback error:\n{msg}")

    def _on_play_done(self):
        self._ticker.stop()
        self._playing = False
        self._prog_lbl.setText("")
        self._reset_ui()

    def _on_delete(self):
        sel = self._list.selectedItems()
        if not sel:
            return
        name = sel[0].text().strip()
        dlg  = ConfirmDialog(self, "Delete Script",
                             f'Delete  "{name}" ?')
        if dlg.exec_() == QDialog.Accepted:
            fp = Path(sel[0].data(Qt.UserRole))
            try:
                fp.unlink(missing_ok=True)
            except Exception:
                pass
            self._refresh_scripts()

    # ── Update ─────────────────────────────────────────────────────────────
    def _on_update_available(self, version: str, url: str):
        """Called from UpdateChecker when a newer release exists on GitHub."""
        self._update_url = url
        self._btn_update.setText(f"↑  UPDATE  v{version}")
        self._btn_update.setVisible(True)

    def _on_update_click(self):
        if not self._update_url:
            return
        if self._downloader and self._downloader.isRunning():
            return   # already in progress

        dest = str(BASE_DIR / "PhoenixMacro_update.exe")
        self._downloader = Downloader(self._update_url, dest)
        self._downloader.progress.connect(self._on_dl_progress)
        self._downloader.done.connect(self._on_dl_done)
        self._downloader.error.connect(self._on_dl_error)
        self._downloader.start()

        self._btn_update.setText("Downloading…  0%")
        self._btn_update.setEnabled(False)

    def _on_dl_progress(self, pct: int):
        self._btn_update.setText(f"Downloading…  {pct}%")

    def _on_dl_done(self, path: str):
        self._btn_update.setText("↑  Applying…")
        self._apply_update(path)

    def _on_dl_error(self, msg: str):
        self._btn_update.setText(f"↑  UPDATE  (retry)")
        self._btn_update.setEnabled(True)
        self._show_error(f"Download failed:\n{msg}")

    def _apply_update(self, new_exe: str):
        """Replace this exe after the process exits using a helper .bat script."""
        if not getattr(sys, 'frozen', False):
            # Running from source — just tell the user where the file is
            self._show_info(
                "Update downloaded.\n\n"
                f"Replace PhoenixMacro.exe manually with:\n{new_exe}")
            return

        current_exe = sys.executable
        bat_path = str(BASE_DIR / "_phoenix_update.bat")
        bat = (
            "@echo off\n"
            "timeout /t 2 /nobreak >nul\n"
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
        self._btn_create.setStyleSheet(BTN_CREATE_IDLE)
        self._btn_create.setEnabled(True)
        self._btn_start.setText("▶   START SCRIPT")
        self._btn_start.setStyleSheet(BTN_START_IDLE)
        self._status_lbl.setText("IDLE")
        self._status_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; font-weight: bold;"
            f" letter-spacing: 2px; background: transparent;")
        self._status_detail.setText("Ready to record")
        self._timer_lbl.setText("00:00")
        self._timer_lbl.setStyleSheet(
            f"color: {DIM}; font-size: 22px; font-family: 'Courier New',"
            f" Consolas, monospace; font-weight: bold; background: transparent;")
        self._dot.setStyleSheet(
            f"color: {DIM}; font-size: 16px; background: transparent;")
        self._on_sel_changed()

    def _show_error(self, msg: str):
        dlg = QDialog(self)
        dlg.setWindowTitle("Error")
        dlg.setModal(True)
        dlg.setFixedSize(380, 140)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        dlg.setStyleSheet(f"QDialog{{background:{SURF};border:1px solid {BORDER};}}"
                          f"QLabel{{color:{TEXT};font-size:13px;background:transparent;}}")
        vb = QVBoxLayout(dlg)
        vb.setContentsMargins(20, 18, 20, 18)
        vb.setSpacing(14)
        vb.addWidget(QLabel(msg))
        r = QHBoxLayout()
        r.addStretch()
        ok = QPushButton("OK")
        ok.setStyleSheet(BTN_DIALOG_OK)
        ok.setFixedHeight(34)
        ok.clicked.connect(dlg.accept)
        r.addWidget(ok)
        vb.addLayout(r)
        dlg.exec_()

    def _show_info(self, msg: str):
        self._show_error(msg)   # reuse same styled dialog

    # ── Window close ──────────────────────────────────────────────────────
    def closeEvent(self, event):
        if self._recording and self._recorder:
            self._recorder.stop()
        if self._playing and self._player:
            self._player.stop()
            self._player.wait(2000)
        if self._downloader and self._downloader.isRunning():
            self._downloader.stop()
            self._downloader.wait(2000)
        event.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Enable per-monitor DPI awareness on Windows (must be before QApplication)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Phoenix Macro")
    app.setApplicationVersion(VERSION)

    if not HAS_PYNPUT:
        # Show a warning but still open the app so the user can see the message
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
