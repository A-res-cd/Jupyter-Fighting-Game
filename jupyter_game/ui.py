import pygame
import sys

from .config import *
from .roster import LIBRARIES

def draw_bar(x, y, w, h, value, max_value, color, reverse=False):
    pygame.draw.rect(screen, (45, 45, 55), (x, y, w, h), border_radius=7)
    fw = int(w * max(0, value) / max_value)
    if reverse:
        pygame.draw.rect(screen, color, (x + w - fw, y, fw, h), border_radius=7)
    else:
        pygame.draw.rect(screen, color, (x, y, fw, h), border_radius=7)
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 2, border_radius=7)



def draw_back_to_menu_button(battle=False):
    rect = pygame.Rect(20, HEIGHT - 92 if battle else 18, 210, 42)
    pygame.draw.rect(screen, (42, 46, 60), rect, border_radius=10)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=10)
    txt = SMALL.render("Back to Menu [ESC]", True, WHITE)
    screen.blit(txt, txt.get_rect(center=rect.center))
    return rect


def draw_combat_hud(p1, p2, round_timer, right_label='P2'):
    for fighter, x, reverse, label in ((p1, 70, False, 'P1'),
                                      (p2, WIDTH - 530, True, right_label)):
        draw_bar(x, 45, 460, 28, fighter.hp, fighter.max_hp, GREEN if not reverse else RED, reverse)
        draw_bar(x, 80, 460, 13, fighter.energy, 100, CYAN, reverse)
        draw_bar(x, 100, 460, 13, fighter.stagger, fighter.max_stagger, ORANGE, reverse)
        text = SMALL.render(f'{label} {fighter.name} | ENERGY / STAGGER', True, WHITE)
        screen.blit(text, (x, 120))
        if fighter.current_move:
            text = SMALL.render(fighter.moves[fighter.current_move].name, True, fighter.color)
            screen.blit(text, (x, 145))
        if fighter.combo_count >= 2:
            text = FONT.render(f'{fighter.combo_count} HIT COMBO ({fighter.combo_scaling:.0%})', True, YELLOW)
            screen.blit(text, (x, 175))
    text = BIG.render(str(max(0, round_timer // FPS)), True, WHITE)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, 65)))
    text = SMALL.render('Down+Light > Heavy > Air Light > Air Heavy > Special  |  Down, Down+Special = Utility', True, GRAY)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, 215)))


def draw_background():
    screen.fill((24, 28, 40))
    for i in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (31, 36, 50), (0, i), (WIDTH, i))
    for i in range(0, WIDTH, 80):
        pygame.draw.line(screen, (28, 33, 47), (i, 0), (i, HEIGHT))
    pygame.draw.circle(screen, (235, 120, 40), (WIDTH // 2, 160), 55, 5)
    pygame.draw.arc(screen, (245, 190, 130), (WIDTH // 2 - 105, 110, 210, 100), 0.2, 2.9, 4)
    pygame.draw.rect(screen, (50, 54, 65), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(screen, WHITE, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)



def main_menu():
    options = ["SINGLE PLAYER", "MULTIPLAYER", "ONLINE MULTIPLAYER", "QUIT"]
    selected = 0

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))

        title = TITLE.render("JUPYTER", True, ORANGE)
        subtitle = FONT.render("PYTHON LIBRARY BRAWL", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 180)))

        for i, option in enumerate(options):
            rect = pygame.Rect(WIDTH // 2 - 210, 255 + i * 82, 420, 60)
            if i == selected:
                pygame.draw.rect(screen, ORANGE, rect, border_radius=14)
                color = BLACK
            else:
                pygame.draw.rect(screen, (40, 44, 58), rect, border_radius=14)
                pygame.draw.rect(screen, WHITE, rect, 2, border_radius=14)
                color = WHITE

            text = FONT.render(option, True, color)
            screen.blit(text, text.get_rect(center=rect.center))

        hint = SMALL.render(
            "UP/DOWN or W/S = Navigate    ENTER / J / Controller A = Select",
            True, GRAY
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 55)))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "QUIT"

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(options)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(options)
                elif event.key in (pygame.K_RETURN, pygame.K_j):
                    return options[selected]
                elif event.key == pygame.K_ESCAPE:
                    return "QUIT"

            if event.type == pygame.JOYHATMOTION:
                if event.value[1] > 0:
                    selected = (selected - 1) % len(options)
                elif event.value[1] < 0:
                    selected = (selected + 1) % len(options)

            if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 7):
                return options[selected]


def single_player_select():
    index = 0
    cols = 6

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))

        title = TITLE.render("SINGLE PLAYER", True, ORANGE)
        subtitle = FONT.render("CHOOSE YOUR LIBRARY", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 60)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 115)))
        draw_back_to_menu_button()

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
            pygame.draw.rect(
                screen, YELLOW if i == index else WHITE,
                rect, 5 if i == index else 2, border_radius=12
            )

            contrast = BLACK if sum(lib["color"]) > 500 else WHITE
            name = FONT.render(lib["name"], True, contrast)
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.y + 28)))
            screen.blit(SMALL.render(f"HP {lib['hp']}", True, contrast), (rect.x + 12, rect.y + 55))
            screen.blit(SMALL.render(f"PWR {lib['power']}", True, contrast), (rect.x + 12, rect.y + 77))
            screen.blit(SMALL.render(f"SPD {lib['speed']:.1f}", True, contrast), (rect.x + 90, rect.y + 77))

        hint = SMALL.render(
            "Arrow Keys = Choose    Enter = Fight    ESC = Main Menu",
            True, GRAY
        )
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 25)))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                elif event.key == pygame.K_LEFT:
                    index = (index - 1) % len(LIBRARIES)
                elif event.key == pygame.K_RIGHT:
                    index = (index + 1) % len(LIBRARIES)
                elif event.key == pygame.K_UP:
                    index = (index - cols) % len(LIBRARIES)
                elif event.key == pygame.K_DOWN:
                    index = (index + cols) % len(LIBRARIES)
                elif event.key == pygame.K_RETURN:
                    return index


