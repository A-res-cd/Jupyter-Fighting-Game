import pygame

pygame.init()
pygame.joystick.init()

WIDTH, HEIGHT = 1280, 720
FPS = 60
GROUND_Y = 600

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jupyter - Python Library Brawl")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("consolas", 24)
SMALL = pygame.font.SysFont("consolas", 18)
BIG = pygame.font.SysFont("consolas", 54, bold=True)
TITLE = pygame.font.SysFont("consolas", 72, bold=True)

WHITE = (245, 245, 245)
BLACK = (18, 18, 22)
GRAY = (110, 115, 125)
RED = (220, 60, 70)
GREEN = (65, 210, 110)
BLUE = (70, 130, 255)
YELLOW = (255, 215, 80)
CYAN = (80, 220, 240)
ORANGE = (245, 130, 50)
