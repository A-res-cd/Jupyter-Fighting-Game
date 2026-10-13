import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import copy
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import patch
import pygame
from jupyter_game.core.timing import FixedClock
from jupyter_game.combat.match import Match, round_winner
from jupyter_game.input.devices import InputDevice
from jupyter_game.combat.moves import step_battle
from jupyter_game.combat.cpu import CPU, PROFILES
from jupyter_game.modes.training import Training
from jupyter_game.core.settings import load_settings, save_settings, DEFAULTS
from jupyter_game.networking.transport import OnlinePeer
from jupyter_game.networking.protocol import send_json_line, recv_json_line, validate_state, validate_input, PROTOCOL, MAX_PACKET
from jupyter_game.networking.snapshots import fighter_to_state, projectiles_to_state
from jupyter_game.networking.interpolation import Interpolator
from jupyter_game.data.roster import LIBRARIES


def new_match():
    return Match((0, 4), (InputDevice('keyboard1'), InputDevice('keyboard2')))


def snapshot(match, seq=1, match_id='test'):
    return dict(match_id=match_id, seq=seq, tick=match.tick, round=match.round,
                phase=match.phase, timer=match.timer, scores=match.scores,
                winner=match.winner, round_result=match.round_result,
                p1=fighter_to_state(match.p1), p2=fighter_to_state(match.p2),
                projectiles=projectiles_to_state(match.projectiles, match.p1), effects=[])


