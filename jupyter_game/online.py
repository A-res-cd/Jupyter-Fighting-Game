import pygame
import socket
import threading
import json
import time

from .config import *
from .roster import LIBRARIES
from .input_devices import InputDevice
from .entities import Fighter, Particle
from .ui import draw_bar, draw_background, draw_back_to_menu_button

ONLINE_PORT = 50555


def recv_json_line(sock, buffer):
    """Receive newline-delimited JSON. Returns (obj, remaining_buffer)."""
    while b"\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("Connection closed")
        buffer += chunk

    line, buffer = buffer.split(b"\n", 1)
    return json.loads(line.decode("utf-8")), buffer


def send_json_line(sock, payload):
    data = (json.dumps(payload) + "\n").encode("utf-8")
    sock.sendall(data)


class OnlinePeer:
    def __init__(self, sock, is_host):
        self.sock = sock
        self.is_host = is_host
        self.buffer = b""
        self.latest_remote_input = {
            "left": False,
            "right": False,
            "jump": False,
            "guard": False,
            "attack": False,
            "special": False,
        }
        self.latest_state = None
        self.latest_select = {"index": 0, "ready": False}
        self.connected = True
        self.error = None
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        try:
            while self.connected:
                msg, self.buffer = recv_json_line(self.sock, self.buffer)
                with self.lock:
                    if msg.get("type") == "input":
                        self.latest_remote_input = msg.get("data", self.latest_remote_input)
                    elif msg.get("type") == "state":
                        self.latest_state = msg.get("data")
                    elif msg.get("type") == "select":
                        self.latest_select = msg.get("data", self.latest_select)
        except Exception as exc:
            self.error = str(exc)
            self.connected = False

    def send_input(self, data):
        if not self.connected:
            return
        try:
            send_json_line(self.sock, {"type": "input", "data": data})
        except Exception as exc:
            self.error = str(exc)
            self.connected = False

    def send_state(self, data):
        if not self.connected:
            return
        try:
            send_json_line(self.sock, {"type": "state", "data": data})
        except Exception as exc:
            self.error = str(exc)
            self.connected = False

    def get_remote_input(self):
        with self.lock:
            return dict(self.latest_remote_input)

    def get_state(self):
        with self.lock:
            return self.latest_state.copy() if isinstance(self.latest_state, dict) else self.latest_state

    def get_select(self):
        with self.lock:
            return dict(self.latest_select)

    def close(self):
        self.connected = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass


def get_local_ip():
    try:
        temp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        temp.connect(("8.8.8.8", 80))
        ip = temp.getsockname()[0]
        temp.close()
        return ip
    except Exception:
        return "127.0.0.1"


def online_menu():
    options = ["HOST GAME", "JOIN GAME", "BACK"]
    selected = 0

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))

        title = TITLE.render("ONLINE MULTIPLAYER", True, ORANGE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        draw_back_to_menu_button()

        subtitle = FONT.render("LAN / Direct IP", True, WHITE)
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 180)))

        for i, option in enumerate(options):
            rect = pygame.Rect(WIDTH // 2 - 210, 285 + i * 90, 420, 64)
            if i == selected:
                pygame.draw.rect(screen, ORANGE, rect, border_radius=14)
                color = BLACK
            else:
                pygame.draw.rect(screen, (40, 44, 58), rect, border_radius=14)
                pygame.draw.rect(screen, WHITE, rect, 2, border_radius=14)
                color = WHITE

            txt = FONT.render(option, True, color)
            screen.blit(txt, txt.get_rect(center=rect.center))

        hint = SMALL.render(
            "Host: Player 1    Join: Player 2    ESC = Main Menu",
            True, GRAY
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 55)))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "BACK"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "BACK"
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_j):
                    return options[selected]


