import pygame
import sys
from jupyter_game.core.config import *
from jupyter_game.core.settings import preferences, save_settings, DEFAULT_BINDINGS, RESERVED_KEYS, valid_binding
from jupyter_game.ui.rendering import draw_back_to_menu_button, back_clicked


def settings_screen():
    selected = 0
    capture = None
    message = ''
    actions = list(DEFAULT_BINDINGS['keyboard1'])
    rows = ['difficulty', 'input', 'deadzone', 'sound'] + [(kind, action) for kind in DEFAULT_BINDINGS for action in actions] + ['reset', 'save']
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if back_clicked(event) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                if capture:
                    capture = None
                else:
                    return
            if event.type != pygame.KEYDOWN:
                continue
            if capture:
                kind, action = capture
                bindings = preferences['bindings'][kind]
                if event.key in RESERVED_KEYS or not valid_binding(event.key):
                    message = 'Key reserved for menus or training.'
                elif event.key in [v for a, v in bindings.items() if a != action]:
                    message = 'Key already used in this layout.'
                else:
                    bindings[action] = event.key
                    capture = None
                    message = 'Binding changed. Choose Save to keep.'
                continue
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                selected = (selected + (1 if event.key == pygame.K_DOWN else -1)) % len(rows)
            if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN):
                row = rows[selected]
                delta = -1 if event.key == pygame.K_LEFT else 1
                if isinstance(row, tuple):
                    capture = row
                elif row in ('difficulty', 'input'):
                    choices = ('easy', 'normal', 'hard') if row == 'difficulty' else ('keyboard', 'controller')
                    preferences[row] = choices[(choices.index(preferences[row]) + delta) % len(choices)]
                elif row == 'deadzone':
                    preferences[row] = round(max(.1, min(.8, preferences[row] + .05 * delta)), 2)
                elif row == 'sound':
                    preferences[row] = not preferences[row]
                elif row == 'reset':
                    preferences['bindings'] = {k: dict(v) for k, v in DEFAULT_BINDINGS.items()}
                    message = 'Default bindings restored. Choose Save to keep.'
                elif row == 'save':
                    try:
                        save_settings(preferences)
                        message = 'Settings saved.'
                    except OSError as exc:
                        message = f'Could not save: {exc}'
        screen.fill(BLACK)
        draw_back_to_menu_button()
        text = BIG.render('SETTINGS', True, ORANGE)
        screen.blit(text, text.get_rect(center=(WIDTH // 2, 70)))
        start = max(0, min(selected - 5, len(rows) - 12))
        for offset, index in enumerate(range(start, min(start + 12, len(rows)))):
            row = rows[index]
            if isinstance(row, tuple):
                kind, action = row
                label = f'{kind} {action}: {pygame.key.name(preferences["bindings"][kind][action])}'
            else:
                label = f'{row}: {preferences[row]}' if row in preferences else row.title()
            if capture == row:
                label += ' -- press new key'
            text = FONT.render(('> ' if index == selected else '  ') + label, True, YELLOW if index == selected else WHITE)
            screen.blit(text, (350, 135 + offset * 37))
        screen.blit(SMALL.render('Up/Down choose | Left/Right change | Enter rebind/save | Esc back', True, CYAN), (250, 615))
        screen.blit(SMALL.render(message[:95], True, WHITE), (200, 650))
        pygame.display.flip()
