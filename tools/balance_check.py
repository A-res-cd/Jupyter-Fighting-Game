"""Seeded bouts catch invalid/stuck kits; win counts alone do not establish balance."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from jupyter_game.combat.match import Match, round_winner
from jupyter_game.input.devices import InputDevice
from jupyter_game.combat.cpu import CPU
from jupyter_game.data.roster import LIBRARIES


def run():
    names = ('Pandas', 'PyTorch', 'Requests')
    results = []
    for difficulty in ('easy', 'normal', 'hard'):
        for first, second in (('Pandas', 'PyTorch'), ('PyTorch', 'Requests'), ('Requests', 'Pandas')):
            for seed in (7, 19, 41):
                indices = [next(i for i, d in enumerate(LIBRARIES) if d['name'] == name) for name in (first, second)]
                match = Match(indices, (InputDevice('cpu'), InputDevice('cpu')))
                match.phase = 'fighting'
                a, b = CPU(difficulty, seed), CPU(difficulty, seed+1)
                for frame in range(5940):
                    match.step(a.state(match.p1, match.p2), b.state(match.p2, match.p1))
                    if match.phase != 'fighting':
                        break
                results.append(dict(difficulty=difficulty, seed=seed, p1=first, p2=second,
                                    frames=frame+1, winner=round_winner(match.p1, match.p2),
                                    hp=[match.p1.hp, match.p2.hp]))
    return results


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
