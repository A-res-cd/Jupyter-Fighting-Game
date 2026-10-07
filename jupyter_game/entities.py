import pygame
import random
import math

from .config import *

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
    def __init__(self, owner, direction, color, damage, speed=10, y_offset=0):
        self.owner = owner
        self.x = owner.rect.centerx + direction * 45
        self.y = owner.rect.centery - 10 + y_offset
        self.vx = direction * speed
        self.damage = damage
        self.color = color
        self.rect = pygame.Rect(self.x - 10, self.y - 8, 20, 16)
        self.alive = True

    def update(self):
        self.x += self.vx
        self.rect.center = (int(self.x), int(self.y))
        if self.x < -50 or self.x > WIDTH + 50:
            self.alive = False

    def draw(self, surf):
        pygame.draw.ellipse(surf, self.color, self.rect)
        pygame.draw.ellipse(surf, WHITE, self.rect, 2)


class Fighter:
    def __init__(self, data, x, facing, input_device):
        self.data = data
        self.name = data["name"]
        self.color = data["color"]
        self.max_hp = data["hp"]
        self.hp = self.max_hp
        self.speed = data["speed"]
        self.power = data["power"]
        self.special_name = data["special"]
        self.input = input_device
        self.rect = pygame.Rect(x, GROUND_Y - 120, 70, 120)
        self.vel_y = 0
        self.on_ground = True
        self.facing = facing
        self.attack_cd = 0
        self.special_cd = 0
        self.stun = 0
        self.flash = 0
        self.guard = False
        self.energy = 0
        self.combo = 0
        self.combo_timer = 0

    def hurt(self, dmg, knockback=0):
        if self.guard:
            dmg *= 0.35
        self.hp = max(0, self.hp - int(dmg))
        self.rect.x += int(knockback)
        self.stun = 8
        self.flash = 6
        self.energy = min(100, self.energy + 10)

    def normal_attack(self, opponent, particles):
        if self.attack_cd > 0 or self.stun > 0:
            return
        self.attack_cd = 22
        hitbox = pygame.Rect(0, 0, 55, 50)
        hitbox.centery = self.rect.centery - 10
        if self.facing == 1:
            hitbox.left = self.rect.right
        else:
            hitbox.right = self.rect.left
        if hitbox.colliderect(opponent.rect):
            dmg = self.power + random.randint(-2, 3)
            opponent.hurt(dmg, self.facing * 14)
            self.energy = min(100, self.energy + 16)
            self.combo += 1
            self.combo_timer = 60
            for _ in range(10):
                particles.append(Particle(opponent.rect.centerx, opponent.rect.centery, YELLOW))

    def special(self, projectiles):
        if self.special_cd > 0 or self.energy < 50 or self.stun > 0:
            return
        self.energy -= 50
        self.special_cd = 70
        ranged = {"NumPy", "SciPy", "OpenCV", "Plotly", "Matplotlib", "PyTorch"}
        dashers = {"FastAPI", "Requests", "Selenium", "Flask"}
        if self.name in ranged:
            for offset in (-20, 0, 20):
                projectiles.append(Projectile(self, self.facing, self.color, self.power + 6, 11, offset))
        elif self.name in dashers:
            self.rect.x += self.facing * 90
            projectiles.append(Projectile(self, self.facing, CYAN, self.power + 10, 14))
        else:
            projectiles.append(Projectile(self, self.facing, self.color, self.power + 16, 8))

    def jump(self):
        if self.on_ground and self.stun <= 0:
            self.vel_y = -13
            self.on_ground = False

    def handle_action(self, action, opponent, projectiles, particles):
        if action in ("jump", "up"):
            self.jump()
        elif action == "attack":
            self.normal_attack(opponent, particles)
        elif action == "special":
            self.special(projectiles)

    def update(self, opponent):
        if self.attack_cd > 0: self.attack_cd -= 1
        if self.special_cd > 0: self.special_cd -= 1
        if self.stun > 0: self.stun -= 1
        if self.flash > 0: self.flash -= 1
        if self.combo_timer > 0: self.combo_timer -= 1
        else: self.combo = 0

        self.guard = self.input.guarding()
        if self.stun <= 0:
            move = self.input.move_x()
            if move:
                self.rect.x += move * self.speed
                self.facing = 1 if move > 0 else -1

        self.vel_y += 0.7
        self.rect.y += int(self.vel_y)
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0
            self.on_ground = True

        self.rect.x = max(10, min(WIDTH - self.rect.width - 10, self.rect.x))

        if self.rect.colliderect(opponent.rect):
            overlap = min(self.rect.right, opponent.rect.right) - max(self.rect.left, opponent.rect.left)
            if overlap > 0:
                if self.rect.centerx < opponent.rect.centerx:
                    self.rect.x -= overlap // 2
                else:
                    self.rect.x += overlap // 2

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
