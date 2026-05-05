<div align="center">

<img src="phoenix.ico" width="80" height="80" alt="Phoenix Macro Icon"/>

# Phoenix Macro

**Mouse & Keyboard macro recorder for Windows**

[![Release](https://img.shields.io/github/v/release/PhoenixAnalist/phoenix-macro?color=e85a00&label=latest)](https://github.com/PhoenixAnalist/phoenix-macro/releases/latest)
[![Build](https://img.shields.io/github/actions/workflow/status/PhoenixAnalist/phoenix-macro/build.yml?label=build&color=cc2800)](https://github.com/PhoenixAnalist/phoenix-macro/actions)
[![Platform](https://img.shields.io/badge/platform-Windows-blue)](https://github.com/PhoenixAnalist/phoenix-macro/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)

Record any sequence of mouse and keyboard actions, save them as scripts, and replay them on demand — with loop support and full hotkey control.

</div>

---

## Features

- **Record** — captures every mouse click, scroll, movement and keypress with precise timing
- **Playback** — replays scripts exactly as recorded; supports looping N times or infinitely
- **Script Library** — all scripts are saved as JSON files you can manage, rename and share
- **Action Editor** — view and delete individual events inside a script before playback
- **Custom Hotkeys** — rebind the Record/Stop and Play/Stop keys to any key you prefer
- **Auto-Update** — checks GitHub for new releases and installs the latest exe in one click
- **Phoenix UI** — dark fire-themed interface with animated flame gradients

---

## Download

Get the latest pre-built **PhoenixMacro.exe** from the [Releases](https://github.com/PhoenixAnalist/phoenix-macro/releases/latest) page.

No installation needed — just run the exe.

> **Note:** Windows Defender or your antivirus may flag a PyInstaller exe.
> If prompted, add an exception for `PhoenixMacro.exe`.

---

## Quick Start

| Action | Default key |
|---|---|
| Start / Stop recording | **F9** |
| Start / Stop playback | **F10** |

1. Press **F9** (or click **NEW SCRIPT**) to start recording.
2. Perform the actions you want to automate.
3. Press **F9** again to stop and save the script.
4. Select the script from the list and press **F10** (or click **START**) to play it back.

To loop, enable the **Loop** toggle and set the repeat count (0 = infinite).

---

## Settings

Open the **⚙** button in the top-right corner to:

- **Rebind hotkeys** — click any hotkey button then press your desired key
- **Check for updates manually** — see if a new version is available and install it instantly

---

## Action Editor

Select a script and click **✎ EDIT SCRIPT** to open the Action Editor.

- Browse the full list of recorded events (clicks, moves, key presses, scrolls)
- Select one or multiple events and click **Delete Selected** to remove them
- Click **Save** to write the changes back to the script file

---

## Building from Source

### Requirements

- Python 3.10+
- Windows (pynput uses Windows accessibility APIs)

### Install & Build

```bat
build.bat
```

This installs all dependencies and produces `dist\PhoenixMacro.exe`.

### Manual build

```bash
pip install PyQt5 pynput pyinstaller certifi
pyinstaller --onefile --windowed --name PhoenixMacro --icon phoenix.ico --add-data "phoenix.ico;." phoenix_macro.py
```

---

## Tech Stack

| Component | Library |
|---|---|
| UI | PyQt5 |
| Input capture & replay | pynput |
| Packaging | PyInstaller |
| Scripts format | JSON |

---

## Changelog

### v1.6.0
- **Horizontal layout** — window now uses a landscape split: Script Library on the left, controls on the right
- **Gradient background** — window background uses a diagonal gradient instead of flat black
- **Rounded buttons** — all buttons use larger border-radius (20px pill shape for primary, 12px for secondary)
- **3 design themes** — choose between Phoenix Fire (fire/orange), Midnight Ocean (blue/cyan), and Neon Storm (purple/magenta) in Settings
- **Two-panel UI** — left panel shows script library with count badge and meta info; right panel holds all controls

### v1.5.2
- Fixed "Failed to load Python DLL" error on auto-update: PyInstaller now extracts to the app folder (`--runtime-tmpdir .`) instead of `%TEMP%`, which Windows Defender monitors aggressively and may delete `python311.dll` right after extraction
- On startup, leftover `_MEI*` extraction folders from crashed previous runs are cleaned up automatically

### v1.5.1
- Fixed auto-update: downloader now uses the certifi CA bundle so SSL connections to GitHub CDN succeed inside the exe
- Added PE signature + size validation after download — corrupted or blocked files are rejected with a clear error instead of crashing on launch

### v1.5.0
- **Script search** — filter bar above the script list; type to instantly narrow results
- **Rename scripts** — double-click any script name to rename it (updates the JSON file and filename)

### v1.4.0
- Added **Action Editor** — inspect and delete individual events in a script
- Added **Settings window** — rebind hotkeys, manual update check
- Moved update functionality into Settings; main window shows an orange badge when an update is available

### v1.3.1
- Bug fixes and stability improvements

### v1.3.0
- Added auto-update checker with one-click install

### v1.2.0
- Added phoenix bird icon to exe and window title bar
- Widened default window so all controls fit without clipping

---

<div align="center">

Made with fire 🔥

</div>