def device_screen(p1_input, p2_input):
    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))
        title = TITLE.render("LOCAL MULTIPLAYER", True, ORANGE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 105)))
        subtitle = FONT.render("Two-player input devices detected automatically", True, WHITE)
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 165)))
        draw_back_to_menu_button()

        boxes = [
            (pygame.Rect(110, 235, 500, 250), "PLAYER 1", p1_input, BLUE),
            (pygame.Rect(670, 235, 500, 250), "PLAYER 2", p2_input, RED),
        ]
        for rect, player, device, accent in boxes:
            pygame.draw.rect(screen, (35, 39, 52), rect, border_radius=18)
            pygame.draw.rect(screen, accent, rect, 4, border_radius=18)
            ptxt = BIG.render(player, True, accent)
            screen.blit(ptxt, ptxt.get_rect(center=(rect.centerx, rect.y + 60)))
            dtxt = FONT.render(device.label[:38], True, WHITE)
            screen.blit(dtxt, dtxt.get_rect(center=(rect.centerx, rect.y + 130)))
            words = device.short_controls().split()
            lines = ['']
            for word in words:
                candidate = (lines[-1] + ' ' + word).strip()
                if SMALL.size(candidate)[0] > rect.width - 30:
                    lines.append(word)
                else:
                    lines[-1] = candidate
            for line_num, line in enumerate(lines):
                ctxt = SMALL.render(line, True, GRAY)
                screen.blit(ctxt, ctxt.get_rect(center=(rect.centerx, rect.y + 180 + 24 * line_num)))

        info = SMALL.render("Connect both controllers before launching. ENTER / Controller A = continue", True, (205, 205, 215))
        screen.blit(info, info.get_rect(center=(WIDTH // 2, 555)))
        refresh = SMALL.render("R = Redetect controllers     ESC = Main Menu", True, GRAY)
        screen.blit(refresh, refresh.get_rect(center=(WIDTH // 2, 600)))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if event.key == pygame.K_r:
                    return "redetect"
                if event.key == pygame.K_RETURN:
                    return "continue"
            if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 7):
                return "continue"


def select_screen(p1_input, p2_input):
    p1_index, p2_index = 0, 1
    p1_ready = p2_ready = False
    cols = 6

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

            for player_num, device in ((1, p1_input), (2, p2_input)):
                action = device.event_action(event)
                if not action:
                    continue
                index = p1_index if player_num == 1 else p2_index
                ready = p1_ready if player_num == 1 else p2_ready
                if ready:
                    if action == "back":
                        if player_num == 1: p1_ready = False
                        else: p2_ready = False
                    continue

                if action == "left": index = (index - 1) % len(LIBRARIES)
                elif action == "right": index = (index + 1) % len(LIBRARIES)
                elif action in ("up", "jump"): index = (index - cols) % len(LIBRARIES)
                elif action == "down": index = (index + cols) % len(LIBRARIES)
                elif action in ("attack", "confirm"):
                    if player_num == 1: p1_ready = True
                    else: p2_ready = True
                elif action == "back":
                    return None

                if player_num == 1: p1_index = index
                else: p2_index = index

        if p1_ready and p2_ready:
            pygame.time.delay(250)
            return p1_index, p2_index

        screen.fill((20, 23, 32))
        title = TITLE.render("JUPYTER", True, ORANGE)
        subtitle = FONT.render("PYTHON LIBRARY BRAWL - LOCAL VERSUS", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 55)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 108)))
        draw_back_to_menu_button()
        p1txt = FONT.render(f"P1: {'READY!' if p1_ready else 'Choose fighter'}", True, BLUE)
        p2txt = FONT.render(f"P2: {'READY!' if p2_ready else 'Choose fighter'}", True, RED)
        screen.blit(p1txt, (70, 145))
        screen.blit(p2txt, (WIDTH - 70 - p2txt.get_width(), 145))

        card_w, card_h = 180, 120
        start_x, start_y = 65, 195
        gap_x, gap_y = 22, 28

        for i, lib in enumerate(LIBRARIES):
            row, col = divmod(i, cols)
            rect = pygame.Rect(start_x + col * (card_w + gap_x), start_y + row * (card_h + gap_y), card_w, card_h)
            pygame.draw.rect(screen, lib["color"], rect, border_radius=12)
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=12)
            if i == p1_index:
                pygame.draw.rect(screen, CYAN if p1_ready else BLUE, rect.inflate(8, 8), 5, border_radius=15)
            if i == p2_index:
                pygame.draw.rect(screen, YELLOW if p2_ready else RED, rect.inflate(18, 18), 5, border_radius=18)
            contrast = BLACK if sum(lib["color"]) > 500 else WHITE
            name = FONT.render(lib["name"], True, contrast)
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.y + 28)))
            screen.blit(SMALL.render(f"HP {lib['hp']}", True, contrast), (rect.x + 12, rect.y + 55))
            screen.blit(SMALL.render(f"PWR {lib['power']}", True, contrast), (rect.x + 12, rect.y + 77))
            screen.blit(SMALL.render(f"SPD {lib['speed']:.1f}", True, contrast), (rect.x + 90, rect.y + 77))

        hint = SMALL.render("Move to select. Attack/A confirms. Back/B cancels ready.", True, (195, 195, 205))
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 24)))
        pygame.display.flip()
