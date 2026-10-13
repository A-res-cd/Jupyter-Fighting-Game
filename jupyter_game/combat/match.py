"""Shared best-of-three lifecycle for local and authoritative online matches."""
from jupyter_game.core.config import FPS, WIDTH
from jupyter_game.combat.entities import Fighter
from jupyter_game.data.roster import LIBRARIES
from jupyter_game.combat.moves import step_battle
from jupyter_game.audio.effects import cue


def round_winner(p1, p2):
    if p1.hp <= 0 or p2.hp <= 0:
        return 0 if p1.hp <= 0 and p2.hp <= 0 else 2 if p1.hp <= 0 else 1
    # Cross multiply to avoid floating point differences on timeout draws.
    a, b = p1.hp * p2.max_hp, p2.hp * p1.max_hp
    return 0 if a == b else 1 if a > b else 2


class Match:
    def __init__(self, indices, devices):
        self.indices = indices
        self.devices = devices
        self.scores = [0, 0]
        self.round = 0
        self.tick = 0
        self.winner = None
        self.reset_round()

    def reset_round(self):
        self.round += 1
        for device in self.devices:
            device.reset()
        self.p1 = Fighter(LIBRARIES[self.indices[0]], 250, 1, self.devices[0])
        self.p2 = Fighter(LIBRARIES[self.indices[1]], WIDTH - 320, -1, self.devices[1])
        self.projectiles, self.particles = [], []
        self.timer = 99 * FPS
        self.phase = 'round_start'
        self.phase_timer = 60
        self.round_result = None
        cue('round')

    def step(self, state1, state2):
        self.tick += 1
        if self.phase == 'match_end':
            return
        if self.phase != 'fighting':
            self.phase_timer -= 1
            if self.phase_timer <= 0:
                if self.phase == 'round_end':
                    self.reset_round()
                else:
                    self.phase = 'fighting'
            # Countdown inputs cannot leak into fighting.
            self.p1.last_command_id = max(self.p1.last_command_id, max((n for n, _ in state1.get('commands', [])), default=0))
            self.p2.last_command_id = max(self.p2.last_command_id, max((n for n, _ in state2.get('commands', [])), default=0))
            return
        step_battle(self.p1, self.p2, self.projectiles, self.particles, state1, state2)
        self.timer -= 1
        if min(self.p1.hp, self.p2.hp) <= 0 or self.timer <= 0:
            self.round_result = round_winner(self.p1, self.p2)
            if self.round_result:
                self.scores[self.round_result - 1] += 1
            if max(self.scores) >= 2:
                self.winner = self.scores.index(2) + 1
                self.phase = 'match_end'
            else:
                self.phase = 'round_end'
                self.phase_timer = 120

    def clear_inputs(self):
        for fighter, device in zip((self.p1, self.p2), self.devices):
            device.reset(keep_serial=True)
            fighter.input_buffer.clear()
            fighter.last_command_id = device.command_serial
            fighter.previous_actions.clear()
