import pygame

class InputDevice:
    def __init__(self, kind, joystick=None, label=None):
        self.kind = kind
        self.joystick = joystick
        self.label = label or kind

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
            return keys[pygame.K_s]
        if self.kind == "keyboard2":
            return keys[pygame.K_DOWN]
        if self.kind == "gamepad" and self.joystick:
            for btn in (4, 1):
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

    def short_controls(self):
        if self.kind == "keyboard1":
            return "WASD | J Attack | K Special"
        if self.kind == "keyboard2":
            return "Arrows | N Attack | M Special"
        return "Stick/D-pad | A Jump | X Attack | Y Special"


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
