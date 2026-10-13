import random
import sys
import pygame

from jupyter_game.core.config import *
from jupyter_game.input.devices import InputDevice, preferred_device
from jupyter_game.combat.match import Match
from jupyter_game.combat.cpu import CPU
from jupyter_game.core.settings import preferences
from jupyter_game.core.timing import FixedClock, FrameMetrics
from jupyter_game.ui.rendering import draw_match, draw_overlay, draw_back_to_menu_button, back_clicked


def cpu_state(fighter, opponent):
    if not hasattr(fighter, '_cpu'):
        fighter._cpu = CPU(preferences['difficulty'])
    return fighter._cpu.state(fighter, opponent)


def battle(p1_index, p2_index, p1_input, p2_input, cpu=False):
    match = Match((p1_index, p2_index), (p1_input, p2_input))
    timer, metrics = FixedClock(), FrameMetrics()
    paused = confirm_quit = disconnected = debug = False
    previous_round = match.round
    policy = CPU(preferences['difficulty'])
    while True:
        elapsed = clock.tick(FPS) / 1000
        metrics.begin()
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.JOYDEVICEREMOVED:
                if any(d.kind == 'gamepad' and d.instance_id == event.instance_id for d in match.devices):
                    paused = disconnected = True
            key = event.key if event.type == pygame.KEYDOWN else None
            if key == pygame.K_F3:
                debug = not debug
            if match.phase == 'match_end':
                if key == pygame.K_r or (event.type == pygame.JOYBUTTONDOWN and event.button == 0):
                    return 'rematch'
                if key == pygame.K_RETURN or (event.type == pygame.JOYBUTTONDOWN and event.button == 1):
                    return 'select'
            if key == pygame.K_ESCAPE or back_clicked(event, battle=True):
                if match.phase == 'match_end':
                    return 'menu'
                if confirm_quit:
                    confirm_quit = False
                elif paused:
                    confirm_quit = True
                else:
                    paused = True
                match.clear_inputs()
                timer.reset()
            if paused:
                if key == pygame.K_q:
                    confirm_quit = True
                if confirm_quit and key == pygame.K_y:
                    return 'menu'
                if confirm_quit and key == pygame.K_n:
                    confirm_quit = False
                if disconnected and key == pygame.K_k:
                    match.devices = tuple(InputDevice('keyboard1' if i == 0 else 'keyboard2') if d.kind == 'gamepad' else d for i, d in enumerate(match.devices))
                    p1_input, p2_input = match.devices
                    disconnected = False
                if not disconnected and not confirm_quit and (key in (pygame.K_p, pygame.K_RETURN) or (event.type == pygame.JOYBUTTONDOWN and event.button == 7)):
                    paused = False
                    match.clear_inputs()
                    timer.reset()
                    events = []
            elif key == pygame.K_p or (event.type == pygame.JOYBUTTONDOWN and event.button == 7):
                paused = True
                match.clear_inputs()
                timer.reset()
        if not paused:
            state1 = p1_input.battle_state(events, match.p1.facing, advance=False)
            state2 = {} if cpu else p2_input.battle_state(events, match.p2.facing, advance=False)
            for _ in range(timer.steps(elapsed)):
                p1_input.advance_time()
                p2_input.advance_time()
                match.step(state1, policy.state(match.p2, match.p1) if cpu else state2)
                if match.round != previous_round:
                    previous_round = match.round
                    policy = CPU(preferences['difficulty'])
                    state1 = state2 = {}
        metrics.begin_render()
        draw_match(match, 'CPU' if cpu else 'P2')
        hint = SMALL.render(p1_input.short_controls(), True, WHITE)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 35)))
        if match.phase == 'match_end':
            draw_overlay(f'P{match.winner} WINS MATCH', ['R / A = Rematch   Enter / B = Select   Esc = Menu'])
        if paused:
            if disconnected:
                draw_overlay('CONTROLLER DISCONNECTED', ['K = Switch to keyboard', 'Q = Quit match'])
            elif confirm_quit:
                draw_overlay('QUIT MATCH?', ['Y = Quit   N = Stay'])
            else:
                draw_overlay('PAUSED', ['P / Enter / Start = Resume', 'Q = Quit match'])
        if debug:
            screen.blit(SMALL.render(metrics.label(), True, CYAN), (260, HEIGHT - 85))
        draw_back_to_menu_button(battle=True)
        pygame.display.flip()
        metrics.end()


def battle_single_player(player_index, opponent_index=None):
    from jupyter_game.data.roster import LIBRARIES
    if opponent_index is None:
        opponent_index = random.choice([i for i in range(len(LIBRARIES)) if i != player_index])
    return battle(player_index, opponent_index, preferred_device(), InputDevice('cpu'), cpu=True)