class NextReleaseTests(unittest.TestCase):
    def test_render_rates_have_same_simulation_and_commands(self):
        outcomes = []
        for fps in (30, 60, 120):
            match = new_match()
            match.phase = 'fighting'
            match.p1.rect.x, match.p2.rect.x = 300, 375
            timer = FixedClock()
            state = dict(commands=[(1, 'light'), (2, 'light'), (3, 'heavy')])
            for _ in range(fps * 2):
                for _ in range(timer.steps(1 / fps)):
                    match.step(state, {})
            outcomes.append((fighter_to_state(match.p1), fighter_to_state(match.p2), match.timer, match.tick))
            self.assertEqual(match.p1.last_command_id, 3)
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[1], outcomes[2])

    def test_long_stall_caps_catchup(self):
        timer = FixedClock()
        self.assertEqual(timer.steps(5), 8)
        self.assertGreater(timer.dropped_seconds, 4)
        timer.reset()
        self.assertEqual(timer.steps(0), 0)

    def test_input_pending_until_simulation_and_motion_expiry(self):
        device = InputDevice('keyboard1')
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s)], advance=False)
        for _ in range(30):
            device.battle_state([], advance=False)
        self.assertEqual(device.commands.frame, 0)
        device.advance_time(19)
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_k)], advance=False)
        self.assertEqual(state['commands'][-1][1], 'special')

    def test_best_of_three_reset_and_match_end(self):
        match = new_match()
        match.phase = 'fighting'
        match.p2.hp = 0
        match.step({}, {})
        self.assertEqual(match.scores, [1, 0])
        self.assertEqual(match.phase, 'round_end')
        old = match.p1
        old.input_buffer.append(('special', 18))
        for _ in range(120):
            match.step({}, {})
        self.assertEqual(match.round, 2)
        self.assertIsNot(match.p1, old)
        self.assertFalse(match.p1.input_buffer)
        self.assertEqual(match.p2.hp, match.p2.max_hp)
        match.phase = 'fighting'
        match.p2.hp = 0
        match.step({}, {})
        self.assertEqual(match.phase, 'match_end')
        self.assertEqual(match.winner, 1)

    def test_countdown_commands_discarded(self):
        match = new_match()
        state = dict(commands=[(1, 'special')])
        for _ in range(60):
            match.step(state, {})
        match.p1.energy = 100
        match.step(state, {})
        self.assertIsNone(match.p1.current_move)

    def test_timeout_percentage_and_double_ko(self):
        match = new_match()
        match.p1.hp = 100
        match.p2.hp = 110
        self.assertEqual(round_winner(match.p1, match.p2), 1)
        match.p1.hp = match.p2.hp = 0
        self.assertEqual(round_winner(match.p1, match.p2), 0)

    def test_draw_round_does_not_award_win(self):
        match = new_match()
        match.phase = 'fighting'
        match.p1.hp = match.p2.hp = 0
        match.step({}, {})
        self.assertEqual(match.scores, [0, 0])
        self.assertEqual(match.round_result, 0)

    def test_pause_clear_drops_old_inputs(self):
        match = new_match()
        device = match.devices[0]
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)])
        match.p1.prepare(state)
        match.clear_inputs()
        match.p1.prepare(device.battle_state([]))
        self.assertFalse(match.p1.input_buffer)
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_l)])
        match.p1.prepare(state)
        self.assertEqual(match.p1.input_buffer[0][0], 'heavy')

    def test_settings_roundtrip_and_invalid_fallback(self):
        with tempfile.TemporaryDirectory(dir='.') as directory:
            path = Path(directory) / 'prefs.json'
            data = copy.deepcopy(DEFAULTS)
            data['difficulty'] = 'hard'
            data['deadzone'] = .4
            data['bindings']['keyboard1']['light'] = pygame.K_u
            save_settings(data, path)
            self.assertEqual(load_settings(path), data)
            path.write_text('{broken', encoding='utf-8')
            self.assertEqual(load_settings(path), DEFAULTS)
            path.write_text(json.dumps(dict(deadzone=4, bindings=dict(keyboard1=dict(light=-1)))), encoding='utf-8')
            self.assertEqual(load_settings(path), DEFAULTS)

    def test_custom_binding_is_used_in_combat(self):
        device = InputDevice('keyboard1')
        device.bindings['light'] = pygame.K_u
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_u)])
        self.assertEqual(state['commands'], [(1, 'light')])
        state = device.battle_state([pygame.event.Event(pygame.KEYDOWN, key=pygame.K_j)])
        self.assertEqual(state['commands'], [(1, 'light')])

    def test_training_reset_isolated_and_damage_meter(self):
        training = Training(0)
        normal = new_match()
        for frame in range(30):
            training.step(dict(commands=[(1, 'light')]))
        self.assertGreater(training.last_damage, 0)
        self.assertEqual(training.p2.hp, training.p2.max_hp)
        self.assertTrue(training.p1.show_hitboxes)
        self.assertFalse(normal.p1.show_hitboxes)
        training.reset()
        self.assertFalse(training.history)
        self.assertEqual(training.last_damage, 0)
        self.assertFalse(training.projectiles)
        self.assertFalse(training.p1.input_buffer)

    def test_training_dummy_behaviors(self):
        session = Training(0)
        session.behavior = 1
        session.step({})
        self.assertTrue(session.p2.guard)
        session.reset()
        session.behavior = 2
        session.step({})
        self.assertEqual(session.p2.current_move, 'light')
        session.reset()
        session.behavior = 3
        session.step({})
        self.assertFalse(session.p2.on_ground)

    def test_training_parry_drill_requires_punish(self):
        session = Training(0)
        session.behavior = 2
        for _ in range(5):
            session.step({})
        session.step(dict(guard=True))
        self.assertIsNotNone(session.parry_at)
        self.assertFalse(session.drill_parry)
        for _ in range(20):
            session.step(dict(commands=[(1, 'light')]))
        self.assertTrue(session.drill_parry)

    def test_cpu_waits_for_reaction_and_is_seeded(self):
        for difficulty in PROFILES:
            a, b = CPU(difficulty, 42), CPU(difficulty, 42)
            match = new_match()
            match.p1.rect.x, match.p2.rect.x = 300, 375
            match.p2.current_move = 'heavy'
            for frame in range(120):
                first = a.state(match.p1, match.p2)
                self.assertEqual(first, b.state(match.p1, match.p2))
                if frame < PROFILES[difficulty]['delay']:
                    self.assertFalse(first.get('guard'))
                    self.assertFalse(first['commands'])

    def test_cpu_does_not_attack_while_disabled(self):
        match = new_match()
        match.p1.hitstun = 100
        cpu = CPU('hard', 10)
        for _ in range(100):
            self.assertFalse(cpu.state(match.p1, match.p2)['commands'])

    def test_expanded_kits_have_distinct_mechanics(self):
        from jupyter_game.combat.moves import moves_for
        moves = {name: moves_for(next(d for d in LIBRARIES if d['name'] == name)) for name in ('Pandas', 'PyTorch', 'Requests')}
        self.assertFalse(moves['Pandas']['special'].projectile)
        self.assertGreater(moves['Pandas']['special'].guard_damage, 20)
        self.assertEqual(moves['PyTorch']['directional_special'].projectile_count, 3)
        self.assertLess(moves['Requests']['utility'].dash_speed, 0)
        for kit in moves.values():
            self.assertEqual(len({m.name for m in kit.values()}), 12)

    def test_expanded_kits_keep_low_launcher_air_route(self):
        from jupyter_game.combat.entities import Fighter
        for name in ('Pandas', 'PyTorch', 'Requests'):
            with self.subTest(name=name):
                data = next(d for d in LIBRARIES if d['name'] == name)
                a = Fighter(data, 300, 1, InputDevice('cpu'))
                b = Fighter(LIBRARIES[0], 375, -1, InputDevice('cpu'))
                b.hp = b.max_hp = 500
                a.energy = 80
                a.queue_action('low')
                a.queue_action('heavy')
                projectiles, particles, sent = [], [], set()
                maximum = 0
                for _ in range(130):
                    current = a.current_move
                    if a.move_connected and current in ('launcher', 'air_light', 'air_heavy') and current not in sent:
                        sent.add(current)
                        a.queue_action(dict(launcher='light', air_light='heavy', air_heavy='special')[current])
                    step_battle(a, b, projectiles, particles, {}, {})
                    maximum = max(maximum, a.combo_count)
                self.assertEqual(maximum, 5)
                self.assertTrue(a.on_ground and b.on_ground)

    def test_interpolation_does_not_modify_snapshot(self):
        match = new_match()
        a = snapshot(match)
        b = copy.deepcopy(a)
        b['p1']['x'] += 100
        interpolation = Interpolator(delay=0)
        interpolation.add(a, 1)
        interpolation.add(b, 2)
        self.assertEqual(interpolation.positions(1.5)[0][0], a['p1']['x'] + 50)
        self.assertEqual(fighter_to_state(match.p1), a['p1'])
        b['round'] = 2
        interpolation.add(b, 3)
        self.assertEqual(len(interpolation.samples), 1)


