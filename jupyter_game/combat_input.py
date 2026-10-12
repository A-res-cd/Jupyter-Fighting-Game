"""Capture directional commands at button press, before input buffering/networking."""
COMMANDS = ('light', 'heavy', 'special', 'jump', 'low', 'launcher',
            'forward_heavy', 'directional_special', 'utility', 'dash')


class CommandDetector:
    def __init__(self):
        self.frame = 0
        self.down_taps = []

    def tick(self):
        self.frame += 1
        self.down_taps = [f for f in self.down_taps if self.frame - f <= 18]

    def down_pressed(self):
        self.down_taps.append(self.frame)
        self.down_taps = self.down_taps[-2:]

    def detect(self, action, down=False, forward=False):
        if action == 'light' and down:
            return 'low'
        if action == 'heavy':
            return 'launcher' if down else 'forward_heavy' if forward else 'heavy'
        if action == 'special' and self.down_taps:
            result = 'utility' if len(self.down_taps) >= 2 else 'directional_special'
            self.down_taps.clear()
            return result
        return action
