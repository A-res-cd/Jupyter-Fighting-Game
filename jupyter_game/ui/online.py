"""Online menu and address input screen."""
import pygame
from jupyter_game.core.config import *
from jupyter_game.ui.rendering import draw_back_to_menu_button, back_clicked


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
            if back_clicked(event):
                return "BACK"
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
            if back_clicked(event):
                return None
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


