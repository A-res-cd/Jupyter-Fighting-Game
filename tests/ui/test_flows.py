import os
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import copy
import unittest
from unittest.mock import patch
import pygame
from jupyter_game.modes import local as local_modes, training
from jupyter_game.ui import settings as settings_ui, menus as ui
from jupyter_game import app
from jupyter_game.combat.match import Match
from jupyter_game.input.devices import InputDevice
from jupyter_game.core.settings import preferences


def key(value):
    return pygame.event.Event(pygame.KEYDOWN, key=value)


class Clock:
    def tick(self, fps):
        return 17


class UIFlows(unittest.TestCase):
    def test_cpu_rematch_keeps_opponent(self):
        with patch.object(app, 'main_menu', side_effect=['SINGLE PLAYER', 'QUIT']), patch.object(app, 'single_player_select', return_value=0), patch.object(app.random, 'choice', return_value=4) as choose, patch.object(app, 'battle_single_player', side_effect=['rematch', 'menu']) as battle, patch('pygame.quit'):
            with self.assertRaises(SystemExit):
                app.main()
        self.assertEqual([call.args for call in battle.call_args_list], [(0, 4), (0, 4)])
        choose.assert_called_once()

    def test_menu_mouse_training(self):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(600, 450))
        with patch.object(ui, 'clock', Clock()), patch('pygame.event.get', return_value=[event]):
            self.assertEqual(ui.main_menu(), 'TRAINING')

    def test_back_button_in_character_select(self):
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(40, 30))
        with patch.object(ui, 'clock', Clock()), patch('pygame.event.get', return_value=[event]):
            self.assertIsNone(ui.single_player_select())

    def test_local_pause_resume_and_quit_confirmation(self):
        match = Match((0, 4), (InputDevice('keyboard1'), InputDevice('keyboard2')))
        batches = [[], [key(pygame.K_ESCAPE)], [], [key(pygame.K_q)],
                   [key(pygame.K_n)], [key(pygame.K_p)], [],
                   [key(pygame.K_ESCAPE)], [key(pygame.K_q)], [key(pygame.K_y)]]
        ticks = []
        def events():
            ticks.append(match.tick)
            return batches.pop(0)
        with patch.object(local_modes, 'clock', Clock()), patch.object(local_modes, 'Match', return_value=match), patch('pygame.event.get', side_effect=events):
            self.assertEqual(local_modes.battle(0, 4, *match.devices), 'menu')
        self.assertEqual(ticks[2:6], [1, 1, 1, 1])
        self.assertGreater(ticks[7], ticks[5])

    def test_training_toggle_move_list_reset_exit(self):
        batches = [[], [key(pygame.K_F6)], [key(pygame.K_F7)], [key(pygame.K_F8)],
                   [key(pygame.K_TAB)], [], [key(pygame.K_TAB)], [key(pygame.K_F5)],
                   [], [key(pygame.K_ESCAPE)]]
        session = training.Training(0)
        with patch.object(training, 'clock', Clock()), patch.object(training, 'Training', return_value=session), patch('pygame.event.get', side_effect=lambda: batches.pop(0)):
            training.training(0)
        self.assertEqual(session.behavior, 1)
        self.assertFalse(session.infinite_energy)
        self.assertFalse(session.hitboxes)
        self.assertLess(session.frame, 5)

    def test_settings_rebind_save_and_exit(self):
        original = copy.deepcopy(preferences)
        batches = [[key(pygame.K_DOWN)] * 8 + [key(pygame.K_RETURN)],
                   [key(pygame.K_u)], [key(pygame.K_DOWN)] * 15 + [key(pygame.K_RETURN)],
                   [key(pygame.K_ESCAPE)]]
        try:
            with patch.object(settings_ui, 'clock', Clock()), patch.object(settings_ui, 'save_settings') as save, patch('pygame.event.get', side_effect=lambda: batches.pop(0)):
                settings_ui.settings_screen()
            self.assertEqual(preferences['bindings']['keyboard1']['light'], pygame.K_u)
            save.assert_called_once()
        finally:
            preferences.clear()
            preferences.update(original)
