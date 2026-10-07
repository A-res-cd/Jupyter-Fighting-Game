# Jupyter: Python Library Brawl

A Pygame fighting game where Python libraries fight each other.

## Current modes

- Single Player vs CPU
- Local Multiplayer
  - Two controllers
  - Keyboard + controller
  - Two keyboard layouts
- Online Multiplayer
  - LAN / direct IP host and join
  - TCP port `50555`

## Run

```bash
python -m pip install -r requirements.txt
python main.py
```

## Project structure

```text
Jupyter/
├── main.py
├── requirements.txt
├── build_windows.bat
├── assets/
│   ├── audio/
│   │   ├── music/
│   │   └── sfx/
│   ├── fighters/
│   ├── icon/
│   └── ui/
└── jupyter_game/
    ├── __init__.py
    ├── app.py
    ├── config.py
    ├── roster.py
    ├── input_devices.py
    ├── entities.py
    ├── ui.py
    ├── local_modes.py
    └── online.py
```

## What each file does

- `main.py` - tiny application entry point.
- `app.py` - switches between Single Player, Local Multiplayer, Online Multiplayer, and Quit.
- `config.py` - window, fonts, colors, FPS, and shared Pygame configuration.
- `roster.py` - Python library fighter definitions and stats.
- `input_devices.py` - keyboard/controller abstraction and controller detection.
- `entities.py` - Fighter, Projectile, and Particle game objects.
- `ui.py` - menus, character selection, HUD drawing, and shared interface helpers.
- `local_modes.py` - single-player CPU battle and local versus battle.
- `online.py` - LAN/direct-IP host/client networking and online battle synchronization.
- `assets/` - reserved for future sprites, icons, sound effects, and music.

## Windows build

Double-click `build_windows.bat`, or run:

```bash
pyinstaller --clean --noconsole --onedir --name "Jupyter" main.py
```

Use `--onedir` while developing. Once the game is stable, you can switch to `--onefile`.
