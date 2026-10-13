"""Two separate headless game processes: select, best-of-three, rematch, reselect."""
import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import multiprocessing
import socket
import time


def worker(sock, hosting, result):
    import traceback
    peer = None
    try:
        import pygame
        from unittest.mock import patch
        from jupyter_game.modes import online as runtime
        from jupyter_game.networking.transport import OnlinePeer
        from jupyter_game.combat.match import Match
        from jupyter_game.input.devices import InputDevice
        from jupyter_game.combat.cpu import CPU
        from jupyter_game.core.settings import preferences
        preferences['sound'] = False
        active = dict(mode='select', ready_sent=False, match=None, choice='rematch')

        class Bot(InputDevice):
            def __init__(self):
                super().__init__('keyboard1')
                self.policy = CPU('hard', 20 if hosting else 41)

            def reset(self, keep_serial=False):
                super().reset(keep_serial)
                self.policy = CPU('hard', 20 if hosting else 41)

            def battle_state(self, events, facing=1, advance=True):
                match = active['match']
                if match is None:
                    return {}
                a, b = (match.p1, match.p2) if hosting else (match.p2, match.p1)
                return self.policy.state(a, b)

        class TrackedMatch(Match):
            def __init__(self, indices, devices):
                super().__init__(indices, devices)
                active['match'] = self

        class FastClock:
            def tick(self, fps):
                time.sleep(.002)
                return 17

        def events():
            if active['mode'] == 'select' and not active['ready_sent']:
                active['ready_sent'] = True
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)]
            match = active['match']
            if active['mode'] == 'battle' and match and match.phase == 'match_end':
                return [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r if active['choice'] == 'rematch' else pygame.K_RETURN)]
            return []

        peer = OnlinePeer(sock, hosting)
        peer.start_handshake()
        deadline = time.monotonic() + 3
        while peer.connected and not peer.hello and time.monotonic() < deadline:
            peer.heartbeat()
            time.sleep(.002)
        if not peer.hello:
            raise RuntimeError(peer.error or 'Handshake timed out')
        with patch.object(runtime, 'clock', FastClock()), patch.object(runtime, 'preferred_device', side_effect=Bot), patch.object(runtime, 'Match', TrackedMatch), patch('pygame.event.get', side_effect=events):
            selected = runtime.select(peer)
            if not selected:
                raise RuntimeError(peer.error or 'Selection failed')
            indices, match_id = selected
            active['mode'] = 'battle'
            first = runtime.battle(peer, indices, match_id)
            if not first or first['target'] != 'rematch':
                raise RuntimeError(peer.error or 'Rematch failed')
            active['choice'] = 'select'
            second = runtime.battle(peer, first['indices'], first['match_id'])
            if not second or second['target'] != 'select':
                raise RuntimeError(peer.error or 'Reselect failed')
            active.update(mode='select', ready_sent=False)
            peer.latest_select = dict(index=0, ready=False)
            selected = runtime.select(peer)
            if not selected:
                raise RuntimeError(peer.error or 'Reselection failed')
        result.put(dict(host=hosting, ok=True, rematch_id_changed=first['match_id'] != match_id,
                        selected=selected[0]))
        # Let the other process finish its final acknowledgment.
        time.sleep(.1)
    except BaseException:
        result.put(dict(host=hosting, ok=False, error=traceback.format_exc()))
    finally:
        if peer:
            peer.close()


if __name__ == '__main__':
    import json
    context = multiprocessing.get_context('spawn')
    queue = context.Queue()
    a, b = socket.socketpair()
    processes = [context.Process(target=worker, args=(a, True, queue)), context.Process(target=worker, args=(b, False, queue))]
    for process in processes:
        process.start()
    a.close()
    b.close()
    results = []
    try:
        for _ in processes:
            results.append(queue.get(timeout=45))
        print(json.dumps(results, indent=2))
    finally:
        for process in processes:
            process.join(1)
            if process.is_alive():
                process.terminate()
                process.join()
    if len(results) != 2 or not all(r['ok'] for r in results):
        raise SystemExit(1)
