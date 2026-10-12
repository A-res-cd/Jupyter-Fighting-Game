import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import json
import socket
import time
import unittest

import pygame
from jupyter_game.combat import step_battle
from jupyter_game.entities import Fighter, Projectile
from jupyter_game.input_devices import InputDevice
from jupyter_game.roster import LIBRARIES
from jupyter_game.online import (fighter_to_state, apply_fighter_state,
                                 projectiles_to_state, apply_projectiles_state,
                                 OnlinePeer, send_json_line)


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.a = Fighter(LIBRARIES[0], 300, 1, InputDevice('cpu'))
        self.b = Fighter(LIBRARIES[0], 375, -1, InputDevice('cpu'))
        self.projectiles, self.particles = [], []

    def tick(self, a=None, b=None, frames=1):
        for _ in range(frames):
            step_battle(self.a, self.b, self.projectiles, self.particles, a or {}, b or {})

    def hit(self, key='light'):
        return self.b.receive_hit(self.a, self.a.moves[key], 1, self.particles)

    def test_startup_and_single_hit(self):
        self.tick({'light': True})
        self.tick(frames=4)
        self.assertEqual(self.b.hp, self.b.max_hp)
        self.tick()
        hp = self.b.hp
        self.assertLess(hp, self.b.max_hp)
        self.tick(frames=10)
        self.assertEqual(self.b.hp, hp)
        self.assertEqual(self.b.stagger, 8)

    def test_whiff_does_not_build_stagger(self):
        self.b.rect.x = 900
        self.tick({'heavy': True})
        self.tick(frames=40)
        self.assertEqual(self.b.stagger, 0)
        self.assertEqual(self.b.hp, self.b.max_hp)

    def test_buffered_light_light_heavy(self):
        self.a.queue_action('light')
        self.a.queue_action('light')
        self.a.queue_action('heavy')
        self.tick(frames=24)
        self.assertEqual(self.a.combo_count, 3)
        self.assertEqual(self.b.stagger, 34)
        self.assertEqual(self.a.combo_scaling, .9)

    def test_guard_pressure_and_break(self):
        self.b.stagger = 95
        self.b.guard = True
        self.assertEqual(self.hit('heavy'), 'guard')
        self.assertGreater(self.b.hp, self.b.max_hp - self.a.moves['heavy'].damage)
        self.assertTrue(self.b.staggered)
        self.assertEqual(self.b.notice, 'GUARD BREAK')
        self.assertFalse(self.b.guard)

    def test_stagger_break_is_separate_from_hitstun(self):
        self.b.stagger = 95
        self.hit()
        self.assertEqual(self.b.stagger, 0)
        self.assertEqual(self.b.stagger_timer, 60)
        self.assertGreater(self.b.hitstun, 0)
        self.b.queue_action('heavy')
        self.tick(b={'guard': True}, frames=20)
        self.assertTrue(self.b.staggered)
        self.assertFalse(self.b.guard)
        self.assertIsNone(self.b.current_move)
        self.assertEqual(self.b.hitstun, 0)

    def test_stagger_protection_until_neutral(self):
        self.b.stagger = 99
        self.hit()
        self.hit()
        self.assertAlmostEqual(self.b.stagger, 1.2)
        self.assertTrue(self.b.stagger_protected)
        self.tick(frames=95)
        self.assertFalse(self.b.stagger_protected)
        self.hit()
        self.assertEqual(self.b.stagger, 8)

    def test_perfect_parry_no_chip_and_advantage(self):
        self.b.prepare({'guard': True})
        self.assertEqual(self.hit(), 'parry')
        self.assertEqual(self.b.hp, self.b.max_hp)
        self.assertEqual(self.b.energy, 20)
        self.assertEqual(self.a.stagger, 40)
        self.assertEqual(self.a.hitstun, 30)
        self.assertGreater(self.b.hitstop, 0)

    def test_normal_parry(self):
        self.b.prepare({'guard': True})
        for _ in range(5):
            self.b.prepare({'guard': True})
        self.assertEqual(self.hit(), 'parry')
        self.assertEqual(self.a.stagger, 25)
        self.assertEqual(self.a.hitstun, 24)
        self.assertEqual(self.b.energy, 10)

    def test_failed_parry_cannot_be_spammed(self):
        self.b.prepare({'guard': True})
        self.b.prepare({})
        self.b.prepare({'guard': True})
        self.assertEqual(self.b.parry_window, 0)
        self.assertGreater(self.b.parry_recovery, 0)
        self.assertEqual(self.hit(), 'guard')

    def test_held_guard_does_not_rearm_parry(self):
        self.b.prepare({'guard': True})
        for _ in range(35):
            self.b.prepare({'guard': True})
        self.assertEqual(self.b.parry_window, 0)
        self.assertEqual(self.hit(), 'guard')

    def test_back_attack_bypasses_guard(self):
        self.b.facing = 1
        self.b.prepare({'guard': True})
        self.assertEqual(self.hit(), 'hit')

    def test_counter_hit(self):
        self.b.start_move('heavy')
        self.hit()
        self.assertEqual(self.b.hitstun, 27)
        self.assertAlmostEqual(self.b.stagger, 11.2)
        self.assertEqual(self.b.notice, 'COUNTER!')
        self.assertIsNone(self.b.current_move)

    def test_scaling_survives_stagger_break(self):
        self.b.max_hp = self.b.hp = 500
        self.b.stagger = 90
        for _ in range(8):
            self.hit()
        self.assertEqual(self.a.combo_count, 8)
        self.assertEqual(self.a.combo_scaling, .55)
        self.assertTrue(self.b.staggered)

    def test_knockdown_and_wakeup_invulnerability(self):
        self.hit('heavy')
        self.assertTrue(self.b.pending_knockdown)
        self.assertFalse(self.b.knocked_down)
        self.tick(frames=24)
        self.assertTrue(self.b.knocked_down)
        self.assertEqual(self.hit(), 'immune')
        self.tick(frames=30)
        self.assertFalse(self.b.knocked_down)
        self.assertGreater(self.b.wakeup_invulnerability, 0)
        self.assertEqual(self.hit(), 'immune')
        self.tick(frames=12)
        self.assertEqual(self.hit(), 'hit')

    def test_special_cancel_and_projectile_defense(self):
        self.a.energy = 80
        self.a.queue_action('heavy')
        self.a.queue_action('special')
        self.tick(frames=27)
        self.assertEqual(self.a.energy, 54)  # two connected hits refund 12 each
        self.assertEqual(self.a.combo_count, 2)
        self.assertFalse(self.b.pending_knockdown)
        self.assertFalse(self.b.knocked_down)

    def test_network_counter_catches_skipped_and_duplicate_packets(self):
        self.a.prepare({'light_seq': 2})
        self.a.prepare({'light_seq': 2})
        self.assertEqual(len(self.a.input_buffer), 2)
        self.a.prepare({'light_seq': 1})
        self.assertEqual(len(self.a.input_buffer), 2)

    def test_projectile_uses_guard_and_parry_rules(self):
        projectile = Projectile(self.a, 1, self.a.moves['special'])
        projectile.x = self.b.rect.centerx - projectile.vx
        self.projectiles.append(projectile)
        self.tick(b={'guard': True})
        self.assertEqual(self.b.hp, self.b.max_hp)
        self.assertEqual(self.b.notice, 'PERFECT PARRY!')
        self.assertEqual(len(self.projectiles), 0)
        self.assertEqual(self.a.stagger, 40)

    def test_insufficient_energy_does_not_start_special(self):
        self.assertFalse(self.a.start_move('special'))
        self.assertIsNone(self.a.current_move)
        self.assertEqual(self.a.energy, 0)

    def test_input_maps_heavy_and_keeps_menu_back(self):
        device = InputDevice('keyboard1')
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)])
        self.assertEqual(state['heavy_seq'], 1)
        self.assertEqual(device.event_action(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)), 'back')

    def test_snapshots_include_defense_moves_and_projectiles(self):
        self.b.stagger = 99
        self.hit()
        self.a.start_move('heavy')
        clone = Fighter(LIBRARIES[0], 0, 1, InputDevice('cpu'))
        snapshot = json.loads(json.dumps(fighter_to_state(self.b)))
        apply_fighter_state(clone, snapshot)
        self.assertEqual(fighter_to_state(clone), snapshot)
        self.projectiles.append(Projectile(self.a, 1, self.a.moves['special']))
        states = projectiles_to_state(self.projectiles, self.a)
        restored = apply_projectiles_state(states, self.a, self.b)
        self.assertEqual(projectiles_to_state(restored, self.a), states)

    def test_all_roster_works_with_distinct_baselines(self):
        for data in LIBRARIES:
            f = Fighter(data, 300, 1, InputDevice('cpu'))
            self.assertTrue(f.start_move('light'))
        fast = Fighter(LIBRARIES[15], 0, 1, InputDevice('cpu'))
        heavy = Fighter(LIBRARIES[4], 0, 1, InputDevice('cpu'))
        self.assertLess(fast.moves['light'].startup, heavy.moves['light'].startup)
        self.assertLess(fast.moves['heavy'].stagger_damage, heavy.moves['heavy'].stagger_damage)

    def test_socket_peer_preserves_latest_action_counter(self):
        sender, receiver = socket.socketpair()
        peer = OnlinePeer(receiver, True)
        try:
            send_json_line(sender, {'type': 'input', 'data': {'light_seq': 1}})
            send_json_line(sender, {'type': 'input', 'data': {'light_seq': 2}})
            deadline = time.monotonic() + 1
            while peer.get_remote_input().get('light_seq') != 2 and time.monotonic() < deadline:
                time.sleep(.005)
            state = peer.get_remote_input()
            self.a.prepare(state)
            self.a.prepare(state)
            self.assertEqual(len(self.a.input_buffer), 2)
        finally:
            peer.close()
            sender.close()
            peer.thread.join(timeout=1)


if __name__ == '__main__':
    unittest.main()
