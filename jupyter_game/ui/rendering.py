import pygame

from jupyter_game.core.config import *

_background = None
_overlay = None


def back_clicked(event, battle=False):
    return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and
            pygame.Rect(20, HEIGHT - 92 if battle else 18, 210, 42).collidepoint(event.pos))


def draw_overlay(title, lines=()):
    global _overlay
    if _overlay is None:
        _overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        _overlay.fill((0, 0, 0, 185))
    screen.blit(_overlay, (0, 0))
    text = BIG.render(title, True, YELLOW)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, 280)))
    for i, line in enumerate(lines):
        text = FONT.render(line, True, WHITE)
        screen.blit(text, text.get_rect(center=(WIDTH // 2, 345 + i * 38)))


def draw_match(match, right_label='P2'):
    draw_background()
    draw_combat_hud(match.p1, match.p2, match.timer, right_label)
    for item in (match.p1, match.p2, *match.projectiles, *match.particles):
        item.draw(screen)
    text = SMALL.render(f'Round {match.round} | P1 {match.scores[0]} - {match.scores[1]} {right_label}', True, WHITE)
    screen.blit(text, text.get_rect(center=(WIDTH // 2, 245)))
    if match.phase == 'round_start':
        draw_overlay(f'ROUND {match.round}', ['Get ready'])
    elif match.phase == 'round_end':
        draw_overlay('DRAW' if not match.round_result else f'P{match.round_result} TAKES ROUND')

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
    global _background
    if _background is not None:
        screen.blit(_background, (0, 0))
        return
    screen.fill((24, 28, 40))
    for i in range(0, HEIGHT, 40):
        pygame.draw.line(screen, (31, 36, 50), (0, i), (WIDTH, i))
    for i in range(0, WIDTH, 80):
        pygame.draw.line(screen, (28, 33, 47), (i, 0), (i, HEIGHT))
    pygame.draw.circle(screen, (235, 120, 40), (WIDTH // 2, 160), 55, 5)
    pygame.draw.arc(screen, (245, 190, 130), (WIDTH // 2 - 105, 110, 210, 100), 0.2, 2.9, 4)
    pygame.draw.rect(screen, (50, 54, 65), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    pygame.draw.line(screen, WHITE, (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
    _background = screen.copy()



