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
- Training: dummy behaviors, combo damage, input history, hitboxes, move list, and drills.
- Settings: CPU difficulty, preferred controller/keyboard, deadzone, key bindings, and sound.

## Matches and practice

Local and online matches use best-of-three rounds. KO wins a round; timeout compares
remaining HP percentage. Draws replay the round without awarding a win. CPU rematches
keep the same opponent. Combat runs at 60 simulation ticks per second independently
of drawing. Long stalls cap catch-up at eight ticks and discard excess elapsed time.

- Local: `P` or controller Start pauses; `P`/Enter/Start resumes. `Q` opens quit
  confirmation, `Y` quits, `N` stays. Esc or the Back button opens pause.
- `F3` shows update/drawing time and frame-work p95 during local matches.
- Training: `F5` resets, `F6` cycles idle/guard/timed attack/jump dummy, `F7` toggles
  infinite energy, `F8` toggles hitboxes, Tab shows the move list, Esc exits.
- Online result: `R`/controller A requests rematch; Enter/controller B requests
  fighter selection. Both players must choose; selection takes priority if choices
  differ. Esc leaves. Online matches continue while menus are absent; no online pause.

Settings apply to new input devices. Choose Save to persist preferences in
`%LOCALAPPDATA%/JupyterBrawl/settings.json` on Windows. `JUPYTER_SETTINGS_PATH` can
override the file location. Missing preferred controllers fall back to keyboard.
Disconnected local controllers pause the game; `K` switches affected players to
keyboard. An online controller disconnect ends the session with a message.

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

NumPy, TensorFlow, FastAPI, Pandas, PyTorch, and Requests have twelve named moves each and distinct mechanics:
NumPy's Axis Burst fires a rising three-shot fan; TensorFlow's Gradient Slam launches
and Layer Guard blocks/counters; FastAPI's Async Blitz/Coroutine Rush close distance
and Coroutine Dash gives a fast invulnerable escape. Pandas has long-range guard
pressure and Schema Guard; PyTorch has fast projectiles and Flame Fan; Requests
has advancing attacks and a backward Timeout Escape. Utilities require neutral or
recovery completion; they cannot escape hit stun or stagger. The remaining roster
uses the expanded baseline with its existing stats.

CPU, local play, and the online host use the same combat simulation. Online snapshots
include air/juggle states, defensive effects, and each projectile's move/trajectory;
both machines must use this version. Ordered command history preserves directional
inputs and cross-button order across skipped input snapshots.

Full move sets for the remaining fighters, supers, and Burst remain later phases.
Online now uses a version handshake, validated bounded packets, a background send
worker, retained/acknowledged ordered commands, match/round IDs, snapshot sequences,
50 ms fighter position interpolation, ping and snapshot-age indicators, visual hit
events, cancellable connection screens, and rematch/reselection handshakes. Both
machines need this version. The host remains authoritative. Prediction and rollback
remain future work; interpolation adds presentation delay rather than reducing
remote input latency.

Run the headless combat checks with:

```bash
python -m unittest discover -s tests -v
```

Additional headless checks:

```bash
python tools/benchmark.py
python tools/balance_check.py
python tools/online_smoke.py
```

The benchmark compares identical drawing with/without caches, not full-game FPS.
The balance check runs 27 seeded CPU bouts across the three expanded fighter kits.
The online smoke check runs two separate game processes through selection,
best-of-three, rematch, and reselection using local socket pairs.

## Project structure

```text
Jupyter/
|-- main.py
|-- requirements.txt
|-- build_windows.bat
|-- jupyter_game/
|   |-- app.py                  # Mode selection and application flow
|   |-- __main__.py             # python -m jupyter_game
|   |-- core/                   # Display config, timing, preferences
|   |-- combat/                 # Moves, entities, matches, CPU
|   |-- data/                   # Roster and character profiles
|   |-- input/                  # Devices and directional commands
|   |-- audio/                  # Generated sound effects
|   |-- ui/                     # Drawing, menus and settings screens
|   |-- modes/                  # Local, training and online flows
|   `-- networking/             # Protocol, transport, snapshots, interpolation
|-- tests/
|   |-- combat/
|   |-- integration/
|   `-- ui/
|-- tools/                      # Benchmark, balance and online smoke checks
|-- docs/
|   |-- ARCHITECTURE.md
|   `-- ROADMAP.md
`-- assets/                     # Fighter, audio and interface asset directories
```

See [architecture and development guide](docs/ARCHITECTURE.md) for module
responsibilities and focused test commands. The [roadmap](docs/ROADMAP.md)
records completed features and later work.

You can also launch the game with `python -m jupyter_game`.

## Windows build

Double-click `build_windows.bat`, or run:

```bash
pyinstaller --clean --noconsole --onedir --name "Jupyter" main.py
```

Use `--onedir` while developing. Once the game is stable, you can switch to `--onefile`.
