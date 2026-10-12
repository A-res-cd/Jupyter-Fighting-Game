import pygame
import random
import sys

from .config import *
from .roster import LIBRARIES
from .input_devices import InputDevice
from .entities import Fighter
from .combat import step_battle
from .ui import draw_background, draw_back_to_menu_button, draw_combat_hud


def cpu_state(fighter, opponent):
    dx = opponent.rect.centerx - fighter.rect.centerx
    close = abs(dx) < 155
    threatened = opponent.current_move is not None and close
    state = {'left': dx < -100, 'right': dx > 100,
             'guard': threatened and random.random() < .65}
    if close and not state['guard']:
        roll = random.random()
        state['light'] = roll < .055
        state['low'] = .055 <= roll < .075
        state['heavy'] = .075 <= roll < .10
        state['launcher'] = .10 <= roll < .12
        state['special'] = .12 <= roll < .135
        state['directional_special'] = .135 <= roll < .145
    if not fighter.on_ground and opponent.launched:
        state['light'] = fighter.current_move != 'air_light'
        state['heavy'] = fighter.current_move == 'air_light' and fighter.move_connected
        state['special'] = fighter.current_move == 'air_heavy' and fighter.move_connected
    state['utility'] = threatened and fighter.energy >= 25 and random.random() < .015
    state['dash'] = abs(dx) > 200 and random.random() < .025
    state['jump'] = abs(dx) > 200 and random.random() < .008
    return state


def battle(p1_index, p2_index, p1_input, p2_input, cpu=False):
    p1 = Fighter(LIBRARIES[p1_index], 250, 1, p1_input)
    p2 = Fighter(LIBRARIES[p2_index], WIDTH - 320, -1, p2_input)
    projectiles, particles = [], []
    winner = None
    round_timer = 99 * FPS

    while True:
        clock.tick(FPS)
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return 'menu'
            if winner:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        return 'rematch'
                    if event.key == pygame.K_RETURN:
                        return 'select'
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0:
                        return 'rematch'
                    if event.button == 1:
                        return 'select'
        if not winner:
            state1 = p1_input.battle_state(events, p1.facing)
            state2 = cpu_state(p2, p1) if cpu else p2_input.battle_state(events, p2.facing)
            step_battle(p1, p2, projectiles, particles, state1, state2)
            round_timer -= 1
            if p1.hp <= 0 or p2.hp <= 0 or round_timer <= 0:
                if p1.hp == p2.hp:
                    winner = 'DRAW'
                elif p1.hp > p2.hp:
                    winner = f'P1 {p1.name}'
                else:
                    winner = f'{"CPU" if cpu else "P2"} {p2.name}'

        draw_background()
        draw_combat_hud(p1, p2, round_timer, 'CPU' if cpu else 'P2')
        p1.draw(screen)
        p2.draw(screen)
        for proj in projectiles:
            proj.draw(screen)
        for pt in particles:
            pt.draw(screen)
        hints = [p1_input.short_controls()] if cpu else [p1_input.short_controls(), p2_input.short_controls()]
        for line, hint in enumerate(hints):
            txt = SMALL.render(hint, True, WHITE)
            screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT - 42 + 22 * line)))
        if winner:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 165))
            screen.blit(overlay, (0, 0))
            result = 'DRAW!' if winner == 'DRAW' else f'{winner} WINS!'
            txt = TITLE.render(result, True, YELLOW)
            screen.blit(txt, txt.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 35)))
            msg = FONT.render('R = Rematch   Enter = Select   ESC = Main Menu', True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45)))
        draw_back_to_menu_button(battle=True)
        pygame.display.flip()


def battle_single_player(player_index):
    choices = [i for i in range(len(LIBRARIES)) if i != player_index]
    return battle(player_index, random.choice(choices),
                  InputDevice('keyboard1', label='Keyboard'),
                  InputDevice('cpu', label='CPU'), cpu=True)
