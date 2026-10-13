"""Character move overrides. Execution stays in the generic fighter engine."""
from dataclasses import replace


PROFILES = {
    'Pandas': {
        'names': ('Series Jab', 'Index Crush', 'DataFrame Slam', 'Row Sweep',
                  'Pivot Launch', 'Join Advance', 'Air Series', 'Column Drop',
                  'Air DataFrame', 'GroupBy Smash', 'Schema Guard', 'Index Dash'),
        'stagger': 1.2, 'startup': 1,
        'changes': {
            'special': dict(projectile=False, reach=140, guard_damage=28, damage=29),
            'directional_special': dict(projectile=False, reach=110, launch_velocity=-13,
                                        self_launch=-11, guard_damage=24),
            'utility': dict(dash_speed=0, invulnerable_frames=0, guard_frames=20,
                            parry_frames=4, active=20, recovery=18),
        },
    },
    'PyTorch': {
        'names': ('Tensor Jab', 'Gradient Kick', 'Tensor Flame', 'Autograd Sweep',
                  'Backward Launch', 'Graph Advance', 'Air Tensor', 'Gradient Drop',
                  'Air Tensor Flame', 'Flame Fan', 'Graph Escape', 'Tensor Dash'),
        'stagger': 1.1, 'startup': 0,
        'changes': {
            'special': dict(projectile_speed=14, damage=27),
            'directional_special': dict(projectile_count=3, projectile_spread=30,
                                        projectile_vy=-2, damage=15, stagger_damage=12),
            'air_special': dict(projectile_vy=4, projectile_speed=12),
            'utility': dict(dash_speed=8, invulnerable_frames=12, recovery=22),
        },
    },
    'Requests': {
        'names': ('GET Jab', 'POST Kick', 'HTTP Rush', 'Header Sweep',
                  'Redirect Launch', 'Request Advance', 'Air GET', 'Response Drop',
                  'Air HTTP', 'Retry Rush', 'Timeout Escape', 'Keepalive Dash'),
        'stagger': .8, 'startup': -1,
        'changes': {
            'special': dict(projectile=False, dash_speed=8, active=5, reach=85, damage=24),
            'directional_special': dict(projectile=False, dash_speed=9, active=5,
                                        reach=90, launch_velocity=-10, self_launch=-9),
            'utility': dict(dash_speed=-14, invulnerable_frames=10),
            'dash': dict(dash_speed=13),
        },
    },
    'NumPy': {
        'names': ('Vector Jab', 'Matrix Kick', 'Array Burst', 'Scalar Sweep',
                  'Axis Launch', 'Matrix Advance', 'Air Vector', 'Air Matrix',
                  'Air Array Burst', 'Axis Burst', 'Axis Dash', 'Vector Dash'),
        'stagger': 1, 'startup': 0,
        'changes': {
            'directional_special': dict(projectile_count=3, projectile_spread=24, damage=20),
            'utility': dict(dash_speed=12, invulnerable_frames=8),
        },
    },
    'TensorFlow': {
        'names': ('Tensor Smash', 'Layer Crush', 'Neural Network', 'Tensor Sweep',
                  'Gradient Launch', 'Layer Advance', 'Air Tensor', 'Gradient Drop',
                  'Air Neural Network', 'Gradient Slam', 'Layer Guard', 'Tensor Dash'),
        'stagger': 1.45, 'startup': 3,
        'changes': {
            'directional_special': dict(projectile=False, launch_velocity=-14,
                                        self_launch=-11, reach=105, damage=28),
            'utility': dict(dash_speed=0, invulnerable_frames=0, guard_frames=18,
                            parry_frames=6, active=18, recovery=14),
            'dash': dict(dash_speed=7),
            'air_heavy': dict(damage=19, stagger_damage=22, juggle_velocity=3),
        },
    },
    'FastAPI': {
        'names': ('Async Jab', 'Endpoint Kick', 'Async Blitz', 'Await Sweep',
                  'Coroutine Launch', 'Endpoint Rush', 'Air Async', 'Endpoint Drop',
                  'Air Async Blitz', 'Coroutine Rush', 'Coroutine Dash', 'Async Dash'),
        'stagger': .7, 'startup': -2,
        'changes': {
            'special': dict(projectile=False, dash_speed=10, reach=100, damage=22),
            'directional_special': dict(projectile=False, dash_speed=12, reach=100,
                                        launch_velocity=0, damage=20),
            'utility': dict(dash_speed=18, invulnerable_frames=9),
            'dash': dict(dash_speed=14),
        },
    },
}


def tune_moves(name, moves):
    profile = PROFILES.get(name)
    if not profile:
        return moves
    result = {}
    for key, move_name in zip(moves, profile['names']):
        move = moves[key]
        changes = profile['changes'].get(key, {})
        tuned = replace(move, name=move_name,
                        startup=max(2, move.startup + profile['startup']) if not move.utility else move.startup,
                        stagger_damage=move.stagger_damage * profile['stagger'])
        result[key] = replace(tuned, **changes)
    return result
