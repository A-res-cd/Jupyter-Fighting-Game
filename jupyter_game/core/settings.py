"""Validated local preferences; no dependency on display initialization."""
import json
import os
from pathlib import Path
import pygame

DEFAULT_BINDINGS = {
    'keyboard1': dict(left=pygame.K_a, right=pygame.K_d, jump=pygame.K_w,
                      down=pygame.K_s, light=pygame.K_j, heavy=pygame.K_l,
                      special=pygame.K_k, guard=pygame.K_LSHIFT, dash=pygame.K_i),
    'keyboard2': dict(left=pygame.K_LEFT, right=pygame.K_RIGHT, jump=pygame.K_UP,
                      down=pygame.K_DOWN, light=pygame.K_n, heavy=pygame.K_COMMA,
                      special=pygame.K_m, guard=pygame.K_RSHIFT, dash=pygame.K_PERIOD),
}
DEFAULTS = dict(deadzone=.25, difficulty='normal', input='keyboard', sound=True,
                bindings=DEFAULT_BINDINGS)
RESERVED_KEYS = (pygame.K_ESCAPE, pygame.K_p, pygame.K_F3, pygame.K_F5,
                 pygame.K_F6, pygame.K_F7, pygame.K_F8, pygame.K_F9, pygame.K_TAB)


def valid_binding(value):
    return (type(value) is int and 0 <= value <= 2**31 - 1 and
            value not in RESERVED_KEYS and bool(pygame.key.name(value)))


def settings_path():
    override = os.environ.get('JUPYTER_SETTINGS_PATH')
    if override:
        return Path(override)
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'JupyterBrawl' / 'settings.json'


def load_settings(path=None):
    result = json.loads(json.dumps(DEFAULTS))
    try:
        data = json.loads(Path(path or settings_path()).read_text(encoding='utf-8'))
        if not isinstance(data, dict):
            return result
        if isinstance(data.get('deadzone'), (int, float)) and .1 <= data['deadzone'] <= .8:
            result['deadzone'] = data['deadzone']
        for key, choices in (('difficulty', ('easy', 'normal', 'hard')), ('input', ('keyboard', 'controller'))):
            if data.get(key) in choices:
                result[key] = data[key]
        if isinstance(data.get('sound'), bool):
            result['sound'] = data['sound']
        for kind, defaults in DEFAULT_BINDINGS.items():
            candidate = data.get('bindings', {}).get(kind, {}) if isinstance(data.get('bindings'), dict) else {}
            if isinstance(candidate, dict):
                values = {k: candidate.get(k, v) for k, v in defaults.items()}
                if all(valid_binding(v) for v in values.values()) and len(set(values.values())) == len(values):
                    result['bindings'][kind] = values
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return result


def save_settings(data, path=None):
    target = Path(path or settings_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2), encoding='utf-8')
    temporary.replace(target)


preferences = load_settings()
