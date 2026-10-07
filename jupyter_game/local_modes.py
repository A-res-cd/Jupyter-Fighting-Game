import pygame
import random
import sys

from .config import *
from .roster import LIBRARIES
from .input_devices import InputDevice
from .entities import Fighter, Particle
from .ui import draw_bar, draw_background, draw_back_to_menu_button

def battle(p1_index, p2_index, p1_input, p2_input):
    p1 = Fighter(LIBRARIES[p1_index], 250, 1, p1_input)
    p2 = Fighter(LIBRARIES[p2_index], WIDTH - 320, -1, p2_input)
    projectiles, particles = [], []
    winner = None
    round_timer = 99 * FPS

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return "menu"

            if winner:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r: return "rematch"
                    if event.key == pygame.K_RETURN: return "select"
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0: return "rematch"
                    if event.button == 1: return "select"
                continue

            a1 = p1_input.event_action(event)
            a2 = p2_input.event_action(event)
            if a1: p1.handle_action(a1, p2, projectiles, particles)
            if a2: p2.handle_action(a2, p1, projectiles, particles)

        if not winner:
            p1.update(p2)
            p2.update(p1)
            for proj in projectiles:
                proj.update()
                target = p2 if proj.owner is p1 else p1
                if proj.alive and proj.rect.colliderect(target.rect):
                    target.hurt(proj.damage, proj.owner.facing * 20)
                    proj.owner.energy = min(100, proj.owner.energy + 8)
                    proj.alive = False
                    for _ in range(14):
                        particles.append(Particle(target.rect.centerx, target.rect.centery, proj.color))
            projectiles[:] = [p for p in projectiles if p.alive]
            for pt in particles: pt.update()
            particles[:] = [pt for pt in particles if pt.life > 0]
            round_timer -= 1
            if p1.hp <= 0 or p2.hp <= 0 or round_timer <= 0:
                if p1.hp == p2.hp: winner = "DRAW"
                elif p1.hp > p2.hp: winner = f"P1 {p1.name}"
                else: winner = f"P2 {p2.name}"

        draw_background()
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
        screen.blit(SMALL.render(p1.special_name, True, p1.color), (70, 135))
        p2s = SMALL.render(p2.special_name, True, p2.color)
        screen.blit(p2s, (WIDTH - 70 - p2s.get_width(), 135))

        p1.draw(screen); p2.draw(screen)
        for proj in projectiles: proj.draw(screen)
        for pt in particles: pt.draw(screen)

        if p1.combo >= 2 and p1.combo_timer > 0:
            screen.blit(FONT.render(f"P1 {p1.combo} HIT COMBO!", True, BLUE), (65, 180))
        if p2.combo >= 2 and p2.combo_timer > 0:
            t = FONT.render(f"P2 {p2.combo} HIT COMBO!", True, RED)
            screen.blit(t, (WIDTH - 65 - t.get_width(), 180))

        h1 = SMALL.render(p1_input.short_controls(), True, (205, 205, 215))
        h2 = SMALL.render(p2_input.short_controls(), True, (205, 205, 215))
        screen.blit(h1, (30, HEIGHT - 28))
        screen.blit(h2, (WIDTH - 30 - h2.get_width(), HEIGHT - 28))

        if winner:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))
            result = "DRAW!" if winner == "DRAW" else f"{winner} WINS!"
            txt = TITLE.render(result, True, YELLOW)
            screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
            msg1 = FONT.render("R = Rematch    Enter = Character Select    ESC = Main Menu", True, WHITE)
            msg2 = FONT.render("Controller: A = Rematch    B = Character Select", True, WHITE)
            screen.blit(msg1, msg1.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))
            screen.blit(msg2, msg2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 82)))

        pygame.display.flip()


