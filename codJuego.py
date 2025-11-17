# codJuego.py
import pygame
import random
import sys
import math
from typing import Tuple, List

# ------------------------------
# CONFIGURACIÓN GLOBAL
# ------------------------------
SCREEN_W, SCREEN_H = 1000, 600
FPS = 60

# debug
DEBUG_DRAW_CONTACT = True

# Tiles / estética
TILE_SIZE = 64
INITIAL_TILES = 200
TERRAIN_Y = 420

# Jugador
PLAYER_SCREEN_X = 150
CAR_SCALE = 0.35  # escala del sprite si existe
PLAYER_CENTER_Y_OFFSET = -10  # ajuste fino para centrar el coche respecto al tile

# Juego / movimiento
PLAYER_MAX_SPEED = 420.0  # px/s velocidad máxima
PLAYER_ACC = 900.0        # px/s^2 aceleración cuando presionas D
PLAYER_BRAKE = 1400.0     # px/s^2 cuando presionas A para retroceder
FRICTION = 0.9            # fricción pasiva (para estabilizar)
CAMERA_LEAD = 200         # cuánto adelantamos la cámara respecto al jugador

# Fuel y moneda
MAX_FUEL = 100.0
FUEL_DECAY_PER_SEC = 2.0
FUEL_PICKUP = 30.0
COIN_SPAWN_CHANCE = 0.12
FUEL_SPAWN_CHANCE = 0.06
NOS_SPAWN_CHANCE = 0.015
NOS_DURATION = 6.0
NOS_MULTIPLIER = 1.8
COLLECTIBLE_MIN_SEPARATION_TILES = 4
COIN_MIN_SEPARATION_TILES = 2
COLLECTIBLE_VERTICAL_OFFSET = -100

# Sonidos / volúmenes
MUSIC_VOL = 0.20
SFX_VOL = 0.8

# ------------------------------
# UTILIDADES: carga robusta de recursos
# ------------------------------
def load_image(path: str, size: Tuple[int, int] = None, alpha=True, fallback_color=(160,120,60)):
    try:
        if alpha:
            img = pygame.image.load(path).convert_alpha()
        else:
            img = pygame.image.load(path).convert()
        if size:
            img = pygame.transform.scale(img, size)
        return img
    except Exception:
        # fallback surface (visual pero no crashea)
        surf = pygame.Surface(size if size else (64,64), pygame.SRCALPHA if alpha else 0)
        surf.fill(fallback_color)
        pygame.draw.rect(surf, (0,0,0), surf.get_rect(), 2)
        return surf

def load_sound(path: str):
    try:
        s = pygame.mixer.Sound(path)
        s.set_volume(SFX_VOL)
        return s
    except Exception:
        class Silent:
            def play(self, *a, **k): pass
            def set_volume(self, *a, **k): pass
        return Silent()

def load_music(path: str):
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOL)
        return True
    except Exception:
        return False

# ------------------------------
# SPRITES: Collectible simple
# ------------------------------
class Collectible(pygame.sprite.Sprite):
    def __init__(self, world_x: float, world_y: float, image: pygame.Surface, kind: str):
        super().__init__()
        self.base_image = image
        self.image = image
        self.rect = self.image.get_rect()
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.kind = kind  # 'coin' | 'fuel' | 'nos'
        self.collected = False
        self._anim = random.random() * 10.0

    def update_screen_pos(self, camera_x: float):
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)
        self.rect.topleft = (sx, sy)

    def animate(self, dt: float):
        if self.kind == 'coin':
            self._anim += 3.5 * dt
            offset = int(6 * (0.5 + 0.5 * math.sin(self._anim)))
            self.rect = self.image.get_rect()
            # rect updated when drawing

    def draw(self, surface: pygame.Surface, camera_x: float):
        sx = int(self.world_x - camera_x)
        sy = int(self.world_y)
        if self.kind == 'coin':
            offset = int(6 * (0.5 + 0.5 * math.sin(self._anim)))
            surface.blit(self.image, (sx, sy - offset))
        else:
            surface.blit(self.image, (sx, sy))

    def collect(self):
        self.collected = True
        self.kill()

