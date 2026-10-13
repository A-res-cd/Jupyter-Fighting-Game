"""Compare identical fight rendering with caches enabled/disabled; no FPS claims."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import statistics
import time
from unittest.mock import patch
from jupyter_game.ui import rendering as ui
from jupyter_game.core import config
from jupyter_game.combat import entities
from jupyter_game.combat.match import Match
from jupyter_game.input.devices import InputDevice


def measure(cached, frames=1000):
    match = Match((0, 4), (InputDevice('cpu'), InputDevice('cpu')))
    match.phase = 'fighting'
    values = []
    # Disable text caches and rebuild background in the same drawing workload.
    fonts = ('FONT', 'SMALL', 'BIG', 'TITLE')
    from contextlib import ExitStack
    with ExitStack() as stack:
        if not cached:
            for module in (ui, entities):
                for name in fonts:
                    if hasattr(module, name):
                        stack.enter_context(patch.object(module, name, getattr(config, name).font))
        for i in range(frames + 50):
            if not cached:
                ui._background = None
            match.timer = 5940 - i
            start = time.perf_counter()
            ui.draw_match(match)
            config.pygame.display.flip()
            elapsed = (time.perf_counter() - start) * 1000
            if i >= 50:
                values.append(elapsed)
    return dict(mean_ms=round(statistics.mean(values), 3),
                p95_ms=round(sorted(values)[int(len(values)*.95)], 3))


if __name__ == '__main__':
    print(json.dumps(dict(uncached=measure(False), cached=measure(True),
                         note='Headless drawing workload, not full-game FPS or physical GPU performance.'), indent=2))
