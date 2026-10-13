"""Authoritative fighter and projectile snapshot serialization."""
from jupyter_game.combat.entities import Projectile


FIGHTER_STATE_FIELDS = (
    'hp', 'energy', 'facing', 'guard', 'vel_y', 'on_ground', 'hitstun', 'flash',
    'stagger', 'staggered', 'stagger_timer', 'stagger_protected', 'parry_window',
    'parry_recovery', 'knocked_down', 'pending_knockdown', 'knockdown_timer', 'wakeup_invulnerability',
    'combo_count', 'combo_scaling', 'combo_timer', 'current_move', 'move_frame',
    'notice', 'notice_timer', 'hitstop',
    'launched', 'juggle_hits', 'juggle_exhausted', 'move_invulnerability', 'parry_duration',
)


def fighter_to_state(f):
    return dict(x=f.rect.x, y=f.rect.y,
                **{key: getattr(f, key) for key in FIGHTER_STATE_FIELDS})


def apply_fighter_state(f, state):
    if not state:
        return
    f.rect.x = int(state.get('x', f.rect.x))
    f.rect.y = int(state.get('y', f.rect.y))
    for key in FIGHTER_STATE_FIELDS:
        if key in state:
            setattr(f, key, state[key])


def projectiles_to_state(projectiles, p1):
    return [dict(owner=1 if p.owner is p1 else 2, x=p.x, y=p.y,
                 direction=p.direction, move=next(key for key, move in p.owner.moves.items() if move is p.move)) for p in projectiles]


def apply_projectiles_state(states, p1, p2):
    result = []
    for state in states:
        owner = p1 if state['owner'] == 1 else p2
        projectile = Projectile(owner, state['direction'], owner.moves[state.get('move', 'special')])
        projectile.x, projectile.y = state['x'], state['y']
        projectile.rect.center = (int(projectile.x), int(projectile.y))
        result.append(projectile)
    return result


