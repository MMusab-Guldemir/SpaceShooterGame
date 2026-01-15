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

# ---------- Ayarlar ----------
WIDTH, HEIGHT = 900, 700
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

# ---------- Simple helpers ----------
def load_image(fname, fallback_size=(50, 40), colorkey=None):
    """Try to load image from assets; return surface (or simple rect surface)."""
    try:
        img = pygame.image.load(ASSET_PATH + fname).convert_alpha()
        return img
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill((0,0,0,0))
        pygame.draw.rect(surf, (180,180,255), surf.get_rect(), border_radius=6)
        return surf

def clamp(n, a, b): return max(a, min(b, n))

# ---------- Entities ----------
class Player:
    def __init__(self):
        # try to load sprite, else we draw
        self.sprite = load_image("player.png", fallback_size=(64,48))
        self.w, self.h = self.sprite.get_width(), self.sprite.get_height()
        self.x = WIDTH//2 - self.w//2
        self.y = HEIGHT - self.h - 12
        self.speed = 6.5
        self.color = (50,180,255)
        # firing
        self.last_shot = 0
        self.cooldown = BULLET_COOLDOWN_MS
        self.double_shot = False
        self.double_timer = 0
        # slow effect immune placeholder
        self.lives = 3
        self.score = 0
        self.alive = True
        self.invincible_until = 0  # ms timestamp
    
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)
    
    def draw(self, surf):
        # flash if near death? for now normal draw
        surf.blit(self.sprite, (self.x, self.y))
        # draw small thruster flame animation
        t = pygame.time.get_ticks() // 120
        flame_h = 6 + (t % 3)
        flame_rect = pygame.Rect(self.x + self.w//2 - 6, self.y + self.h - 4, 12, flame_h)
        pygame.draw.rect(surf, (255,180,50), flame_rect)
    
    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot >= self.cooldown
    
    def shoot(self, bullets_list):
        now = pygame.time.get_ticks()
        if not self.can_shoot(): return False
        self.last_shot = now
        cx = self.x + self.w//2
        if self.double_shot:
            # fire two bullets slightly off-center
            bullets_list.append(Bullet(cx - 14, self.y + 8, -10))
            bullets_list.append(Bullet(cx + 14, self.y + 8, -10))
        else:
            bullets_list.append(Bullet(cx, self.y + 8, -12))
        if sound_shot: sound_shot.play()
        return True

class Bullet:
    def __init__(self, x, y, vy=-12, color=(255,255,80), radius=6, owner="player"):
        self.x = x
        self.y = y
        self.vy = vy
        self.color = color
        self.radius = radius
        self.owner = owner  # "player" or "enemy"
        self.alive = True
    
    def update(self, dt):
        self.y += self.vy * (dt/16)
        if self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False
    
    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.radius)
        # trail
        for i in range(3):
            alpha = max(0, 150 - i*40)
            s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.radius, self.radius), max(1, self.radius - i*2))
            surf.blit(s, (self.x - self.radius, self.y - self.radius + i*2))

class Enemy:
    def __init__(self, x=None, y=None, speed=1.5, size=36, hp=1):
        self.w = size
        self.h = size
        self.x = random.randint(20, WIDTH - 20) if x is None else x
        self.y = -random.randint(20, 140) if y is None else y
        self.speed = speed
        self.color = (220,60,60)
        self.hp = hp
        self.alive = True
        self.sway_offset = random.random() * 2000
        self.osc_amp = random.uniform(10, 40)
    
    def rect(self):
        return pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)
    
    def update(self, dt, slowed=False):
        mult = 0.35 if slowed else 1.0
        # vertical movement
        self.y += self.speed * mult * (dt/16)
        # horizontal subtle oscillation
        osc = math.sin((pygame.time.get_ticks() + self.sway_offset)/400.0) * self.osc_amp
        self.x += osc * 0.02 * (dt/16)
        if self.y > HEIGHT + 80:
            self.alive = False
    
    def draw(self, surf):
        r = self.rect()
        pygame.draw.rect(surf, self.color, r, border_radius=6)
        # small eyes
        pygame.draw.circle(surf, (20,20,20), (int(self.x-8), int(self.y-6)), 4)
        pygame.draw.circle(surf, (20,20,20), (int(self.x+8), int(self.y-6)), 4)

