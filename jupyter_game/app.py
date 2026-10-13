import pygame
import sys
import random

from jupyter_game.ui.menus import main_menu, single_player_select, device_screen, select_screen
from jupyter_game.input.devices import detect_devices
from jupyter_game.modes.local import battle, battle_single_player
from jupyter_game.modes.online import run_online_multiplayer
from jupyter_game.ui.settings import settings_screen
from jupyter_game.data.roster import LIBRARIES

def main():
    while True:
        choice = main_menu()

        if choice == "QUIT":
            pygame.quit()
            sys.exit()

        if choice == 'SETTINGS':
            settings_screen()
            continue
        if choice == 'TRAINING':
            from jupyter_game.modes.training import training
            index = single_player_select('TRAINING')
            if index is not None:
                training(index)
            continue

        if choice == "SINGLE PLAYER":
            return_to_menu = False

            while not return_to_menu:
                player_index = single_player_select()

                if player_index is None:
                    break

                opponent_index = random.choice([i for i in range(len(LIBRARIES)) if i != player_index])

                while True:
                    result = battle_single_player(player_index, opponent_index)

                    if result == "rematch":
                        continue
                    if result == "select":
                        break
                    if result == "menu":
                        return_to_menu = True
                        break

        elif choice == "ONLINE MULTIPLAYER":
            run_online_multiplayer()

        elif choice == "MULTIPLAYER":
            return_to_menu = False

            while not return_to_menu:
                p1_input, p2_input = detect_devices()

                device_action = device_screen(p1_input, p2_input)

                if device_action == "redetect":
                    continue
                if device_action == "menu":
                    return_to_menu = True
                    break

                while True:
                    selection = select_screen(p1_input, p2_input)

                    if selection is None:
                        return_to_menu = True
                        break

                    p1_index, p2_index = selection

                    while True:
                        result = battle(
                            p1_index,
                            p2_index,
                            p1_input,
                            p2_input
                        )

                        if result == "rematch":
                            continue
                        if result == "menu":
                            return_to_menu = True
                            break

                        # "select" returns to multiplayer character selection.
                        break

                    if return_to_menu:
                        break
