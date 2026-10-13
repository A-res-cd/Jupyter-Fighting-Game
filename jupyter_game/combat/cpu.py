"""Seedable CPU with delayed observations and controlled decision cadence."""
from collections import deque
import random

PROFILES = {
    'easy': dict(delay=24, cadence=24, guard=.25, range=115, combos=False),
    'normal': dict(delay=12, cadence=12, guard=.6, range=125, combos=True),
    'hard': dict(delay=6, cadence=6, guard=.85, range=135, combos=True),
}


class CPU:
    def __init__(self, difficulty='normal', seed=None):
        self.profile = PROFILES[difficulty]
        self.rng = random.Random(seed)
        self.observations = deque(maxlen=self.profile['delay'] + 1)
        self.frame = self.serial = 0
        self.history = []
        self.guard = False
        self.last_combo = None

    def state(self, fighter, opponent):
        self.frame += 1
        self.observations.append((opponent.rect.centerx, opponent.current_move is not None,
                                  opponent.launched))
        state = dict(commands=list(self.history), guard=self.guard)
        if len(self.observations) <= self.profile['delay']:
            return state
        x, attacking, launched = self.observations[0]
        dx = x - fighter.rect.centerx
        state.update(left=dx < -self.profile['range'], right=dx > self.profile['range'])
        if fighter.disabled:
            self.guard = False
            state['guard'] = False
            return state
        if not fighter.current_move:
            fighter.facing = 1 if dx >= 0 else -1
        action = None
        if self.frame % self.profile['cadence'] == 0:
            self.guard = attacking and abs(dx) < 170 and self.rng.random() < self.profile['guard']
            if not self.guard and not fighter.current_move:
                if abs(dx) < 160:
                    action = self.rng.choice(['light', 'light', 'low', 'heavy', 'launcher', 'special'])
                elif abs(dx) > 220:
                    action = 'dash'
        if self.profile['combos'] and fighter.current_move and fighter.move_connected:
            token = (fighter.current_move, fighter.combo_count)
            if token != self.last_combo:
                routes = dict(low='heavy', launcher='light', air_light='heavy', air_heavy='special',
                              light='heavy', heavy='special')
                action = routes.get(fighter.current_move)
                self.last_combo = token
        if action:
            key = {'light': 'air_light', 'heavy': 'air_heavy', 'special': 'air_special'}.get(action, action) if not fighter.on_ground else action
            move = fighter.moves.get(key)
            current = fighter.moves.get(fighter.current_move)
            if move and fighter.energy >= move.energy_cost and (not current or key in current.cancels or (fighter.current_move == 'low' and key == 'heavy')):
                self.serial += 1
                self.history.append((self.serial, action))
                self.history = self.history[-32:]
        state.update(guard=self.guard, commands=list(self.history))
        return state