def text_input_screen(title_text, prompt, initial=""):
    text_value = initial

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))
        draw_back_to_menu_button()

        title = BIG.render(title_text, True, ORANGE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 170)))

        ptxt = FONT.render(prompt, True, WHITE)
        screen.blit(ptxt, ptxt.get_rect(center=(WIDTH // 2, 245)))

        box = pygame.Rect(WIDTH // 2 - 260, 300, 520, 64)
        pygame.draw.rect(screen, (38, 42, 56), box, border_radius=12)
        pygame.draw.rect(screen, WHITE, box, 2, border_radius=12)

        value_surface = FONT.render(text_value or "_", True, CYAN)
        screen.blit(value_surface, value_surface.get_rect(center=box.center))

        hint = SMALL.render("Type address, Enter = Continue, ESC = Back", True, GRAY)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 410)))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_RETURN:
                    return text_value.strip() or None
                if event.key == pygame.K_BACKSPACE:
                    text_value = text_value[:-1]
                elif event.unicode and event.unicode.isprintable() and len(text_value) < 64:
                    text_value += event.unicode


def host_wait_screen():
    server = None
    conn = None

    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", ONLINE_PORT))
        server.listen(1)
        server.setblocking(False)

        local_ip = get_local_ip()

        while True:
            clock.tick(FPS)
            screen.fill((20, 23, 32))
            draw_back_to_menu_button()

            title = BIG.render("HOSTING GAME", True, ORANGE)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 160)))

            msg = FONT.render(f"Give Player 2 this address: {local_ip}:{ONLINE_PORT}", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, 255)))

            wait = FONT.render("Waiting for Player 2 to connect...", True, CYAN)
            screen.blit(wait, wait.get_rect(center=(WIDTH // 2, 315)))

            hint = SMALL.render("ESC = Cancel hosting", True, GRAY)
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 380)))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    server.close()
                    return None
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    server.close()
                    return None

            try:
                conn, _addr = server.accept()
                conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                server.close()
                return OnlinePeer(conn, is_host=True)
            except BlockingIOError:
                pass

    except Exception:
        if server:
            try:
                server.close()
            except Exception:
                pass
        return None


def join_connect_screen():
    address = text_input_screen("JOIN GAME", "Enter host IP address:", "127.0.0.1")
    if not address:
        return None

    host = address
    port = ONLINE_PORT

    if ":" in address:
        maybe_host, maybe_port = address.rsplit(":", 1)
        host = maybe_host
        try:
            port = int(maybe_port)
        except ValueError:
            port = ONLINE_PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5.0)

    try:
        sock.connect((host, port))
        sock.settimeout(None)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return OnlinePeer(sock, is_host=False)
    except Exception:
        try:
            sock.close()
        except Exception:
            pass

        error_until = pygame.time.get_ticks() + 1800
        while pygame.time.get_ticks() < error_until:
            clock.tick(FPS)
            screen.fill((20, 23, 32))
            title = BIG.render("CONNECTION FAILED", True, RED)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            msg = SMALL.render("Check the host IP/port and firewall, then try again.", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
        return None


def fighter_to_state(f):
    return {
        "x": f.rect.x,
        "y": f.rect.y,
        "hp": f.hp,
        "energy": f.energy,
        "facing": f.facing,
        "guard": f.guard,
        "vel_y": f.vel_y,
        "on_ground": f.on_ground,
        "attack_cd": f.attack_cd,
        "special_cd": f.special_cd,
        "stun": f.stun,
        "flash": f.flash,
    }


def apply_fighter_state(f, state):
    if not state:
        return
    f.rect.x = int(state.get("x", f.rect.x))
    f.rect.y = int(state.get("y", f.rect.y))
    f.hp = int(state.get("hp", f.hp))
    f.energy = float(state.get("energy", f.energy))
    f.facing = int(state.get("facing", f.facing))
    f.guard = bool(state.get("guard", f.guard))
    f.vel_y = float(state.get("vel_y", f.vel_y))
    f.on_ground = bool(state.get("on_ground", f.on_ground))
    f.attack_cd = int(state.get("attack_cd", f.attack_cd))
    f.special_cd = int(state.get("special_cd", f.special_cd))
    f.stun = int(state.get("stun", f.stun))
    f.flash = int(state.get("flash", f.flash))


def gather_online_input(device):
    keys = pygame.key.get_pressed()

    if device.kind == "keyboard1":
        return {
            "left": bool(keys[pygame.K_a]),
            "right": bool(keys[pygame.K_d]),
            "jump": False,
            "guard": bool(keys[pygame.K_s]),
            "attack": False,
            "special": False,
        }

    return {
        "left": device.move_x() < 0,
        "right": device.move_x() > 0,
        "jump": False,
        "guard": device.guarding(),
        "attack": False,
        "special": False,
    }


def online_character_select(peer):
    # Simple synchronized character select:
    # Host picks P1, client picks P2; each sends index + ready.
    local_index = 0 if peer.is_host else 1
    remote_index = 1 if peer.is_host else 0
    local_ready = False
    remote_ready = False
    cols = 6

    while True:
        clock.tick(FPS)

        # Send local select state
        try:
            send_json_line(peer.sock, {
                "type": "select",
                "data": {"index": local_index, "ready": local_ready}
            })
        except Exception:
            peer.close()
            return None

        remote_select = peer.get_select()
        remote_index = int(remote_select.get("index", remote_index))
        remote_ready = bool(remote_select.get("ready", remote_ready))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                peer.close()
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    peer.close()
                    return None
                if event.key == pygame.K_LEFT and not local_ready:
                    local_index = (local_index - 1) % len(LIBRARIES)
                elif event.key == pygame.K_RIGHT and not local_ready:
                    local_index = (local_index + 1) % len(LIBRARIES)
                elif event.key == pygame.K_UP and not local_ready:
                    local_index = (local_index - cols) % len(LIBRARIES)
                elif event.key == pygame.K_DOWN and not local_ready:
                    local_index = (local_index + cols) % len(LIBRARIES)
                elif event.key == pygame.K_RETURN:
                    local_ready = not local_ready

        screen.fill((20, 23, 32))
        draw_back_to_menu_button()

        title = TITLE.render("ONLINE FIGHTER SELECT", True, ORANGE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 60)))

        status = FONT.render(
            ("HOST / P1" if peer.is_host else "CLIENT / P2") +
            (" - READY" if local_ready else " - CHOOSING"),
            True, BLUE if peer.is_host else RED
        )
        screen.blit(status, status.get_rect(center=(WIDTH // 2, 118)))

        card_w, card_h = 180, 120
        start_x, start_y = 65, 180
        gap_x, gap_y = 22, 28

        for i, lib in enumerate(LIBRARIES):
            row, col = divmod(i, cols)
            rect = pygame.Rect(
                start_x + col * (card_w + gap_x),
                start_y + row * (card_h + gap_y),
                card_w, card_h
            )
            pygame.draw.rect(screen, lib["color"], rect, border_radius=12)
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=12)

            if i == local_index:
                pygame.draw.rect(screen, BLUE if peer.is_host else RED, rect.inflate(8, 8), 5, border_radius=15)
            if i == remote_index:
                pygame.draw.rect(screen, RED if peer.is_host else BLUE, rect.inflate(18, 18), 4, border_radius=18)

            contrast = BLACK if sum(lib["color"]) > 500 else WHITE
            name = FONT.render(lib["name"], True, contrast)
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.y + 28)))

        hint = SMALL.render("Arrow Keys = Choose    Enter = Ready/Unready    ESC = Main Menu", True, GRAY)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 25)))
        pygame.display.flip()

        if local_ready and remote_ready:
            if peer.is_host:
                return local_index, remote_index
            return remote_index, local_index


