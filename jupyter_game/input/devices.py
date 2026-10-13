import pygame
from jupyter_game.input.commands import COMMANDS, CommandDetector
from jupyter_game.core.settings import preferences

class InputDevice:
    def __init__(self, kind, joystick=None, label=None):
        self.kind = kind
        self.joystick = joystick
        self.instance_id = joystick.get_instance_id() if joystick else None
        self.label = label or kind
        self.sequences = {action: 0 for action in COMMANDS}
        self.commands = CommandDetector()
        self.down_held = False
        self.command_serial = 0
        self.command_history = []
        self.bindings = dict(preferences['bindings'].get(kind, {}))

    def reset(self, keep_serial=False):
        serial = self.command_serial if keep_serial else 0
        self.commands = CommandDetector()
        self.down_held = False
        self.command_history = []
        self.command_serial = serial
        self.sequences = {action: 0 for action in COMMANDS}

    def advance_time(self, frames=1):
        self.commands.tick(frames)

    def connected(self):
        if self.kind != 'gamepad':
            return True
        try:
            return self.joystick is not None and self.joystick.get_init()
        except pygame.error:
            return False

    def holding_down(self):
        keys = pygame.key.get_pressed()
        if self.kind == 'keyboard1':
            return bool(keys[self.bindings['down']])
        if self.kind == 'keyboard2':
            return bool(keys[self.bindings['down']])
        if self.kind == 'gamepad' and self.joystick:
            hat = self.joystick.get_numhats() and self.joystick.get_hat(0)[1] < 0
            axis = self.joystick.get_numaxes() > 1 and self.joystick.get_axis(1) > preferences['deadzone']
            return bool(hat or axis)
        return False

    def move_x(self):
        keys = pygame.key.get_pressed()
        if self.kind == "keyboard1":
            return (-1 if keys[self.bindings['left']] else 0) + (1 if keys[self.bindings['right']] else 0)
        if self.kind == "keyboard2":
            return (-1 if keys[self.bindings['left']] else 0) + (1 if keys[self.bindings['right']] else 0)
        if self.kind == "gamepad" and self.joystick:
            if self.joystick.get_numhats() > 0:
                hx, _ = self.joystick.get_hat(0)
                if hx:
                    return hx
            x = self.joystick.get_axis(0) if self.joystick.get_numaxes() > 0 else 0
            if abs(x) < preferences['deadzone']:
                return 0
            return -1 if x < 0 else 1
        return 0

    def guarding(self):
        keys = pygame.key.get_pressed()
        if self.kind == "keyboard1":
            return keys[self.bindings['guard']]
        if self.kind == "keyboard2":
            return keys[self.bindings['guard']]
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
            iid = self.instance_id
            if event.type == pygame.JOYBUTTONDOWN and event.instance_id == iid:
                return {0: "jump", 1: "back", 2: "attack", 3: "special", 7: "confirm"}.get(event.button)
            if event.type == pygame.JOYHATMOTION and event.instance_id == iid:
                x, y = event.value
                if x < 0: return "left"
                if x > 0: return "right"
                if y > 0: return "up"
                if y < 0: return "down"
        return None

    def battle_state(self, events, facing=1, advance=True):
        """Held directions/guard plus persistent counters for discrete presses."""
        if advance:
            self.commands.tick()
        down = self.down_held
        sampled_down = self.holding_down()
        move = self.move_x()
        saw_down_event = False
        down_key = self.bindings.get('down', pygame.K_DOWN)
        down_events = any(
            (self.kind in ('keyboard1', 'keyboard2') and
             event.type in (pygame.KEYDOWN, pygame.KEYUP) and event.key == down_key)
            or (self.kind == 'gamepad' and self.joystick and
             getattr(event, 'instance_id', None) == self.instance_id and
                (event.type == pygame.JOYHATMOTION or
                 (event.type == pygame.JOYAXISMOTION and event.axis == 1)))
            for event in events)
        if not down_events:
            down = sampled_down
            if down and not self.down_held:
                self.commands.down_pressed()
        for event in events:
            action = self.event_action(event)
            if self.kind in ('keyboard1', 'keyboard2') and event.type == pygame.KEYDOWN:
                action = next((a for a, k in self.bindings.items() if k == event.key), None)
            if action == 'attack':
                action = 'light'
            if action == 'up':
                action = 'jump'
            if event.type == pygame.KEYDOWN:
                heavy_key = self.bindings.get('heavy')
                dash_key = self.bindings.get('dash')
                if self.kind in ('keyboard1', 'keyboard2') and event.key == heavy_key:
                    action = 'heavy'
                if self.kind in ('keyboard1', 'keyboard2') and event.key == dash_key:
                    action = 'dash'
            if self.kind in ('keyboard1', 'keyboard2'):
                down_key = self.bindings['down']
                left_key = self.bindings['left']
                right_key = self.bindings['right']
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
                    event.instance_id == self.instance_id and event.button == 1):
                action = 'heavy'
            if self.kind == 'gamepad' and self.joystick and getattr(event, 'instance_id', None) == self.instance_id:
                if event.type == pygame.JOYBUTTONDOWN and event.button == 5:
                    action = 'dash'
                if event.type == pygame.JOYHATMOTION or (event.type == pygame.JOYAXISMOTION and event.axis == 1):
                    pressed = event.value[1] < 0 if event.type == pygame.JOYHATMOTION else event.value > preferences['deadzone']
                    if pressed and not down:
                        self.commands.down_pressed()
                    down = pressed
                    saw_down_event = True
            action = self.commands.detect(action, down, move == facing)
            if action in self.sequences:
                self.sequences[action] += 1
                self.command_serial += 1
                self.command_history.append((self.command_serial, action))
                self.command_history = self.command_history[-256:]
        self.down_held = down if saw_down_event else sampled_down
        return dict(left=move < 0, right=move > 0, down=self.down_held, guard=bool(self.guarding()),
                    commands=list(self.command_history),
                    **{a + '_seq': n for a, n in self.sequences.items()})

    def short_controls(self):
        if self.bindings:
            return '  '.join(f'{pygame.key.name(self.bindings[a])}: {a}' for a in ('left', 'right', 'jump', 'light', 'heavy', 'special', 'guard', 'dash'))
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


def preferred_device():
    if preferences['input'] == 'controller':
        pygame.joystick.init()
        if pygame.joystick.get_count():
            js = pygame.joystick.Joystick(0)
            js.init()
            return InputDevice('gamepad', js, js.get_name())
    return InputDevice('keyboard1', label='Keyboard')
