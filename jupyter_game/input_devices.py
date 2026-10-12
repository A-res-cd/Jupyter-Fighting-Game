import pygame
from .combat_input import COMMANDS, CommandDetector

class InputDevice:
    def __init__(self, kind, joystick=None, label=None):
        self.kind = kind
        self.joystick = joystick
        self.label = label or kind
        self.sequences = {action: 0 for action in COMMANDS}
        self.commands = CommandDetector()
        self.down_held = False
        self.command_serial = 0
        self.command_history = []

    def holding_down(self):
        keys = pygame.key.get_pressed()
        if self.kind == 'keyboard1':
            return bool(keys[pygame.K_s])
        if self.kind == 'keyboard2':
            return bool(keys[pygame.K_DOWN])
        if self.kind == 'gamepad' and self.joystick:
            hat = self.joystick.get_numhats() and self.joystick.get_hat(0)[1] < 0
            axis = self.joystick.get_numaxes() > 1 and self.joystick.get_axis(1) > .5
            return bool(hat or axis)
        return False

    def move_x(self):
        keys = pygame.key.get_pressed()
        if self.kind == "keyboard1":
            return (-1 if keys[pygame.K_a] else 0) + (1 if keys[pygame.K_d] else 0)
        if self.kind == "keyboard2":
            return (-1 if keys[pygame.K_LEFT] else 0) + (1 if keys[pygame.K_RIGHT] else 0)
        if self.kind == "gamepad" and self.joystick:
            if self.joystick.get_numhats() > 0:
                hx, _ = self.joystick.get_hat(0)
                if hx:
                    return hx
            x = self.joystick.get_axis(0) if self.joystick.get_numaxes() > 0 else 0
            if abs(x) < 0.25:
                return 0
            return -1 if x < 0 else 1
        return 0

    def guarding(self):
        keys = pygame.key.get_pressed()
        if self.kind == "keyboard1":
            return keys[pygame.K_LSHIFT]
        if self.kind == "keyboard2":
            return keys[pygame.K_RSHIFT]
        if self.kind == "gamepad" and self.joystick:
            for btn in (4,):
                if btn < self.joystick.get_numbuttons() and self.joystick.get_button(btn):
                    return True
        return False

    def event_action(self, event):
        if event.type == pygame.KEYDOWN:
            if self.kind == "keyboard1":
                return {
                    pygame.K_a: "left", pygame.K_d: "right", pygame.K_w: "up",
                    pygame.K_s: "down", pygame.K_j: "attack", pygame.K_k: "special",
                    pygame.K_RETURN: "confirm", pygame.K_ESCAPE: "back",
                }.get(event.key)
            if self.kind == "keyboard2":
                return {
                    pygame.K_LEFT: "left", pygame.K_RIGHT: "right", pygame.K_UP: "up",
                    pygame.K_DOWN: "down", pygame.K_n: "attack", pygame.K_m: "special",
                    pygame.K_RCTRL: "confirm",
                }.get(event.key)

        if self.kind == "gamepad" and self.joystick:
            iid = self.joystick.get_instance_id()
            if event.type == pygame.JOYBUTTONDOWN and event.instance_id == iid:
                return {0: "jump", 1: "back", 2: "attack", 3: "special", 7: "confirm"}.get(event.button)
            if event.type == pygame.JOYHATMOTION and event.instance_id == iid:
                x, y = event.value
                if x < 0: return "left"
                if x > 0: return "right"
                if y > 0: return "up"
                if y < 0: return "down"
        return None

    def battle_state(self, events, facing=1):
        """Held directions/guard plus persistent counters for discrete presses."""
        self.commands.tick()
        down = self.down_held
        sampled_down = self.holding_down()
        move = self.move_x()
        saw_down_event = False
        down_key = pygame.K_s if self.kind == 'keyboard1' else pygame.K_DOWN
        down_events = any(
            (self.kind in ('keyboard1', 'keyboard2') and
             event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key == down_key)
            or (self.kind == 'gamepad' and self.joystick and
                getattr(event, 'instance_id', None) == self.joystick.get_instance_id() and
                (event.type == pygame.JOYHATMOTION or
                 (event.type == pygame.JOYAXISMOTION and event.axis == 1)))
            for event in events)
        if not down_events:
            down = sampled_down
            if down and not self.down_held:
                self.commands.down_pressed()
        for event in events:
            action = self.event_action(event)
            if action == 'attack':
                action = 'light'
            if action == 'up':
                action = 'jump'
            if event.type == pygame.KEYDOWN:
                heavy_key = pygame.K_l if self.kind == 'keyboard1' else pygame.K_COMMA
                dash_key = pygame.K_i if self.kind == 'keyboard1' else pygame.K_PERIOD
                if self.kind in ('keyboard1', 'keyboard2') and event.key == heavy_key:
                    action = 'heavy'
                if self.kind in ('keyboard1', 'keyboard2') and event.key == dash_key:
                    action = 'dash'
            if self.kind in ('keyboard1', 'keyboard2'):
                down_key = pygame.K_s if self.kind == 'keyboard1' else pygame.K_DOWN
                left_key = pygame.K_a if self.kind == 'keyboard1' else pygame.K_LEFT
                right_key = pygame.K_d if self.kind == 'keyboard1' else pygame.K_RIGHT
                if event.type in (pygame.KEYDOWN, pygame.KEYUP):
                    if event.key == down_key:
                        pressed = event.type == pygame.KEYDOWN
                        if pressed and not down:
                            self.commands.down_pressed()
                        down = pressed
                        saw_down_event = True
                    if event.key in (left_key, right_key):
                        move = (-1 if event.key == left_key else 1) if event.type == pygame.KEYDOWN else 0
            if (self.kind == 'gamepad' and self.joystick and
                    event.type == pygame.JOYBUTTONDOWN and
                    event.instance_id == self.joystick.get_instance_id() and event.button == 1):
                action = 'heavy'
            if self.kind == 'gamepad' and self.joystick and getattr(event, 'instance_id', None) == self.joystick.get_instance_id():
                if event.type == pygame.JOYBUTTONDOWN and event.button == 5:
                    action = 'dash'
                if event.type == pygame.JOYHATMOTION or (event.type == pygame.JOYAXISMOTION and event.axis == 1):
                    pressed = event.value[1] < 0 if event.type == pygame.JOYHATMOTION else event.value > .5
                    if pressed and not down:
                        self.commands.down_pressed()
                    down = pressed
                    saw_down_event = True
            action = self.commands.detect(action, down, move == facing)
            if action in self.sequences:
                self.sequences[action] += 1
                self.command_serial += 1
                self.command_history.append((self.command_serial, action))
                self.command_history = self.command_history[-32:]
        self.down_held = down if saw_down_event else sampled_down
        return dict(left=move < 0, right=move > 0, down=self.down_held, guard=bool(self.guarding()),
                    commands=list(self.command_history),
                    **{a + '_seq': n for a, n in self.sequences.items()})

    def short_controls(self):
        if self.kind == "keyboard1":
            return "AD Move W Jump S Down Shift Guard J Light L Heavy K Special I Dash"
        if self.kind == "keyboard2":
            return "Arrows | N Light , Heavy M Special RShift Guard . Dash"
        return "Stick | A Jump X Light B Heavy Y Special LB Guard RB Dash"


def detect_devices():
    pygame.joystick.quit()
    pygame.joystick.init()
    pads = []
    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        pads.append(js)

    if len(pads) >= 2:
        return (
            InputDevice("gamepad", pads[0], f"Controller 1: {pads[0].get_name()}"),
            InputDevice("gamepad", pads[1], f"Controller 2: {pads[1].get_name()}"),
        )
    if len(pads) == 1:
        return (
            InputDevice("keyboard1", label="Keyboard 1"),
            InputDevice("gamepad", pads[0], f"Controller: {pads[0].get_name()}"),
        )
    return (
        InputDevice("keyboard1", label="Keyboard 1"),
        InputDevice("keyboard2", label="Keyboard 2"),
    )