def online_battle(peer, p1_index, p2_index):
    """
    Host-authoritative networking:
    - Host simulates the battle.
    - Both machines send local input.
    - Host broadcasts authoritative fighter state.
    """
    local_is_p1 = peer.is_host
    local_device = InputDevice("keyboard1", label="Keyboard")

    p1 = Fighter(LIBRARIES[p1_index], 250, 1, local_device)
    p2 = Fighter(LIBRARIES[p2_index], WIDTH - 320, -1, local_device)

    projectiles = []
    particles = []
    round_timer = 99 * FPS
    winner = None

    local_edge = {"jump": False, "attack": False, "special": False}

    while True:
        clock.tick(FPS)

        input_state = gather_online_input(local_device)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                peer.close()
                return "menu"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    peer.close()
                    return "menu"
                if event.key == pygame.K_w:
                    input_state["jump"] = True
                elif event.key == pygame.K_j:
                    input_state["attack"] = True
                elif event.key == pygame.K_k:
                    input_state["special"] = True

        peer.send_input(input_state)

        if not peer.connected:
            return "menu"

        if peer.is_host:
            remote_input = peer.get_remote_input()

            def apply_input(fighter, opponent, state):
                fighter.guard = bool(state.get("guard", False))
                if fighter.stun <= 0:
                    move = (-1 if state.get("left") else 0) + (1 if state.get("right") else 0)
                    if move:
                        fighter.rect.x += move * fighter.speed
                        fighter.facing = 1 if move > 0 else -1

                    if state.get("jump"):
                        fighter.jump()
                    if state.get("attack"):
                        fighter.normal_attack(opponent, particles)
                    if state.get("special"):
                        fighter.special(projectiles)

                # Timers / physics
                if fighter.attack_cd > 0:
                    fighter.attack_cd -= 1
                if fighter.special_cd > 0:
                    fighter.special_cd -= 1
                if fighter.stun > 0:
                    fighter.stun -= 1
                if fighter.flash > 0:
                    fighter.flash -= 1
                if fighter.combo_timer > 0:
                    fighter.combo_timer -= 1
                else:
                    fighter.combo = 0

                fighter.vel_y += 0.7
                fighter.rect.y += int(fighter.vel_y)
                if fighter.rect.bottom >= GROUND_Y:
                    fighter.rect.bottom = GROUND_Y
                    fighter.vel_y = 0
                    fighter.on_ground = True

                fighter.rect.x = max(10, min(WIDTH - fighter.rect.width - 10, fighter.rect.x))

            if local_is_p1:
                apply_input(p1, p2, input_state)
                apply_input(p2, p1, remote_input)
            else:
                apply_input(p1, p2, remote_input)
                apply_input(p2, p1, input_state)

            if p1.rect.colliderect(p2.rect):
                overlap = min(p1.rect.right, p2.rect.right) - max(p1.rect.left, p2.rect.left)
                if overlap > 0:
                    if p1.rect.centerx < p2.rect.centerx:
                        p1.rect.x -= overlap // 2
                        p2.rect.x += overlap // 2
                    else:
                        p1.rect.x += overlap // 2
                        p2.rect.x -= overlap // 2

            for proj in projectiles:
                proj.update()
                target = p2 if proj.owner is p1 else p1
                if proj.alive and proj.rect.colliderect(target.rect):
                    target.hurt(proj.damage, proj.owner.facing * 20)
                    proj.owner.energy = min(100, proj.owner.energy + 8)
                    proj.alive = False

            projectiles[:] = [p for p in projectiles if p.alive]

            for pt in particles:
                pt.update()
            particles[:] = [pt for pt in particles if pt.life > 0]

            round_timer -= 1

            if p1.hp <= 0 or p2.hp <= 0 or round_timer <= 0:
                if p1.hp == p2.hp:
                    winner = "DRAW"
                elif p1.hp > p2.hp:
                    winner = f"P1 {p1.name}"
                else:
                    winner = f"P2 {p2.name}"

            peer.send_state({
                "p1": fighter_to_state(p1),
                "p2": fighter_to_state(p2),
                "timer": round_timer,
                "winner": winner,
            })

        else:
            state = peer.get_state()
            if state:
                apply_fighter_state(p1, state.get("p1"))
                apply_fighter_state(p2, state.get("p2"))
                round_timer = int(state.get("timer", round_timer))
                winner = state.get("winner")

        draw_background()
        draw_back_to_menu_button()

        draw_bar(70, 45, 460, 28, p1.hp, p1.max_hp, GREEN)
        draw_bar(WIDTH - 530, 45, 460, 28, p2.hp, p2.max_hp, RED, True)
        draw_bar(70, 80, 300, 13, p1.energy, 100, CYAN)
        draw_bar(WIDTH - 370, 80, 300, 13, p2.energy, 100, CYAN, True)

        n1 = FONT.render(f"P1  {p1.name}", True, WHITE)
        n2 = FONT.render(f"{p2.name}  P2", True, WHITE)
        screen.blit(n1, (70, 105))
        screen.blit(n2, (WIDTH - 70 - n2.get_width(), 105))

        time_txt = BIG.render(str(max(0, round_timer // FPS)), True, WHITE)
        screen.blit(time_txt, time_txt.get_rect(center=(WIDTH // 2, 65)))

        p1.draw(screen)
        p2.draw(screen)

        for proj in projectiles:
            proj.draw(screen)
        for pt in particles:
            pt.draw(screen)

        net = SMALL.render(
            "ONLINE HOST" if peer.is_host else "ONLINE CLIENT",
            True, CYAN
        )
        screen.blit(net, net.get_rect(center=(WIDTH // 2, 140)))

        if winner:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))
            result = "DRAW!" if winner == "DRAW" else f"{winner} WINS!"
            txt = TITLE.render(result, True, YELLOW)
            screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
            msg = FONT.render("ESC = Main Menu", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))

        pygame.display.flip()


def run_online_multiplayer():
    while True:
        choice = online_menu()

        if choice == "BACK":
            return

        if choice == "HOST GAME":
            peer = host_wait_screen()
        else:
            peer = join_connect_screen()

        if not peer:
            continue

        selection = online_character_select(peer)
        if selection is None:
            peer.close()
            continue

        p1_index, p2_index = selection
        online_battle(peer, p1_index, p2_index)
        peer.close()
