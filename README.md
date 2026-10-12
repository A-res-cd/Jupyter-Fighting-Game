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

## Combat v2

The core combat and launcher/air-combo implementation phases are complete: data-driven light, heavy,
and special moves with startup, active, and recovery frames; a 300 ms input
buffer; Light > Light > Heavy chains; special cancels; separate hit stun,
stagger break, and knockdown; guard pressure; normal/perfect parries; counter
hits; combo scaling; and wake-up invulnerability.

Connected hits build stagger. At 100 stagger, the meter resets and the defender
cannot act for 60 frames. Stagger gain drops to 15% until 30 neutral frames
have passed, preventing repeated breaks within the same combo. Guarded hits
deal chip damage and stagger pressure. Tap guard before impact to parry:
the first 4 frames give a perfect parry, and the whole window lasts 9 frames.
Missed taps have an 18-frame retry cooldown. Hold guard to keep blocking.

| Action | Keyboard 1 | Keyboard 2 | Controller |
|---|---|---|---|
| Move | A / D | Left / Right | Stick / D-pad |
| Jump | W | Up | A |
| Light | J | N | X |
| Heavy | L | Comma | B |
| Special (50 energy) | K | M | Y |
| Down | S | Down | Stick / D-pad down |
| Guard / Parry | Left Shift | Right Shift | LB |
| Dash | I | Period | RB |
| Main menu | Esc | Esc | Esc on keyboard |

Guard moved from S/Down to Shift to make directional attacks available.

New routes and commands:

- Down + Light starts a low attack; a connected low cancels into a launcher with Heavy.
- Down + Heavy also launches directly. A connected launcher automatically jumps after the opponent.
- Light/Heavy/Special in the air select their air versions. Try Low > Heavy > Light > Heavy > Special.
- Forward + Heavy closes distance. Light > Light > Dash > Heavy > Special is also supported.
- Tap Down, then Special within 300 ms for a directional special.
- Tap Down twice, then Special within 300 ms for a 25-energy defensive utility.
- A launched opponent can take four follow-up hits before juggle protection forces landing,
  knockdown, and wake-up invulnerability. Combo scaling continues through the air sequence.

NumPy, TensorFlow, and FastAPI have twelve named moves each and distinct mechanics:
NumPy's Axis Burst fires a rising three-shot fan; TensorFlow's Gradient Slam launches
and Layer Guard blocks/counters; FastAPI's Async Blitz/Coroutine Rush close distance
and Coroutine Dash gives a fast invulnerable escape. Utilities require neutral or
recovery completion; they cannot escape hit stun or stagger. The remaining roster
uses the expanded baseline with its existing stats.

CPU, local play, and the online host use the same combat simulation. Online snapshots
include air/juggle states, defensive effects, and each projectile's move/trajectory;
both machines must use this version. Ordered command history preserves directional
inputs and cross-button order across skipped input snapshots.

Full move sets for the remaining fighters, supers, and Burst remain later phases.
LAN latency
interpolation, prediction, and online rematches also remain future work.

Run the headless combat checks with:

```bash
python -m unittest discover -s tests -v
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
- `combat.py` - Move data, baseline/test-fighter profiles, and shared round simulation.
- `combat_input.py` - Directional command detection and motion timing.
- `characters.py` - NumPy, TensorFlow, and FastAPI move overrides.
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