# ------------------------------
# TERRAIN procedural suave
# ------------------------------
class Terrain:
    def __init__(self, tile_size:int, initial_tiles:int, base_y:int, ground_img:pygame.Surface):
        self.tile_size = tile_size
        self.base_y = base_y
        # Usamos lista de alturas por tile (cada tile representa la Y del tope)
        self.tiles = [self.base_y for _ in range(initial_tiles)]
        self.ground_img = ground_img
        # Generamos con un método suave
        self.generate_initial_smooth(initial_tiles)

    def generate_initial_smooth(self, initial_tiles):
        # Genera usando ondas sin + suave jitter para evitar saltos
        self.tiles = []
        amplitude = 60
        freq = 0.008
        base = self.base_y
        for i in range(initial_tiles):
            x = i * self.tile_size
            y = base + math.sin(i * freq * 2*math.pi) * amplitude + math.sin(i*0.02) * 12
            y += random.randint(-3, 3)
            self.tiles.append(int(y))

    def ensure_tiles(self, idx: int):
        if idx < len(self.tiles):
            return
        # Generar por chunks
        while len(self.tiles) <= idx:
            self.generate_chunk(80)

    def generate_chunk(self, count:int):
        # Genera tiles continuos con cambios suaves
        cur_len = len(self.tiles)
        for i in range(count):
            idx = cur_len + i
            # combinamos ondas de distinta frecuencia + pequeño noise
            amplitude = 70
            freq = 0.006
            y = self.base_y + math.sin(idx * freq * 2*math.pi) * amplitude
            y += math.sin(idx * 0.02) * 18
            y += random.randint(-3, 3)
            # suavizar con último valor
            if self.tiles:
                prev = self.tiles[-1]
                # limitar cambio por tile
                max_change = 12
                y = int(max(min(prev + max_change, y), prev - max_change))
            self.tiles.append(int(y))

    def tile_y_at_pixel_x(self, world_x_px:int) -> int:
        tile_idx = max(0, world_x_px // self.tile_size)
        if tile_idx >= len(self.tiles):
            self.ensure_tiles(tile_idx)
        return self.tiles[tile_idx]

    def terrain_interpolated_y(self, world_x_px: int) -> int:
        tile_idx = max(0, world_x_px // self.tile_size)
        if tile_idx + 1 >= len(self.tiles):
            self.ensure_tiles(tile_idx + 1)
        y0 = self.tiles[tile_idx]
        y1 = self.tiles[tile_idx + 1]
        t = (world_x_px % self.tile_size) / self.tile_size
        interpolated_y = y0 + (y1 - y0) * t
        return int(interpolated_y)

    def draw(self, surf:pygame.Surface, camera_x:float, street_img: pygame.Surface = None):
        screen_tile_start = int(camera_x) // self.tile_size
        offset_x = int(camera_x) % self.tile_size
        tiles_on_screen = surf.get_width() // self.tile_size + 3

        for i in range(tiles_on_screen):
            tile_idx = screen_tile_start + i
            if tile_idx >= len(self.tiles):
                # generar un chunk
                self.generate_chunk(50)
            ty = self.tiles[tile_idx]
            screen_x = i * self.tile_size - offset_x

            # top tile (puede ser calle o tierra)
            top_img = street_img if (street_img is not None and tile_idx < 20) else self.ground_img
            surf.blit(top_img, (screen_x, ty))

            # dibujar repetidamente abajo para cubrir pantalla
            y = ty + self.tile_size
            while y < surf.get_height():
                surf.blit(self.ground_img, (screen_x, y))
                y += self.tile_size

# ------------------------------
# CAR BODY simple (sin rotación)
# ------------------------------
class CarBody:
    def __init__(self, base_image: pygame.Surface):
        self.base_image = base_image
        self.image = base_image
        self.rect = self.image.get_rect()

    def set_screen_pos(self, screen_x: int, screen_y: int):
        # establece rect topleft tomando como referencia la esquina superior izquierda
        self.rect.topleft = (screen_x - self.rect.width // 2, screen_y - self.rect.height // 2)

# ------------------------------
# PLAYER (sin rotación, sigue terreno)
# ------------------------------
class Player:
    def __init__(self, screen_x:int, car_body:CarBody):
        self.screen_x = screen_x
        self.car_body = car_body
        # world_x es la posición real en el mundo (px)
        self.world_x = float(screen_x)
        # world_y sirve para lógica pero el dibujo usa la Y del terreno
        self.world_y = float(TERRAIN_Y)
        self.velocity_x = 0.0
        self.coins = 0
        self.fuel = MAX_FUEL
        self.nos_time_left = 0.0
        self.speed_multiplier = 1.0

    def update(self, dt: float, keys: List[bool], terrain: Terrain):
        # NOS
        if self.nos_time_left > 0:
            self.nos_time_left -= dt
            self.speed_multiplier = NOS_MULTIPLIER
        else:
            self.speed_multiplier = 1.0

        # Entradas
        accel = 0.0
        if keys[pygame.K_d]:
            accel += 1.0
        if keys[pygame.K_a]:
            accel -= 1.0

        # Aplicar fuerzas horizontales (no hay gravedad vertical compleja)
        if accel > 0:
            self.velocity_x += PLAYER_ACC * accel * dt * self.speed_multiplier
        elif accel < 0:
            self.velocity_x += PLAYER_BRAKE * accel * dt  # accel negative reduces speed quickly
        else:
            # fricción natural
            self.velocity_x *= (FRICTION ** dt)

        # limitar velocidad
        max_speed = PLAYER_MAX_SPEED * self.speed_multiplier
        if self.velocity_x > max_speed:
            self.velocity_x = max_speed
        if self.velocity_x < -max_speed * 0.3:
            self.velocity_x = -max_speed * 0.3  # backwards limited

        # consumir fuel si se acelera hacia adelante
        if self.fuel > 0 and accel > 0:
            self.fuel -= FUEL_DECAY_PER_SEC * dt * accel * (1.0 if self.speed_multiplier == 1.0 else 1.5)
            if self.fuel < 0:
                self.fuel = 0.0

        # actualizar posición en el mundo
        self.world_x += self.velocity_x * dt

        # aseguramos que world_x no sea menor que 0
        if self.world_x < self.screen_x:
            self.world_x = self.screen_x
            self.velocity_x = 0.0

        # ajustar world_y a la Y del terreno (snap)
        terrain_y = terrain.terrain_interpolated_y(int(self.world_x))
        self.world_y = float(terrain_y)

    def draw(self, surf: pygame.Surface, camera_x: float, terrain: Terrain):
        # calcular screen Y usando la interpolación del terreno
        sx = int(self.screen_x)
        world_center_x = int(self.world_x)
        terrain_y = terrain.terrain_interpolated_y(world_center_x)
        # colocamos el coche un poco por encima del terreno (offset)
        car_draw_y = terrain_y - self.car_body.rect.height // 2 + PLAYER_CENTER_Y_OFFSET
        self.car_body.set_screen_pos(sx, car_draw_y + self.car_body.rect.height // 2)
        surf.blit(self.car_body.image, self.car_body.rect.topleft)

        # debug: punto de contacto
        if DEBUG_DRAW_CONTACT:
            contact_screen_y = car_draw_y + self.car_body.rect.height - PLAYER_CENTER_Y_OFFSET
            pygame.draw.circle(surf, (255, 0, 0), (sx, contact_screen_y), 4)

# ------------------------------
# HUD y controles simples
# ------------------------------
class HUD:
    def __init__(self, font:pygame.font.Font):
        self.font = font

    def draw(self, surf:pygame.Surface, player: Player):
        # Monedas
        txt = self.font.render(f"Monedas: {player.coins}", True, (255,215,0))
        surf.blit(txt, (20, 20))
        # Distancia (en metros aproximados)
        dist_txt = self.font.render(f"Distancia: {int(player.world_x / 100)}m", True, (255,255,255))
        surf.blit(dist_txt, (SCREEN_W - dist_txt.get_width() - 20, 20))

        # Barra de fuel
        bx, by, bw, bh = 20, 60, 220, 20
        pygame.draw.rect(surf, (0,0,0), (bx, by, bw, bh), 2)
        fill = int((player.fuel / MAX_FUEL) * (bw - 4))
        col = (255, 60, 60) if player.fuel < 30 else (0,160,0)
        pygame.draw.rect(surf, col, (bx + 2, by + 2, fill, bh - 4))
        perc = self.font.render(f"{int(player.fuel)}%", True, (255,255,255))
        surf.blit(perc, (bx + bw + 10, by - 1))

        # NOS
        if player.nos_time_left > 0:
            nos_txt = self.font.render(f"NOS: {int(player.nos_time_left)}s", True, (120,200,255))
            surf.blit(nos_txt, (20, 90))

# ------------------------------
# GAME principal
# ------------------------------
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except Exception:
            pass
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Hill Drive - Simple (Auto sin rotación)")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)

        # assets (carga con fallback)
        self.sky = load_image("assets/sky.png", (SCREEN_W * 2, SCREEN_H), alpha=False, fallback_color=(120,200,255))
        self.ground = load_image("assets/ground.png", (TILE_SIZE, TILE_SIZE), alpha=False, fallback_color=(160,100,50))
        self.street_img = load_image("assets/calle.png", (TILE_SIZE, TILE_SIZE), alpha=False, fallback_color=(120,120,120))

        # Coche: cargado y escalado desde lancer.png
        car_original_img = load_image("assets/lancer.png", size=None, alpha=True, fallback_color=(220,220,220))
        try:
            ow, oh = car_original_img.get_size()
            tw = max(1, int(ow * CAR_SCALE))
            th = max(1, int(oh * CAR_SCALE))
            self.car_img = pygame.transform.scale(car_original_img, (tw, th))
        except Exception:
            self.car_img = car_original_img

        # crear una versión alternativa si la imagen no tiene el tamaño esperado
        if self.car_img.get_width() > 300:
            # escalar a un ancho razonable
            self.car_img = pygame.transform.scale(self.car_img, (int(self.car_img.get_width()*0.4), int(self.car_img.get_height()*0.4)))

        self.coin_img = load_image("assets/coin.png", (36,36), alpha=True, fallback_color=(240,220,20))
        self.nos_img = load_image("assets/nos.png", (40,40), alpha=True, fallback_color=(120,200,255))
        self.fuel_img = load_image("assets/fuel.png", (40,40), alpha=True, fallback_color=(200,0,0))

        # sonidos con fallback silencioso
        self.sfx_pick = load_sound("assets/sfx_pickup.wav")
        self.sfx_gameover = load_sound("assets/sfx_gameover.wav")
        if load_music("assets/music.ogg"):
            try:
                pygame.mixer.music.play(-1)
            except Exception:
                pass

        # instancias de mundo
        self.terrain = Terrain(TILE_SIZE, INITIAL_TILES, TERRAIN_Y, self.ground)
        self.car_body = CarBody(self.car_img)
        self.player = Player(PLAYER_SCREEN_X, self.car_body)
        self.hud = HUD(self.font)
        self.camera_x = 0.0

        # collectibles
        self.collectibles = pygame.sprite.Group()
        self.collectible_tiles = set()
        self.last_collectible_tile = -999
        self.last_coin_tile = -999
        self.spawn_initial_collectibles()

        # estado
        self.running = True
        self.game_over = False

    def spawn_initial_collectibles(self):
        self.collectibles.empty()
        self.collectible_tiles.clear()
        self.last_collectible_tile = -999
        self.last_coin_tile = -999

        # spawn a lo largo de los primeros tiles
        end = min(len(self.terrain.tiles), 400)
        for tile_idx in range(10, end):
            spawned = False
            if tile_idx - self.last_coin_tile >= COIN_MIN_SEPARATION_TILES and random.random() < COIN_SPAWN_CHANCE:
                wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
                wy = self.terrain.terrain_interpolated_y(wx) + COLLECTIBLE_VERTICAL_OFFSET
                c = Collectible(wx, wy, self.coin_img, 'coin')
                self.collectibles.add(c)
                self.collectible_tiles.add(tile_idx)
                self.last_coin_tile = tile_idx
                self.last_collectible_tile = tile_idx
                spawned = True
            elif tile_idx - self.last_collectible_tile >= COLLECTIBLE_MIN_SEPARATION_TILES:
                wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
                wy = self.terrain.terrain_interpolated_y(wx) + COLLECTIBLE_VERTICAL_OFFSET
                if random.random() < NOS_SPAWN_CHANCE:
                    c = Collectible(wx, wy, self.nos_img, 'nos')
                    self.collectibles.add(c)
                    self.collectible_tiles.add(tile_idx)
                    self.last_collectible_tile = tile_idx
                    spawned = True
                elif random.random() < FUEL_SPAWN_CHANCE:
                    c = Collectible(wx, wy, self.fuel_img, 'fuel')
                    self.collectibles.add(c)
                    self.collectible_tiles.add(tile_idx)
                    self.last_collectible_tile = tile_idx
                    spawned = True

    def spawn_collectible_at_tile(self, tile_idx:int):
        if tile_idx in self.collectible_tiles:
            return
        last_collect = self.last_collectible_tile
        last_coin = self.last_coin_tile
        wx = tile_idx * TILE_SIZE + TILE_SIZE // 2
        if tile_idx + 1 >= len(self.terrain.tiles):
            self.terrain.ensure_tiles(tile_idx + 1)
        wy = self.terrain.terrain_interpolated_y(wx) + COLLECTIBLE_VERTICAL_OFFSET

        spawned = False
        kind = None
        if tile_idx - last_coin >= COIN_MIN_SEPARATION_TILES and random.random() < COIN_SPAWN_CHANCE:
            kind = 'coin'
            self.last_coin_tile = tile_idx
            self.last_collectible_tile = tile_idx
            spawned = True
        elif tile_idx - last_collect >= COLLECTIBLE_MIN_SEPARATION_TILES:
            if random.random() < NOS_SPAWN_CHANCE:
                kind = 'nos'
                self.last_collectible_tile = tile_idx
                spawned = True
            elif random.random() < FUEL_SPAWN_CHANCE:
                kind = 'fuel'
                self.last_collectible_tile = tile_idx
                spawned = True

        if spawned:
            img = self.coin_img
            if kind == 'fuel':
                img = self.fuel_img
            elif kind == 'nos':
                img = self.nos_img
            c = Collectible(wx, wy, img, kind)
            self.collectibles.add(c)
            self.collectible_tiles.add(tile_idx)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif self.game_over and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.restart()
                elif event.key == pygame.K_q:
                    self.running = False

    def restart(self):
        self.game_over = False
        self.camera_x = 0.0
        self.player.world_x = self.player.screen_x
        self.player.world_y = TERRAIN_Y
        self.player.velocity_x = 0.0
        self.player.coins = 0
        self.player.fuel = MAX_FUEL
        self.player.nos_time_left = 0.0
        self.spawn_initial_collectibles()

    def update(self, dt:float):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.terrain)

        # actualizar cámara centrada con adelanto
        target_cam = self.player.world_x - self.player.screen_x + CAMERA_LEAD
        if target_cam < 0:
            target_cam = 0
        # suavizado simple
        self.camera_x += (target_cam - self.camera_x) * min(1.0, 6.0 * dt)

        # generar terreno y coleccionables por delante
        camera_tile = int(self.camera_x) // TILE_SIZE
        desired_ahead_tiles = (SCREEN_W // TILE_SIZE) + 12
        desired_len = camera_tile + desired_ahead_tiles + 200
        if len(self.terrain.tiles) < desired_len:
            old_len = len(self.terrain.tiles)
            to_gen = desired_len - old_len
            self.terrain.generate_chunk(to_gen)
            for t in range(old_len, len(self.terrain.tiles)):
                # spawn con probabilidad (no en todos)
                if random.random() < 0.08:
                    self.spawn_collectible_at_tile(t)

        # actualizar collectibles: animar, update screen pos, colisiones
        for c in list(self.collectibles):
            c.animate(dt)
            c.update_screen_pos(self.camera_x)

            # eliminar si muy atrasado
            if c.world_x + 300 < self.camera_x:
                try:
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.kill()
                continue

            # rect de colisión: lo situamos cerca del centro del coche
            player_screen_rect = self.player.car_body.rect.copy()
            # actualizar player rect a su lugar actual
            # (aseguramos que draw() fue llamado al menos una vez; si no, actualizamos manualmente)
            sx = int(self.player.screen_x)
            terrain_y = self.terrain.terrain_interpolated_y(int(self.player.world_x))
            car_draw_y = terrain_y - self.player.car_body.rect.height // 2 + PLAYER_CENTER_Y_OFFSET
            player_screen_rect.topleft = (sx - player_screen_rect.width // 2, car_draw_y)

            if player_screen_rect.colliderect(c.rect):
                if c.kind == 'coin':
                    self.player.coins += 1
                elif c.kind == 'fuel':
                    self.player.fuel = min(MAX_FUEL, self.player.fuel + FUEL_PICKUP)
                elif c.kind == 'nos':
                    self.player.nos_time_left = NOS_DURATION

                try:
                    self.sfx_pick.play()
                    tidx = int(c.world_x) // TILE_SIZE
                    self.collectible_tiles.discard(tidx)
                except Exception:
                    pass
                c.collect()

        # game over si sin fuel y velocidad 0
        if self.player.fuel <= 0:
            if not self.game_over:
                try:
                    self.sfx_gameover.play()
                except Exception:
                    pass
            self.game_over = True

    def draw(self):
        # sky parallax
        sky_scroll = int(-self.camera_x * 0.1) % self.sky.get_width()
        self.screen.blit(self.sky, (sky_scroll, 0))
        self.screen.blit(self.sky, (sky_scroll - self.sky.get_width(), 0))

        # terreno
        self.terrain.draw(self.screen, self.camera_x, self.street_img)

        # collectibles
        for c in self.collectibles:
            c.draw(self.screen, self.camera_x)

        # jugador (draw ajusta Y al terreno)
        self.player.draw(self.screen, self.camera_x, self.terrain)

        # HUD
        self.hud.draw(self.screen, self.player)

        # game over overlay
        if self.game_over:
            overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 190))
            self.screen.blit(overlay, (0, 0))
            go_font = pygame.font.SysFont("consolas", 56, bold=True)
            go_txt = go_font.render("GAME OVER", True, (255, 60, 60))
            self.screen.blit(go_txt, (SCREEN_W // 2 - go_txt.get_width() // 2, SCREEN_H // 2 - 80))
            score_txt = self.font.render(f"Distancia: {int(self.player.world_x / 100)}m | Monedas: {self.player.coins}", True, (255,255,255))
            self.screen.blit(score_txt, (SCREEN_W // 2 - score_txt.get_width() // 2, SCREEN_H // 2 + 10))
            restart_txt = self.font.render("Presiona R para Reiniciar o Q para Salir", True, (200,200,200))
            self.screen.blit(restart_txt, (SCREEN_W // 2 - restart_txt.get_width() // 2, SCREEN_H // 2 + 60))

    def run(self):
        try:
            while self.running:
                dt_ms = self.clock.tick(FPS)
                dt = dt_ms / 1000.0
                self.handle_events()
                if not self.game_over:
                    self.update(dt)
                self.draw()
                pygame.display.flip()
        except Exception as e:
            print("Error en el loop:", e)
        finally:
            try:
                pygame.quit()
            except Exception:
                pass
            try:
                sys.exit()
            except Exception:
                pass

# ------------------------------
# INICIO
# ------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
