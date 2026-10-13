"""Small generated audio cues; gracefully disabled without an audio device."""
from array import array
import math
import pygame
from jupyter_game.core.settings import preferences

_sounds = {}


def cue(kind):
    if not preferences['sound'] or not pygame.mixer.get_init():
        return
    try:
        if kind not in _sounds:
            rate, fmt, channels = pygame.mixer.get_init()
            if fmt != -16:
                return
            frequency = dict(hit=180, guard=300, parry=880, attack=440, round=660).get(kind, 440)
            length = int(rate * .065)
            samples = array('h')
            for i in range(length):
                value = int(2800 * (1 - i / length) * math.sin(2 * math.pi * frequency * i / rate))
                samples.extend([value] * channels)
            _sounds[kind] = pygame.mixer.Sound(buffer=samples.tobytes())
        _sounds[kind].play()
    except pygame.error:
        pass
