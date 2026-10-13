"""Packet limits, JSON framing, and protocol validation."""
import json
import math
import socket
import time
from jupyter_game.input.commands import COMMANDS
from jupyter_game.data.roster import LIBRARIES

PROTOCOL = 3
MAX_PACKET = 65536
MAX_COMMANDS = 256
MOVE_KEYS = ('light', 'heavy', 'special', 'low', 'launcher', 'forward_heavy',
             'air_light', 'air_heavy', 'air_special', 'directional_special', 'utility', 'dash')


def recv_json_line(sock, buffer):
    deadline = time.monotonic() + 10
    while b'\n' not in buffer:
        if len(buffer) > MAX_PACKET:
            raise ValueError('Packet too large')
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            if not buffer or time.monotonic() > deadline:
                raise
            continue
        if not chunk:
            raise ConnectionError('Connection closed')
        buffer += chunk
    line, remaining = buffer.split(b'\n', 1)
    if len(line) > MAX_PACKET:
        raise ValueError('Packet too large')
    obj = json.loads(line.decode('utf-8'))
    if not isinstance(obj, dict):
        raise ValueError('Expected object')
    return obj, remaining


def send_json_line(sock, payload):
    data = (json.dumps(payload, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    if len(data) > MAX_PACKET:
        raise ValueError('Packet too large')
    sock.sendall(data)


def integer(value, low=0, high=2**31 - 1):
    return type(value) is int and low <= value <= high


def number(value, low=-100000, high=100000):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_input(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid input')
    for key, value in data.items():
        if key == 'commands':
            if not isinstance(value, list) or len(value) > MAX_COMMANDS:
                raise ValueError('Too many commands')
            previous = 0
            for command in value:
                if not isinstance(command, (list, tuple)) or len(command) != 2 or not integer(command[0], 1) or command[0] <= previous or command[1] not in COMMANDS:
                    raise ValueError('Invalid command')
                previous = command[0]
        elif key.endswith('_seq') and key[:-4] in COMMANDS:
            if not integer(value):
                raise ValueError('Invalid command counter')
        elif key in ('left', 'right', 'down', 'guard'):
            if type(value) is not bool:
                raise ValueError('Invalid held input')
        else:
            raise ValueError('Unknown input field')


def validate_state(data):
    if not isinstance(data, dict):
        raise ValueError('Invalid snapshot')
    if not integer(data.get('tick')) or not integer(data.get('seq')) or not integer(data.get('round'), 1) or not integer(data.get('timer'), 0, 5940):
        raise ValueError('Invalid snapshot timing')
    if data.get('phase') not in ('round_start', 'fighting', 'round_end', 'match_end') or data.get('winner') not in (None, 1, 2) or data.get('round_result') not in (None, 0, 1, 2):
        raise ValueError('Invalid match phase')
    scores = data.get('scores')
    if not isinstance(scores, list) or len(scores) != 2 or not all(integer(n, 0, 2) for n in scores):
        raise ValueError('Invalid score')
    for name in ('p1', 'p2'):
        fighter = data.get(name)
        if not isinstance(fighter, dict) or not all(k in fighter for k in ('x', 'y', 'current_move')):
            raise ValueError('Missing fighter')
        for key, value in fighter.items():
            if key == 'current_move':
                if value is not None and value not in MOVE_KEYS:
                    raise ValueError('Invalid move')
            elif key == 'notice':
                if not isinstance(value, str) or len(value) > 80:
                    raise ValueError('Invalid notice')
            elif key in ('guard', 'on_ground', 'staggered', 'stagger_protected', 'knocked_down', 'pending_knockdown', 'launched', 'juggle_exhausted'):
                if type(value) is not bool:
                    raise ValueError('Invalid fighter flag')
            elif key in ('hp', 'energy', 'stagger', 'combo_scaling'):
                if not number(value, 0, 1000):
                    raise ValueError('Invalid fighter meter')
            elif key in ('x', 'y', 'vel_y'):
                if not number(value):
                    raise ValueError('Invalid fighter position')
            elif key == 'facing':
                if value not in (-1, 1) or type(value) is not int:
                    raise ValueError('Invalid fighter direction')
            elif key in ('hitstun', 'flash', 'stagger_timer', 'parry_window', 'parry_recovery', 'knockdown_timer', 'wakeup_invulnerability', 'combo_count', 'combo_timer', 'move_frame', 'notice_timer', 'hitstop', 'juggle_hits', 'move_invulnerability', 'parry_duration'):
                if not integer(value, 0, 100000):
                    raise ValueError('Invalid fighter timer')
            else:
                raise ValueError('Unknown fighter field')
        if not number(fighter['x'], -100, 1380) or not number(fighter['y'], -3000, 720):
            raise ValueError('Invalid fighter position')
    projectiles = data.get('projectiles')
    if not isinstance(projectiles, list) or len(projectiles) > 128:
        raise ValueError('Invalid projectiles')
    for projectile in projectiles:
        if not isinstance(projectile, dict) or projectile.get('owner') not in (1, 2) or projectile.get('direction') not in (-1, 1) or projectile.get('move') not in MOVE_KEYS or not all(number(projectile.get(k)) for k in ('x', 'y')):
            raise ValueError('Invalid projectile')
    effects = data.get('effects', [])
    if not isinstance(effects, list) or len(effects) > 64:
        raise ValueError('Invalid effects')
    for effect in effects:
        if not isinstance(effect, dict) or not integer(effect.get('id'), 1) or effect.get('kind') not in ('hit', 'guard', 'parry') or not all(number(effect.get(k)) for k in ('x', 'y')):
            raise ValueError('Invalid effect')