def battle_single_player(player_index):
    cpu_choices = [i for i in range(len(LIBRARIES)) if i != player_index]
    cpu_index = random.choice(cpu_choices)

    player_input = InputDevice("keyboard1", label="Keyboard")
    dummy_input = InputDevice("keyboard2", label="CPU")

    p1 = Fighter(LIBRARIES[player_index], 250, 1, player_input)
    p2 = Fighter(LIBRARIES[cpu_index], WIDTH - 320, -1, dummy_input)

    projectiles, particles = [], []
    winner = None
    round_timer = 99 * FPS

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"

                if winner:
                    if event.key == pygame.K_r:
                        return "rematch"
                    if event.key == pygame.K_RETURN:
                        return "select"
                else:
                    action = player_input.event_action(event)
                    if action:
                        p1.handle_action(action, p2, projectiles, particles)

        if not winner:
            # Player movement/physics.
            p1.update(p2)

            # CPU timers.
            for attr in ("attack_cd", "special_cd", "stun", "flash"):
                value = getattr(p2, attr)
                if value > 0:
                    setattr(p2, attr, value - 1)

            if p2.combo_timer > 0:
                p2.combo_timer -= 1
            else:
                p2.combo = 0

            dx = p1.rect.centerx - p2.rect.centerx
            p2.facing = 1 if dx > 0 else -1
            p2.guard = False

            if p2.stun <= 0:
                distance = abs(dx)

                if distance > 100:
                    p2.rect.x += p2.facing * p2.speed * 0.72
                else:
                    roll = random.random()
                    if roll < 0.055:
                        p2.normal_attack(p1, particles)
                    elif roll < 0.075:
                        p2.special(projectiles)
                    elif roll < 0.10:
                        p2.guard = True

                if random.random() < 0.008 and p2.on_ground:
                    p2.jump()

            p2.vel_y += 0.7
            p2.rect.y += int(p2.vel_y)

            if p2.rect.bottom >= GROUND_Y:
                p2.rect.bottom = GROUND_Y
                p2.vel_y = 0
                p2.on_ground = True

            p2.rect.x = max(10, min(WIDTH - p2.rect.width - 10, p2.rect.x))

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

                    for _ in range(14):
                        particles.append(
                            Particle(target.rect.centerx, target.rect.centery, proj.color)
                        )

            projectiles[:] = [p for p in projectiles if p.alive]

            for pt in particles:
                pt.update()
            particles[:] = [pt for pt in particles if pt.life > 0]

            round_timer -= 1

            if p1.hp <= 0 or p2.hp <= 0 or round_timer <= 0:
                if p1.hp == p2.hp:
                    winner = "DRAW"
                elif p1.hp > p2.hp:
                    winner = p1.name
                else:
                    winner = p2.name

        draw_background()
        draw_back_to_menu_button()

        draw_bar(70, 45, 460, 28, p1.hp, p1.max_hp, GREEN)
        draw_bar(WIDTH - 530, 45, 460, 28, p2.hp, p2.max_hp, RED, True)
        draw_bar(70, 80, 300, 13, p1.energy, 100, CYAN)
        draw_bar(WIDTH - 370, 80, 300, 13, p2.energy, 100, CYAN, True)

        left_name = FONT.render(f"P1  {p1.name}", True, WHITE)
        right_name = FONT.render(f"CPU  {p2.name}", True, WHITE)
        screen.blit(left_name, (70, 105))
        screen.blit(right_name, (WIDTH - 70 - right_name.get_width(), 105))

        time_txt = BIG.render(str(max(0, round_timer // FPS)), True, WHITE)
        screen.blit(time_txt, time_txt.get_rect(center=(WIDTH // 2, 65)))

        p1.draw(screen)
        p2.draw(screen)

        for proj in projectiles:
            proj.draw(screen)
        for pt in particles:
            pt.draw(screen)

        hint = SMALL.render(
            "A/D Move   W Jump   S Guard   J Attack   K Special",
            True, (205, 205, 215)
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 28)))

        if winner:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))

            result = "DRAW!" if winner == "DRAW" else f"{winner} WINS!"
            txt = TITLE.render(result, True, YELLOW)
            screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))

            msg = FONT.render(
                "R = Rematch    Enter = Character Select    Esc = Main Menu",
                True, WHITE
            )
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))

        pygame.display.flip()
