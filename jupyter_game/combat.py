"""Frame-based, device-independent combat definitions and round simulation."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Move:
    name: str
    damage: float
    stagger_damage: float
    hitstun: int
    knockback: int
    startup: int
    active: int
    recovery: int
    guard_damage: float = 4
    reach: int = 65
    cancels: tuple = ()
    air_usable: bool = False
    knockdown: bool = False
    energy_cost: int = 0
    projectile: bool = False
    projectile_speed: int = 10
    projectile_count: int = 1
    projectile_spread: int = 0
    projectile_vy: float = 0
    launch_velocity: float = 0
    self_launch: float = 0
    juggle_velocity: float = 0
    dash_speed: float = 0
    invulnerable_frames: int = 0
    parry_frames: int = 0
    guard_frames: int = 0
    utility: bool = False
    free_cancel: bool = False
    cancel_after: int = 0
    air_only: bool = False
    hitbox_y: int = -35
    hitbox_height: int = 70

    @property
    def duration(self):
        return self.startup + self.active + self.recovery


def moves_for(data):
    """Migrate the roster through a baseline; tune three test fighters first."""
    power = data['power']
    moves = {
        'light': Move('Light', power * .65, 8, 18, 3, 5, 3, 12,
                      cancels=('light', 'heavy', 'special', 'directional_special', 'dash')),
        'heavy': Move('Heavy', power * 1.25, 18, 24, 12, 9, 4, 20,
                      guard_damage=10, reach=85, cancels=('special', 'directional_special'), knockdown=True),
        'special': Move(data['special'], power + 16, 25, 25, 24, 10, 1, 28,
                        guard_damage=15, energy_cost=50, projectile=True),
    }
    moves.update({
        'low': Move('Low Strike', power * .5, 8, 24, 2, 5, 3, 12,
                    hitbox_y=15, hitbox_height=40, cancels=('launcher', 'special')),
        'launcher': Move('Launcher', power, 22, 36, 4, 8, 4, 20,
                         launch_velocity=-12, self_launch=-11, reach=85,
                         cancels=('air_light', 'air_heavy', 'air_special')),
        'forward_heavy': replace(moves['heavy'], name='Forward Heavy', dash_speed=4),
        'air_light': Move('Air Light', power * .6, 6, 20, 2, 4, 4, 8,
                          air_usable=True, air_only=True, juggle_velocity=-4,
                          cancels=('air_heavy', 'air_special'), reach=80),
        'air_heavy': Move('Air Heavy', power * .9, 12, 22, 8, 6, 4, 16,
                          air_usable=True, air_only=True, juggle_velocity=2,
                          knockdown=True, cancels=('air_special',), reach=85),
        'air_special': replace(moves['special'], name='Air ' + data['special'],
                               air_usable=True, air_only=True, startup=5),
        'directional_special': replace(moves['special'], name='Rising ' + data['special'],
                                       projectile_vy=-4, launch_velocity=-9),
        'utility': Move('Defensive Dash', 0, 0, 0, 0, 0, 6, 16,
                        utility=True, dash_speed=10, invulnerable_frames=6, energy_cost=25),
        'dash': Move('Dash', 0, 0, 0, 0, 0, 6, 8, utility=True, dash_speed=10,
                     free_cancel=True, cancel_after=4,
                     cancels=('heavy', 'forward_heavy', 'special', 'directional_special')),
    })
    from .characters import tune_moves
    moves = tune_moves(data['name'], moves)
    return moves


COMBO_SCALING = (1, .95, .9, .82, .75, .65, .55)
INPUT_BUFFER_FRAMES = 18  # 300 ms at 60 FPS
PARRY_FRAMES = 9          # 150 ms
PERFECT_PARRY_FRAMES = 4  # first 67 ms
MAX_JUGGLE_HITS = 4


def step_battle(p1, p2, projectiles, particles, state1, state2):
    """Sample both defenses before resolving either attack (also used by host)."""
    p1.prepare(state1)
    p2.prepare(state2)
    p1.advance(p2, projectiles, particles)
    p2.advance(p1, projectiles, particles)
    for projectile in projectiles:
        if projectile.owner.hitstop:
            continue
        projectile.update()
        target = p2 if projectile.owner is p1 else p1
        if projectile.alive and projectile.rect.colliderect(target.rect):
            target.receive_hit(projectile.owner, projectile.move,
                               projectile.direction, particles)
            projectile.alive = False
    projectiles[:] = [p for p in projectiles if p.alive]
    for particle in particles:
        particle.update()
    particles[:] = [p for p in particles if p.life > 0]
