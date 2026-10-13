"""Threaded peer transport with bounded queues and command acknowledgments."""
from collections import deque
import copy
import socket
import threading
import time
from jupyter_game.data.roster import LIBRARIES
from jupyter_game.networking.protocol import PROTOCOL, MAX_COMMANDS, integer, number, recv_json_line, send_json_line, validate_input, validate_state


class OnlinePeer:
    def __init__(self, sock, is_host):
        self.sock = sock
        self.sock.settimeout(2.0)
        self.is_host = is_host
        self.buffer = b''
        self.latest_remote_input = {}
        self.latest_state = None
        self.latest_select = dict(index=0, ready=False)
        self.connected = True
        self.error = None
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.control = deque(maxlen=64)
        self.outbox = deque()
        self.coalesced = {}
        self.pending_commands = {}
        self.remote_commands = {}
        self.last_remote_command = 0
        self.last_ack = 0
        self.sent_command = 0
        self.epoch = None
        self.hello = None
        self.last_received = time.monotonic()
        self.state_received = self.last_received
        self.last_ping = 0
        self.ping_ms = None
        self.latest_sequence = -1
        self.writer = threading.Thread(target=self._writer, daemon=True)
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.writer.start()
        self.thread.start()

    def fail(self, error):
        self.error = str(error)
        self.close()

    def _queue(self, message, replace=False):
        with self.condition:
            if not self.connected:
                return
            if replace:
                self.coalesced[message['type']] = message
            elif len(self.outbox) >= 64:
                self.fail('Network control queue overflow')
                return
            else:
                self.outbox.append(message)
            self.condition.notify()

    def _writer(self):
        try:
            while self.connected:
                with self.condition:
                    self.condition.wait_for(lambda: not self.connected or self.outbox or self.coalesced, timeout=.5)
                    if not self.connected:
                        return
                    if self.outbox:
                        message = self.outbox.popleft()
                    elif self.coalesced:
                        key = next(iter(self.coalesced))
                        message = self.coalesced.pop(key)
                    else:
                        continue
                send_json_line(self.sock, message)
        except Exception as exc:
            self.fail(exc)

    def _reader(self):
        try:
            while self.connected:
                try:
                    message, self.buffer = recv_json_line(self.sock, self.buffer)
                except socket.timeout:
                    if time.monotonic() - self.last_received > 10:
                        raise ConnectionError('Peer stopped responding')
                    continue
                self.last_received = time.monotonic()
                kind, data = message.get('type'), message.get('data')
                with self.lock:
                    if kind == 'hello':
                        if not isinstance(data, dict) or data.get('version') != PROTOCOL or type(data.get('host')) is not bool or data.get('host') == self.is_host or data.get('roster') != [d['name'] for d in LIBRARIES]:
                            raise ValueError('Incompatible game version')
                        self.hello = data
                    elif kind == 'ping':
                        if not number(data, 0, 1e12):
                            raise ValueError('Invalid heartbeat')
                        self._queue(dict(type='pong', data=data), replace=True)
                    elif kind == 'pong':
                        if not number(data, 0, 1e12):
                            raise ValueError('Invalid heartbeat')
                        self.ping_ms = max(0, (time.monotonic() - data) * 1000)
                    elif kind == 'select':
                        if not isinstance(data, dict) or not integer(data.get('index'), 0, len(LIBRARIES)-1) or type(data.get('ready')) is not bool:
                            raise ValueError('Invalid fighter selection')
                        self.latest_select = data
                    elif kind == 'control':
                        if not isinstance(data, dict) or data.get('action') not in ('start', 'start_ack', 'choice', 'transition', 'transition_ack'):
                            raise ValueError('Invalid match control')
                        if not isinstance(data.get('match_id'), str) or len(data['match_id']) > 40:
                            raise ValueError('Invalid match ID')
                        if data['action'] == 'choice' and data.get('choice') not in ('rematch', 'select'):
                            raise ValueError('Invalid match choice')
                        if data['action'] in ('start', 'transition'):
                            if not isinstance(data.get('indices'), list) or len(data['indices']) != 2 or not all(integer(i, 0, len(LIBRARIES)-1) for i in data['indices']):
                                raise ValueError('Invalid match fighters')
                            if data['action'] == 'transition' and data.get('target') not in ('rematch', 'select'):
                                raise ValueError('Invalid transition')
                            if self.is_host:
                                raise ValueError('Only host can start matches')
                        if data['action'] == 'transition' and (not isinstance(data.get('from_id'), str) or len(data['from_id']) > 40):
                            raise ValueError('Invalid prior match ID')
                        if len(self.control) >= 64:
                            raise ValueError('Too many match controls')
                        self.control.append(data)
                    elif kind == 'input':
                        if not self.is_host:
                            raise ValueError('Only host receives input')
                        validate_input(data)
                        if message.get('epoch') != self.epoch:
                            continue
                        commands = data.get('commands', [])
                        for n, action in commands:
                            if n > self.last_remote_command:
                                self.remote_commands[n] = action
                                self.last_remote_command = n
                        if len(self.remote_commands) > MAX_COMMANDS:
                            raise ValueError('Too many unread commands')
                        self.latest_remote_input = data
                        if commands:
                            self._queue(dict(type='ack', data=self.last_remote_command, epoch=self.epoch), replace=True)
                    elif kind == 'ack':
                        if not integer(data):
                            raise ValueError('Invalid input acknowledgment')
                        if message.get('epoch') == self.epoch:
                            if data > self.sent_command:
                                raise ValueError('Acknowledgment exceeds sent commands')
                            self.last_ack = max(self.last_ack, data)
                            self.pending_commands = {n: a for n, a in self.pending_commands.items() if n > self.last_ack}
                    elif kind == 'state':
                        if self.is_host:
                            raise ValueError('Only client receives snapshots')
                        validate_state(data)
                        if not isinstance(data.get('match_id'), str) or len(data['match_id']) > 40:
                            raise ValueError('Invalid snapshot match')
                        if self.epoch is None or data['match_id'] != self.epoch.split(':')[0] or data['round'] < int(self.epoch.split(':')[1]):
                            continue
                        if data['seq'] > self.latest_sequence:
                            self.latest_sequence = data['seq']
                            self.latest_state = data
                            self.state_received = time.monotonic()
                    else:
                        raise ValueError('Unknown network message')
        except Exception as exc:
            self.fail(exc)

    def start_handshake(self):
        self._queue(dict(type='hello', data=dict(version=PROTOCOL, host=self.is_host, roster=[d['name'] for d in LIBRARIES])))

    def heartbeat(self):
        now = time.monotonic()
        if now - self.last_ping >= 1:
            self.last_ping = now
            self._queue(dict(type='ping', data=now), replace=True)

    def set_epoch(self, match_id, round_number):
        with self.lock:
            epoch = f'{match_id}:{round_number}'
            if epoch == self.epoch:
                return
            self.epoch = epoch
            self.pending_commands.clear()
            self.remote_commands.clear()
            self.latest_remote_input = {}
            self.last_remote_command = self.last_ack = self.sent_command = 0
            self.coalesced.pop('input', None)
            self.coalesced.pop('ack', None)
            if self.latest_state and self.latest_state['match_id'] != match_id:
                self.latest_state = None
                self.latest_sequence = -1

    def send_input(self, data):
        with self.lock:
            for n, action in data.get('commands', []):
                if n > self.last_ack:
                    self.pending_commands[n] = action
                    self.sent_command = max(self.sent_command, n)
            if len(self.pending_commands) > MAX_COMMANDS:
                self.fail('Input queue overflow')
                return
            ordered = sorted(self.pending_commands)
            if ordered and (len(ordered) != ordered[-1] - self.last_ack or
                            any(n != self.last_ack + i + 1 for i, n in enumerate(ordered))):
                self.fail('Input history exceeded retention limit')
                return
            state = dict(data)
            state['commands'] = sorted(self.pending_commands.items())
            self._queue(dict(type='input', data=state, epoch=self.epoch), replace=True)

    def send_state(self, data):
        self._queue(dict(type='state', data=data), replace=True)

    def send_select(self, data):
        self._queue(dict(type='select', data=data), replace=True)

    def send_control(self, data):
        self._queue(dict(type='control', data=data))

    def get_remote_input(self):
        with self.lock:
            result = dict(self.latest_remote_input)
            if 'commands' in result:
                result['commands'] = sorted(self.remote_commands.items())
                self.remote_commands.clear()
            return result

    def get_state(self):
        with self.lock:
            return copy.deepcopy(self.latest_state)

    def get_select(self):
        with self.lock:
            return dict(self.latest_select)

    def get_controls(self):
        with self.lock:
            result = list(self.control)
            self.control.clear()
            return result

    def close(self):
        with self.condition:
            self.connected = False
            self.condition.notify_all()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
