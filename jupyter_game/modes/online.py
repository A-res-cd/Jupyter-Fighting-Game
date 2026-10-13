"""Responsive connection screens and authoritative online match lifecycle."""
from collections import deque
import socket
import threading
import time
import uuid
import sys
import pygame
from jupyter_game.core.config import *
from jupyter_game.networking.transport import OnlinePeer
from jupyter_game.networking.interpolation import Interpolator
from jupyter_game.input.devices import InputDevice, preferred_device
from jupyter_game.combat.match import Match
from jupyter_game.core.timing import FixedClock
from jupyter_game.combat.entities import Particle
from jupyter_game.audio.effects import cue
from jupyter_game.data.roster import LIBRARIES
from jupyter_game.ui.rendering import draw_overlay, draw_match, draw_back_to_menu_button, back_clicked
from jupyter_game.ui.online import online_menu, text_input_screen
from jupyter_game.networking.address import get_local_ip, ONLINE_PORT
from jupyter_game.networking.snapshots import fighter_to_state, apply_fighter_state, projectiles_to_state, apply_projectiles_state


def cancelled(events, battle=False):
    if any(e.type == pygame.QUIT for e in events):
        pygame.quit()
        sys.exit()
    return any(back_clicked(e, battle) or
               (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) for e in events)


def notice(title, detail):
    until = time.monotonic() + 2.5
    while time.monotonic() < until:
        clock.tick(FPS)
        if cancelled(pygame.event.get()):
            return
        screen.fill(BLACK)
        draw_overlay(title, [detail[:85], 'Esc = Back'])
        pygame.display.flip()


def connect(hosting):
    host, port = '', ONLINE_PORT
    if not hosting:
        address = text_input_screen('JOIN GAME', 'Enter host IP or IP:port:', '127.0.0.1')
        if not address:
            return None
        host = address
        if ':' in address:
            host, raw_port = address.rsplit(':', 1)
            try:
                port = int(raw_port)
                if not 1 <= port <= 65535:
                    raise ValueError()
            except ValueError:
                notice('INVALID ADDRESS', 'Port must be between 1 and 65535.')
                return None
    stopped = threading.Event()
    result = {}
    lock = threading.Lock()

    def worker():
        listener = sock = None
        try:
            if hosting:
                listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind(('', port))
                listener.listen(1)
                listener.settimeout(.2)
                result['address'] = get_local_ip()
                while not stopped.is_set():
                    try:
                        sock, _ = listener.accept()
                        break
                    except socket.timeout:
                        pass
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # DNS/connect stay on worker; cancellation closes its socket.
                with lock:
                    result['connecting'] = sock
                sock.settimeout(5)
                sock.connect((host, port))
            if stopped.is_set() or sock is None:
                return
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            peer = OnlinePeer(sock, hosting)
            sock = None
            peer.start_handshake()
            with lock:
                if stopped.is_set():
                    peer.close()
                else:
                    result['peer'] = peer
        except Exception as exc:
            result['error'] = str(exc)
        finally:
            if listener:
                listener.close()
            if sock:
                sock.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    deadline = None
    while True:
        clock.tick(FPS)
        if cancelled(pygame.event.get()):
            stopped.set()
            with lock:
                if result.get('connecting'):
                    result['connecting'].close()
                if result.get('peer'):
                    result['peer'].close()
            return None
        if result.get('error'):
            stopped.set()
            notice('CONNECTION FAILED', result['error'])
            return None
        peer = result.get('peer')
        if peer:
            peer.heartbeat()
            if deadline is None:
                deadline = time.monotonic() + 5
            if not peer.connected:
                notice('CONNECTION FAILED', peer.error or 'Connection closed')
                return None
            if peer.hello:
                return peer
            if time.monotonic() > deadline:
                peer.close()
                notice('CONNECTION FAILED', 'Version handshake timed out.')
                return None
        screen.fill(BLACK)
        detail = f'Give P2 address: {result.get("address", "finding LAN address")}:{port}' if hosting else f'Connecting to {host}:{port}'
        draw_overlay('CHECKING VERSION' if peer else 'HOSTING' if hosting else 'CONNECTING', [detail, 'Esc = Cancel'])
        draw_back_to_menu_button()
        pygame.display.flip()


