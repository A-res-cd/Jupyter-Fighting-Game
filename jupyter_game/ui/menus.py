"""Main menu, fighter selection, and local device screens."""
import pygame
import sys
from jupyter_game.core.config import *
from jupyter_game.data.roster import LIBRARIES
from jupyter_game.ui.rendering import draw_back_to_menu_button, back_clicked


def main_menu():
    options = ["SINGLE PLAYER", "MULTIPLAYER", "ONLINE MULTIPLAYER", "TRAINING", "SETTINGS", "QUIT"]
    selected = 0

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))

        title = TITLE.render("JUPYTER", True, ORANGE)
        subtitle = FONT.render("PYTHON LIBRARY BRAWL", True, WHITE)
        screen.blit(title, title.get_rect(center=(WIDTH // 2, 120)))
        screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 180)))

        for i, option in enumerate(options):
            rect = pygame.Rect(WIDTH // 2 - 210, 235 + i * 65, 420, 55)
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
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, option in enumerate(options):
                    if pygame.Rect(WIDTH // 2 - 210, 235 + i * 65, 420, 55).collidepoint(event.pos):
                        return option
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


def single_player_select(title_label='SINGLE PLAYER'):
    index = 0
    cols = 6

    while True:
        clock.tick(FPS)
        screen.fill((20, 23, 32))

        title = TITLE.render(title_label, True, ORANGE)
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
            if back_clicked(event):
                return None
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.JOYBUTTONDOWN and event.button in (0, 7):
                return index
            if event.type == pygame.JOYHATMOTION:
                x, y = event.value
                index = (index + x - y * cols) % len(LIBRARIES)
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
            if back_clicked(event):
                return 'menu'
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
            if back_clicked(event):
                return None
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