class Boss:
    def __init__(self, level):
        self.w = 220
        self.h = 110
        self.x = WIDTH//2
        self.y = -150
        self.speed = 0.6 + level * 0.15
        self.alive = True
        self.hp = 6 + level*3
        self.angle = 0
        self.spawned_at = pygame.time.get_ticks()
        self.last_shot = 0
        self.shoot_interval = max(400, 900 - level*40)
        # pattern queue: spits bullets in radial bursts
        self.color = (160, 40, 200)
    
    def rect(self): return pygame.Rect(self.x - self.w//2, self.y - self.h//2, self.w, self.h)
    
    def update(self, dt):
        # enter screen then start moving laterally
        if self.y < 120:
            self.y += self.speed * (dt/16)
        else:
            # lateral oscillation once entered
            self.x = (WIDTH//2) + math.sin(pygame.time.get_ticks()/800.0) * 200
    
    def draw(self, surf):
        r = self.rect()
        pygame.draw.ellipse(surf, self.color, r)
        # HP bar
        hp_ratio = max(0, self.hp) / (6)
        bar_w = int((self.w-20) * (self.hp / (6 + 3*current_level)))
        pygame.draw.rect(surf, (60,60,60), (r.x+10, r.y-12, self.w-20, 8))
        pygame.draw.rect(surf, (255,50,50), (r.x+10, r.y-12, max(0, bar_w), 8))
    
    def can_shoot(self):
        return pygame.time.get_ticks() - self.last_shot >= self.shoot_interval
    
    def shoot(self, bullets_list):
        # radial burst of bullets
        n = 10
        for i in range(n):
            ang = i * (2*math.pi / n) + (pygame.time.get_ticks()%1000)/700.0
            vx = math.cos(ang) * 4.5
            vy = math.sin(ang) * 4.5
            b = Bullet(self.x, self.y + self.h//2 - 10, vy=vy*1.5, color=(255,120,60), radius=6, owner="enemy")
            # override x motion via vy only: we simulate by setting vx into x via property hack: put vx into b.vx
            b.vx = vx
            bullets_list.append(b)
        self.last_shot = pygame.time.get_ticks()
        if sound_boss: sound_boss.play()

# ---------- Power-ups ----------
class PowerUp:
    def __init__(self, kind=None):
        self.size = 28
        self.x = random.randint(30, WIDTH-30)
        self.y = -50
        self.vel = 2.4
        self.kind = random.choice(["double","slow","life"]) if kind is None else kind
        self.alive = True
        self.spawned = pygame.time.get_ticks()
    
    def rect(self): return pygame.Rect(self.x, self.y, self.size, self.size)
    
    def update(self, dt):
        self.y += self.vel * (dt/16)
        if self.y > HEIGHT + 60:
            self.alive = False
    
    def draw(self, surf):
        colors = {"double":(255,200,60), "slow":(100,255,150), "life":(255,120,180)}
        pygame.draw.rect(surf, colors[self.kind], self.rect(), border_radius=6)
        # symbol
        txt = {"double":"II", "slow":"Zz", "life":"♥"}
        label = font_small.render(txt[self.kind], True, (20,20,20))
        surf.blit(label, (self.x + 6, self.y + 4))

# ---------- Explosion animation ----------
class Explosion:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.start = pygame.time.get_ticks()
        self.duration = 500
        self.alive = True
    def update(self, dt):
        if pygame.time.get_ticks() - self.start > self.duration:
            self.alive = False
    def draw(self, surf):
        t = (pygame.time.get_ticks() - self.start) / self.duration
        if t > 1: t = 1
        r = int(8 + t * 40)
        alpha = int(255 * (1-t))
        s = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255,150,60,alpha), (r,r), r)
        surf.blit(s, (self.x - r, self.y - r))

# ---------- Game state ----------
player = Player()
bullets = []        # all bullets
enemies = []
powerups = []
explosions = []
boss = None
current_level = 1
spawn_rate = INITIAL_SPAWN_RATE_MS
last_spawn_time = pygame.time.get_ticks()
enemy_speed = ENEMY_BASE_SPEED
enemies_killed = 0

# ---------- Helper functions ----------
def spawn_enemy():
    e = Enemy(speed=enemy_speed, size=random.randint(28,44), hp=1)
    enemies.append(e)
    # maybe spawn powerup
    if random.random() < POWERUP_CHANCE:
        powerups.append(PowerUp())

def spawn_boss_for_level(lvl):
    global boss
    boss = Boss(lvl)
    if sound_boss: sound_boss.play()

def draw_hud():
    # score lives level
    score_s = font_small.render(f"Score: {player.score}", True, (255,255,255))
    lives_s = font_small.render(f"Lives: {player.lives}", True, (255,255,255))
    level_s = font_small.render(f"Level: {current_level}", True, (255,255,255))
    screen.blit(score_s, (12, 10))
    screen.blit(lives_s, (12, 36))
    screen.blit(level_s, (12, 62))
    # cooldown bar
    cd = clamp((pygame.time.get_ticks() - player.last_shot) / max(1, player.cooldown), 0, 1)
    pygame.draw.rect(screen, (60,60,60), (WIDTH-160, 18, 140, 12), border_radius=6)
    pygame.draw.rect(screen, (80,200,120), (WIDTH-160, 18, int(140*cd), 12), border_radius=6)
    screen.blit(font_small.render("Weapon CD", True, (220,220,220)), (WIDTH-160, 34))

# ---------- Main loop ----------
running = True
paused = False
game_over = False
boss_alert_until = 0

while running:
    dt = clock.tick(FPS)
    now = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                paused = not paused
            if event.key == pygame.K_r and game_over:
                # reset basic state
                player = Player()
                bullets = []; enemies=[]; powerups=[]; explosions=[]
                boss = None; current_level = 1; spawn_rate = INITIAL_SPAWN_RATE_MS
                enemy_speed = ENEMY_BASE_SPEED; enemies_killed = 0; game_over = False
    
    if paused or game_over:
        # draw freeze screen
        screen.fill((12,12,22))
        draw_hud()
        if game_over:
            txt = font_big.render("GAME OVER - Press R to Restart", True, (255,120,120))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 30))
        else:
            txt = font_big.render("PAUSED - Press P to Resume", True, (180,180,255))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 30))
        pygame.display.flip()
        continue

    # ---------- Input & player control ----------
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player.x -= player.speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player.x += player.speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player.y -= player.speed * 0.6
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player.y += player.speed * 0.6
    # clamp player
    player.x = clamp(player.x, 6, WIDTH - player.w - 6)
    player.y = clamp(player.y, HEIGHT//2, HEIGHT - player.h - 6)

    # shooting (space)
    if keys[pygame.K_SPACE]:
        player.shoot(bullets)

    # ---------- Spawning logic ----------
    if boss is None and now - last_spawn_time >= spawn_rate:
        spawn_enemy()
        last_spawn_time = now

    # level up logic
    # increase difficulty every N kills
    target_for_level = 7 + (current_level-1)*3
    if enemies_killed >= target_for_level:
        current_level += 1
        enemies_killed = 0
        # make spawn faster and enemies faster
        spawn_rate = max(MIN_SPAWN_RATE_MS, spawn_rate - SPAWN_DECREASE_PER_LEVEL)
        enemy_speed += ENEMY_SPEED_INCREASE_PER_LEVEL
        # boss spawn condition
        if current_level % BOSS_EVERY_N_LEVELS == 0:
            spawn_boss_for_level(current_level)
            boss_alert_until = now + 2200

    # ---------- Update enemies ----------
    slowed = False
    # Check if slow powerup active: use player's double_shot_timer for simplicity? We'll manage separate timers
    # We will keep a simple list of active slow effects (timestamp)
    # For brevity, check if global slow_active flag exists:
    # implement as: any powerup with kind 'slow' applied will set slowed_until variable
    if 'slowed_until' in globals() and globals()['slowed_until'] > now:
        slowed = True

    for e in enemies[:]:
        e.update(dt, slowed=slowed)
        if not e.alive:
            enemies.remove(e)
            continue

    # ---------- Update boss ----------
    if boss:
        boss.update(dt)
        # boss shooting
        if boss.can_shoot():
            boss.shoot(bullets)
        # boss death
        if boss.hp <= 0:
            explosions.append(Explosion(boss.x, boss.y))
            if sound_explosion: sound_explosion.play()
            player.score += 400 + current_level*50
            boss = None
            # reward nice powerups
            powerups.append(PowerUp(kind='life'))
            spawn_rate = max(MIN_SPAWN_RATE_MS, spawn_rate - 200)
            enemy_speed += 0.6

    # ---------- Update bullets ----------
    for b in bullets[:]:
        # boss bullets might have b.vx property
        if hasattr(b, 'vx'):
            b.x += b.vx * (dt/16)
        b.update(dt)
        if not b.alive:
            bullets.remove(b)

    # ---------- Update powerups ----------
    for p in powerups[:]:
        p.update(dt)
        if not p.alive:
            powerups.remove(p)

    # ---------- Update explosions ----------
    for ex in explosions[:]:
        ex.update(dt)
        if not ex.alive:
            explosions.remove(ex)

    # ---------- Collisions: bullets vs enemies ----------
    for b in bullets[:]:
        if b.owner == "player":
            # with regular enemies
            for e in enemies[:]:
                if e.rect().collidepoint(b.x, b.y):
                    # hit
                    e.hp -= 1
                    b.alive = False
                    explosions.append(Explosion(b.x, b.y))
                    if sound_explosion: sound_explosion.play()
                    if e.hp <= 0:
                        try:
                            enemies.remove(e)
                        except ValueError:
                            pass
                        player.score += 10
                        enemies_killed += 1
                        # small chance to drop a powerup handled at spawn time
                    break
            # with boss
            if boss and boss.rect().collidepoint(b.x, b.y):
                boss.hp -= 1
                b.alive = False
                explosions.append(Explosion(b.x, b.y))
                if sound_explosion: sound_explosion.play()

    # ---------- Collisions: enemy bullets vs player ----------
    for b in bullets[:]:
        if b.owner == "enemy":
            if player.rect().collidepoint(b.x, b.y):
                b.alive = False
                explosions.append(Explosion(player.x + player.w//2, player.y + player.h//2))
                if sound_explosion: sound_explosion.play()
                if now > player.invincible_until:
                    player.lives -= 1
                    player.invincible_until = now + 1200
                    if player.lives <= 0:
                        game_over = True

    # ---------- Collisions: player vs enemies (ram) ----------
    for e in enemies[:]:
        if e.rect().colliderect(player.rect()) and now > player.invincible_until:
            explosions.append(Explosion(e.x, e.y))
            try: enemies.remove(e)
            except: pass
            player.lives -= 1
            player.invincible_until = now + 1200
            if sound_explosion: sound_explosion.play()
            if player.lives <= 0:
                game_over = True

    # ---------- Collisions: player collects powerup ----------
    for p in powerups[:]:
        if p.rect().colliderect(player.rect()):
            if p.kind == "double":
                player.double_shot = True
                player.double_timer = now
            elif p.kind == "slow":
                globals()['slowed_until'] = now + SLOW_DURATION_MS
            elif p.kind == "life":
                player.lives += 1
            powerups.remove(p)
            if sound_power: sound_power.play()

    # ---------- Timeout for double shot ----------
    if player.double_shot and now - player.double_timer > DOUBLE_SHOT_DURATION_MS:
        player.double_shot = False

    # ---------- Draw ----------
    screen.fill((8, 10, 22))
    # background stars
    for i in range(60):
        sx = (i*47 + (now//6)) % WIDTH
        sy = (i*31 + (now//12)) % HEIGHT
        screen.set_at((sx, sy), (40,40,90))

    # draw player
    player.draw(screen)
    # draw enemies
    for e in enemies:
        e.draw(screen)
    # draw boss
    if boss:
        boss.draw(screen)
    # draw bullets
    for b in bullets:
        b.draw(screen)
    # draw powerups
    for p in powerups:
        p.draw(screen)
    # draw explosions
    for ex in explosions:
        ex.draw(screen)

    # boss alert
    if boss and now < boss_alert_until:
        a = font_big.render("BOSS INCOMING!", True, (255,80,80))
        screen.blit(a, (WIDTH//2 - a.get_width()//2, 20 + math.sin(now/200.0)*6))

    draw_hud()

    # small tips
    tip = font_small.render("Arrows / WASD to move, SPACE to shoot. P pause. Double-shot & Slow & Extra-life powerups!", True, (200,200,220))
    screen.blit(tip, (12, HEIGHT-28))

    pygame.display.flip()

pygame.quit()