class NetworkingTests(unittest.TestCase):
    def setUp(self):
        self.peers = []
        self.sockets = []

    def tearDown(self):
        for peer in self.peers:
            peer.close()
        for sock in self.sockets:
            sock.close()
        for peer in self.peers:
            peer.thread.join(1)
            peer.writer.join(1)

    def pair(self):
        a, b = socket.socketpair()
        host, client = OnlinePeer(a, True), OnlinePeer(b, False)
        self.peers.extend((host, client))
        return host, client

    def raw_peer(self, is_host=True):
        sender, receiver = socket.socketpair()
        peer = OnlinePeer(receiver, is_host)
        self.peers.append(peer)
        self.sockets.append(sender)
        return sender, peer

    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate() and time.monotonic() < deadline:
            time.sleep(.002)
        self.assertTrue(predicate())

    def test_handshake_and_ping(self):
        host, client = self.pair()
        host.start_handshake()
        client.start_handshake()
        self.wait_for(lambda: host.hello is not None and client.hello is not None)
        host.heartbeat()
        self.wait_for(lambda: host.ping_ms is not None)

    def test_wrong_version_and_malformed_packet_fail_cleanly(self):
        sender, peer = self.raw_peer()
        send_json_line(sender, dict(type='hello', data=dict(version=PROTOCOL-1, host=False, roster=[])))
        self.wait_for(lambda: not peer.connected)
        self.assertIn('version', peer.error)
        sender, peer = self.raw_peer()
        sender.sendall(b'[]\n')
        self.wait_for(lambda: not peer.connected)
        self.assertIn('object', peer.error)

    def test_coalesced_inputs_ack_and_order_without_duplicates(self):
        host, client = self.pair()
        host.set_epoch('test', 1)
        client.set_epoch('test', 1)
        for n in range(1, 51):
            client.send_input(dict(commands=[(n, 'light' if n % 2 else 'heavy')], left=False))
        self.wait_for(lambda: client.last_ack == 50)
        state = host.get_remote_input()
        self.assertEqual([n for n, _ in state['commands']], list(range(1, 51)))
        client.send_input(dict(commands=[(50, 'heavy')]))
        time.sleep(.02)
        self.assertEqual(host.get_remote_input()['commands'], [])
        self.assertFalse(client.pending_commands)

    def test_old_round_input_rejected(self):
        sender, host = self.raw_peer()
        host.set_epoch('test', 2)
        send_json_line(sender, dict(type='input', epoch='test:1', data=dict(commands=[[1, 'special']])))
        send_json_line(sender, dict(type='input', epoch='test:2', data=dict(commands=[[1, 'light']])))
        self.wait_for(lambda: host.last_remote_command == 1)
        self.assertEqual(host.get_remote_input()['commands'], [(1, 'light')])

    def test_stale_snapshot_not_applied_and_epoch_reset(self):
        sender, client = self.raw_peer(False)
        client.set_epoch('test', 1)
        data = snapshot(new_match(), 3)
        send_json_line(sender, dict(type='state', data=data))
        older = copy.deepcopy(data)
        older['seq'] = 2
        older['p1']['x'] = 900
        send_json_line(sender, dict(type='state', data=older))
        self.wait_for(lambda: client.latest_sequence == 3)
        self.assertEqual(client.get_state()['p1']['x'], data['p1']['x'])
        client.set_epoch('next', 1)
        self.assertIsNone(client.get_state())
        self.assertEqual(client.latest_sequence, -1)

    def test_bad_move_and_numeric_fields_rejected(self):
        state = snapshot(new_match())
        validate_state(state)
        state['p1']['current_move'] = 'unknown'
        with self.assertRaises(ValueError):
            validate_state(state)
        state = snapshot(new_match())
        state['p1']['hp'] = float('nan')
        with self.assertRaises(ValueError):
            validate_state(state)
        with self.assertRaises(ValueError):
            validate_input(dict(commands=[[2, 'light'], [1, 'heavy']]))

    def test_packet_size_bounded(self):
        with self.assertRaises(ValueError):
            send_json_line(None, dict(data='x' * MAX_PACKET))

    def test_fragmented_packet_across_timeout(self):
        sender, receiver = socket.socketpair()
        self.sockets.extend((sender, receiver))
        receiver.settimeout(.01)
        import threading
        def delayed():
            sender.sendall(b'{"type":')
            time.sleep(.04)
            sender.sendall(b'"ping","data":1}\n')
        thread = threading.Thread(target=delayed)
        thread.start()
        message, rest = recv_json_line(receiver, b'')
        thread.join()
        self.assertEqual(message, dict(type='ping', data=1))
        self.assertEqual(rest, b'')

    def test_reliable_match_controls_and_reconnect(self):
        host, client = self.pair()
        host.send_control(dict(action='transition', match_id='new', from_id='old', target='rematch', indices=[0, 4]))
        self.wait_for(lambda: bool(client.control))
        transition = client.get_controls()[0]
        self.assertEqual(transition['match_id'], 'new')
        client.send_control(dict(action='transition_ack', match_id='new'))
        self.wait_for(lambda: bool(host.control))
        self.assertEqual(host.get_controls()[0]['action'], 'transition_ack')
        client.close()
        self.wait_for(lambda: not host.connected)
        host2, client2 = self.pair()
        host2.start_handshake()
        client2.start_handshake()
        self.wait_for(lambda: host2.hello is not None)

    def test_slow_peer_send_keeps_game_thread_responsive(self):
        sender, peer = self.raw_peer(False)
        # Sender deliberately never reads; worker may block, caller must not.
        peer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024)
        began = time.monotonic()
        for _ in range(500):
            peer.send_state(dict(data='x' * 16000))
        self.assertLess(time.monotonic() - began, .5)
        self.assertLessEqual(len(peer.coalesced), 1)


if __name__ == '__main__':
    unittest.main()
