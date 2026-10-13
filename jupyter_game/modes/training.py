"""Practice uses the same combat simulation, with isolated dummy options."""
import pygame
import sys
from jupyter_game.core.config import *
from jupyter_game.combat.entities import Fighter
from jupyter_game.data.roster import LIBRARIES
from jupyter_game.input.devices import InputDevice, preferred_device
from jupyter_game.combat.moves import step_battle
from jupyter_game.core.timing import FixedClock
from jupyter_game.ui.rendering import draw_background, draw_combat_hud, draw_back_to_menu_button, back_clicked, draw_overlay


class Training:
    behaviors = ('idle', 'guard', 'timed attack', 'jump')

    def __init__(self, index, device=None):
        self.index = index
        self.device = device or InputDevice('keyboard1')
        self.behavior = 0
        self.infinite_energy = True
        self.hitboxes = True
        self.reset()

    def reset(self):
        self.device.reset()
        self.p1 = Fighter(LIBRARIES[self.index], 430, 1, self.device)
        self.p2 = Fighter(LIBRARIES[0], 510, -1, InputDevice('cpu'))
        self.p2.hp = self.p2.max_hp = 10000
        self.projectiles, self.particles = [], []
        self.frame = self.combo_damage = self.last_damage = 0
        self.history = []
        self.last_id = 0
        self.drill_combo = self.drill_parry = False
        self.parry_at = None

    def step(self, state):
        self.frame += 1
        for serial, action in state.get('commands', []):
            if serial > self.last_id:
                self.history.append(action)
                self.history = self.history[-8:]
                self.last_id = serial
        if self.infinite_energy:
            self.p1.energy = 100
        behavior = self.behaviors[self.behavior]
        dummy = dict(guard=behavior == 'guard', light=behavior == 'timed attack' and self.frame % 90 == 1,
                     jump=behavior == 'jump' and self.frame % 90 == 1)
        self.p2.facing = -1 if self.p2.rect.centerx > self.p1.rect.centerx else 1
        hp = self.p2.hp
        previous_notice_timer = self.p1.notice_timer
        step_battle(self.p1, self.p2, self.projectiles, self.particles, state, dummy)
        if 'PARRY' in self.p1.notice and self.p1.notice_timer > previous_notice_timer:
            self.parry_at = self.frame
        damage = hp - self.p2.hp
        if damage:
            self.combo_damage = damage if self.p1.combo_count <= 1 else self.combo_damage + damage
            self.last_damage = self.combo_damage
        elif self.p1.combo_count == 0:
            self.combo_damage = 0
        self.drill_combo |= self.p1.combo_count >= 5
        self.drill_parry |= bool(damage and self.parry_at is not None and self.frame - self.parry_at <= 36)
        self.p1.hp = self.p1.max_hp
        self.p2.hp = self.p2.max_hp
        self.p1.show_hitboxes = self.p2.show_hitboxes = self.hitboxes


def training(index):
    session = Training(index, preferred_device())
    timer = FixedClock()
    move_list = False
    disconnected = False
    while True:
        elapsed = clock.tick(FPS) / 1000
        events = pygame.event.get()
        reset = False
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if back_clicked(event, True) or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                return
            if event.type == pygame.JOYDEVICEREMOVED and session.device.kind == 'gamepad' and event.instance_id == session.device.instance_id:
                disconnected = True
            if event.type == pygame.KEYDOWN:
                if disconnected and event.key == pygame.K_k:
                    session.device = InputDevice('keyboard1')
                    disconnected = False
                    reset = True
                if event.key == pygame.K_F5:
                    reset = True
                if event.key == pygame.K_F6:
                    session.behavior = (session.behavior + 1) % len(session.behaviors)
                if event.key == pygame.K_F7:
                    session.infinite_energy = not session.infinite_energy
                if event.key == pygame.K_F8:
                    session.hitboxes = not session.hitboxes
                if event.key == pygame.K_TAB:
                    move_list = not move_list
                    session.device.reset(keep_serial=True)
                    session.p1.input_buffer.clear()
                    timer.reset()
        if reset:
            session.reset()
            timer.reset()
            events = []
        if not move_list and not disconnected:
            state = session.device.battle_state(events, session.p1.facing, advance=False)
            for _ in range(timer.steps(elapsed)):
                session.device.advance_time()
                session.step(state)
        draw_background()
        draw_combat_hud(session.p1, session.p2, 99 * FPS, 'DUMMY')
        for item in (session.p1, session.p2, *session.projectiles, *session.particles):
            item.draw(screen)
        lines = [f'TRAINING | Dummy: {session.behaviors[session.behavior]} | Infinite energy: {session.infinite_energy}',
                 f'Combo damage: {session.last_damage} | Inputs: {" > ".join(session.history[-5:])}',
                 f'Air combo drill: {"DONE" if session.drill_combo else "low > heavy > air light > heavy > special"}',
                 f'Parry punish: {"DONE" if session.drill_parry else "F6 attacking dummy; tap guard, release, then Light"}']
        if session.p1.current_move:
            move = session.p1.moves[session.p1.current_move]
            lines.append(f'{move.name}: startup {move.startup} / active {move.active} / recovery {move.recovery} | frame {session.p1.move_frame}')
        for i, line in enumerate(lines):
            screen.blit(SMALL.render(line, True, WHITE), (55, 270 + i * 25))
        screen.blit(SMALL.render('F5 Reset | F6 Dummy | F7 Energy | F8 Hitboxes | Tab Move list | Esc Menu', True, CYAN), (300, 650))
        draw_back_to_menu_button(True)
        if move_list:
            draw_overlay('')
            title = BIG.render('MOVE LIST', True, YELLOW)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, 40)))
            for i, (key, move) in enumerate(session.p1.moves.items()):
                text = SMALL.render(f'{key}: {move.name} | {move.startup}/{move.active}/{move.recovery} | energy {move.energy_cost}', True, WHITE)
                screen.blit(text, (300, 80 + i * 38))
            screen.blit(SMALL.render('Down+Light low | Down+Heavy launcher | Forward+Heavy advancing heavy', True, CYAN), (250, 560))
            screen.blit(SMALL.render('Down,Special rising special | Down,Down,Special utility', True, CYAN), (320, 585))
            screen.blit(SMALL.render('Tab closes move list', True, YELLOW), (480, 620))
        if disconnected:
            draw_overlay('CONTROLLER DISCONNECTED', ['K = Switch to keyboard | Esc = Menu'])
        pygame.display.flip()
