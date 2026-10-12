import pygame
import random
import math

from .config import *
from .combat import (moves_for, COMBO_SCALING, INPUT_BUFFER_FRAMES,
                     PARRY_FRAMES, PERFECT_PARRY_FRAMES, MAX_JUGGLE_HITS)
from .combat_input import COMMANDS

class Particle:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-7, -2)
        self.life = random.randint(20, 40)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.25
        self.life -= 1

    def draw(self, surf):
        if self.life > 0:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), 4)


class Projectile:
    def __init__(self, owner, direction, move, y_offset=0):
        self.owner = owner
        self.direction = direction
        self.move = move
        self.x = owner.rect.centerx + direction * 45
        self.y = owner.rect.centery - 10 + y_offset
        self.vx = direction * move.projectile_speed
        self.vy = move.projectile_vy
        self.color = owner.color
        self.rect = pygame.Rect(self.x - 10, self.y - 8, 20, 16)
        self.alive = True

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.rect.center = (int(self.x), int(self.y))
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surf):
        pygame.draw.ellipse(surf, self.color, self.rect)
        pygame.draw.ellipse(surf, WHITE, self.rect, 2)


class Fighter:
    def __init__(self, data, x, facing, input_device):
        self.data = data
        self.name = data['name']
        self.color = data['color']
        self.max_hp = data['hp']
        self.hp = self.max_hp
        self.speed = data['speed']
        self.power = data['power']
        self.input = input_device
        self.moves = moves_for(data)
        self.special_name = self.moves['special'].name
        self.rect = pygame.Rect(x, GROUND_Y - 120, 70, 120)
        self.vel_y = 0
        self.on_ground = True
        self.launched = False
        self.juggle_hits = 0
        self.juggle_exhausted = False
        self.facing = facing
        self.hitstun = self.flash = self.hitstop = 0
        self.stagger = 0
        self.max_stagger = 100
        self.staggered = False
        self.stagger_timer = 0
        self.stagger_protected = False
        self.neutral_frames = 0
        self.guard = False
        self.guard_held = False
        self.parry_window = self.parry_recovery = 0
        self.parry_duration = PARRY_FRAMES
        self.parry_success = False
        self.knocked_down = False
        self.pending_knockdown = False
        self.knockdown_timer = self.wakeup_invulnerability = 0
        self.move_invulnerability = 0
        self.energy = 0
        self.combo_count = self.combo_timer = 0
        self.combo_scaling = 1.0
        self.combo_target = None
        self.current_move = None
        self.move_frame = 0
        self.move_connected = False
        self.move_resolved = False
        self.light_chain = 0
        self.input_buffer = []
        self.previous_actions = {}
        self.action_sequences = {}
        self.last_command_id = 0
        self.move_x = 0
        self.notice = ''
        self.notice_timer = 0

    @property
    def combo(self):
        return self.combo_count

    @property
    def disabled(self):
        return self.hp <= 0 or self.hitstun > 0 or self.staggered or self.knocked_down or self.launched

    @property
    def vulnerable(self):
        return self.hitstun > 0 or self.staggered or self.knocked_down or not self.on_ground

    def announce(self, text):
        self.notice = text
        self.notice_timer = 60

    def queue_action(self, action):
        if action in ('up', 'jump'):
            action = 'jump'
        elif action == 'attack':
            action = 'light'
        if action in COMMANDS:
            self.input_buffer.append((action, INPUT_BUFFER_FRAMES))
            self.input_buffer = self.input_buffer[-8:]

    def prepare(self, state):
        history = state.get('commands')
        if history is not None:
            for command_id, action in history:
                if command_id > self.last_command_id:
                    self.queue_action(action)
                    self.last_command_id = command_id
        # Network action counters survive skipped packets and never repeat a press.
        for action in (() if history is not None else COMMANDS):
            sequence = state.get(action + '_seq')
            if sequence is not None:
                previous = self.action_sequences.get(action, 0)
                if sequence > previous:
                    for _ in range(min(4, sequence - previous)):
                        self.queue_action(action)
                    self.action_sequences[action] = sequence
            elif state.get(action, False) and not self.previous_actions.get(action, False):
                self.queue_action(action)
            self.previous_actions[action] = bool(state.get(action, False))
        self.move_x = int(bool(state.get('right'))) - int(bool(state.get('left')))
        held = bool(state.get('guard'))
        if not self.hitstop:
            for attr in ('hitstun', 'flash', 'parry_recovery', 'wakeup_invulnerability',
                         'notice_timer', 'knockdown_timer', 'stagger_timer', 'move_invulnerability'):
                setattr(self, attr, max(0, getattr(self, attr) - 1))
            if self.parry_window:
                self.parry_window -= 1
                if not self.parry_window and not self.parry_success:
                    self.parry_recovery = 18
            self.staggered = self.stagger_timer > 0
            if self.pending_knockdown and self.on_ground and not self.hitstun and not self.staggered:
                self.pending_knockdown = False
                self.knocked_down = True
                self.knockdown_timer = 30
            if self.knocked_down and self.knockdown_timer == 0:
                self.knocked_down = False
                self.wakeup_invulnerability = 12
                self.juggle_hits = 0
                self.juggle_exhausted = False
            if self.combo_target and not self.combo_target.vulnerable:
                self.combo_timer -= 1
                if self.combo_timer <= 0:
                    self.combo_count = 0
                    self.combo_scaling = 1
                    self.combo_target = None
            if self.vulnerable or self.current_move or held:
                self.neutral_frames = 0
            else:
                self.neutral_frames += 1
                if self.neutral_frames >= 30:
                    self.stagger_protected = False
                    self.stagger = max(0, self.stagger - .3)
            if held and not self.guard_held and not self.disabled and not self.current_move and not self.parry_recovery:
                self.parry_window = PARRY_FRAMES
                self.parry_duration = PARRY_FRAMES
                self.parry_success = False
        self.guard_held = held
        move_guard = bool(self.current_move and self.move_frame < self.moves[self.current_move].guard_frames)
        self.guard = not self.disabled and ((held and not self.current_move) or move_guard)
        # Releasing guard ends its parry window; rapid retries still incur recovery.
        if not held and not move_guard and self.parry_window:
            if not self.parry_success:
                self.parry_recovery = 18
            self.parry_window = 0

    def start_move(self, key):
        if not self.on_ground:
            key = {'light': 'air_light', 'heavy': 'air_heavy', 'special': 'air_special'}.get(key, key)
        elif key == 'heavy' and self.current_move == 'low' and self.move_connected:
            key = 'launcher'
        if key not in self.moves:
            return False
        move = self.moves[key]
        if (self.disabled or self.guard or (not self.on_ground and not move.air_usable)
                or (self.on_ground and move.air_only)):
            return False
        if self.energy < move.energy_cost:
            return False
        if self.current_move:
            current = self.moves[self.current_move]
            if ((not self.move_connected and not current.free_cancel)
                    or self.move_frame < max(current.startup, current.cancel_after) or key not in current.cancels):
                return False
            if key == 'light' and self.light_chain >= 2:
                return False
        else:
            self.light_chain = 0
        if key != 'dash':
            self.light_chain = self.light_chain + 1 if key == 'light' else 0
        self.current_move = key
        self.move_frame = 0
        self.move_connected = self.move_resolved = False
        self.energy -= move.energy_cost
        self.parry_window = move.parry_frames
        self.parry_duration = move.parry_frames or PARRY_FRAMES
        self.parry_success = False
        self.move_invulnerability = move.invulnerable_frames
        self.guard = move.guard_frames > 0
        return True

    def advance(self, opponent, projectiles, particles):
        if self.hitstop:
            self.hitstop -= 1
            return
        for i, (action, _) in enumerate(self.input_buffer):
            if action == 'jump':
                accepted = self.on_ground and not self.disabled and not self.current_move and not self.guard
                if accepted:
                    self.vel_y = -13
                    self.on_ground = False
            else:
                accepted = self.start_move(action)
            if accepted:
                del self.input_buffer[i]
                break
        self.input_buffer = [(a, t - 1) for a, t in self.input_buffer if t > 1]
        if self.current_move and not self.disabled:
            move = self.moves[self.current_move]
            if self.move_frame < move.startup + move.active:
                self.rect.x += int(self.facing * move.dash_speed)
            if (not move.utility and move.startup <= self.move_frame < move.startup + move.active
                    and not self.move_resolved):
                if move.projectile:
                    for shot in range(move.projectile_count):
                        offset = (shot - (move.projectile_count - 1) / 2) * move.projectile_spread
                        projectiles.append(Projectile(self, self.facing, move, offset))
                    self.move_resolved = True
                else:
                    hitbox = pygame.Rect(0, self.rect.centery + move.hitbox_y, move.reach, move.hitbox_height)
                    if self.facing == 1:
                        hitbox.left = self.rect.right
                    else:
                        hitbox.right = self.rect.left
                    if hitbox.colliderect(opponent.rect):
                        result = opponent.receive_hit(self, move, self.facing, particles)
                        self.move_resolved = True
                        self.move_connected = result in ('hit', 'guard')
                        if result == 'hit' and move.self_launch:
                            self.vel_y = move.self_launch
                            self.on_ground = False
            if self.current_move:
                self.move_frame += 1
                if self.move_frame >= move.duration:
                    self.current_move = None
        if not self.disabled and not self.current_move and not self.guard:
            self.rect.x += int(self.move_x * self.speed)
            if self.move_x:
                self.facing = 1 if self.move_x > 0 else -1
        self.vel_y += .7
        self.rect.y += int(self.vel_y)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True
            if self.current_move and self.moves[self.current_move].air_only:
                self.current_move = None
            if self.launched:
                self.launched = False
                self.pending_knockdown = False
                self.knocked_down = True
                self.knockdown_timer = 30
                self.hitstun = 0
        if self.rect.colliderect(opponent.rect):
            overlap = min(self.rect.right, opponent.rect.right) - max(self.rect.left, opponent.rect.left)
            self.rect.x += (-1 if self.rect.centerx < opponent.rect.centerx else 1) * ((overlap + 1) // 2)
        self.rect.x = max(10, min(WIDTH - self.rect.width - 10, self.rect.x))

    def add_stagger(self, amount, guarded=False):
        self.neutral_frames = 0
        self.stagger = min(self.max_stagger, self.stagger + amount * (.15 if self.stagger_protected else 1))
        if self.stagger >= self.max_stagger and not self.stagger_protected:
            self.stagger = 0
            self.staggered = True
            self.stagger_timer = 60
            self.stagger_protected = True
            self.guard = False
            self.parry_window = 0
            self.current_move = None
            self.knocked_down = False
            self.knockdown_timer = 0
            self.pending_knockdown = False
            self.announce('GUARD BREAK' if guarded else 'STAGGER BREAK')

    def receive_hit(self, attacker, move, direction, particles):
        if (self.hp <= 0 or self.knocked_down or self.wakeup_invulnerability
                or self.move_invulnerability or self.juggle_exhausted):
            return 'immune'
        defending = self.guard and self.facing == -direction
        if defending and self.parry_window and not self.parry_recovery:
            perfect = self.parry_window > self.parry_duration - PERFECT_PARRY_FRAMES
            self.parry_success = True
            if self.current_move and self.moves[self.current_move].utility:
                self.current_move = None
                self.guard = False
            self.parry_window = 0
            self.parry_recovery = 12
            self.energy = min(100, self.energy + (20 if perfect else 10))
            self.hitstop = attacker.hitstop = 5 if perfect else 3
            attacker.current_move = None
            attacker.move_invulnerability = 0
            attacker.guard = False
            attacker.parry_window = 0
            attacker.hitstun = max(attacker.hitstun, 30 if perfect else 24)
            attacker.rect.x -= direction * 10
            attacker.add_stagger(40 if perfect else 25)
            self.announce('PERFECT PARRY!' if perfect else 'PARRY!')
            return 'parry'
        counter = bool(self.current_move and self.move_frame < self.moves[self.current_move].startup)
        if defending:
            self.hp = max(0, self.hp - max(1, int(move.damage * .15)))
            self.hitstun = max(self.hitstun, 5)
            self.add_stagger(move.guard_damage, guarded=True)
        else:
            # Scaling follows the defender's uninterrupted vulnerability, including breaks.
            if attacker.combo_target is not self or (not self.vulnerable and attacker.combo_timer <= 0):
                attacker.combo_count = 0
            scaling = COMBO_SCALING[min(attacker.combo_count, len(COMBO_SCALING) - 1)]
            attacker.combo_scaling = scaling
            attacker.combo_count += 1
            attacker.combo_target = self
            attacker.combo_timer = 1
            self.hp = max(0, self.hp - max(1, int(move.damage * scaling)))
            self.hitstun = max(self.hitstun, int(move.hitstun * (1.5 if counter else 1)))
            self.current_move = None
            self.move_invulnerability = 0
            self.guard = False
            self.parry_window = 0
            self.add_stagger(move.stagger_damage * (1.4 if counter else 1))
            # A finisher falls after hit stun, leaving time for a special cancel.
            self.pending_knockdown = move.knockdown and not self.staggered
            if move.launch_velocity and not self.launched:
                self.launched = True
                self.on_ground = False
                self.juggle_hits = 0
                self.vel_y = move.launch_velocity
                self.pending_knockdown = False
                self.announce('LAUNCH!')
            elif self.launched:
                self.juggle_hits += 1
                if move.juggle_velocity:
                    self.vel_y = move.juggle_velocity
                if self.juggle_hits >= MAX_JUGGLE_HITS:
                    self.juggle_exhausted = True
                    self.vel_y = max(8, self.vel_y)
                    self.announce('JUGGLE LIMIT')
            if counter:
                self.announce('COUNTER!')
            attacker.energy = min(100, attacker.energy + 12)
        self.energy = min(100, self.energy + 5)
        self.rect.x += int(direction * move.knockback * (.35 if defending else 1))
        self.rect.x = max(10, min(WIDTH - self.rect.width - 10, self.rect.x))
        self.flash = 6
        for _ in range(10):
            particles.append(Particle(self.rect.centerx, self.rect.centery, YELLOW))
        return 'guard' if defending else 'hit'

    def draw(self, surf):
        body_color = WHITE if self.flash and self.flash % 2 == 0 else self.color
        pygame.draw.rect(surf, body_color, self.rect, border_radius=14)
        pygame.draw.rect(surf, BLACK, self.rect, 3, border_radius=14)
        eye_y = self.rect.y + 28
        if self.facing == 1:
            ex1, ex2 = self.rect.x + 42, self.rect.x + 55
        else:
            ex1, ex2 = self.rect.x + 15, self.rect.x + 28
        pygame.draw.circle(surf, BLACK, (ex1, eye_y), 4)
        pygame.draw.circle(surf, BLACK, (ex2, eye_y), 4)
        arm_y = self.rect.y + 62
        pygame.draw.line(surf, body_color, (self.rect.centerx, arm_y), (self.rect.centerx + self.facing * 45, arm_y - 6), 12)
        txt = SMALL.render(self.name, True, WHITE)
        surf.blit(txt, txt.get_rect(center=(self.rect.centerx, self.rect.y - 18)))
        if self.guard:
            pygame.draw.arc(surf, CYAN, self.rect.inflate(28, 12), math.radians(-80), math.radians(80), 5)
        if self.current_move:
            move = self.moves[self.current_move]
            if not move.utility and move.startup <= self.move_frame < move.startup + move.active:
                x = self.rect.right if self.facing == 1 else self.rect.left - move.reach
                pygame.draw.rect(surf, YELLOW, (x, self.rect.centery + move.hitbox_y, move.reach, move.hitbox_height), 2)
        if self.notice_timer:
            txt = SMALL.render(self.notice, True, YELLOW)
            surf.blit(txt, txt.get_rect(center=(self.rect.centerx, self.rect.y - 42)))
        if self.knocked_down:
            pygame.draw.line(surf, GRAY, self.rect.midleft, self.rect.midright, 6)
