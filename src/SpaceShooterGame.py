"""
space_shooter_full.py
Gelişmiş Space Shooter:
- Player sprite (ve yoksa fallback drawing)
- Mermi cooldown
- Double-shot + slow + extra life powerups
- Powerup animasyonu
- Düşman dalgalari, zamanla hizlanma
- Boss düşmani (her birkaç level'da)
- Patlama animasyonlari
- Level & score & lives & HUD
- Basit ses yönetimi (assets varsa çalar; yoksa sessizce geçer)
"""

import pygame
import random
import math
from collections import deque

# ---------- Settings ----------
WIDHT, HEIGHT = 900, 700
FPS = 60

# Gameplay tuning


INITIAL_SPAWN_RATE_MS = 1400
MIN_SPAWN_RATE_MS = 350
SPAWN_DECREASE_PER_LEVEL = 80  # ms less per level
ENEMY_BASE_SPEED = 1.5
ENEMY_SPEED_INCREASE_PER_LEVEL = 0.35
POWERUP_CHANCE = 0.12  # %12 chance when enemy spawned
DOUBLE_SHOT_DURATION_MS = 6000
SLOW_DURATION_MS = 4000
BULLET_COOLDOWN_MS = 300  # base cooldown (can be lowered by powerups / upgrades)
BOSS_EVERY_N_LEVELS = 4

ASSET_PATH = "assets/"  # optional, sa sadece varsa kullan

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Advanced Space Shooter")
clock = pygame.time.Clock()
font_small = pygame.font.SysFont("arial", 20)
font_big = pygame.font.SysFont("arial", 40)

# ---------- Sound loader (optional) ----------
def try_load_sound(fname):
    try:
        return pygame.mixer.Sound(ASSET_PATH + fname)
    except Exception:
        return None

sound_shot = try_load_sound("laser.wav")
sound_explosion = try_load_sound("explosion.wav")
sound_power = try_load_sound("powerup.wav")
sound_boss = try_load_sound("boss.wav")
# background music optional (loop)
try:
    pygame.mixer.music.load(ASSET_PATH + "background.wav")
    pygame.mixer.music.play(-1)
except Exception:
    pass