def select(peer):
    device = preferred_device()
    index = 0 if peer.is_host else 1
    ready = False
    sent = None
    last_sent = 0
    starting = None
    starting_at = 0
    while peer.connected:
        clock.tick(FPS)
        peer.heartbeat()
        events = pygame.event.get()
        if cancelled(events):
            return None
        for event in events:
            if event.type == pygame.JOYDEVICEREMOVED and device.kind == 'gamepad' and event.instance_id == device.instance_id:
                notice('CONTROLLER DISCONNECTED', 'Use Settings to choose keyboard, then reconnect.')
                return None
            action = device.event_action(event)
            if event.type == pygame.KEYDOWN:
                action = {pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right', pygame.K_UP: 'up', pygame.K_DOWN: 'down', pygame.K_RETURN: 'confirm'}.get(event.key, action)
            if not ready and not starting:
                if action in ('left', 'right', 'up', 'down', 'jump'):
                    index = (index + dict(left=-1, right=1, up=-6, jump=-6, down=6)[action]) % len(LIBRARIES)
            if not starting and action in ('confirm', 'attack', 'jump') and not (event.type == pygame.JOYHATMOTION):
                ready = not ready
        current = dict(index=index, ready=ready)
        if current != sent or time.monotonic() - last_sent > 1:
            peer.send_select(current)
            sent, last_sent = current, time.monotonic()
        remote = peer.get_select()
        if peer.is_host and ready and remote['ready'] and not starting:
            starting = dict(action='start', match_id=uuid.uuid4().hex,
                            indices=[index, remote['index']])
            peer.send_control(starting)
            starting_at = time.monotonic()
        if starting and time.monotonic() - starting_at > 5:
            peer.fail('Match start acknowledgment timed out')
            break
        for control in peer.get_controls():
            if not peer.is_host and control['action'] == 'start':
                peer.set_epoch(control['match_id'], 1)
                peer.send_control(dict(action='start_ack', match_id=control['match_id']))
                return control['indices'], control['match_id']
            if peer.is_host and starting and control['action'] == 'start_ack' and control['match_id'] == starting['match_id']:
                peer.set_epoch(starting['match_id'], 1)
                return starting['indices'], starting['match_id']
        screen.fill(BLACK)
        text = BIG.render('ONLINE FIGHTER SELECT', True, ORANGE)
        screen.blit(text, text.get_rect(center=(WIDTH // 2, 70)))
        for i, data in enumerate(LIBRARIES):
            row, col = divmod(i, 6)
            rect = pygame.Rect(55 + col * 200, 190 + row * 140, 185, 115)
            pygame.draw.rect(screen, data['color'], rect, border_radius=12)
            if i == index:
                pygame.draw.rect(screen, CYAN, rect.inflate(8, 8), 4, border_radius=12)
            if i == remote['index']:
                pygame.draw.rect(screen, RED, rect.inflate(18, 18), 3, border_radius=12)
            text = FONT.render(data['name'], True, WHITE if sum(data['color']) < 500 else BLACK)
            screen.blit(text, text.get_rect(center=rect.center))
        status = f'{"HOST P1" if peer.is_host else "CLIENT P2"}: {"READY" if ready else "CHOOSE"} | Other: {"READY" if remote["ready"] else "CHOOSE"}'
        screen.blit(FONT.render(status, True, WHITE), (300, 125))
        screen.blit(SMALL.render('Arrows / D-pad choose | Enter / A / Start ready | Esc menu', True, CYAN), (300, 650))
        draw_back_to_menu_button()
        pygame.display.flip()
    notice('DISCONNECTED', peer.error or 'Other player left.')
    return None


def battle(peer, indices, match_id):
    local = preferred_device()
    devices = (local, InputDevice('cpu')) if peer.is_host else (InputDevice('cpu'), local)
    match = Match(indices, devices)
    timer = FixedClock()
    interpolation = Interpolator()
    peer.set_epoch(match_id, 1)
    sequence = 0
    applied = -1
    choice = other_choice = transition = None
    transition_at = 0
    effects = deque(maxlen=64)
    event_id = last_effect = 0
    pending_remote = {}
    while peer.connected:
        elapsed = clock.tick(FPS) / 1000
        peer.heartbeat()
        events = pygame.event.get()
        if cancelled(events, True):
            return None
        for event in events:
            if event.type == pygame.JOYDEVICEREMOVED and local.kind == 'gamepad' and event.instance_id == local.instance_id:
                peer.close()
                notice('CONTROLLER DISCONNECTED', 'Online match ended. Choose keyboard in Settings.')
                return None
            if match.phase == 'match_end':
                key = event.key if event.type == pygame.KEYDOWN else None
                if key == pygame.K_r or (event.type == pygame.JOYBUTTONDOWN and event.button == 0):
                    choice = 'rematch'
                if key == pygame.K_RETURN or (event.type == pygame.JOYBUTTONDOWN and event.button == 1):
                    choice = 'select'
                if choice:
                    peer.send_control(dict(action='choice', choice=choice, match_id=match_id))
        for control in peer.get_controls():
            if control['action'] == 'choice' and control['match_id'] == match_id:
                other_choice = control['choice']
            if not peer.is_host and control['action'] == 'transition' and control.get('from_id') == match_id:
                peer.send_control(dict(action='transition_ack', match_id=control['match_id']))
                return control
            if peer.is_host and transition and control['action'] == 'transition_ack' and control['match_id'] == transition['match_id']:
                return transition
        if peer.is_host and match.phase == 'match_end' and choice and other_choice and not transition:
            transition = dict(action='transition', from_id=match_id, match_id=uuid.uuid4().hex,
                              target='select' if 'select' in (choice, other_choice) else 'rematch', indices=list(indices))
            peer.send_control(transition)
            transition_at = time.monotonic()
        if transition and time.monotonic() - transition_at > 5:
            peer.fail('Rematch acknowledgment timed out')
            break
        input_state = local.battle_state(events, match.p1.facing if peer.is_host else match.p2.facing, advance=False)
        if peer.is_host:
            # Preserve received commands even on render frames with no simulation step.
            remote = peer.get_remote_input()
            for n, action in remote.get('commands', []):
                pending_remote[n] = action
            remote['commands'] = sorted(pending_remote.items())
            for _ in range(timer.steps(elapsed)):
                old_round = match.round
                local.advance_time()
                before = [(f.hp, f.notice, f.notice_timer) for f in (match.p1, match.p2)]
                match.step(input_state, remote)
                if match.round != old_round:
                    peer.set_epoch(match_id, match.round)
                    pending_remote.clear()
                    input_state = remote = {}
                else:
                    pending_remote = {n: a for n, a in pending_remote.items() if n > match.p2.last_command_id}
                    for fighter, (hp, notice_text, notice_timer) in zip((match.p1, match.p2), before):
                        parry = 'PARRY' in fighter.notice and fighter.notice_timer > notice_timer
                        if fighter.hp < hp or parry:
                            event_id += 1
                            effects.append(dict(id=event_id, kind='parry' if parry else 'guard' if fighter.guard else 'hit',
                                                x=fighter.rect.centerx, y=fighter.rect.centery))
            sequence += 1
            peer.send_state(dict(match_id=match_id, seq=sequence, tick=match.tick,
                                 round=match.round, phase=match.phase, round_result=match.round_result,
                                 scores=match.scores, winner=match.winner, timer=match.timer,
                                 p1=fighter_to_state(match.p1), p2=fighter_to_state(match.p2),
                                 projectiles=projectiles_to_state(match.projectiles, match.p1), effects=list(effects)))
        else:
            for _ in range(timer.steps(elapsed)):
                local.advance_time()
                for particle in match.particles:
                    particle.update()
                match.particles[:] = [p for p in match.particles if p.life > 0]
            snapshot = peer.get_state()
            if snapshot and snapshot['seq'] > applied and snapshot['match_id'] == match_id:
                applied = snapshot['seq']
                if snapshot['round'] != match.round:
                    local.reset()
                    input_state = {}
                    peer.set_epoch(match_id, snapshot['round'])
                    match.particles.clear()
                apply_fighter_state(match.p1, snapshot['p1'])
                apply_fighter_state(match.p2, snapshot['p2'])
                match.projectiles = apply_projectiles_state(snapshot['projectiles'], match.p1, match.p2)
                for key in ('round', 'phase', 'round_result', 'scores', 'winner', 'timer', 'tick'):
                    setattr(match, key, snapshot[key])
                interpolation.add(snapshot, peer.state_received)
                for effect in snapshot.get('effects', []):
                    if effect['id'] > last_effect:
                        last_effect = effect['id']
                        cue(effect['kind'])
                        for _ in range(10):
                            match.particles.append(Particle(effect['x'], effect['y'], YELLOW))
            peer.send_input(input_state)
        authoritative = [match.p1.rect.topleft, match.p2.rect.topleft]
        if not peer.is_host:
            positions = interpolation.positions(time.monotonic())
            if positions:
                match.p1.rect.topleft, match.p2.rect.topleft = positions
        draw_match(match)
        match.p1.rect.topleft, match.p2.rect.topleft = authoritative
        age = (time.monotonic() - peer.state_received) * 1000
        status = f'ONLINE {"HOST" if peer.is_host else "CLIENT"} | Ping {peer.ping_ms:.0f} ms' if peer.ping_ms is not None else 'ONLINE | Measuring ping'
        if not peer.is_host:
            status += f' | Snapshot age {age:.0f} ms'
        screen.blit(SMALL.render(status, True, CYAN if age < 1000 or peer.is_host else RED), (330, 140))
        screen.blit(SMALL.render(local.short_controls(), True, WHITE), (150, HEIGHT - 30))
        if match.phase == 'match_end':
            draw_overlay(f'P{match.winner} WINS MATCH', ['R / A = Rematch   Enter / B = Select   Esc = Menu',
                                                      f'Your choice: {choice or "waiting"} | Other: {other_choice or "waiting"}'])
        draw_back_to_menu_button(True)
        pygame.display.flip()
    notice('DISCONNECTED', peer.error or 'Other player left.')
    return None


def run_online_multiplayer():
    option = online_menu()
    if option == 'BACK':
        return
    peer = connect(option == 'HOST GAME')
    if not peer:
        return
    try:
        selected = select(peer)
        while selected and peer.connected:
            indices, match_id = selected
            transition = battle(peer, indices, match_id)
            if not transition:
                return
            if transition['target'] == 'select':
                peer.latest_select = dict(index=0, ready=False)
                selected = select(peer)
            else:
                selected = transition['indices'], transition['match_id']
    finally:
        peer.close()
