import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import unittest
import json
from unittest.mock import patch
import pygame

from jupyter_game.combat import step_battle, MAX_JUGGLE_HITS
from jupyter_game.combat_input import CommandDetector
from jupyter_game.entities import Fighter, Projectile
from jupyter_game.input_devices import InputDevice
from jupyter_game.roster import LIBRARIES
from jupyter_game.online import (fighter_to_state, apply_fighter_state,
                                 projectiles_to_state, apply_projectiles_state)


def fighter(name='NumPy', x=300, facing=1):
    return Fighter(next(d for d in LIBRARIES if d['name'] == name), x, facing, InputDevice('cpu'))


class PhaseTwoTests(unittest.TestCase):
    def setUp(self):
        self.a = fighter()
        self.b = fighter(x=375, facing=-1)
        self.b.hp = self.b.max_hp = 500
        self.projectiles, self.particles = [], []

    def tick(self, a=None, b=None, frames=1):
        for _ in range(frames):
            step_battle(self.a, self.b, self.projectiles, self.particles, a or {}, b or {})

    def hit(self, key):
        return self.b.receive_hit(self.a, self.a.moves[key], 1, self.particles)

    def test_launcher_lifts_and_chases_only_on_hit(self):
        self.tick({'launcher': True}, frames=9)
        self.assertTrue(self.b.launched)
        self.assertFalse(self.b.on_ground)
        self.assertLess(self.b.vel_y, 0)
        self.assertFalse(self.a.on_ground)
        self.assertTrue(self.b.disabled)

    def test_guarded_launcher_does_not_lift(self):
        self.b.guard = True
        self.assertEqual(self.hit('launcher'), 'guard')
        self.assertFalse(self.b.launched)
        self.assertTrue(self.b.on_ground)

    def test_low_launcher_air_light_heavy_special_all_test_fighters(self):
        for name in ('NumPy', 'TensorFlow', 'FastAPI'):
            with self.subTest(name=name):
                self.setUp()
                self.a = fighter(name)
                self.a.energy = 80
                self.a.queue_action('low')
                self.a.queue_action('heavy')
                sent = set()
                max_hits = 0
                for _ in range(110):
                    key = self.a.current_move
                    if self.a.move_connected and key in ('launcher', 'air_light', 'air_heavy') and key not in sent:
                        sent.add(key)
                        self.a.queue_action({'launcher': 'light', 'air_light': 'heavy', 'air_heavy': 'special'}[key])
                    self.tick()
                    max_hits = max(max_hits, self.a.combo_count)
                self.assertEqual(max_hits, 5)
                self.assertTrue(self.a.on_ground)
                self.assertTrue(self.b.on_ground)
                self.assertFalse(self.b.launched)
                self.assertFalse(self.b.knocked_down)
                self.assertLess(self.b.hp, 460)

    def test_juggle_limit_forces_landing_and_wakeup(self):
        self.hit('launcher')
        for _ in range(MAX_JUGGLE_HITS):
            self.assertEqual(self.hit('air_light'), 'hit')
        self.assertTrue(self.b.juggle_exhausted)
        hp = self.b.hp
        self.assertEqual(self.hit('air_light'), 'immune')
        self.assertEqual(self.b.hp, hp)
        self.tick()
        self.assertTrue(self.b.knocked_down)
        self.tick(frames=42)
        self.assertFalse(self.b.juggle_exhausted)
        self.assertFalse(self.b.knocked_down)
        self.assertEqual(self.hit('light'), 'hit')

    def test_air_move_requirements_and_landing_cancels(self):
        self.assertFalse(self.a.start_move('air_light'))
        self.a.on_ground = False
        self.a.rect.y -= 5
        self.a.vel_y = 5
        self.assertFalse(self.a.start_move('low'))
        self.assertTrue(self.a.start_move('light'))
        self.assertEqual(self.a.current_move, 'air_light')
        self.tick()
        self.assertTrue(self.a.on_ground)
        self.assertIsNone(self.a.current_move)

    def test_advanced_dash_cancel_combo(self):
        self.a.energy = 80
        self.a.queue_action('light')
        self.a.queue_action('light')
        sent = set()
        maximum = 0
        for _ in range(65):
            if self.a.combo_count == 2 and self.a.move_connected and 'dash' not in sent:
                self.a.queue_action('dash')
                sent.add('dash')
            if self.a.current_move == 'dash' and 'heavy' not in sent:
                self.a.queue_action('heavy')
                sent.add('heavy')
            if self.a.current_move == 'heavy' and self.a.move_connected and 'special' not in sent:
                self.a.queue_action('special')
                sent.add('special')
            self.tick()
            maximum = max(maximum, self.a.combo_count)
        self.assertEqual(maximum, 4)

    def test_character_specials_have_distinct_mechanics(self):
        self.a.energy = 50
        self.tick({'directional_special': True}, frames=11)
        # Move NumPy far enough away to see all three shots rather than hits.
        self.assertEqual(self.a.energy, 0 if not self.a.combo_count else self.a.combo_count * 12)
        fast = fighter('FastAPI')
        tensor = fighter('TensorFlow')
        self.assertFalse(fast.moves['special'].projectile)
        self.assertGreater(fast.moves['special'].dash_speed, 0)
        self.assertGreater(tensor.moves['utility'].guard_frames, 0)
        self.assertGreater(tensor.moves['directional_special'].launch_velocity * -1, 0)

    def test_fan_projectiles_and_network_preserve_move_and_velocity(self):
        self.b.rect.x = 900
        self.a.energy = 50
        self.tick({'directional_special': True}, frames=11)
        self.assertEqual(len(self.projectiles), 3)
        self.assertEqual(len({p.y for p in self.projectiles}), 3)
        states = json.loads(json.dumps(projectiles_to_state(self.projectiles, self.a)))
        restored = apply_projectiles_state(states, self.a, self.b)
        self.assertEqual(projectiles_to_state(restored, self.a), states)
        for p in restored:
            self.assertIs(p.move, self.a.moves['directional_special'])
            y = p.y
            p.update()
            self.assertLess(p.y, y)

    def test_defensive_utility_cost_and_invulnerability(self):
        self.a.energy = 25
        self.b.rect.x = 900
        self.tick({'utility': True})
        self.assertEqual(self.a.energy, 0)
        self.assertGreater(self.a.rect.x, 300)
        self.assertEqual(self.a.receive_hit(self.b, self.b.moves['light'], -1, []), 'immune')
        self.tick(frames=10)
        self.assertEqual(self.a.receive_hit(self.b, self.b.moves['light'], -1, []), 'hit')

    def test_tensor_guard_counter_gives_immediate_punish(self):
        self.b = fighter('TensorFlow', x=375, facing=-1)
        self.b.energy = 25
        self.assertTrue(self.b.start_move('utility'))
        self.assertEqual(self.hit('heavy'), 'parry')
        self.assertIsNone(self.b.current_move)
        self.assertTrue(self.b.start_move('light'))

    def test_direction_motion_expires_and_is_consumed(self):
        detector = CommandDetector()
        detector.down_pressed()
        self.assertEqual(detector.detect('special'), 'directional_special')
        self.assertEqual(detector.detect('special'), 'special')
        detector.down_pressed()
        detector.tick()
        detector.down_pressed()
        self.assertEqual(detector.detect('special'), 'utility')
        detector.down_pressed()
        for _ in range(19):
            detector.tick()
        self.assertEqual(detector.detect('special'), 'special')

    def test_keyboard_directional_commands_keep_order_across_packets(self):
        device = InputDevice('keyboard1')
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j),
                  pygame.event.Event(pygame.KEYUP, key=pygame.K_s),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)]
        state = json.loads(json.dumps(device.battle_state(events)))
        self.assertEqual(state['commands'], [[1, 'low'], [2, 'heavy']])
        self.a.prepare(state)
        self.a.prepare(state)
        self.assertEqual([a for a, _ in self.a.input_buffer], ['low', 'heavy'])

    def test_keyboard_double_down_special_and_forward_relative_to_facing(self):
        device = InputDevice('keyboard1')
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s),
                  pygame.event.Event(pygame.KEYUP, key=pygame.K_s),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k)]
        self.assertEqual(device.battle_state(events)['utility_seq'], 1)
        events = [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a),
                  pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)]
        device = InputDevice('keyboard1')
        self.assertEqual(device.battle_state(events, facing=-1)['forward_heavy_seq'], 1)

    def test_shift_guard_separate_from_down(self):
        keys = {pygame.K_s: True, pygame.K_LSHIFT: False}
        with patch('pygame.key.get_pressed', return_value=keys):
            device = InputDevice('keyboard1')
            self.assertTrue(device.holding_down())
            self.assertFalse(device.guarding())
            keys[pygame.K_LSHIFT] = True
            self.assertTrue(device.guarding())

    def test_already_held_down_selects_low_on_first_input_sample(self):
        device = InputDevice('keyboard1')
        with patch.object(device, 'holding_down', return_value=True):
            state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)])
        self.assertEqual(state['low_seq'], 1)
        self.assertEqual(state['light_seq'], 0)

    def test_gamepad_directional_moves_and_dash(self):
        class Pad:
            def get_instance_id(self): return 42
            def get_numhats(self): return 0
            def get_numaxes(self): return 2
            def get_axis(self, axis): return 0
            def get_numbuttons(self): return 6
            def get_button(self, button): return 0
        device = InputDevice('gamepad', Pad())
        events = [pygame.event.Event(pygame.JOYAXISMOTION, instance_id=42, axis=1, value=.8),
                  pygame.event.Event(pygame.JOYBUTTONDOWN, instance_id=42, button=2),
                  pygame.event.Event(pygame.JOYBUTTONDOWN, instance_id=42, button=5)]
        state = device.battle_state(events)
        self.assertEqual(state['low_seq'], 1)
        self.assertEqual(state['dash_seq'], 1)

    def test_snapshot_air_and_defensive_state_roundtrip(self):
        self.hit('launcher')
        self.b.juggle_hits = 2
        clone = fighter()
        state = json.loads(json.dumps(fighter_to_state(self.b)))
        apply_fighter_state(clone, state)
        self.assertEqual(fighter_to_state(clone), state)
        self.assertTrue(clone.launched)


if __name__ == '__main__':
    unittest.main()
